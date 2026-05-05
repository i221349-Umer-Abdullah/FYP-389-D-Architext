"use client";

import { useMemo, useState } from "react";
import {
  computeCostBreakdown,
  type StyleId,
  type MaterialTier,
} from "@/lib/architectureStyles";
import { GenerationResult } from "@/lib/types";

import styles from "./CostBreakdownPanel.module.css";

function fmt(n: number) {
  if (n >= 10_000_000) return `Rs. ${(n / 10_000_000).toFixed(2)} Cr`;
  if (n >= 100_000)    return `Rs. ${(n / 100_000).toFixed(1)} L`;
  return `Rs. ${n.toLocaleString("en-PK")}`;
}

function fmtSqm(n: number) {
  return `Rs. ${n.toLocaleString("en-PK")} / m²`;
}

interface SingleEstimateProps {
  result: GenerationResult;
  label: string;
}

function SingleEstimate({ result, label }: SingleEstimateProps) {
  const [showRooms, setShowRooms] = useState(false);

  const cost = useMemo(
    () => computeCostBreakdown(result.rooms, result.styleId, result.materialTier),
    [result.rooms, result.styleId, result.materialTier],
  );

  const maxCatHigh = Math.max(...cost.categories.map((c) => c.high));

  return (
    <div className={styles.estimate}>
      <p className={styles.estimateLabel}>{label}</p>

      {/* Total cost hero */}
      <div className={styles.hero}>
        <span className={styles.heroRange}>
          {fmt(cost.totalLow)} – {fmt(cost.totalHigh)}
        </span>
        <span className={styles.heroBadges}>
          <span className={styles.badge}>{cost.styleLabel}</span>
          <span className={styles.badge}>{cost.tierLabel}</span>
        </span>
      </div>
      <p className={styles.perSqm}>
        {fmtSqm(cost.costPerSqmLow)}–{fmtSqm(cost.costPerSqmHigh)} &nbsp;·&nbsp; {cost.totalAreaM2.toFixed(1)} m² total
      </p>

      {/* Category bars */}
      <div className={styles.categories}>
        {cost.categories.map((cat) => (
          <div key={cat.name} className={styles.catRow}>
            <span className={styles.catName}>{cat.name}</span>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{ width: `${maxCatHigh > 0 ? (cat.high / maxCatHigh) * 100 : 0}%` }}
              />
            </div>
            <span className={styles.catRange}>
              {fmt(cat.low)}–{fmt(cat.high)}
            </span>
          </div>
        ))}
      </div>

      {/* Per-room toggle */}
      <button
        type="button"
        className={`button-chip ${styles.roomsToggle}`}
        onClick={() => setShowRooms((v) => !v)}
      >
        {showRooms ? "Hide room breakdown" : "Show room breakdown"}
      </button>

      {showRooms && (
        <table className={styles.roomTable}>
          <thead>
            <tr>
              <th>Room</th>
              <th>Area</th>
              <th>Estimated cost</th>
            </tr>
          </thead>
          <tbody>
            {cost.perRoom.map((r, i) => (
              <tr key={i}>
                <td className={styles.roomName}>{r.name.replace(/_/g, " ")}</td>
                <td className={styles.roomArea}>{r.area_m2.toFixed(1)} m²</td>
                <td className={styles.roomCost}>{fmt(r.low)}–{fmt(r.high)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

interface CostBreakdownPanelProps {
  llmResult: GenerationResult | null;
  gnnResult: GenerationResult | null;
}

export function CostBreakdownPanel({ llmResult, gnnResult }: CostBreakdownPanelProps) {
  if (!llmResult && !gnnResult) return null;

  return (
    <div className={styles.panel}>
      <p className={styles.panelTitle}>Cost Estimation</p>
      <p className={styles.panelNote}>
        Estimates are based on architecture style, material tier, and room areas.
        Actual costs vary by region, contractor, and site conditions.
      </p>

      <div className={styles.estimatesRow}>
        {llmResult && (
          <SingleEstimate result={llmResult} label="Primary Generator" />
        )}
        {gnnResult && (
          <SingleEstimate result={gnnResult} label="Competition" />
        )}
      </div>
    </div>
  );
}
