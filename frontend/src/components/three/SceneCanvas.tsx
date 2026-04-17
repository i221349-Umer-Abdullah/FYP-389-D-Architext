"use client";

import { Suspense, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import * as THREE from "three";

import { WorkflowState } from "@/lib/types";

import { DisassemblyRig } from "./DisassemblyRig";
import { ParticleBuildLoader } from "./ParticleBuildLoader";
import { StudioLights } from "./StudioLights";
import { WireframeBackdrop } from "./WireframeBackdrop";
import styles from "./SceneCanvas.module.css";

type SceneMode = "hero" | "showcase" | "studio";

interface SceneCanvasProps {
  mode: SceneMode;
  state?: WorkflowState;
  disassemblyProgress?: number;
  rotationY?: number;
}

/**
 * Sets camera position + FOV + lookAt BEFORE the first Three.js render.
 * useEffect fires after browser paint (too late — first frame is wrong).
 * useFrame fires before each render; a ref guard ensures it only runs once.
 *
 * Camera maths:
 *   position [0, 7, 4] → distance to target [0, 0.3, 0] ≈ 8.1 units
 *   fov 56° vertical → visible height ≈ 8.6 units at that distance
 *   floor plan footprint 8.4 × 6.4 units → ~98% fill of a square canvas ✓
 *   elevation ≈ 60° — shows wall depth without losing plan legibility
 */
function ShowcaseCamera() {
  const { camera } = useThree();
  const ready = useRef(false);

  useFrame(() => {
    if (ready.current) return;
    ready.current = true;
    camera.position.set(0, 12, 7);
    if ((camera as THREE.PerspectiveCamera).isPerspectiveCamera) {
      (camera as THREE.PerspectiveCamera).fov = 60;
      (camera as THREE.PerspectiveCamera).updateProjectionMatrix();
    }
    camera.lookAt(0, 0.3, 0);
    camera.updateMatrixWorld();
  });

  return null;
}

export default function SceneCanvas({
  mode,
  state = "idle",
  disassemblyProgress = 0,
  rotationY = 0,
}: SceneCanvasProps) {
  const camera = useMemo(
    () =>
      mode === "hero"
        ? { position: [0, 0.6, 8] as [number, number, number], fov: 50 }
        : { position: [8, 7, 8] as [number, number, number], fov: 42 },
    [mode],
  );

  return (
    <div className={styles.canvas}>
      <Canvas
        shadows
        dpr={[1, 1.8]}
        camera={camera}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      >
        <color attach="background" args={["#F9F9F9"]} />
        <fog attach="fog" args={["#F9F9F9", 14, 34]} />
        <Suspense fallback={null}>
          <StudioLights dramatic={mode !== "hero"} />

          {mode === "hero" ? <WireframeBackdrop /> : null}

          {mode === "showcase" ? (
            <>
              {/* Sets camera position + fov + lookAt atomically after mount */}
              <ShowcaseCamera />
              <DisassemblyRig
                progress={disassemblyProgress}
                rotationY={rotationY}
                xrayProgress={disassemblyProgress}
              />
            </>
          ) : null}

          {mode === "studio" && state === "building" ? (
            <ParticleBuildLoader />
          ) : null}

          {mode === "studio" && state !== "building" ? (
            <DisassemblyRig progress={disassemblyProgress} rotationY={rotationY || 0.35} />
          ) : null}

          {mode !== "hero" ? (
            <ContactShadows
              opacity={0.28}
              blur={2.8}
              far={15}
              width={18}
              height={18}
              position={mode === "showcase" ? [0, -0.42, 0] : [0, -1.4, 0]}
            />
          ) : null}

          {mode === "studio" ? (
            <OrbitControls
              makeDefault
              enableDamping
              dampingFactor={0.08}
              minDistance={5.5}
              maxDistance={18}
              minPolarAngle={0.55}
              maxPolarAngle={Math.PI / 2.04}
              target={[0, 0.4, 0]}
            />
          ) : null}
        </Suspense>
      </Canvas>
    </div>
  );
}
