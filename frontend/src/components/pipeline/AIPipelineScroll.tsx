"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import {
  CatmullRomCurve3,
  Group,
  MathUtils,
  Quaternion,
  Vector3,
} from "three";

import styles from "./AIPipelineScroll.module.css";

interface LayerCopy {
  id: string;
  index: string;
  chip: string;
  title: string;
  description: string;
  waypoint: number;
}

const LAYERS: LayerCopy[] = [
  {
    id: "parse",
    index: "01",
    chip: "NLP",
    title: "Layer 1 - Parse",
    description:
      "Natural language understanding extracts rooms, sizes, constraints, and adjacencies from your plain-English description.",
    waypoint: 0.15,
  },
  {
    id: "layout",
    index: "02",
    chip: "GRAPH AI",
    title: "Layer 2 - Layout",
    description:
      "A spatial graph is constructed representing room relationships, circulation paths, and structural dependencies.",
    waypoint: 0.38,
  },
  {
    id: "optimise",
    index: "03",
    chip: "CSP SOLVER",
    title: "Layer 3 - Optimise",
    description:
      "Constraint-satisfaction solving arranges rooms to maximise natural light, minimise circulation, and meet code requirements.",
    waypoint: 0.63,
  },
  {
    id: "generate",
    index: "04",
    chip: "IFC 4.X",
    title: "Layer 4 - Generate",
    description:
      "IFC 4.x geometry is assembled: IfcSpace, IfcWall, IfcSlab, IfcDoor - a fully valid BIM file ready for Revit or ArchiCAD.",
    waypoint: 0.87,
  },
];

const TRAIN_STOPS = [0.06, ...LAYERS.map((l) => l.waypoint)];
const CARD_ENTER_EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
const CARD_EXIT_EASE: [number, number, number, number] = [0.4, 0, 1, 1];

// Card slide direction: positive = forward (up-exit / bottom-enter), negative = reverse
const cardVariants: Variants = {
  enter: (dir: number) => ({
    y: dir > 0 ? 60 : -60,
    opacity: 0,
    filter: "blur(8px)",
  }),
  visible: {
    y: 0,
    opacity: 1,
    filter: "blur(0px)",
    transition: { duration: 0.52, ease: CARD_ENTER_EASE },
  },
  exit: (dir: number) => ({
    y: dir > 0 ? -60 : 60,
    opacity: 0,
    filter: "blur(8px)",
    transition: { duration: 0.36, ease: CARD_EXIT_EASE },
  }),
};

interface SceneProps {
  onAnimationComplete: () => void;
  targetStop: number;
}

