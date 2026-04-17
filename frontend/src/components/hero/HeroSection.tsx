"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import gsap from "gsap";

import { HERO_HEADLINE, HERO_SUBTEXT } from "@/lib/constants";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

import { PromptBar } from "./PromptBar";
import styles from "./HeroSection.module.css";

const SceneCanvas = dynamic(() => import("@/components/three/SceneCanvas"), {
  ssr: false,
  loading: () => <div className={styles.canvasFallback} aria-hidden />,
});

export function HeroSection() {
  const router = useRouter();
  const reducedMotion = usePrefersReducedMotion();
  const lineRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const kickerRef = useRef<HTMLParagraphElement | null>(null);
  const wowRef = useRef<HTMLParagraphElement | null>(null);
  const subtitleRef = useRef<HTMLParagraphElement | null>(null);
  const promptWrapRef = useRef<HTMLDivElement | null>(null);
  const actionsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (reducedMotion) {
      return;
    }

    const lines = lineRefs.current.filter(
      (line): line is HTMLSpanElement => Boolean(line),
    );

    if (!lines.length) {
      return;
    }

    const timeline = gsap.timeline();

    timeline.fromTo(
      lines,
      { yPercent: 115, opacity: 0 },
      {
        yPercent: 0,
        opacity: 1,
        duration: 1.12,
        stagger: 0.13,
        ease: "power4.out",
      },
    );

    timeline.fromTo(
      [kickerRef.current, wowRef.current],
      { opacity: 0, y: 14 },
      {
        opacity: 1,
        y: 0,
        duration: 0.62,
        ease: "power3.out",
        stagger: 0.07,
      },
      0.08,
    );

    timeline.fromTo(
      subtitleRef.current,
      { opacity: 0, y: 18 },
      { opacity: 1, y: 0, duration: 0.8, ease: "power3.out" },
      0.45,
    );

    timeline.fromTo(
      [promptWrapRef.current, actionsRef.current],
      { opacity: 0, y: 20 },
      {
        opacity: 1,
        y: 0,
        duration: 0.74,
        ease: "power3.out",
        stagger: 0.09,
      },
      0.62,
    );

    return () => {
      timeline.kill();
    };
  }, [reducedMotion]);

  const handlePromptSubmit = async (prompt: string) => {
    router.push(`/studio?prompt=${encodeURIComponent(prompt)}`);
  };

  return (
    <section className={styles.hero}>
      <div className={styles.ambient} aria-hidden>
        <span className={`${styles.orb} ${styles.orbOne}`} />
        <span className={`${styles.orb} ${styles.orbTwo}`} />
        <span className={`${styles.orb} ${styles.orbThree}`} />
      </div>
      <div className={styles.canvasLayer} aria-hidden>
        <SceneCanvas mode="hero" />
      </div>
      <div className="app-container">
        <div className={styles.content}>
          <p ref={kickerRef} className={styles.kicker}>
            NLP x 3D Floor Intelligence
          </p>
          <p ref={wowRef} className={styles.wow}>
            Just wow.
          </p>
          <h1 className={styles.title}>
            {HERO_HEADLINE.map((line, index) => (
              <span
                key={line}
                className={styles.titleLine}
                ref={(element) => {
                  lineRefs.current[index] = element;
                }}
              >
                {line}
              </span>
            ))}
          </h1>
          <p ref={subtitleRef} className={styles.subtitle}>
            {HERO_SUBTEXT}
          </p>
          <div ref={promptWrapRef}>
            <PromptBar onSubmit={handlePromptSubmit} />
          </div>
          <div ref={actionsRef} className={styles.actions}>
            <Link href="/studio" className="button-chip button-chip-solid">
              Open Studio
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
