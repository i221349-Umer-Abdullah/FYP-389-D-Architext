"use client";

import { motion } from "framer-motion";

import styles from "./AnimatedSectionHeading.module.css";

interface AnimatedSectionHeadingProps {
  kicker: string;
  title: string;
  subtitle?: string;
}

const kickerVariant = {
  hidden: { rotateX: -90, opacity: 0 },
  visible: {
    rotateX: 0,
    opacity: 1,
    transition: { duration: 0.52, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const titleVariant = {
  hidden: { rotateX: -90, opacity: 0 },
  visible: {
    rotateX: 0,
    opacity: 1,
    transition: { duration: 0.76, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const subtitleVariant = {
  hidden: { opacity: 0, y: 14 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.65, ease: [0.16, 1, 0.3, 1] as const },
  },
};

export function AnimatedSectionHeading({
  kicker,
  title,
  subtitle,
}: AnimatedSectionHeadingProps) {
  return (
    <motion.div
      className={styles.heading}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.4 }}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.12 } },
      }}
    >
      {/* Kicker — small louvre, pivots from top */}
      <div className={styles.kickerSlat}>
        <motion.p
          className={styles.kicker}
          variants={kickerVariant}
          style={{ transformOrigin: "center top" }}
        >
          {kicker}
        </motion.p>
      </div>

      {/* Title — large louvre, pivots from top */}
      <div className={styles.titleSlat}>
        <motion.h2
          className={styles.title}
          variants={titleVariant}
          style={{ transformOrigin: "center top" }}
        >
          {title}
        </motion.h2>
      </div>

      {/* Subtitle keeps a simple fade-up (too long for rotateX) */}
      {subtitle ? (
        <motion.p className={styles.subtitle} variants={subtitleVariant}>
          {subtitle}
        </motion.p>
      ) : null}
    </motion.div>
  );
}
