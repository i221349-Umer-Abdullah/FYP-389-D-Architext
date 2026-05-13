"use client";

import { useState } from "react";
import { PromptBar } from "@/components/hero/PromptBar";
import { GeneratorMode, PlotConstraint, WorkflowState } from "@/lib/types";
import type { StyleId } from "@/lib/architectureStyles";
import { usePromptHistory } from "@/hooks/usePromptHistory";
import { AreaInput } from "./AreaInput";
import { StyleSelector } from "./StyleSelector";

import styles from "./StudioPromptPanel.module.css";

interface ModeOption {
  value: GeneratorMode;
  label: string;
}

interface StudioPromptPanelProps {
  state: WorkflowState;
  currentPrompt: string;
  mode: GeneratorMode;
  modeOptions: ModeOption[];
  onModeChange: (m: GeneratorMode) => void;
  onSubmit: (prompt: string) => Promise<void>;
  onReset: () => void;
  onSaveProject: () => void;
  isSavingProject: boolean;
  saveMessage: string;
  saveError: string;
  buildMessage: string;
  show2D: boolean;
  onToggle2D: () => void;
  has2DResults: boolean;
  plotConstraint: PlotConstraint | null;
  onPlotChange: (dims: PlotConstraint | null) => void;
  selectedStyle: StyleId;
  onStyleChange: (id: StyleId) => void;
  onExportPDF?: () => void;
  isExportingPDF?: boolean;
}

export function StudioPromptPanel({
  state,
  currentPrompt,
  mode,
  modeOptions,
  onModeChange,
  onSubmit,
  onReset,
  onSaveProject,
  isSavingProject,
  saveMessage,
  saveError,
  buildMessage,
  show2D,
  onToggle2D,
  has2DResults,
  plotConstraint,
  onPlotChange,
  selectedStyle,
  onStyleChange,
  onExportPDF,
  isExportingPDF = false,
}: StudioPromptPanelProps) {
  const canSave = state === "ready" && Boolean(currentPrompt) && !isSavingProject;
  const { history, addEntry, clearHistory } = usePromptHistory();
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = async (prompt: string) => {
    addEntry(prompt);
    await onSubmit(prompt);
  };

  const handleHistoryClick = async (entry: string) => {
    if (state === "building") return;
    addEntry(entry);
    await onSubmit(entry);
  };

  return (
    <aside className={styles.panel}>
      <p className={styles.kicker}>3D Analysis Workspace</p>
      <h1 className={styles.title}>Compose a floor intent, then inspect it in motion.</h1>

      <div className={styles.modeRow}>
        {modeOptions.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`button-chip${mode === opt.value ? " button-chip-solid" : ""}`}
            onClick={() => onModeChange(opt.value)}
            disabled={state === "building"}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <PromptBar
        onSubmit={handleSubmit}
        disabled={state === "building"}
        buttonLabel={state === "building" ? "Building..." : "Build Plan"}
        placeholder="e.g. 3 bedroom house in 10 marla, modern style with a veranda and parking"
        className={styles.prompt}
        multiline
      />

      {/* ── Advanced options toggle ─────────────────────────────────────── */}
      <button
        type="button"
        className={styles.advancedToggle}
        onClick={() => setShowAdvanced((v) => !v)}
        aria-expanded={showAdvanced}
      >
        <span className={`${styles.chevron}${showAdvanced ? ` ${styles.chevronOpen}` : ""}`}>▼</span>
        {showAdvanced ? "Hide options" : "Plot size, style & recent prompts"}
      </button>

      <div className={`${styles.advanced}${showAdvanced ? ` ${styles.advancedOpen}` : ""}`}>
        <div className={styles.advancedInner}>
          <AreaInput
            value={plotConstraint}
            onChange={onPlotChange}
            disabled={state === "building"}
          />

          <StyleSelector
            selectedStyle={selectedStyle}
            onStyleChange={onStyleChange}
            disabled={state === "building"}
            showTier={false}
          />

          {history.length > 0 && (
            <div className={styles.history}>
              <div className={styles.historyHeader}>
                <span className={styles.historyLabel}>Recent prompts</span>
                <button
                  type="button"
                  className={styles.historyClear}
                  onClick={clearHistory}
                  aria-label="Clear history"
                >
                  Clear
                </button>
              </div>
              <div className={styles.historyList}>
                {history.map((entry, i) => (
                  <button
                    key={i}
                    type="button"
                    className={styles.historyChip}
                    onClick={() => void handleHistoryClick(entry)}
                    disabled={state === "building"}
                    title={entry}
                  >
                    {entry.length > 38 ? entry.slice(0, 35) + "…" : entry}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {buildMessage ? (
        <p className={styles.buildMessage}>{buildMessage}</p>
      ) : currentPrompt ? (
        <p className={styles.promptEcho}>
          Last prompt: <span>{currentPrompt}</span>
        </p>
      ) : null}

      <div className={styles.actions}>
        <button
          type="button"
          className="button-chip"
          onClick={onReset}
          disabled={state === "building"}
        >
          Reset
        </button>
        <button
          type="button"
          className={`button-chip${show2D ? " button-chip-solid" : ""}`}
          onClick={onToggle2D}
          disabled={!has2DResults}
        >
          {show2D ? "Hide 2D Plans" : "Show 2D Plans"}
        </button>
        <button
          type="button"
          className="button-chip button-chip-solid"
          onClick={onSaveProject}
          disabled={!canSave}
        >
          {isSavingProject ? "Saving..." : "Save to Library"}
        </button>
        {onExportPDF && (
          <button
            type="button"
            className="button-chip"
            onClick={onExportPDF}
            disabled={!has2DResults || isExportingPDF || state === "building"}
          >
            {isExportingPDF ? "Generating PDF..." : "Export PDF"}
          </button>
        )}
      </div>

      {saveError ? <p className={styles.saveError}>{saveError}</p> : null}
      {saveMessage ? <p className={styles.saveMessage}>{saveMessage}</p> : null}

      <p className={styles.downloadHint}>
        {state === "ready"
          ? "Download IFC files from the floor plan cards below."
          : "Build a plan first to unlock project save and IFC download."}
      </p>
    </aside>
  );
}
