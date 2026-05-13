"use client";

import { useMemo, useState } from "react";
import {
  computeCostBreakdown,
  MATERIAL_TIER_MULTIPLIERS,
  type StyleId,
  type MaterialTier,
} from "@/lib/architectureStyles";
import {
  computeMaterialsBreakdown,
  type MaterialCategory,
  type MaterialItem,
} from "@/lib/materialsEstimator";
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

function fmtQty(n: number) {
  return n % 1 === 0 ? n.toLocaleString("en-PK") : n.toFixed(1);
}

const CATEGORY_LABELS: Record<MaterialCategory, string> = {
  structure: "Grey Structure",
  finishes:  "Finishes",
  services:  "Services Rough-in",
};

function MaterialsTable({ items, area, styleLabel, tierLabel }: {
  items: MaterialItem[];
  area: number;
  styleLabel: string;
  tierLabel: string;
}) {
  const categories: MaterialCategory[] = ["structure", "finishes", "services"];
  return (
    <div className={styles.materialsWrap}>
      <p className={styles.materialsNote}>
        Approximate material quantities for {area.toFixed(1)} m² &nbsp;·&nbsp; {styleLabel} &nbsp;·&nbsp; {tierLabel}
      </p>
      {categories.map((cat) => {
        const group = items.filter((i) => i.category === cat);
        if (!group.length) return null;
        return (
          <div key={cat} className={styles.matGroup}>
            <p className={styles.matGroupLabel}>{CATEGORY_LABELS[cat]}</p>
            <table className={styles.matTable}>
              <tbody>
                {group.map((item) => (
                  <tr key={item.key}>
                    <td className={styles.matName}>{item.name}</td>
                    <td className={styles.matQty}>
                      <span className={styles.matQtyNum}>{fmtQty(item.quantity)}</span>
                      <span className={styles.matUnit}>{item.unit}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

interface SingleEstimateProps {
  result: GenerationResult;
  label: string;
  tierOverride: MaterialTier;
}

function SingleEstimate({ result, label, tierOverride }: SingleEstimateProps) {
  const [showRooms, setShowRooms]         = useState(false);
  const [showMaterials, setShowMaterials] = useState(false);

  const cost = useMemo(
    () => computeCostBreakdown(result.rooms, result.styleId, tierOverride),
    [result.rooms, result.styleId, tierOverride],
  );

  const materials = useMemo(
    () => computeMaterialsBreakdown(result.rooms, result.styleId, tierOverride),
    [result.rooms, result.styleId, tierOverride],
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
      <div className={styles.toggleRow}>
        <button
          type="button"
          className={`button-chip ${styles.roomsToggle}`}
          onClick={() => setShowRooms((v) => !v)}
        >
          {showRooms ? "Hide room breakdown" : "Show room breakdown"}
        </button>
        <button
          type="button"
          className={`button-chip ${styles.roomsToggle}`}
          onClick={() => setShowMaterials((v) => !v)}
        >
          {showMaterials ? "Hide materials list" : "Show materials list"}
        </button>
      </div>

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

      {showMaterials && (
        <MaterialsTable
          items={materials.items}
          area={materials.totalAreaM2}
          styleLabel={materials.styleLabel}
          tierLabel={materials.tierLabel}
        />
      )}
    </div>
  );
}

interface CostBreakdownPanelProps {
  llmResult: GenerationResult | null;
  gnnResult: GenerationResult | null;
  selectedTier: MaterialTier;
  onTierChange: (tier: MaterialTier) => void;
}

export function CostBreakdownPanel({ llmResult, gnnResult, selectedTier, onTierChange }: CostBreakdownPanelProps) {
  if (!llmResult && !gnnResult) return null;

  return (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <p className={styles.panelTitle}>Cost &amp; Materials Estimation</p>
        <div className={styles.tierRow}>
          {(Object.keys(MATERIAL_TIER_MULTIPLIERS) as MaterialTier[]).map((tier) => (
            <button
              key={tier}
              type="button"
              className={`button-chip${selectedTier === tier ? " button-chip-solid" : ""}`}
              onClick={() => onTierChange(tier)}
            >
              {MATERIAL_TIER_MULTIPLIERS[tier].label}
            </button>
          ))}
        </div>
      </div>
      <p className={styles.panelNote}>
        Estimates are based on architecture style, material tier, and room areas.
        Material quantities follow standard Pakistani residential construction norms.
        Actual costs and quantities vary by region, contractor, and site conditions.
      </p>

      <div className={styles.estimatesRow}>
        {llmResult && (
          <SingleEstimate result={llmResult} label="Primary Generator" tierOverride={selectedTier} />
        )}
        {gnnResult && (
          <SingleEstimate result={gnnResult} label="Competition" tierOverride={selectedTier} />
        )}
      </div>
    </div>
  );
}