function PipelineScene({ onAnimationComplete, targetStop }: SceneProps) {
  const trainRef = useRef<Group | null>(null);
  const currentTRef = useRef(TRAIN_STOPS[0]);
  const sceneStopRef = useRef(0);
  const motionRef = useRef({
    active: false,
    start: TRAIN_STOPS[0],
    end: TRAIN_STOPS[0],
    elapsed: 0,
    duration: 0.95,
    nextStop: 0,
  });

  const onCompleteRef = useRef(onAnimationComplete);
  onCompleteRef.current = onAnimationComplete;

  const targetStopRef = useRef(targetStop);
  useEffect(() => {
    targetStopRef.current = targetStop;
  }, [targetStop]);

  const axisY = useMemo(() => new Vector3(0, 1, 0), []);
  const correctionQuat = useMemo(
    () => new Quaternion().setFromAxisAngle(axisY, Math.PI / 2),
    [axisY],
  );
  const targetQuat = useMemo(() => new Quaternion(), []);
  const lookTargetRef = useRef<Group | null>(null);

  const curve = useMemo(() => {
    const points = Array.from({ length: 220 }, (_, i) => {
      const t = i / 219;
      const angle = t * Math.PI * 6.2;
      const radius = MathUtils.lerp(5.4, 1.3, t);
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = MathUtils.lerp(2.8, -2.7, t);
      return new Vector3(x, y, z);
    });
    return new CatmullRomCurve3(points, false, "catmullrom", 0.42);
  }, []);

  const waypointPoints = useMemo(
    () => LAYERS.map((layer) => curve.getPointAt(layer.waypoint)),
    [curve],
  );

  useFrame((_, delta) => {
    if (!trainRef.current) return;

    const motion = motionRef.current;
    const desired = targetStopRef.current;

    if (!motion.active && desired !== sceneStopRef.current) {
      motion.active = true;
      motion.start = currentTRef.current;
      motion.end = TRAIN_STOPS[desired];
      motion.elapsed = 0;
      motion.duration = 0.95;
      motion.nextStop = desired;
    }

    if (motion.active) {
      motion.elapsed = Math.min(motion.duration, motion.elapsed + delta);
      const alpha = motion.elapsed / motion.duration;
      const eased =
        alpha < 0.5 ? 2 * alpha * alpha : 1 - Math.pow(-2 * alpha + 2, 2) / 2;
      currentTRef.current = MathUtils.lerp(motion.start, motion.end, eased);

      if (alpha >= 1) {
        motion.active = false;
        sceneStopRef.current = motion.nextStop;
        currentTRef.current = TRAIN_STOPS[motion.nextStop];
        onCompleteRef.current();
      }
    }

    const t = MathUtils.clamp(currentTRef.current, 0.001, 0.999);
    const position = curve.getPointAt(t);
    const lookAhead = curve.getPointAt(Math.min(0.999, t + 0.012));

    if (lookTargetRef.current) {
      lookTargetRef.current.position.copy(position);
      lookTargetRef.current.lookAt(lookAhead);
      targetQuat.copy(lookTargetRef.current.quaternion).multiply(correctionQuat);
      trainRef.current.quaternion.slerp(targetQuat, 0.24);
    }

    trainRef.current.position.copy(position);
  });

  return (
    <>
      <color attach="background" args={["#050505"]} />
      <fog attach="fog" args={["#050505", 7, 26]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[5.5, 9, 4]} intensity={1.25} color="#f9f9f9" />
      <pointLight position={[-4, 4.5, -3]} intensity={3.9} color="#f9f9f9" />

      <mesh>
        <tubeGeometry args={[curve, 620, 0.09, 18, false]} />
        <meshStandardMaterial
          color="#f9f9f9"
          emissive="#e9e9e9"
          emissiveIntensity={1.45}
          roughness={0.2}
          metalness={0.6}
        />
      </mesh>

      <mesh>
        <tubeGeometry args={[curve, 620, 0.2, 14, false]} />
        <meshStandardMaterial
          color="#131313"
          emissive="#1f1f1f"
          emissiveIntensity={0.42}
          transparent
          opacity={0.44}
          roughness={0.86}
          metalness={0.18}
        />
      </mesh>

      <group ref={trainRef}>
        <mesh castShadow>
          <boxGeometry args={[0.9, 0.26, 0.34]} />
          <meshStandardMaterial
            color="#f9f9f9"
            emissive="#ebebeb"
            emissiveIntensity={0.2}
            roughness={0.2}
            metalness={0.84}
          />
        </mesh>
        <mesh position={[0, 0.22, 0]} castShadow>
          <boxGeometry args={[0.5, 0.18, 0.28]} />
          <meshStandardMaterial color="#f3f3f3" roughness={0.3} metalness={0.72} />
        </mesh>
        <mesh position={[0.43, -0.16, 0.11]}>
          <cylinderGeometry args={[0.07, 0.07, 0.08, 20]} />
          <meshStandardMaterial color="#e6e6e6" emissive="#cfcfcf" emissiveIntensity={0.2} />
        </mesh>
        <mesh position={[0.43, -0.16, -0.11]}>
          <cylinderGeometry args={[0.07, 0.07, 0.08, 20]} />
          <meshStandardMaterial color="#e6e6e6" emissive="#cfcfcf" emissiveIntensity={0.2} />
        </mesh>
        <mesh position={[-0.43, -0.16, 0.11]}>
          <cylinderGeometry args={[0.07, 0.07, 0.08, 20]} />
          <meshStandardMaterial color="#e6e6e6" emissive="#cfcfcf" emissiveIntensity={0.2} />
        </mesh>
        <mesh position={[-0.43, -0.16, -0.11]}>
          <cylinderGeometry args={[0.07, 0.07, 0.08, 20]} />
          <meshStandardMaterial color="#e6e6e6" emissive="#cfcfcf" emissiveIntensity={0.2} />
        </mesh>
      </group>

      {waypointPoints.map((point, idx) => (
        <group key={LAYERS[idx].id} position={point}>
          <mesh>
            <sphereGeometry args={[0.14, 24, 24]} />
            <meshStandardMaterial
              color="#f9f9f9"
              emissive="#ebebeb"
              emissiveIntensity={0.78}
              roughness={0.16}
              metalness={0.35}
            />
          </mesh>
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.24, 0.02, 12, 40]} />
            <meshStandardMaterial
              color="#d8d8d8"
              emissive="#f0f0f0"
              emissiveIntensity={0.45}
              roughness={0.22}
            />
          </mesh>
        </group>
      ))}
      <group ref={lookTargetRef} visible={false} />
    </>
  );
}

