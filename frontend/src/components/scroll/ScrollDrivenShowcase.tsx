"use client";

import dynamic from "next/dynamic";
import {
  motion,
  useMotionValueEvent,
  useScroll,
  useTransform,
} from "framer-motion";
import { useRef, useState } from "react";

import styles from "./ScrollDrivenShowcase.module.css";

const SceneCanvas = dynamic(() => import("@/components/three/SceneCanvas"), {
  ssr: false,
  loading: () => <div className={styles.canvasFallback} aria-hidden />,
});

export function ScrollDrivenShowcase() {
  const targetRef = useRef<HTMLDivElement | null>(null);
  const [rotationY, setRotationY] = useState(0);
  const [disassembly, setDisassembly] = useState(0);
  const [opacity, setOpacity] = useState(0.24);
  const { scrollYProgress } = useScroll({
    target: targetRef,
    offset: ["start end", "end start"],
  });

  const mappedRotation = useTransform(scrollYProgress, [0, 1], [0, Math.PI * 1.65]);
  const mappedDisassembly = useTransform(scrollYProgress, [0, 1], [0, 1]);
  const mappedOpacity = useTransform(scrollYProgress, [0, 1], [0.24, 1]);

  useMotionValueEvent(mappedRotation, "change", (latest) => {
    setRotationY(latest);
  });

  useMotionValueEvent(mappedDisassembly, "change", (latest) => {
    setDisassembly(latest);
  });

  useMotionValueEvent(mappedOpacity, "change", (latest) => {
    setOpacity(latest);
  });

  return (
    <section className={styles.section} ref={targetRef}>
      <div className={styles.sticky}>
        <div className="app-container">
          <div className={styles.layout}>
            <div className={styles.copy}>
              <motion.p className={styles.tag} style={{ opacity }}>
                AI Plan Breakdown
              </motion.p>
              <motion.h2 className={styles.title} style={{ opacity }}>
                See how the generated plan is organized for BIM.
              </motion.h2>
              <motion.p className={styles.text} style={{ opacity }}>
                Architext separates walls, slabs, room volumes, and planning logic so
                the output can move from AI generation into design review and export.
              </motion.p>
            </div>
            <div className={styles.canvasWrap}>
              <SceneCanvas
                mode="showcase"
                rotationY={rotationY}
                disassemblyProgress={disassembly}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
