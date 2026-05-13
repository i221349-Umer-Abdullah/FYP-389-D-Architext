"use client";

import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, Line, OrbitControls } from "@react-three/drei";

import { GenerationRoom, PlotConstraint, WorkflowState } from "@/lib/types";
import { getStyle, type StyleId } from "@/lib/architectureStyles";
import { ParticleBuildLoader } from "@/components/three/ParticleBuildLoader";
import { RoomFloorPlanModel } from "@/components/three/RoomFloorPlanModel";
import { StudioLights } from "@/components/three/StudioLights";

import styles from "./GeneratorCanvas.module.css";

interface GeneratorCanvasProps {
  state: WorkflowState;
  rooms: GenerationRoom[] | null;
  label: string;
  styleId?: StyleId;
  plotConstraint?: PlotConstraint | null;
}

function PlotBoundaryBox({ width, height }: { width: number; height: number }) {
  const hw = width / 2;
  const hh = height / 2;
  const y  = 0.02;
  const points: [number, number, number][] = [
    [-hw, y, -hh], [hw, y, -hh], [hw, y, hh], [-hw, y, hh], [-hw, y, -hh],
  ];
  return <Line points={points} color="#22c55e" lineWidth={2} />;
}

function cameraForRooms(rooms: GenerationRoom[] | null, plotConstraint?: PlotConstraint | null) {
  const plotSpan = plotConstraint ? Math.max(plotConstraint.width, plotConstraint.height) : 0;
  if (!rooms?.length) {
    const base = Math.max(plotSpan, 8);
    const dist = base * 1.1;
    return { position: [dist, dist * 0.8, dist] as [number, number, number], fov: 42 };
  }
  const maxX = Math.max(...rooms.map((r) => r.x + r.width));
  const maxY = Math.max(...rooms.map((r) => r.y + r.height));
  const span = Math.max(maxX, maxY, plotSpan, 8);
  const dist = span * 1.1;
  return { position: [dist, dist * 0.8, dist] as [number, number, number], fov: 42 };
}

export function GeneratorCanvas({ state, rooms, label, styleId = "modern", plotConstraint }: GeneratorCanvasProps) {
  const camera     = useMemo(() => cameraForRooms(rooms, plotConstraint), [rooms, plotConstraint]);
  const canvasBg   = useMemo(() => getStyle(styleId).visuals.canvasBg, [styleId]);
  const showModel  = state === "ready" && rooms && rooms.length > 0;
  const showLoader = state === "building";
  const showBoundary = Boolean(plotConstraint) && (state === "ready" || state === "idle");

  return (
    <div className={styles.wrap}>
      <span className={styles.label}>{label}</span>
      <Canvas
        shadows
        dpr={[1, 1.8]}
        camera={camera}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      >
        <color attach="background" args={[canvasBg]} />
        <fog attach="fog" args={[canvasBg, 28, 60]} />
        <Suspense fallback={null}>
          <StudioLights dramatic />

          {showLoader && <ParticleBuildLoader />}

          {showModel && (
            <>
              <RoomFloorPlanModel rooms={rooms} styleId={styleId} />
              <ContactShadows opacity={0.22} blur={2.5} far={12} width={24} height={24} position={[0, -0.1, 0]} />
            </>
          )}

          {showBoundary && (
            <PlotBoundaryBox width={plotConstraint!.width} height={plotConstraint!.height} />
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
