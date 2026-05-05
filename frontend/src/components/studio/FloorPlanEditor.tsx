"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import Konva from "konva";
import { Stage, Layer, Rect, Text, Circle, Transformer } from "react-konva";
import { GenerationRoom } from "@/lib/types";
import styles from "./FloorPlanEditor.module.css";

// ── Palette: distinct warm beige family — each has its own hue lean ────────
const ROOM_COLORS: Record<string, string> = {
  living:   "#EDE6C8",  // warm straw yellow
  bedroom:  "#E0D0CC",  // soft dusty rose
  bathroom: "#C8D8E0",  // cool slate blue
  kitchen:  "#EAD49A",  // golden amber
  balcony:  "#C4DCBE",  // muted sage green
  dining:   "#E8C8AA",  // warm terracotta
  corridor: "#D0CCCA",  // neutral grey
  storage:  "#C4BEBC",  // darker grey-brown
  garage:   "#D4C8B4",  // warm stone
  study:    "#DDD8B8",  // khaki tan
  library:  "#D0C8B0",  // deeper khaki
  gym:      "#CCd0C4",  // cool sage grey
};
const DEFAULT_COLOR = "#D8D4CC";
const EDGE_COLOR    = "#5C4A3C"; // dark warm brown
const DOT_R         = 3;         // corner dot radius px

// ── Canvas constants ───────────────────────────────────────────────────────
const PAD      = 52;
const CANVAS_W = 700;
const CANVAS_H = 520;
const MIN_PX   = 18;

// ── Snap logic (all in metre coords) ──────────────────────────────────────
const TOUCH_EPS    = 0.15; // m — wall gap within this counts as already connected
const MIN_SHARE    = 0.3;  // m — minimum wall overlap enforced after snap

// Axis-aligned bounding box distance (0 if overlapping)
function bboxDist(a: GenerationRoom, b: GenerationRoom): number {
  const dx = Math.max(0, Math.max(a.x, b.x) - Math.min(a.x + a.width,  b.x + b.width));
  const dy = Math.max(0, Math.max(a.y, b.y) - Math.min(a.y + a.height, b.y + b.height));
  return Math.sqrt(dx * dx + dy * dy);
}

function isConnected(a: GenerationRoom, b: GenerationRoom): boolean {
  const ar = a.x + a.width,  ab = a.y + a.height;
  const br = b.x + b.width,  bb = b.y + b.height;
  // Shared wall on X axis: walls flush + Y overlap
  const yShare = Math.min(ab, bb) - Math.max(a.y, b.y);
  if (yShare > 0 && (Math.abs(ar - b.x) <= TOUCH_EPS || Math.abs(br - a.x) <= TOUCH_EPS))
    return true;
  // Shared wall on Y axis: walls flush + X overlap
  const xShare = Math.min(ar, br) - Math.max(a.x, b.x);
  if (xShare > 0 && (Math.abs(ab - b.y) <= TOUCH_EPS || Math.abs(bb - a.y) <= TOUCH_EPS))
    return true;
  return false;
}

function snapToNearest(dragged: GenerationRoom, others: GenerationRoom[]): GenerationRoom {
  if (!others.length) return dragged;

  // Already properly connected to something — leave as-is
  if (others.some(o => isConnected(dragged, o))) return dragged;

  // Find nearest room by bounding-box distance
  const nearest = others.reduce((best, o) =>
    bboxDist(dragged, o) < bboxDist(dragged, best) ? o : best
  );

  const o  = nearest;
  const dr = dragged.x + dragged.width;
  const db = dragged.y + dragged.height;
  const or = o.x + o.width;
  const ob = o.y + o.height;

  // 4 wall-to-wall candidates against the nearest room
  type WSnap = { axis: 'x'; dist: number; val: number } | { axis: 'y'; dist: number; val: number };
  const candidates: WSnap[] = [
    { axis: 'x', dist: Math.abs(dr      - o.x), val: o.x - dragged.width }, // drag.right → target.left
    { axis: 'x', dist: Math.abs(dragged.x - or), val: or },                  // drag.left  → target.right
    { axis: 'y', dist: Math.abs(db      - o.y), val: o.y - dragged.height }, // drag.bot   → target.top
    { axis: 'y', dist: Math.abs(dragged.y - ob), val: ob },                  // drag.top   → target.bot
  ];

  const best = candidates.reduce((a, b) => a.dist < b.dist ? a : b);

  let newX = dragged.x;
  let newY = dragged.y;

  if (best.axis === 'x') {
    newX = best.val;
    // Ensure Y overlap so walls actually connect — clamp into target's Y range
    const yLo = o.y  - dragged.height + MIN_SHARE;
    const yHi = ob - MIN_SHARE;
    if (yHi >= yLo) newY = Math.max(yLo, Math.min(yHi, newY));
  } else {
    newY = best.val;
    // Ensure X overlap so walls actually connect — clamp into target's X range
    const xLo = o.x  - dragged.width + MIN_SHARE;
    const xHi = or - MIN_SHARE;
    if (xHi >= xLo) newX = Math.max(xLo, Math.min(xHi, newX));
  }

  return { ...dragged, x: newX, y: newY };
}

