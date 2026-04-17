import { memo, useEffect, useRef } from "react";
import { BufferAttribute, MathUtils, Points } from "three";
import { useFrame } from "@react-three/fiber";

import { FLOOR_PLAN_PARTS } from "@/lib/constants";

const PARTICLE_COUNT = 1800;

interface ParticleLayout {
  currentPositions: Float32Array<ArrayBufferLike>;
  targetPositions: Float32Array<ArrayBufferLike>;
}

function seededNoise(seed: number) {
  const value = Math.sin(seed * 127.1 + 311.7) * 43758.5453123;
  return value - Math.floor(value);
}

function createParticleLayout(): ParticleLayout {
  const current = new Float32Array(PARTICLE_COUNT * 3);
  const target = new Float32Array(PARTICLE_COUNT * 3);

  for (let i = 0; i < PARTICLE_COUNT; i += 1) {
    const i3 = i * 3;
    const r1 = seededNoise(i + 1);
    const r2 = seededNoise(i + 17);
    const r3 = seededNoise(i + 89);
    const r4 = seededNoise(i + 131);
    const r5 = seededNoise(i + 251);
    const r6 = seededNoise(i + 419);

    const theta = r1 * Math.PI * 2;
    const phi = Math.acos(2 * r2 - 1);
    const radius = 6 + r3 * 4;

    current[i3] = radius * Math.sin(phi) * Math.cos(theta);
    current[i3 + 1] = (r4 - 0.5) * 5.5;
    current[i3 + 2] = radius * Math.sin(phi) * Math.sin(theta);

    const part = FLOOR_PLAN_PARTS[i % FLOOR_PLAN_PARTS.length];
    const [px, py, pz] = part.position;
    const [sx, sy, sz] = part.size;

    target[i3] = px + (r4 - 0.5) * sx;
    target[i3 + 1] = py + (r5 - 0.5) * sy;
    target[i3 + 2] = pz + (r6 - 0.5) * sz;
  }

  return { currentPositions: current, targetPositions: target };
}

function ParticleBuildLoaderComponent() {
  const pointsRef = useRef<Points | null>(null);
  const progressRef = useRef(0);
  const currentPositionsRef = useRef<Float32Array<ArrayBufferLike>>(
    new Float32Array(0),
  );
  const targetPositionsRef = useRef<Float32Array<ArrayBufferLike>>(
    new Float32Array(0),
  );
  const initializedRef = useRef(false);

  useEffect(() => {
    const layout = createParticleLayout();
    currentPositionsRef.current = layout.currentPositions;
    targetPositionsRef.current = layout.targetPositions;

    if (pointsRef.current) {
      pointsRef.current.geometry.setAttribute(
        "position",
        new BufferAttribute(currentPositionsRef.current, 3),
      );
    }

    initializedRef.current = true;
  }, []);

  useFrame((_, delta) => {
    if (!pointsRef.current || !initializedRef.current) {
      return;
    }

    progressRef.current = Math.min(1, progressRef.current + delta * 0.55);
    const currentPositions = currentPositionsRef.current;
    const targetPositions = targetPositionsRef.current;
    const positionAttribute = pointsRef.current.geometry.attributes
      .position as BufferAttribute;

    for (let i = 0; i < currentPositions.length; i += 1) {
      currentPositions[i] = MathUtils.lerp(
        currentPositions[i],
        targetPositions[i],
        0.055 + progressRef.current * 0.075,
      );
    }

    positionAttribute.needsUpdate = true;
    pointsRef.current.rotation.y += delta * 0.4;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry />
      <pointsMaterial
        color="#0A0A0A"
        size={0.038}
        sizeAttenuation
        transparent
        opacity={0.86}
      />
    </points>
  );
}

export const ParticleBuildLoader = memo(ParticleBuildLoaderComponent);
