import { memo, useRef } from "react";
import { Group } from "three";
import { useFrame } from "@react-three/fiber";

interface WireframeBackdropProps {
  speed?: number;
}

function WireframeBackdropComponent({ speed = 0.12 }: WireframeBackdropProps) {
  const groupRef = useRef<Group | null>(null);

  useFrame((_, delta) => {
    if (!groupRef.current) {
      return;
    }

    groupRef.current.rotation.y += delta * speed;
    groupRef.current.rotation.x += delta * speed * 0.22;
  });

  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      <mesh position={[0, 0, 0]}>
        <icosahedronGeometry args={[2.6, 1]} />
        <meshBasicMaterial color="#0A0A0A" wireframe transparent opacity={0.24} />
      </mesh>
      <mesh position={[-2.9, -1.4, -0.6]} rotation={[0.25, 0.12, 0]}>
        <torusKnotGeometry args={[1.15, 0.24, 120, 12]} />
        <meshBasicMaterial color="#0A0A0A" wireframe transparent opacity={0.14} />
      </mesh>
      <mesh position={[2.65, 1.15, 0.45]} rotation={[-0.15, 0.2, 0]}>
        <dodecahedronGeometry args={[1.4, 0]} />
        <meshBasicMaterial color="#0A0A0A" wireframe transparent opacity={0.2} />
      </mesh>
    </group>
  );
}

export const WireframeBackdrop = memo(WireframeBackdropComponent);
