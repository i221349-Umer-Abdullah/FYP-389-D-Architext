import { memo } from "react";

interface StudioLightsProps {
  dramatic?: boolean;
}

function StudioLightsComponent({ dramatic = false }: StudioLightsProps) {
  return (
    <>
      <ambientLight intensity={dramatic ? 0.35 : 0.58} color="#F9F9F9" />
      <directionalLight
        castShadow
        intensity={dramatic ? 1.45 : 0.92}
        color="#F9F9F9"
        position={[7.5, 11, 5.5]}
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
        shadow-bias={-0.00008}
      />
      <directionalLight
        intensity={dramatic ? 0.62 : 0.4}
        color="#F9F9F9"
        position={[-6, 6, -8]}
      />
      <hemisphereLight
        intensity={dramatic ? 0.32 : 0.18}
        color="#F9F9F9"
        groundColor="#0A0A0A"
      />
    </>
  );
}

export const StudioLights = memo(StudioLightsComponent);
