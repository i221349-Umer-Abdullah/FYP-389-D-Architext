"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

import styles from "./ProjectBriefExperience.module.css";

const WORKFLOW_STEPS = ["Layer 1", "Layer 2", "Layer 3", "Layer 4"];

const API_ENDPOINTS = [
  { method: "GET", path: "/api/health", purpose: "Check if backend is alive." },
  { method: "POST", path: "/api/generate", purpose: "Submit text and receive job_id." },
  {
    method: "GET",
    path: "/api/status/{job_id}",
    purpose: "Poll generation progress from 0 to 100.",
  },
  {
    method: "GET",
    path: "/api/preview/{job_id}",
    purpose: "Fetch room layout JSON for 2D floorplan draw.",
  },
  {
    method: "GET",
    path: "/api/download/{job_id}",
    purpose: "Download generated IFC BIM file.",
  },
  { method: "GET", path: "/docs", purpose: "Open Swagger API documentation." },
];

const FRONTEND_VIEWS = [
  {
    title: "Prompt Input",
    items: [
      "Large text area to describe the building",
      "Generate button and optional presets",
      "Progress indicator while polling status",
    ],
  },
  {
    title: "2D Floorplan Preview",
    items: [
      "Draw room rectangles from x/y/width/height (metres)",
      "Color code room types and label area inside each room",
      "Click room to highlight and inspect details",
    ],
  },
  {
    title: "3D IFC Viewer",
    items: [
      "Load /api/download/{job_id} result in-browser",
      "Render IFC with WebGL viewer interactions",
      "Enable final IFC download once file is ready",
    ],
  },
];

const TECH_STACK = [
  "Next.js + TypeScript",
  "Framer Motion",
  "GSAP",
  "Konva.js",
  "web-ifc-viewer",
  "Zustand",
  "Fetch API",
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.7,
      ease: [0.16, 1, 0.3, 1] as const,
    },
  },
};

export function ProjectBriefExperience() {
  const sectionRef = useRef<HTMLElement | null>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  });
  const flowX = useTransform(scrollYProgress, [0, 1], [-38, 38]);
  const flowRotate = useTransform(scrollYProgress, [0, 1], [-2.2, 2.2]);
  const glowOpacity = useTransform(scrollYProgress, [0, 1], [0.2, 0.6]);

  return (
    <section ref={sectionRef} className={styles.section} id="project-brief">
      <div className={styles.backgroundGrid} aria-hidden />
      <div className="app-container">
        <motion.div
          className={styles.heroBlock}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.72, ease: [0.16, 1, 0.3, 1] as const }}
        >
          <p className={styles.kicker}>ArchiText Frontend Partner Brief</p>
          <h2 className={styles.title}>
            One prompt in. One IFC BIM out. Frontend explains every step.
          </h2>
          <p className={styles.subtitle}>
            Backend AI pipeline is already working. This frontend layer visualizes
            workflow, shows required screens, and prepares users for live generation.
          </p>
          <div className={styles.badges}>
            <span className={styles.badge}>Frontend mode active</span>
            <span className={styles.badge}>No backend wiring required now</span>
            <span className={styles.badge}>Port 8000 API contract documented</span>
          </div>
        </motion.div>

        <motion.div
          className={styles.pipelinePanel}
          style={{ x: flowX, rotate: flowRotate }}
        >
          <motion.div className={styles.pipelineGlow} style={{ opacity: glowOpacity }} />
          <p className={styles.pipelinePrompt}>
            &quot;3 bedroom house, 2 baths, garden, 5 marla plot&quot;
          </p>
          <div className={styles.pipelineTrack}>
            {WORKFLOW_STEPS.map((step) => (
              <div key={step} className={styles.pipelineStep}>
                {step}
              </div>
            ))}
          </div>
          <p className={styles.pipelineOutput}>Output: Room JSON + IFC file</p>
        </motion.div>

        <motion.div
          className={styles.apiGrid}
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.18 }}
        >
          {API_ENDPOINTS.map((endpoint) => (
            <motion.article
              key={endpoint.path}
              className={styles.apiCard}
              variants={itemVariants}
            >
              <div className={styles.apiMeta}>
                <span className={styles.method}>{endpoint.method}</span>
                <span className={styles.path}>{endpoint.path}</span>
              </div>
              <p className={styles.purpose}>{endpoint.purpose}</p>
            </motion.article>
          ))}
        </motion.div>

        <motion.div
          className={styles.viewGrid}
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.24 }}
        >
          {FRONTEND_VIEWS.map((view) => (
            <motion.article
              key={view.title}
              className={styles.viewCard}
              variants={itemVariants}
            >
              <h3 className={styles.viewTitle}>{view.title}</h3>
              <ul className={styles.viewList}>
                {view.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </motion.article>
          ))}
        </motion.div>

        <motion.div
          className={styles.stackPanel}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{ duration: 0.68, ease: [0.16, 1, 0.3, 1] as const }}
        >
          <p className={styles.stackTitle}>Recommended stack</p>
          <div className={styles.stackPills}>
            {TECH_STACK.map((item) => (
              <span key={item} className={styles.stackPill}>
                {item}
              </span>
            ))}
          </div>
        </motion.div>

        <motion.div
          className={styles.layoutBoard}
          initial={{ opacity: 0, y: 26 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.74, ease: [0.16, 1, 0.3, 1] as const }}
        >
          <p className={styles.layoutLabel}>Suggested product layout</p>
          <div className={styles.layoutGrid}>
            <div className={styles.layoutLeft}>
              Prompt input
              <br />
              Generate button
              <br />
              Progress + spec summary
              <br />
              Download IFC
            </div>
            <div className={styles.layoutTop}>2D floorplan canvas (rooms + labels)</div>
            <div className={styles.layoutBottom}>3D IFC viewer (interactive WebGL)</div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
