"use client";

import { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, Edges, Html, OrbitControls } from "@react-three/drei";

import styles from "./dashboard.module.css";

type RoomBlock = {
  id: string;
  name: string;
  type: string;
  area: number;
  width: number;
  depth: number;
  height: number;
  x: number;
  z: number;
  color: string;
};

type PartBlock = {
  id: string;
  position: [number, number, number];
  size: [number, number, number];
};

type ParsedPreview =
  | { mode: "rooms"; rooms: RoomBlock[]; slabSize: [number, number, number] }
  | { mode: "parts"; parts: PartBlock[] }
  | { mode: "empty" };

type FloorPlanJsonPreviewProps = {
  data: unknown;
  title: string;
};

const roomColors = ["#dbeafe", "#dcfce7", "#fef3c7", "#fce7f3", "#e0e7ff", "#ccfbf1"];
const WALL_HEIGHT = 0.95;
const WALL_THICKNESS = 0.08;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getRecord(source: unknown, key: string) {
  if (!isRecord(source)) return null;
  const value = source[key];
  return isRecord(value) ? value : null;
}

function getArray(source: unknown, key: string) {
  if (!isRecord(source)) return null;
  const value = source[key];
  return Array.isArray(value) ? value : null;
}

function firstArray(source: unknown, keys: string[]) {
  if (!isRecord(source)) return null;

  for (const key of keys) {
    const value = source[key];

    if (Array.isArray(value)) {
      return value;
    }
  }

  return null;
}

function getFloorPlanData(data: unknown) {
  if (!isRecord(data)) return null;

  return (
    getRecord(data, "floorPlan") ??
    getRecord(data, "plan") ??
    getRecord(data, "layout") ??
    getRecord(data, "project") ??
    data
  );
}

function getString(source: Record<string, unknown>, keys: string[], fallback: string) {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }

  return fallback;
}

function getNumber(source: Record<string, unknown> | null, keys: string[], fallback: number) {
  if (!source) return fallback;

  for (const key of keys) {
    const value = source[key];
    if (typeof value === "number" && Number.isFinite(value) && value > 0) {
      return value;
    }
  }

  return fallback;
}