// ── Component ──────────────────────────────────────────────────────────────
interface FloorPlanEditorProps {
  rooms: GenerationRoom[];
  onComplete: (rooms: GenerationRoom[]) => void;
  onCancel: () => void;
}

export function FloorPlanEditor({ rooms, onComplete, onCancel }: FloorPlanEditorProps) {
  // Fixed transform derived once from initial rooms
  const { minX, minY, scale } = useMemo(() => {
    const minX    = Math.min(...rooms.map(r => r.x));
    const minY    = Math.min(...rooms.map(r => r.y));
    const layoutW = Math.max(...rooms.map(r => r.x + r.width))  - minX;
    const layoutH = Math.max(...rooms.map(r => r.y + r.height)) - minY;
    const scale   = Math.min(
      (CANVAS_W - PAD * 2) / layoutW,
      (CANVAS_H - PAD * 2) / layoutH,
    );
    return { minX, minY, scale };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Size conversion (no offset)
  const toMeter  = useCallback((px: number) => px / scale, [scale]);
  // Position conversion — must undo the PAD + minX/Y offsets
  const fromCanvasX = useCallback((px: number) => (px - PAD) / scale + minX, [scale, minX]);
  const fromCanvasY = useCallback((py: number) => (py - PAD) / scale + minY, [scale, minY]);

  // Canvas coords for a room (top-left x/y + size)
  const rc = useCallback((room: GenerationRoom) => ({
    cx: (room.x - minX) * scale + PAD,
    cy: (room.y - minY) * scale + PAD,
    cw: Math.max(room.width  * scale, MIN_PX),
    ch: Math.max(room.height * scale, MIN_PX),
  }), [minX, minY, scale]);

  const [localRooms, setLocalRooms] = useState<GenerationRoom[]>(() =>
    rooms.map(r => ({ ...r }))
  );
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const trRef    = useRef<Konva.Transformer>(null);
  const rectRefs = useRef<(Konva.Rect | null)[]>([]);

  // Sync transformer to selected rect
  useEffect(() => {
    if (!trRef.current) return;
    if (selectedIdx !== null && rectRefs.current[selectedIdx]) {
      trRef.current.nodes([rectRefs.current[selectedIdx]!]);
    } else {
      trRef.current.nodes([]);
    }
    trRef.current.getLayer()?.batchDraw();
  }, [selectedIdx]);

  const handleDragEnd = useCallback(
    (e: Konva.KonvaEventObject<DragEvent>, i: number) => {
      const node = e.target as Konva.Rect;
      setLocalRooms(prev => {
        const moved: GenerationRoom = {
          ...prev[i],
          x: fromCanvasX(node.x()),
          y: fromCanvasY(node.y()),
        };
        const others = prev.filter((_, idx) => idx !== i);
        const snapped = snapToNearest(moved, others);

        // Imperatively move the node to the snapped position so the
        // visual update is immediate and not deferred to React re-render
        node.x((snapped.x - minX) * scale + PAD);
        node.y((snapped.y - minY) * scale + PAD);
        node.getLayer()?.batchDraw();

        const next = [...prev];
        next[i] = snapped;
        return next;
      });
    },
    [fromCanvasX, fromCanvasY, minX, minY, scale],
  );

  const handleTransformEnd = useCallback(
    (i: number) => {
      const node = rectRefs.current[i];
      if (!node) return;
      const newW = Math.max(node.width()  * node.scaleX(), MIN_PX);
      const newH = Math.max(node.height() * node.scaleY(), MIN_PX);
      node.scaleX(1); node.scaleY(1);
      node.width(newW); node.height(newH);
      setLocalRooms(prev => {
        const next = [...prev];
        next[i] = {
          ...next[i],
          x:       fromCanvasX(node.x()),
          y:       fromCanvasY(node.y()),
          width:   toMeter(newW),
          height:  toMeter(newH),
          area_m2: toMeter(newW) * toMeter(newH),
        };
        return next;
      });
    },
    [fromCanvasX, fromCanvasY, toMeter],
  );

  const legendTypes = [...new Set(rooms.map(r => r.type))];

  return (
    <div
      className={styles.overlay}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div className={styles.modal}>
        <div className={styles.header}>
          <div>
            <h3 className={styles.title}>Edit Floor Plan</h3>
            <p className={styles.hint}>
              Click to select · Drag to move · Handles to resize · Auto-snaps to nearest wall
            </p>
          </div>
          <button className={styles.closeBtn} onClick={onCancel}>✕</button>
        </div>

        <div className={styles.canvasWrap}>
          <Stage
            width={CANVAS_W}
            height={CANVAS_H}
            onMouseDown={(e) => {
              if (e.target === e.target.getStage()) setSelectedIdx(null);
            }}
          >
            <Layer>
              {/* ── Room fills ── */}
              {localRooms.map((room, i) => {
                const { cx, cy, cw, ch } = rc(room);
                const isSelected = selectedIdx === i;
                return (
                  <Rect
                    key={`rect-${i}`}
                    ref={(node) => { rectRefs.current[i] = node; }}
                    x={cx} y={cy} width={cw} height={ch}
                    fill={ROOM_COLORS[room.type] ?? DEFAULT_COLOR}
                    stroke={EDGE_COLOR}
                    strokeWidth={1}
                    shadowBlur={isSelected ? 14 : 0}
                    shadowColor="rgba(92, 74, 60, 0.5)"
                    draggable
                    onClick={() => setSelectedIdx(i)}
                    onTap={() => setSelectedIdx(i)}
                    onDragEnd={(e) => handleDragEnd(e, i)}
                    onTransformEnd={() => handleTransformEnd(i)}
                  />
                );
              })}

              {/* ── Corner dots ── */}
              {localRooms.flatMap((room, i) => {
                const { cx, cy, cw, ch } = rc(room);
                return [
                  <Circle key={`d${i}0`} x={cx}      y={cy}      radius={DOT_R} fill={EDGE_COLOR} listening={false} />,
                  <Circle key={`d${i}1`} x={cx + cw} y={cy}      radius={DOT_R} fill={EDGE_COLOR} listening={false} />,
                  <Circle key={`d${i}2`} x={cx}      y={cy + ch} radius={DOT_R} fill={EDGE_COLOR} listening={false} />,
                  <Circle key={`d${i}3`} x={cx + cw} y={cy + ch} radius={DOT_R} fill={EDGE_COLOR} listening={false} />,
                ];
              })}

              {/* ── Labels (non-interactive, on top) ── */}
              {localRooms.map((room, i) => {
                const { cx, cy, cw, ch } = rc(room);
                const label    = room.type.charAt(0).toUpperCase() + room.type.slice(1);
                const fontSize = Math.max(9, Math.min(12, cw / 6));
                return (
                  <Text
                    key={`lbl-${i}`}
                    x={cx} y={cy + ch / 2 - fontSize / 2}
                    width={cw}
                    text={label}
                    fontSize={fontSize}
                    fill="#3E2E24"
                    align="center"
                    listening={false}
                  />
                );
              })}

              <Transformer
                ref={trRef}
                rotateEnabled={false}
                borderStroke={EDGE_COLOR}
                anchorStroke={EDGE_COLOR}
                anchorFill="#F5EDE4"
                anchorSize={8}
                borderDash={[4, 3]}
                boundBoxFunc={(oldBox, newBox) =>
                  newBox.width < MIN_PX || newBox.height < MIN_PX ? oldBox : newBox
                }
              />
            </Layer>
          </Stage>
        </div>

        <div className={styles.footer}>
          <div className={styles.legend}>
            {legendTypes.map(type => (
              <span key={type} className={styles.legendItem}>
                <span
                  className={styles.legendDot}
                  style={{
                    background: ROOM_COLORS[type] ?? DEFAULT_COLOR,
                    border: `1.5px solid ${EDGE_COLOR}`,
                  }}
                />
                {type}
              </span>
            ))}
          </div>
          <div className={styles.actions}>
            <button className={styles.cancelBtn} onClick={onCancel}>Cancel</button>
            <button className={styles.applyBtn} onClick={() => onComplete(localRooms)}>
              Apply to 3D
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
