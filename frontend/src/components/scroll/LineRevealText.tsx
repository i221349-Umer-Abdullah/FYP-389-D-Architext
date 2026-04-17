"use client";

import { motion } from "framer-motion";

import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { unfoldContainer, unfoldSlat } from "@/lib/motion";
import { LineRevealTextProps } from "@/lib/types";

import styles from "./LineRevealText.module.css";

export function LineRevealText({ lines, once = true }: LineRevealTextProps) {
  const reducedMotion = usePrefersReducedMotion();

  if (reducedMotion) {
    return (
      <div className={styles.block}>
        {lines.map((line) => (
          <p key={line} className={styles.line}>
            {line}
          </p>
        ))}
      </div>
    );
  }

  return (
    <motion.div
      className={styles.block}
      variants={unfoldContainer}
      initial="hidden"
      whileInView="visible"
      viewport={{ once, amount: 0.25 }}
    >
      {lines.map((line) => (
        /* Each wrapper gives the rotateX child a perspective context
           and clips any overshoot during the unfold arc */
        <div key={line} className={styles.slatWrap}>
          <motion.p
            className={styles.line}
            variants={unfoldSlat}
            style={{ transformOrigin: "center top" }}
          >
            {line}
          </motion.p>
        </div>
      ))}
    </motion.div>
  );
}
