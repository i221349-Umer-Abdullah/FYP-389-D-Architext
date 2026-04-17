"use client";

import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";

import { GenerationRoom, WorkflowState } from "@/lib/types";
import { ParticleBuildLoader } from "@/components/three/ParticleBuildLoader";
import { RoomFloorPlanModel } from "@/components/three/RoomFloorPlanModel";
import { StudioLights } from "@/components/three/StudioLights";

import styles from "./GeneratorCanvas.module.css";

interface GeneratorCanvasProps {
  state: WorkflowState;
  rooms: GenerationRoom[] | null;
  label: string;
}

function cameraForRooms(rooms: GenerationRoom[] | null) {
  if (!rooms?.length) return { position: [10, 9, 10] as [number, number, number], fov: 42 };
  const maxX = Math.max(...rooms.map((r) => r.x + r.width));
  const maxY = Math.max(...rooms.map((r) => r.y + r.height));
  const span = Math.max(maxX, maxY, 8);
  const dist = span * 1.1;
  return { position: [dist, dist * 0.8, dist] as [number, number, number], fov: 42 };
}

export function GeneratorCanvas({ state, rooms, label }: GeneratorCanvasProps) {
  const camera = useMemo(() => cameraForRooms(rooms), [rooms]);
  const showModel = state === "ready" && rooms && rooms.length > 0;
  const showLoader = state === "building";

  return (
    <div className={styles.wrap}>
      <span className={styles.label}>{label}</span>
      <Canvas
        shadows
        dpr={[1, 1.8]}
        camera={camera}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      >
        <color attach="background" args={["#F9F9F9"]} />
        <fog attach="fog" args={["#F9F9F9", 28, 60]} />
        <Suspense fallback={null}>
          <StudioLights dramatic />

          {showLoader && <ParticleBuildLoader />}

          {showModel && (
            <>
              <RoomFloorPlanModel rooms={rooms} />
              <ContactShadows opacity={0.22} blur={2.5} far={12} width={24} height={24} position={[0, -0.1, 0]} />
            </>
          )}

          {(showModel || state === "idle") && (
            <OrbitControls
              makeDefault
              enableDamping
              dampingFactor={0.08}
              minDistance={4}
              maxDistance={60}
              minPolarAngle={0.3}
              maxPolarAngle={Math.PI / 2.05}
              target={[0, 0.8, 0]}
            />
          )}
        </Suspense>
      </Canvas>
    </div>
  );
}
