import { memo } from "react";
import { Edges } from "@react-three/drei";

import { FLOOR_PLAN_PARTS } from "@/lib/constants";

interface FloorPlanModelProps {
  explodedOffset?: number;
  xrayProgress?: number;
}

function FloorPlanModelComponent({ explodedOffset = 0, xrayProgress = 0 }: FloorPlanModelProps) {
  const clamped = Math.max(0, Math.min(1, explodedOffset));
  const xray = Math.max(0, Math.min(1, xrayProgress));

  // Solid until 30% scroll, then fades toward near-transparent (frosted glass → wireframe)
  const meshOpacity = xray < 0.3
    ? 1
    : 1 - Math.pow((xray - 0.3) / 0.7, 0.55) * 0.92;
  const isTransparent = meshOpacity < 0.99;

  // Edges intensify as mesh fades: 0 → full opacity at xray=1
  const edgeBrightness = 0.55 + xray * 0.45;

  return (
    <group>
      {FLOOR_PLAN_PARTS.map((part, index) => {
        const [x, y, z] = part.position;
        const [sx, sy, sz] = part.size;
        const radialLength = Math.hypot(x, z) || 1;
        const xOffset = (x / radialLength) * clamped * 1.25;
        const zOffset = (z / radialLength) * clamped * 1.25;
        const yOffset = clamped * (index % 2 === 0 ? 0.2 : 0.12);
        const isSlab = part.id.includes("slab");

        // Slabs (dark) fade faster so the structural skeleton reads clearly
        const opacity = isSlab ? meshOpacity * 0.82 : meshOpacity;

        // Edge colour: slabs keep white edges; walls darken edges proportionally
        const edgeColor = isSlab
          ? `#F9F9F9`
          : `#${Math.round(10 * (1 - edgeBrightness * 0.06)).toString(16).padStart(2, "0").repeat(3)}`;

        return (
          <mesh
            key={part.id}
            castShadow={opacity > 0.15}
            receiveShadow={opacity > 0.15}
            position={[x + xOffset, y + yOffset, z + zOffset]}
          >
            <boxGeometry args={[sx, sy, sz]} />
            <meshStandardMaterial
              color={isSlab ? "#0A0A0A" : "#F9F9F9"}
              roughness={isSlab ? 0.62 : 0.22}
              metalness={isSlab ? 0.16 : 0.1}
              transparent={isTransparent}
              opacity={opacity}
              depthWrite={opacity > 0.5}
            />
            <Edges color={isSlab ? "#F9F9F9" : "#0A0A0A"} scale={1.001} />
          </mesh>
        );
      })}
    </group>
  );
}

export const FloorPlanModel = memo(FloorPlanModelComponent);
