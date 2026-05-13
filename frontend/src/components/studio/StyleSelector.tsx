"use client";

import {
  ARCHITECTURE_STYLES,
  MATERIAL_TIER_MULTIPLIERS,
  type StyleId,
  type MaterialTier,
} from "@/lib/architectureStyles";

import styles from "./StyleSelector.module.css";

interface StyleSelectorProps {
  selectedStyle: StyleId;
  onStyleChange: (id: StyleId) => void;
  selectedTier?: MaterialTier;
  onTierChange?: (tier: MaterialTier) => void;
  disabled?: boolean;
  showTier?: boolean;
}

export function StyleSelector({
  selectedStyle,
  onStyleChange,
  selectedTier,
  onTierChange,
  disabled = false,
  showTier = true,
}: StyleSelectorProps) {
  return (
    <div className={`${styles.root}${disabled ? ` ${styles.disabled}` : ""}`}>
      <p className={styles.sectionLabel}>Architecture Style</p>
      <p className={styles.hint}>Selected style applies on next generation.</p>

      <div className={styles.styleGrid}>
        {ARCHITECTURE_STYLES.map((style) => {
          const active = style.id === selectedStyle;
          return (
            <button
              key={style.id}
              type="button"
              disabled={disabled}
              onClick={() => onStyleChange(style.id)}
              className={`${styles.styleCard}${active ? ` ${styles.activeCard}` : ""}`}
            >
              {/* Color swatch row */}
              <span className={styles.swatches}>
                <span
                  className={styles.swatch}
                  style={{ background: style.visuals.wallColor, border: `1px solid ${style.visuals.edgeColor}` }}
                />
                <span
                  className={styles.swatch}
                  style={{ background: style.visuals.slabColor }}
                />
              </span>
              <span className={styles.cardName}>{style.label}</span>
              <span className={styles.cardDesc}>{style.description}</span>
              <span className={styles.wallSpec}>
                {(style.visuals.wallThickness * 100).toFixed(0)} cm walls
              </span>
            </button>
          );
        })}
      </div>

      {showTier && selectedTier !== undefined && onTierChange && (
        <>
          <p className={styles.sectionLabel} style={{ marginTop: 18 }}>Material Tier</p>
          <div className={styles.tierRow}>
            {(Object.keys(MATERIAL_TIER_MULTIPLIERS) as MaterialTier[]).map((tier) => (
              <button
                key={tier}
                type="button"
                disabled={disabled}
                onClick={() => onTierChange(tier)}
                className={`button-chip${selectedTier === tier ? " button-chip-solid" : ""}`}
              >
                {MATERIAL_TIER_MULTIPLIERS[tier].label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
