"use client";

import { motion } from "framer-motion";

import styles from "./MarqueeStrip.module.css";

interface MarqueeStripProps {
  text: string;
}

export function MarqueeStrip({ text }: MarqueeStripProps) {
  const repeated = `${text} \u25C6 ${text} \u25C6 ${text} \u25C6 ${text}`;

  return (
    <motion.section
      className={styles.shell}
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.5 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] as const }}
      aria-label="Animated highlight strip"
    >
      <div className={styles.track}>
        <span>{repeated}</span>
        <span aria-hidden>{repeated}</span>
      </div>
    </motion.section>
  );
}