function getCoordinate(source: Record<string, unknown> | null, keys: string[]) {
  if (!source) return null;

  for (const key of keys) {
    const value = source[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
  }

  return null;
}

function toVector3(value: unknown): [number, number, number] | null {
  if (!Array.isArray(value) || value.length < 3) return null;

  const [x, y, z] = value;
  if (
    typeof x === "number" &&
    typeof y === "number" &&
    typeof z === "number" &&
    Number.isFinite(x) &&
    Number.isFinite(y) &&
    Number.isFinite(z)
  ) {
    return [x, y, z];
  }

  return null;
}

function parseParts(data: unknown): PartBlock[] {
  const floorPlan = getFloorPlanData(data);
  const rawParts = firstArray(floorPlan, ["parts", "models", "elements", "objects"]);

  if (!rawParts) return [];

  return rawParts.flatMap((part, index) => {
    if (!isRecord(part)) return [];

    const position = toVector3(part.position);
    const size = toVector3(part.size);

    if (!position || !size) return [];

    return [
      {
        id: getString(part, ["id", "name"], `part-${index + 1}`),
        position,
        size,
      },
    ];
  });
}

function parseRooms(data: unknown): RoomBlock[] {
  const floorPlan = getFloorPlanData(data);
  const rawRooms = firstArray(floorPlan, ["rooms", "spaces", "zones", "areas"]) ?? getArray(data, "rooms");

  if (!rawRooms) return [];

  const draftRooms = rawRooms.flatMap((room, index) => {
    if (!isRecord(room)) return [];

    const size = getRecord(room, "size");
    const position = getRecord(room, "position");
    const area = getNumber(room, ["areaSqm", "area", "area_sqm"], 12 + index * 2);
    const inferredWidth = Math.max(2.4, Math.sqrt(area * 1.15));
    const inferredDepth = Math.max(2.2, area / inferredWidth);
    const width = getNumber(size ?? room, ["width", "w"], inferredWidth);
    const depth = getNumber(size ?? room, ["depth", "height", "d"], inferredDepth);
    const explicitX = getCoordinate(position ?? room, ["x"]);
    const explicitZ = getCoordinate(position ?? room, ["z", "y"]);

    return [
      {
        id: getString(room, ["id"], `room-${index + 1}`),
        name: getString(room, ["name", "title", "label"], `Room ${index + 1}`),
        type: getString(room, ["type", "category"], "room"),
        area,
        width,
        depth,
        height: Math.max(0.34, Math.min(1.1, area / 42)),
        x: explicitX,
        z: explicitZ,
        color: roomColors[index % roomColors.length],
      },
    ];
  });

  const columns = Math.max(1, Math.ceil(Math.sqrt(draftRooms.length)));
  const maxWidth = Math.max(...draftRooms.map((room) => room.width), 3);
  const maxDepth = Math.max(...draftRooms.map((room) => room.depth), 3);
  const cellWidth = maxWidth + 0.8;
  const cellDepth = maxDepth + 0.8;

  const positioned = draftRooms.map((room, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    const centeredColumn = column - (columns - 1) / 2;
    const rowCount = Math.ceil(draftRooms.length / columns);
    const centeredRow = row - (rowCount - 1) / 2;

    return {
      ...room,
      // room.x/z are top-left corners when explicit; shift to box center for Three.js
      x: room.x !== null ? room.x + room.width / 2 : centeredColumn * cellWidth,
      z: room.z !== null ? room.z + room.depth / 2 : centeredRow * cellDepth,
    };
  });

  // Center the layout at the scene origin so all rooms sit on the slab
  const allX = positioned.map((r) => r.x);
  const allZ = positioned.map((r) => r.z);
  const cx = (Math.min(...allX) + Math.max(...allX)) / 2;
  const cz = (Math.min(...allZ) + Math.max(...allZ)) / 2;
  return positioned.map((r) => ({ ...r, x: r.x - cx, z: r.z - cz }));
}

function getSlabSize(rooms: RoomBlock[]): [number, number, number] {
  const minX = Math.min(...rooms.map((room) => room.x - room.width / 2));
  const maxX = Math.max(...rooms.map((room) => room.x + room.width / 2));
  const minZ = Math.min(...rooms.map((room) => room.z - room.depth / 2));
  const maxZ = Math.max(...rooms.map((room) => room.z + room.depth / 2));

  return [Math.max(5, maxX - minX + 1.2), 0.18, Math.max(5, maxZ - minZ + 1.2)];
}

function parsePreview(data: unknown): ParsedPreview {
  const parts = parseParts(data);

  if (parts.length) {
    return { mode: "parts", parts };
  }

  const rooms = parseRooms(data);

  if (rooms.length) {
    return { mode: "rooms", rooms, slabSize: getSlabSize(rooms) };
  }

  return { mode: "empty" };
}

export function FloorPlanJsonPreview({ data, title }: FloorPlanJsonPreviewProps) {
  const preview = useMemo(() => parsePreview(data), [data]);

  if (preview.mode === "empty") {
    return (
      <div className={styles.unsupportedPreview}>
        <p className={styles.previewMessage}>
          This JSON file does not include recognizable room or 3D part data.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.jsonPreview}>
      <div className={styles.jsonCanvasWrap}>
        <Canvas
          shadows
          dpr={[1, 1.7]}
          camera={{ position: [8, 7, 8], fov: 45 }}
          gl={{ antialias: true, alpha: true }}
        >
          <color attach="background" args={["#ffffff"]} />
          <ambientLight intensity={0.58} />
          <directionalLight castShadow intensity={1.2} position={[7, 10, 6]} />
          <directionalLight intensity={0.42} position={[-6, 5, -7]} />

          {preview.mode === "rooms" ? (
            <group>
              <mesh receiveShadow position={[0, -0.11, 0]}>
                <boxGeometry args={preview.slabSize} />
                <meshStandardMaterial color="#0a0a0a" roughness={0.65} metalness={0.08} />
              </mesh>

              {preview.rooms.map((room) => (
                <group key={room.id} position={[room.x, 0, room.z]}>
                  <mesh castShadow receiveShadow position={[0, 0.04, 0]}>
                    <boxGeometry args={[room.width, 0.08, room.depth]} />
                    <meshStandardMaterial color={room.color} roughness={0.44} metalness={0.03} />
                    <Edges color="#0a0a0a" scale={1.002} />
                  </mesh>

                  <mesh castShadow receiveShadow position={[0, WALL_HEIGHT / 2 + 0.08, -room.depth / 2]}>
                    <boxGeometry args={[room.width, WALL_HEIGHT, WALL_THICKNESS]} />
                    <meshStandardMaterial color="#f8fafc" roughness={0.31} metalness={0.04} />
                    <Edges color="#0a0a0a" scale={1.002} />
                  </mesh>

                  <mesh castShadow receiveShadow position={[0, WALL_HEIGHT / 2 + 0.08, room.depth / 2]}>
                    <boxGeometry args={[room.width, WALL_HEIGHT, WALL_THICKNESS]} />
                    <meshStandardMaterial color="#f8fafc" roughness={0.31} metalness={0.04} />
                    <Edges color="#0a0a0a" scale={1.002} />
                  </mesh>

                  <mesh castShadow receiveShadow position={[-room.width / 2, WALL_HEIGHT / 2 + 0.08, 0]}>
                    <boxGeometry args={[WALL_THICKNESS, WALL_HEIGHT, room.depth]} />
                    <meshStandardMaterial color="#f8fafc" roughness={0.31} metalness={0.04} />
                    <Edges color="#0a0a0a" scale={1.002} />
                  </mesh>

                  <mesh castShadow receiveShadow position={[room.width / 2, WALL_HEIGHT / 2 + 0.08, 0]}>
                    <boxGeometry args={[WALL_THICKNESS, WALL_HEIGHT, room.depth]} />
                    <meshStandardMaterial color="#f8fafc" roughness={0.31} metalness={0.04} />
                    <Edges color="#0a0a0a" scale={1.002} />
                  </mesh>

                  <Html center position={[0, WALL_HEIGHT + 0.32, 0]} distanceFactor={9}>
                    <span className={styles.roomLabel}>
                      {room.name}
                      <small>
                        {room.area.toFixed(room.area % 1 ? 1 : 0)} m2 {room.type}
                      </small>
                    </span>
                  </Html>
                </group>
              ))}
            </group>
          ) : null}

          {preview.mode === "parts" ? (
            <group>
              {preview.parts.map((part) => {
                const isSlab = part.id.toLowerCase().includes("slab");

                return (
                  <mesh key={part.id} castShadow={!isSlab} receiveShadow position={part.position}>
                    <boxGeometry args={part.size} />
                    <meshStandardMaterial
                      color={isSlab ? "#0a0a0a" : "#f8fafc"}
                      roughness={isSlab ? 0.62 : 0.28}
                      metalness={0.06}
                    />
                    <Edges color={isSlab ? "#f9f9f9" : "#0a0a0a"} scale={1.002} />
                  </mesh>
                );
              })}
            </group>
          ) : null}

          <ContactShadows opacity={0.24} blur={2.4} far={16} width={18} height={18} />
          <OrbitControls
            makeDefault
            enableDamping
            dampingFactor={0.08}
            minDistance={4}
            maxDistance={24}
            target={[0, 0.25, 0]}
          />
        </Canvas>
      </div>
      <p className={styles.previewCaption}>
        {title} rendered from the JSON floor-plan data. Drag to orbit, scroll to zoom.
      </p>
    </div>
  );
}
