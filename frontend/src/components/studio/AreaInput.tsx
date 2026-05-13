"use client";

import { useState } from "react";
import {
  UNIT_LABELS,
  UNIT_PLACEHOLDERS,
  plotSummary,
  toPlotDims,
  type PlotDims,
  type PlotUnit,
} from "@/lib/plotUnits";

import styles from "./AreaInput.module.css";

const UNITS: PlotUnit[] = ["marla", "kanal", "sqm", "mxm", "ftxft"];
const DUAL_UNITS: PlotUnit[] = ["mxm", "ftxft"];

interface AreaInputProps {
  value: PlotDims | null;
  onChange: (dims: PlotDims | null) => void;
  disabled?: boolean;
}

export function AreaInput({ value, onChange, disabled = false }: AreaInputProps) {
  const [unit, setUnit]   = useState<PlotUnit>("marla");
  const [v1, setV1]       = useState("");
  const [v2, setV2]       = useState("");

  const isDual     = DUAL_UNITS.includes(unit);
  const placeholders = UNIT_PLACEHOLDERS[unit];
  const preview    = toPlotDims(unit, v1, v2);

  function handleV1(val: string) {
    setV1(val);
    const dims = toPlotDims(unit, val, v2);
    onChange(dims);
  }

  function handleV2(val: string) {
    setV2(val);
    const dims = toPlotDims(unit, v1, val);
    onChange(dims);
  }

  function handleUnit(u: PlotUnit) {
    setUnit(u);
    setV1("");
    setV2("");
    onChange(null);
  }

  function handleClear() {
    setV1("");
    setV2("");
    onChange(null);
  }

  return (
    <div className={`${styles.root}${disabled ? ` ${styles.disabled}` : ""}`}>
      <div className={styles.labelRow}>
        <span className={styles.label}>Plot Size</span>
        <span className={styles.optional}>optional</span>
        {value && (
          <button type="button" className={styles.clearBtn} onClick={handleClear}>
            clear
          </button>
        )}
      </div>

      {/* Unit selector */}
      <div className={styles.unitRow}>
        {UNITS.map((u) => (
          <button
            key={u}
            type="button"
            disabled={disabled}
            onClick={() => handleUnit(u)}
            className={`${styles.unitChip}${unit === u ? ` ${styles.unitActive}` : ""}`}
          >
            {UNIT_LABELS[u]}
          </button>
        ))}
      </div>

      {/* Value input(s) */}
      <div className={styles.inputRow}>
        <input
          type="number"
          min="0"
          step="any"
          disabled={disabled}
          placeholder={placeholders[0]}
          value={v1}
          onChange={(e) => handleV1(e.target.value)}
          className={styles.numInput}
        />
        {isDual && (
          <>
            <span className={styles.times}>×</span>
            <input
              type="number"
              min="0"
              step="any"
              disabled={disabled}
              placeholder={placeholders[1]}
              value={v2}
              onChange={(e) => handleV2(e.target.value)}
              className={styles.numInput}
            />
          </>
        )}
        <span className={styles.unitSuffix}>
          {unit === "mxm" ? "m" : unit === "ftxft" ? "ft" : UNIT_LABELS[unit]}
        </span>
      </div>

      {/* Live preview */}
      {preview ? (
        <p className={`${styles.preview} ${styles.previewOk}`}>
          {plotSummary(preview)}
        </p>
      ) : (v1 || v2) ? (
        <p className={`${styles.preview} ${styles.previewErr}`}>
          Enter valid positive values
        </p>
      ) : (
        <p className={styles.preview}>
          House layout will scale to fit this plot
        </p>
      )}
    </div>
  );
}
