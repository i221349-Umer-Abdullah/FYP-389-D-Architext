"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

import { FEATURE_CARDS } from "@/lib/constants";

import styles from "./FeatureCards.module.css";

// ─── 3-D cube ─────────────────────────────────────────────────────────────────
const CUBE_HALF = 54;
const BASE_VERTS: [number, number, number][] = (
  [
    [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
    [-1, -1,  1], [1, -1,  1], [1, 1,  1], [-1, 1,  1],
  ] as [number, number, number][]
).map(([x, y, z]) => [x * CUBE_HALF, y * CUBE_HALF, z * CUBE_HALF]);

const CUBE_EDGES: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 0],
  [4, 5], [5, 6], [6, 7], [7, 4],
  [0, 4], [1, 5], [2, 6], [3, 7],
];

function rotY(v: [number, number, number], a: number): [number, number, number] {
  const c = Math.cos(a), s = Math.sin(a);
  return [v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c];
}
function rotX(v: [number, number, number], a: number): [number, number, number] {
  const c = Math.cos(a), s = Math.sin(a);
  return [v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c];
}
function proj(v: [number, number, number], cx: number, cy: number): [number, number] {
  const fov = 340, sc = fov / (fov + v[2]);
  return [cx + v[0] * sc, cy + v[1] * sc];
}

// ─── particles ────────────────────────────────────────────────────────────────
type PShape = "dot" | "line" | "box" | "bracket";
interface Particle {
  x: number; y: number; vx: number; vy: number;
  tx: number; ty: number;                        // snap target
  ox: number; oy: number;                        // orbit centre
  or: number; oa: number; os: number;            // orbit radius / angle / speed
  sz: number; shape: PShape; la: number; ll: number; // line angle / length
  col: 0 | 1 | 2;
  alpha: number;
}

// ─── phase ids & durations (ms) ───────────────────────────────────────────────
const PH = { BLOCK: 0, FRACTURE: 1, ORBIT: 2, SNAP: 3, DRAW: 4, REVEAL: 5 } as const;
type Phase = (typeof PH)[keyof typeof PH];
const DUR: Record<Phase, number> = { 0: 1500, 1: 520, 2: 1050, 3: 720, 4: 980, 5: 480 };
const N_PARTICLES = 165;

