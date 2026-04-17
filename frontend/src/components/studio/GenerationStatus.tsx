"use client";

import { AnimatePresence, motion } from "framer-motion";

import { WorkflowState } from "@/lib/types";

import styles from "./GenerationStatus.module.css";

interface GenerationStatusProps {
  state: WorkflowState;
  message?: string;
}

const STATUS_COPY: Record<WorkflowState, string> = {
  idle: "Idle: awaiting your prompt.",
  building: "Generating floor plan layout...",
  ready: "Ready: floor plans generated. See results below.",
  error: "Generation failed — check the message above.",
};

export function GenerationStatus({ state, message }: GenerationStatusProps) {
  const text = (state === "building" && message) ? message : STATUS_COPY[state];
  return (
    <div className={styles.shell} aria-live="polite">
      <AnimatePresence mode="wait">
        <motion.p
          key={text}
          className={styles.text}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
        >
          {text}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
