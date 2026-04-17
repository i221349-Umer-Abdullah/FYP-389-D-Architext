"use client";

import { memo, useMemo } from "react";
import { Edges } from "@react-three/drei";

import { GenerationRoom } from "@/lib/types";

const WALL_H   = 2.7;   // metres ceiling height
const WALL_T   = 0.22;  // metres wall thickness
const WALL_CLR = "#EFEFEF";
const SLAB_CLR = "#1A1A1A";

interface RoomFloorPlanModelProps {
  rooms: GenerationRoom[];
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

function buildWalls(rooms: GenerationRoom[]): WallBox[] {
  if (!rooms.length) return [];

  // Centre the layout
  const minX = Math.min(...rooms.map((r) => r.x));
  const minY = Math.min(...rooms.map((r) => r.y));
  const maxX = Math.max(...rooms.map((r) => r.x + r.width));
  const maxY = Math.max(...rooms.map((r) => r.y + r.height));
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;

  const boxes: WallBox[] = [];

  rooms.forEach((room, i) => {
    const rx = room.x - cx;   // left edge (centred)
    const rz = room.y - cy;   // front edge (centred)
    const rw = room.width;
    const rd = room.height;
    const t  = WALL_T;
    const h  = WALL_H;
    const hh = h / 2;

    // Floor slab — thin dark rectangle
    boxes.push({
      key: `slab-${i}`,
      x: rx + rw / 2, y: -0.05, z: rz + rd / 2,
      sx: rw, sy: 0.1, sz: rd,
      isSlab: true,
    });

    // South wall (along X, front)
    boxes.push({ key: `s-${i}`, x: rx + rw / 2, y: hh, z: rz,       sx: rw + t, sy: h, sz: t });
    // North wall (along X, back)
    boxes.push({ key: `n-${i}`, x: rx + rw / 2, y: hh, z: rz + rd,  sx: rw + t, sy: h, sz: t });
    // West wall (along Z, left)
    boxes.push({ key: `w-${i}`, x: rx,           y: hh, z: rz + rd / 2, sx: t, sy: h, sz: rd });
    // East wall (along Z, right)
    boxes.push({ key: `e-${i}`, x: rx + rw,      y: hh, z: rz + rd / 2, sx: t, sy: h, sz: rd });
  });

  return boxes;
}

function RoomFloorPlanModelComponent({ rooms }: RoomFloorPlanModelProps) {
  const walls = useMemo(() => buildWalls(rooms), [rooms]);

  return (
    <group>
      {walls.map((w) => (
        <mesh key={w.key} position={[w.x, w.y, w.z]} castShadow receiveShadow>
          <boxGeometry args={[w.sx, w.sy, w.sz]} />
          <meshStandardMaterial
            color={w.isSlab ? SLAB_CLR : WALL_CLR}
            roughness={w.isSlab ? 0.7 : 0.25}
            metalness={w.isSlab ? 0.2 : 0.05}
          />
          <Edges
            color={w.isSlab ? "#F9F9F9" : "#333"}
            scale={1.001}
            threshold={15}
          />
        </mesh>
      ))}
    </group>
  );
}

export const RoomFloorPlanModel = memo(RoomFloorPlanModelComponent);
