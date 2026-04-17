"use client";

import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { usePromptWorkflow } from "@/hooks/usePromptWorkflow";
import { GeneratorMode } from "@/lib/types";
import { createFileSlug } from "@/lib/projectExport";

import { GenerationStatus } from "./GenerationStatus";
import { StudioPromptPanel } from "./StudioPromptPanel";
import styles from "./StudioShell.module.css";

const GeneratorCanvas = dynamic(
  () => import("./GeneratorCanvas").then((m) => ({ default: m.GeneratorCanvas })),
  { ssr: false, loading: () => <div className={styles.canvasFallback} aria-hidden /> },
);

const MODE_OPTIONS: { value: GeneratorMode; label: string }[] = [
  { value: "both", label: "Compare Both" },
  { value: "llm",  label: "LLM Only" },
  { value: "gnn",  label: "GNN Only" },
];

export function StudioShell() {
  const searchParams = useSearchParams();
  const initialPromptUsed = useRef(false);
  const {
    state, currentPrompt, mode, setMode,
    llmResult, gnnResult, buildMessage,
    submitPrompt, reset,
  } = usePromptWorkflow();
  const [isSavingProject, setIsSavingProject] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const [show2D, setShow2D] = useState(false);

  useEffect(() => {
    if (initialPromptUsed.current) return;
    const seededPrompt = searchParams.get("prompt");
    if (seededPrompt?.trim()) {
      initialPromptUsed.current = true;
      void submitPrompt(seededPrompt);
    }
  }, [searchParams, submitPrompt]);

  async function saveGeneratedProject() {
    if (state !== "ready" || !currentPrompt.trim()) {
      setSaveError("Build a plan before saving it to the library.");
      return;
    }
    setIsSavingProject(true);
    setSaveMessage("");
    setSaveError("");
    try {
      const result = llmResult ?? gnnResult;
      const contents = JSON.stringify({
        format: "architext-studio-project",
        version: 1,
        prompt: currentPrompt,
        generatedAt: new Date().toISOString(),
        llm: llmResult ? { rooms: llmResult.rooms, totalAreaM2: llmResult.totalAreaM2 } : null,
        gnn: gnnResult ? { rooms: gnnResult.rooms, totalAreaM2: gnnResult.totalAreaM2 } : null,
      }, null, 2);
      const fileName = `${createFileSlug(currentPrompt)}.architext-project.json`;
      const file = new File([contents], fileName, { type: "application/json" });
      const formData = new FormData();
      formData.set("title", `Generated: ${currentPrompt.slice(0, 82)}`);
      formData.set("description", result
        ? `${result.roomCount} rooms · ${result.totalAreaM2.toFixed(1)} m²`
        : "Generated in Architext Studio");
      formData.set("file", file);
      const response = await fetch("/api/floor-plans", { method: "POST", body: formData });
      const payload = (await response.json()) as { error?: string };
      if (!response.ok) throw new Error(payload.error ?? "Could not save project.");
      setSaveMessage("Saved to your library.");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Could not save project.");
    } finally {
      setIsSavingProject(false);
    }
  }

  const showLlm = mode === "llm" || mode === "both";
  const showGnn = mode === "gnn" || mode === "both";

  return (
    <section className={styles.section}>
      <div className="app-container">
        <div className={styles.layout}>
          <StudioPromptPanel
            state={state}
            currentPrompt={currentPrompt}
            mode={mode}
            modeOptions={MODE_OPTIONS}
            onModeChange={setMode}
            onSubmit={submitPrompt}
            onReset={reset}
            onSaveProject={() => void saveGeneratedProject()}
            isSavingProject={isSavingProject}
            saveMessage={saveMessage}
            saveError={saveError}
            buildMessage={buildMessage}
            show2D={show2D}
            onToggle2D={() => setShow2D((v) => !v)}
            has2DResults={(llmResult ?? gnnResult) !== null}
          />

          <div className={styles.canvasPanel}>
            <GenerationStatus state={state} message={buildMessage} />

            <div className={`${styles.viewportsRow} ${!showLlm || !showGnn ? styles.single : ""}`}>
              {showLlm && (
                <div className={styles.viewport}>
                  <GeneratorCanvas
                    state={state}
                    rooms={llmResult?.rooms ?? null}
                    label="LLM Generator"
                  />
                  <div className={styles.viewportFooter}>
                    <span className={styles.viewportMeta}>
                      {llmResult
                        ? `${llmResult.roomCount} rooms · ${llmResult.totalAreaM2.toFixed(1)} m²`
                        : state === "building" ? "Generating..." : "—"}
                    </span>
                    {llmResult && (
                      <a href={llmResult.ifcDownloadUrl} download className="button-chip button-chip-solid">
                        Download IFC
                      </a>
                    )}
                  </div>
                </div>
              )}

              {showGnn && (
                <div className={styles.viewport}>
                  <GeneratorCanvas
                    state={state}
                    rooms={gnnResult?.rooms ?? null}
                    label="StructuralGNN"
                  />
                  <div className={styles.viewportFooter}>
                    <span className={styles.viewportMeta}>
                      {gnnResult
                        ? `${gnnResult.roomCount} rooms · ${gnnResult.totalAreaM2.toFixed(1)} m²`
                        : state === "building" ? "Generating..." : "—"}
                    </span>
                    {gnnResult && (
                      <a href={gnnResult.ifcDownloadUrl} download className="button-chip button-chip-solid">
                        Download IFC
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {show2D && (llmResult ?? gnnResult) && (
          <div className={styles.floorPlanCard}>
            <p className={styles.floorPlanTitle}>2D Floor Plans</p>
            <div className={styles.floorPlanRow}>
              {llmResult && (
                <div className={styles.floorPlanItem}>
                  <span className={styles.floorPlanLabel}>LLM Generator</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={llmResult.previewUrl} alt="LLM 2D floor plan" className={styles.floorPlanImg} />
                  <span className={styles.floorPlanMeta}>
                    {llmResult.roomCount} rooms · {llmResult.totalAreaM2.toFixed(1)} m²
                  </span>
                </div>
              )}
              {gnnResult && (
                <div className={styles.floorPlanItem}>
                  <span className={styles.floorPlanLabel}>StructuralGNN</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={gnnResult.previewUrl} alt="GNN 2D floor plan" className={styles.floorPlanImg} />
                  <span className={styles.floorPlanMeta}>
                    {gnnResult.roomCount} rooms · {gnnResult.totalAreaM2.toFixed(1)} m²
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