export function FeatureCards() {
  const wrapRef  = useRef<HTMLDivElement>(null);
  const gridRef  = useRef<HTMLDivElement>(null);
  const cvRef    = useRef<HTMLCanvasElement>(null);
  const cardEls  = useRef<(HTMLElement | null)[]>([null, null, null]);

  // mutable animation state kept in refs (no re-renders in the loop)
  const rafId    = useRef(0);
  const ps       = useRef<Particle[]>([]);
  const phRef    = useRef<Phase>(PH.BLOCK);
  const phStart  = useRef(0);
  const ryRef    = useRef(0);
  const rxRef    = useRef(0.32);
  const cvAlpha  = useRef(1);

  const [entered, setEntered]           = useState(false);
  const [cardsVisible, setCardsVisible] = useState(false);
  const [animDone, setAnimDone]         = useState(false);

  // ── trigger animation once on scroll-in ─────────────────────────────────────
  useEffect(() => {
    if (entered || !wrapRef.current) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setEntered(true); obs.disconnect(); } },
      { threshold: 0.25 },
    );
    obs.observe(wrapRef.current);
    return () => obs.disconnect();
  }, [entered]);

  // ── main canvas loop ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!entered || !cvRef.current || !wrapRef.current) return;

    const cv  = cvRef.current;
    const ctx = cv.getContext("2d")!;

    function resize() {
      if (!wrapRef.current) return;
      cv.width  = wrapRef.current.clientWidth;
      cv.height = wrapRef.current.clientHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    const cw = () => cv.width;
    const ch = () => cv.height;
    const cx = () => cw() / 2;
    const cy = () => ch() / 2;

    // measure actual card rects relative to the canvas / wrapper
    function cardRects() {
      if (!wrapRef.current) return [] as { x: number; y: number; w: number; h: number }[];
      const wR = wrapRef.current.getBoundingClientRect();
      return cardEls.current.map((el) => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: r.left - wR.left, y: r.top - wR.top, w: r.width, h: r.height };
      }).filter(Boolean) as { x: number; y: number; w: number; h: number }[];
    }

    // ── initialise particles ────────────────────────────────────────────────
    function initParticles() {
      const rects  = cardRects();
      const shapes: PShape[] = ["dot", "dot", "line", "line", "box", "bracket"];
      ps.current = Array.from({ length: N_PARTICLES }, (_, i) => {
        const col = (i % 3) as 0 | 1 | 2;
        const r   = rects[col];
        const tx  = r ? r.x + 20 + Math.random() * (r.w - 40) : cx();
        const ty  = r ? r.y + 20 + Math.random() * (r.h - 40) : cy();
        return {
          x: cx() + (Math.random() - 0.5) * 50,
          y: cy() + (Math.random() - 0.5) * 50,
          vx: 0, vy: 0, tx, ty,
          ox: cx() + (Math.random() - 0.5) * 130,
          oy: cy() + (Math.random() - 0.5) * 70,
          or: 55 + Math.random() * 130,
          oa: Math.random() * Math.PI * 2,
          os: (0.3 + Math.random() * 0.7) * (Math.random() > 0.5 ? 1 : -1) * 0.016,
          sz: 1 + Math.random() * 2.5,
          shape: shapes[Math.floor(Math.random() * shapes.length)],
          la: Math.random() * Math.PI,
          ll: 7 + Math.random() * 17,
          col, alpha: 0,
        };
      });
    }
    initParticles();

    // ── draw helpers ─────────────────────────────────────────────────────────
    function drawParticle(p: Particle) {
      const a = Math.max(0, p.alpha) * cvAlpha.current;
      if (a <= 0.01) return;
      ctx.globalAlpha = a;
      ctx.fillStyle   = "#0a0a0a";
      ctx.strokeStyle = "#0a0a0a";
      ctx.lineWidth   = 1;
      switch (p.shape) {
        case "dot":
          ctx.beginPath(); ctx.arc(p.x, p.y, p.sz, 0, Math.PI * 2); ctx.fill(); break;
        case "line": {
          const dx = Math.cos(p.la) * p.ll / 2, dy = Math.sin(p.la) * p.ll / 2;
          ctx.beginPath(); ctx.moveTo(p.x - dx, p.y - dy); ctx.lineTo(p.x + dx, p.y + dy); ctx.stroke(); break;
        }
        case "box":
          ctx.strokeRect(p.x - p.sz * 2, p.y - p.sz, p.sz * 4, p.sz * 2); break;
        case "bracket": {
          const s = p.sz * 2.8;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y + s); ctx.lineTo(p.x, p.y); ctx.lineTo(p.x + s, p.y);
          ctx.stroke(); break;
        }
      }
      ctx.globalAlpha = 1;
    }

    function drawCube(opacity: number) {
      if (opacity <= 0.01) return;
      const verts = BASE_VERTS.map(v => rotX(rotY(v, ryRef.current), rxRef.current));
      const bcx = cx(), bcy = cy();

      // main wireframe edges
      ctx.strokeStyle = `rgba(10,10,10,${0.78 * opacity})`;
      ctx.lineWidth   = 1.5;
      ctx.beginPath();
      for (const [a, b] of CUBE_EDGES) {
        const [x1, y1] = proj(verts[a], bcx, bcy);
        const [x2, y2] = proj(verts[b], bcx, bcy);
        ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
      }
      ctx.stroke();

      // vertex dots
      ctx.fillStyle = `rgba(10,10,10,${0.55 * opacity})`;
      for (const v of verts) {
        const [px, py] = proj(v, bcx, bcy);
        ctx.beginPath(); ctx.arc(px, py, 2.5, 0, Math.PI * 2); ctx.fill();
      }

      // cross-diagonal architectural detail lines
      ctx.strokeStyle = `rgba(10,10,10,${0.13 * opacity})`;
      ctx.lineWidth   = 1;
      ctx.beginPath();
      const [ax, ay] = proj(verts[6], bcx, bcy);
      const [bx2, by2] = proj(verts[0], bcx, bcy);
      const [cx2, cy2] = proj(verts[1], bcx, bcy);
      const [dx, dy]  = proj(verts[7], bcx, bcy);
      ctx.moveTo(ax, ay); ctx.lineTo(bx2, by2);
      ctx.moveTo(cx2, cy2); ctx.lineTo(dx, dy);
      ctx.stroke();

      // dimension-line tick marks at midpoints
      ctx.strokeStyle = `rgba(10,10,10,${0.22 * opacity})`;
      ctx.lineWidth   = 1;
      for (const [a, b] of [[0,1],[4,7],[2,6]] as [number,number][]) {
        const [x1, y1] = proj(verts[a], bcx, bcy);
        const [x2, y2] = proj(verts[b], bcx, bcy);
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        ctx.beginPath(); ctx.moveTo(mx - 5, my); ctx.lineTo(mx + 5, my); ctx.stroke();
      }
    }

    function drawBorders(progress: number) {
      const rects = cardRects();
      rects.forEach((r, i) => {
        const delay = i * 0.24;
        const p = Math.max(0, Math.min(1, (progress - delay) / 0.62));
        if (p <= 0) return;

        const perim = 2 * (r.w + r.h);
        let rem = perim * p;

        ctx.strokeStyle = `rgba(10,10,10,${0.22 * cvAlpha.current})`;
        ctx.lineWidth   = 1.5;
        ctx.beginPath();

        // draw clockwise: top → right → bottom → left
        const top = Math.min(rem, r.w);
        ctx.moveTo(r.x, r.y); ctx.lineTo(r.x + top, r.y); rem -= top;
        if (rem > 0) {
          const right = Math.min(rem, r.h);
          ctx.moveTo(r.x + r.w, r.y); ctx.lineTo(r.x + r.w, r.y + right); rem -= right;
        }
        if (rem > 0) {
          const bot = Math.min(rem, r.w);
          ctx.moveTo(r.x + r.w, r.y + r.h); ctx.lineTo(r.x + r.w - bot, r.y + r.h); rem -= bot;
        }
        if (rem > 0) {
          const left = Math.min(rem, r.h);
          ctx.moveTo(r.x, r.y + r.h); ctx.lineTo(r.x, r.y + r.h - left);
        }
        ctx.stroke();

        // corner accent dots when a corner is reached
        const corners = [
          { reached: p * perim >= r.w,             x: r.x + r.w, y: r.y },
          { reached: p * perim >= r.w + r.h,       x: r.x + r.w, y: r.y + r.h },
          { reached: p * perim >= r.w * 2 + r.h,   x: r.x,       y: r.y + r.h },
          { reached: p * perim >= perim - 1,        x: r.x,       y: r.y },
        ];
        ctx.fillStyle = `rgba(10,10,10,${0.35 * cvAlpha.current})`;
        for (const c of corners) {
          if (!c.reached) continue;
          ctx.beginPath(); ctx.arc(c.x, c.y, 3, 0, Math.PI * 2); ctx.fill();
        }
      });
    }

    // ── animation loop ───────────────────────────────────────────────────────
    phRef.current  = PH.BLOCK;
    phStart.current = performance.now();
    ryRef.current  = 0;
    rxRef.current  = 0.32;
    cvAlpha.current = 1;

    function loop(now: number) {
      rafId.current = requestAnimationFrame(loop);
      ctx.clearRect(0, 0, cw(), ch());

      const elapsed = now - phStart.current;
      const ph  = phRef.current;
      const dur = DUR[ph];
      const t   = Math.min(1, elapsed / dur);  // 0-1 phase progress

      // ── phase transitions ───────────────────────────────────────────────
      if (ph === PH.BLOCK && elapsed > dur) {
        phRef.current = PH.FRACTURE;
        phStart.current = now;
        // spawn particles at cube vertices with explosive velocities
        const verts = BASE_VERTS.map(v => rotX(rotY(v, ryRef.current), rxRef.current));
        ps.current.forEach((p, i) => {
          const [px, py] = proj(verts[i % 8], cx(), cy());
          p.x = px + (Math.random() - 0.5) * 22;
          p.y = py + (Math.random() - 0.5) * 22;
          const angle = Math.random() * Math.PI * 2;
          const speed = 5 + Math.random() * 13;
          p.vx = Math.cos(angle) * speed;
          p.vy = Math.sin(angle) * speed;
          p.ox = cx() + (Math.random() - 0.5) * 110;
          p.oy = cy() + (Math.random() - 0.5) * 65;
          p.alpha = 0.8;
        });

      } else if (ph === PH.FRACTURE && elapsed > dur) {
        phRef.current = PH.ORBIT;
        phStart.current = now;
        ps.current.forEach(p => {
          p.or = Math.max(40, Math.hypot(p.x - p.ox, p.y - p.oy) * 0.88);
          p.oa = Math.atan2(p.y - p.oy, p.x - p.ox);
        });

      } else if (ph === PH.ORBIT && elapsed > dur) {
        phRef.current = PH.SNAP;
        phStart.current = now;

      } else if (ph === PH.SNAP && elapsed > dur) {
        phRef.current = PH.DRAW;
        phStart.current = now;

      } else if (ph === PH.DRAW && elapsed > dur) {
        phRef.current = PH.REVEAL;
        phStart.current = now;
        setCardsVisible(true);

      } else if (ph === PH.REVEAL && elapsed > dur) {
        cancelAnimationFrame(rafId.current);
        ctx.clearRect(0, 0, cw(), ch());
        setAnimDone(true);
        return;
      }

      // ── render each phase ───────────────────────────────────────────────
      const fadeIn = Math.min(1, elapsed / 280);

      if (ph === PH.BLOCK) {
        ryRef.current += 0.019;
        rxRef.current  = 0.32 + Math.sin(ryRef.current * 0.42) * 0.13;
        drawCube(fadeIn);
      }

      else if (ph === PH.FRACTURE) {
        // cube crumbles away
        drawCube((1 - t) * 0.55);
        ps.current.forEach(p => {
          p.vx *= 0.88; p.vy *= 0.88;
          p.x  += p.vx;  p.y  += p.vy;
          p.la += 0.02;
          p.alpha = 0.5 + t * 0.45;
          drawParticle(p);
        });
      }

      else if (ph === PH.ORBIT) {
        ps.current.forEach(p => {
          p.oa += p.os;
          const tx = p.ox + Math.cos(p.oa) * p.or;
          const ty = p.oy + Math.sin(p.oa) * p.or * 0.52; // ellipse
          p.x  += (tx - p.x) * 0.07;
          p.y  += (ty - p.y) * 0.07;
          p.la += 0.009;
          p.alpha = 0.6 + Math.sin(p.oa * 2) * 0.15;
          drawParticle(p);
        });
      }

      else if (ph === PH.SNAP) {
        // ease-in-out — violent snap
        const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        ps.current.forEach(p => {
          const f = 0.04 + ease * 0.32;
          p.vx += (p.tx - p.x) * f; p.vy += (p.ty - p.y) * f;
          p.vx *= 0.66; p.vy *= 0.66;
          p.x  += p.vx;  p.y  += p.vy;
          p.alpha = 0.65 + ease * 0.35;
          drawParticle(p);
        });
      }

      else if (ph === PH.DRAW) {
        ps.current.forEach(p => {
          p.x += (p.tx - p.x) * 0.13; p.y += (p.ty - p.y) * 0.13;
          p.alpha = 0.35 * (1 - t * 0.75);
          drawParticle(p);
        });
        drawBorders(t);
      }

      else if (ph === PH.REVEAL) {
        cvAlpha.current = 1 - t;
        ps.current.forEach(p => { p.alpha = 0.1 * (1 - t); drawParticle(p); });
        drawBorders(1);
      }
    }

    rafId.current = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(rafId.current);
      window.removeEventListener("resize", resize);
    };
  }, [entered]);

  return (
    <div ref={wrapRef} className={styles.wrapper}>
      {/* canvas overlay — covers the grid during animation */}
      {!animDone && (
        <canvas ref={cvRef} className={styles.canvas} aria-hidden />
      )}

      {/* cards are always in the DOM (layout anchor for particle targets) */}
      <div ref={gridRef} className={styles.grid}>
        {FEATURE_CARDS.map((card, i) => (
          <motion.article
            key={card.title}
            ref={(el) => { cardEls.current[i] = el; }}
            className={styles.card}
            initial={{ opacity: 0 }}
            animate={{ opacity: cardsVisible ? 1 : 0 }}
            transition={{ duration: 0.55, delay: i * 0.12, ease: [0.16, 1, 0.3, 1] }}
          >
            <h3 className={styles.title}>{card.title}</h3>
            <p className={styles.text}>{card.description}</p>
          </motion.article>
        ))}
      </div>
    </div>
  );
}
