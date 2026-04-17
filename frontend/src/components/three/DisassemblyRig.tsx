import { memo } from "react";

import { FloorPlanModel } from "@/components/three/FloorPlanModel";

interface DisassemblyRigProps {
  progress: number;
  rotationY?: number;
  xrayProgress?: number;
}

function DisassemblyRigComponent({ progress, rotationY = 0, xrayProgress = 0 }: DisassemblyRigProps) {
  const clamped = Math.max(0, Math.min(1, progress));

  return (
    <group rotation={[0, rotationY, 0]}>
      <FloorPlanModel explodedOffset={clamped} xrayProgress={xrayProgress} />
    </group>
  );
}

export const DisassemblyRig = memo(DisassemblyRigComponent);
