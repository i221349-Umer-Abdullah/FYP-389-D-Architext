"use client";

import { PromptBar } from "@/components/hero/PromptBar";
import { GeneratorMode, WorkflowState } from "@/lib/types";

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
}: StudioPromptPanelProps) {
  const canSave = state === "ready" && Boolean(currentPrompt) && !isSavingProject;

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
        onSubmit={onSubmit}
        disabled={state === "building"}
        buttonLabel={state === "building" ? "Building..." : "Build Plan"}
        placeholder="Create a compact two-level plan with a double-height living volume and circulation around a central stair."
        className={styles.prompt}
      />

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
