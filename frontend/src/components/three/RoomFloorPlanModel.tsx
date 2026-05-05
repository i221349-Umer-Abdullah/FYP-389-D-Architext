"use client";

import { memo, useMemo } from "react";
import { Edges } from "@react-three/drei";

import { GenerationRoom } from "@/lib/types";
import { getStyle, type StyleId, type StyleVisuals } from "@/lib/architectureStyles";

interface RoomFloorPlanModelProps {
  rooms: GenerationRoom[];
  styleId?: StyleId;
}

interface WallBox {
  key: string;
  x: number;
  y: number;
  z: number;
  sx: number;
  sy: number;
  sz: number;
  isSlab?: boolean;
}

function buildWalls(rooms: GenerationRoom[], vis: StyleVisuals): WallBox[] {
  if (!rooms.length) return [];

  const minX = Math.min(...rooms.map((r) => r.x));
  const minY = Math.min(...rooms.map((r) => r.y));
  const maxX = Math.max(...rooms.map((r) => r.x + r.width));
  const maxY = Math.max(...rooms.map((r) => r.y + r.height));
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  const t  = vis.wallThickness;
  const h  = vis.ceilingHeight;
  const hh = h / 2;

  const boxes: WallBox[] = [];

  rooms.forEach((room, i) => {
    const rx = room.x - cx;
    const rz = room.y - cy;
    const rw = room.width;
    const rd = room.height;

    // Floor slab
    boxes.push({
      key: `slab-${i}`,
      x: rx + rw / 2, y: -0.05, z: rz + rd / 2,
      sx: rw, sy: 0.1, sz: rd,
      isSlab: true,
    });

    // Four walls
    boxes.push({ key: `s-${i}`, x: rx + rw / 2, y: hh, z: rz,           sx: rw + t, sy: h, sz: t });
    boxes.push({ key: `n-${i}`, x: rx + rw / 2, y: hh, z: rz + rd,      sx: rw + t, sy: h, sz: t });
    boxes.push({ key: `w-${i}`, x: rx,           y: hh, z: rz + rd / 2,  sx: t, sy: h, sz: rd });
    boxes.push({ key: `e-${i}`, x: rx + rw,      y: hh, z: rz + rd / 2,  sx: t, sy: h, sz: rd });
  });

  return boxes;
}

function RoomFloorPlanModelComponent({ rooms, styleId = "modern" }: RoomFloorPlanModelProps) {
  const vis   = useMemo(() => getStyle(styleId).visuals, [styleId]);
  const walls = useMemo(() => buildWalls(rooms, vis), [rooms, vis]);

  return (
    <group>
      {walls.map((w) => (
        <mesh key={w.key} position={[w.x, w.y, w.z]} castShadow receiveShadow>
          <boxGeometry args={[w.sx, w.sy, w.sz]} />
          <meshStandardMaterial
            color={w.isSlab ? vis.slabColor : vis.wallColor}
            roughness={w.isSlab ? vis.slabRoughness : vis.wallRoughness}
            metalness={w.isSlab ? 0.15 : vis.wallMetalness}
          />
          <Edges
            color={w.isSlab ? "#F0F0F0" : vis.edgeColor}
            scale={1.001}
            threshold={15}
          />
        </mesh>
      ))}
    </group>
  );
}

export const RoomFloorPlanModel = memo(RoomFloorPlanModelComponent);