export function AIPipelineScroll() {
  const [targetStop, setTargetStop] = useState(0);
  const [direction, setDirection] = useState(1);
  const sectionRef = useRef<HTMLElement | null>(null);
  const currentStopRef = useRef(0);
  const isAnimatingRef = useRef(false);

  const handleAnimationComplete = useCallback(() => {
    isAnimatingRef.current = false;
  }, []);

  useEffect(() => {
    const onWheel = (e: WheelEvent) => {
      const el = sectionRef.current;
      if (!el) return;

      const rect = el.getBoundingClientRect();
      const isPinned = rect.top <= 1 && rect.bottom >= window.innerHeight - 1;
      if (!isPinned) return;

      const dir = e.deltaY > 0 ? 1 : -1;
      const nextStop = currentStopRef.current + dir;

      if (nextStop < 0) {
        e.preventDefault();
        window.scrollTo({ top: Math.max(0, el.offsetTop - 100) });
        return;
      }

      if (nextStop >= TRAIN_STOPS.length) {
        e.preventDefault();
        const sectionEnd = el.offsetTop + el.offsetHeight - window.innerHeight;
        window.scrollTo({ top: sectionEnd + 100 });
        return;
      }

      e.preventDefault();
      if (isAnimatingRef.current) return;

      isAnimatingRef.current = true;
      currentStopRef.current = nextStop;
      setDirection(dir);
      setTargetStop(nextStop);
    };

    window.addEventListener("wheel", onWheel, { passive: false });
    return () => window.removeEventListener("wheel", onWheel);
  }, []);

  // Card to display: stop 0 = none, stop 1–4 = LAYERS[0–3]
  const activeLayer = targetStop >= 1 ? LAYERS[targetStop - 1] : null;

  return (
    <section ref={sectionRef} className={styles.section}>
      <div className={styles.pinWrap}>
        <div className={styles.canvasWrap}>
          <Canvas
            dpr={[1, 1.8]}
            camera={{ position: [0, 1.4, 10], fov: 42 }}
            gl={{ antialias: true, powerPreference: "high-performance" }}
          >
            <PipelineScene
              onAnimationComplete={handleAnimationComplete}
              targetStop={targetStop}
            />
          </Canvas>
        </div>

        <div className={styles.overlay}>
          <motion.p
            className={styles.kicker}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.64, ease: [0.16, 1, 0.3, 1] as const }}
          >
            THE AI PIPELINE
          </motion.p>
          <motion.h2
            className={styles.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, delay: 0.08, ease: [0.16, 1, 0.3, 1] as const }}
          >
            Words in.
            <br />
            Buildings out.
          </motion.h2>
          <motion.p
            className={styles.subtitle}
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.76, delay: 0.14, ease: [0.16, 1, 0.3, 1] as const }}
          >
            Four specialised AI layers transform a sentence into a valid IFC BIM
            file - no CAD, no Revit licence, no expertise required.
          </motion.p>

          {/* Single centered card — swaps with direction-aware slide */}
          <div className={styles.cardStage}>
            <AnimatePresence mode="wait" custom={direction}>
              {activeLayer && (
                <motion.article
                  key={activeLayer.id}
                  className={styles.floatCard}
                  custom={direction}
                  variants={cardVariants}
                  initial="enter"
                  animate="visible"
                  exit="exit"
                >
                  <p className={styles.index}>{activeLayer.index}</p>
                  <span className={styles.chip}>{activeLayer.chip}</span>
                  <h3>{activeLayer.title}</h3>
                  <p>{activeLayer.description}</p>
                </motion.article>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
