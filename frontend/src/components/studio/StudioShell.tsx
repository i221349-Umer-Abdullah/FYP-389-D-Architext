"use client";

import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { usePromptWorkflow } from "@/hooks/usePromptWorkflow";
import { GeneratorMode } from "@/lib/types";
import { createFileSlug } from "@/lib/projectExport";

import { GenerationStatus } from "./GenerationStatus";
import { StudioPromptPanel } from "./StudioPromptPanel";
import { StyleSelector } from "./StyleSelector";
import { CostBreakdownPanel } from "./CostBreakdownPanel";
import { FloorPlanEditor } from "./FloorPlanEditor";
import styles from "./StudioShell.module.css";

const GeneratorCanvas = dynamic(
  () => import("./GeneratorCanvas").then((m) => ({ default: m.GeneratorCanvas })),
  { ssr: false, loading: () => <div className={styles.canvasFallback} aria-hidden /> },
);

const MODE_OPTIONS: { value: GeneratorMode; label: string }[] = [
  { value: "both", label: "Compare Both" },
  { value: "llm",  label: "Primary Only" },
  { value: "gnn",  label: "Competition Only" },
];

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function StudioShell() {
  const searchParams = useSearchParams();
  const initialPromptUsed = useRef(false);
  const {
    state, currentPrompt, mode, setMode,
    selectedStyle, setSelectedStyle,
    selectedTier, setSelectedTier,
    llmResult, gnnResult, buildMessage,
    submitPrompt, reset,
  } = usePromptWorkflow();
  const [isSavingProject, setIsSavingProject] = useState(false);
  const [saveMessage, setSaveMessage]         = useState("");
  const [saveError, setSaveError]             = useState("");
  const [show2D, setShow2D]                   = useState(false);
  const [showCost, setShowCost]               = useState(false);
  const [editingGenerator, setEditingGenerator] = useState<"llm" | "gnn" | null>(null);
  const [editedLlmRooms, setEditedLlmRooms]   = useState<import("@/lib/types").GenerationRoom[] | null>(null);
  const [editedGnnRooms, setEditedGnnRooms]   = useState<import("@/lib/types").GenerationRoom[] | null>(null);
  const [downloadingIfc, setDownloadingIfc]   = useState<"llm" | "gnn" | null>(null);

  useEffect(() => {
    if (initialPromptUsed.current) return;
    const seededPrompt = searchParams.get("prompt");
    if (seededPrompt?.trim()) {
      initialPromptUsed.current = true;
      void submitPrompt(seededPrompt);
    }
  }, [searchParams, submitPrompt]);

  useEffect(() => {
    if (state === "building") {
      setEditedLlmRooms(null);
      setEditedGnnRooms(null);
      setShowCost(false);
    }
    if (state === "ready") {
      setShowCost(true);
    }
  }, [state]);

  async function downloadIfc(source: "llm" | "gnn") {
    const result      = source === "llm" ? llmResult : gnnResult;
    const editedRooms = source === "llm" ? editedLlmRooms : editedGnnRooms;
    if (!result) return;

    if (!editedRooms) {
      window.location.href = result.ifcDownloadUrl;
      return;
    }

    setDownloadingIfc(source);
    try {
      const res = await fetch(`${API}/api/ifc-from-rooms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rooms: editedRooms, prompt: currentPrompt }),
      });
      if (!res.ok) throw new Error(`IFC generation failed (${res.status})`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = "architext-floor-plan.ifc";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("IFC download error:", err);
    } finally {
      setDownloadingIfc(null);
    }
  }

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
      if (!result) throw new Error("No result to save.");

      const pngResponse = await fetch(result.previewUrl);
      if (!pngResponse.ok) throw new Error("Could not fetch floor plan image.");
      const pngBlob = await pngResponse.blob();
      const fileName = `${createFileSlug(currentPrompt)}.png`;
      const file = new File([pngBlob], fileName, { type: "image/png" });

      const primaryRooms =
        editedLlmRooms ?? llmResult?.rooms ??
        editedGnnRooms ?? gnnResult?.rooms ?? [];

      const studioData = JSON.stringify({
        format: "architext-studio-project",
        version: 1,
        prompt: currentPrompt,
        generatedAt: new Date().toISOString(),
        architectureStyle: selectedStyle,
        materialTier: selectedTier,
        rooms: primaryRooms,
        llm: llmResult
          ? { rooms: editedLlmRooms ?? llmResult.rooms, totalAreaM2: llmResult.totalAreaM2, styleId: llmResult.styleId, materialTier: llmResult.materialTier }
          : null,
        gnn: gnnResult
          ? { rooms: editedGnnRooms ?? gnnResult.rooms, totalAreaM2: gnnResult.totalAreaM2, styleId: gnnResult.styleId, materialTier: gnnResult.materialTier }
          : null,
      });

      const formData = new FormData();
      formData.set("title", `Generated: ${currentPrompt.slice(0, 82)}`);
      formData.set("description", `${result.roomCount} rooms · ${result.totalAreaM2.toFixed(1)} m² · ${result.styleId}`);
      formData.set("file", file);
      formData.set("studioData", studioData);

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
  const hasResults = (llmResult ?? gnnResult) !== null;

  return (
    <section className={styles.section}>
      <div className="app-container">
        <div className={styles.layout}>
          {/* ── Left column: prompt panel + style selector ── */}
          <div className={styles.leftColumn}>
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
              has2DResults={hasResults}
            />

            <StyleSelector
              selectedStyle={selectedStyle}
              selectedTier={selectedTier}
              onStyleChange={setSelectedStyle}
              onTierChange={setSelectedTier}
              disabled={state === "building"}
            />
          </div>

          {/* ── Right column: viewports ── */}
          <div className={styles.canvasPanel}>
            <GenerationStatus state={state} message={buildMessage} />

            <div className={`${styles.viewportsRow} ${!showLlm || !showGnn ? styles.single : ""}`}>
              {showLlm && (
                <div className={styles.viewport}>
                  <GeneratorCanvas
                    key={`llm-${mode}`}
                    state={state}
                    rooms={editedLlmRooms ?? llmResult?.rooms ?? null}
                    label="Primary Generator"
                    styleId={llmResult?.styleId ?? selectedStyle}
                  />
                  <div className={styles.viewportFooter}>
                    <span className={styles.viewportMeta}>
                      {llmResult
                        ? `${llmResult.roomCount} rooms · ${llmResult.totalAreaM2.toFixed(1)} m²`
                        : state === "building" ? "Generating..." : "—"}
                    </span>
                    <div style={{ display: "flex", gap: 8 }}>
                      {llmResult && (
                        <button className="button-chip" onClick={() => setEditingGenerator("llm")}>
                          Edit 2D
                        </button>
                      )}
                      {llmResult && (
                        <button
                          className="button-chip button-chip-solid"
                          disabled={downloadingIfc === "llm"}
                          onClick={() => void downloadIfc("llm")}
                        >
                          {downloadingIfc === "llm" ? "Generating…" : editedLlmRooms ? "Download Edited IFC" : "Download IFC"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {showGnn && (
                <div className={styles.viewport}>
                  <GeneratorCanvas
                    key={`gnn-${mode}`}
                    state={state}
                    rooms={editedGnnRooms ?? gnnResult?.rooms ?? null}
                    label="Competition"
                    styleId={gnnResult?.styleId ?? selectedStyle}
                  />
                  <div className={styles.viewportFooter}>
                    <span className={styles.viewportMeta}>
                      {gnnResult
                        ? `${gnnResult.roomCount} rooms · ${gnnResult.totalAreaM2.toFixed(1)} m²`
                        : state === "building" ? "Generating..." : "—"}
                    </span>
                    <div style={{ display: "flex", gap: 8 }}>
                      {gnnResult && (
                        <button className="button-chip" onClick={() => setEditingGenerator("gnn")}>
                          Edit 2D
                        </button>
                      )}
                      {gnnResult && (
                        <button
                          className="button-chip button-chip-solid"
                          disabled={downloadingIfc === "gnn"}
                          onClick={() => void downloadIfc("gnn")}
                        >
                          {downloadingIfc === "gnn" ? "Generating…" : editedGnnRooms ? "Download Edited IFC" : "Download IFC"}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── 2D floor plan overlay ── */}
        {editingGenerator === "llm" && llmResult && (
          <FloorPlanEditor
            rooms={editedLlmRooms ?? llmResult.rooms}
            onComplete={(updated) => { setEditedLlmRooms(updated); setEditingGenerator(null); }}
            onCancel={() => setEditingGenerator(null)}
          />
        )}

        {editingGenerator === "gnn" && gnnResult && (
          <FloorPlanEditor
            rooms={editedGnnRooms ?? gnnResult.rooms}
            onComplete={(updated) => { setEditedGnnRooms(updated); setEditingGenerator(null); }}
            onCancel={() => setEditingGenerator(null)}
          />
        )}

        {/* ── 2D PNG preview cards ── */}
        {show2D && hasResults && (
          <div className={styles.floorPlanCard}>
            <p className={styles.floorPlanTitle}>2D Floor Plans</p>
            <div className={styles.floorPlanRow}>
              {llmResult && (
                <div className={styles.floorPlanItem}>
                  <span className={styles.floorPlanLabel}>Primary Generator</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={llmResult.previewUrl} alt="Primary Generator 2D floor plan" className={styles.floorPlanImg} />
                  <span className={styles.floorPlanMeta}>
                    {llmResult.roomCount} rooms · {llmResult.totalAreaM2.toFixed(1)} m²
                  </span>
                </div>
              )}
              {gnnResult && (
                <div className={styles.floorPlanItem}>
                  <span className={styles.floorPlanLabel}>Competition</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={gnnResult.previewUrl} alt="Competition 2D floor plan" className={styles.floorPlanImg} />
                  <span className={styles.floorPlanMeta}>
                    {gnnResult.roomCount} rooms · {gnnResult.totalAreaM2.toFixed(1)} m²
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Cost breakdown panel ── */}
        {showCost && hasResults && (
          <CostBreakdownPanel
            llmResult={llmResult}
            gnnResult={gnnResult}
          />
        )}
      </div>
    </section>
  );
}
