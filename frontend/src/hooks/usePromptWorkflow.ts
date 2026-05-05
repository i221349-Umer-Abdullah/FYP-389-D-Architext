"use client";

import { useCallback, useRef, useState } from "react";
import { GenerationResult, GeneratorMode, WorkflowState } from "@/lib/types";
import {
  DEFAULT_MATERIAL_TIER,
  DEFAULT_STYLE_ID,
  type MaterialTier,
  type StyleId,
} from "@/lib/architectureStyles";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS  = 120_000;

async function startJob(prompt: string, mode: "llm" | "gnn"): Promise<string> {
  const res = await fetch(`${API}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: prompt, generator_mode: mode }),
  });
  if (!res.ok) throw new Error(`Backend error ${res.status}`);
  const data = (await res.json()) as { job_id: string };
  return data.job_id;
}

async function pollUntilDone(
  jobId: string,
  styleId: StyleId,
  materialTier: MaterialTier,
): Promise<GenerationResult> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;

  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));

    const res = await fetch(`${API}/api/status/${jobId}`);
    if (!res.ok) throw new Error(`Status check failed for ${jobId}`);
    const data = await res.json();

    if (data.status === "failed") throw new Error(data.error ?? "Generation failed");

    if (data.status === "done") {
      const rooms = data.preview?.rooms ?? [];
      return {
        jobId,
        mode: "llm",
        rooms,
        roomCount:    data.preview?.room_count    ?? rooms.length,
        totalAreaM2:  data.preview?.total_area_m2 ?? 0,
        previewUrl:   `${API}/api/preview/${jobId}`,
        ifcDownloadUrl: `${API}/api/download/${jobId}`,
        styleId,
        materialTier,
      };
    }
  }

  throw new Error("Generation timed out after 2 minutes");
}

interface UsePromptWorkflowResult {
  state: WorkflowState;
  currentPrompt: string;
  mode: GeneratorMode;
  setMode: (m: GeneratorMode) => void;
  selectedStyle: StyleId;
  setSelectedStyle: (id: StyleId) => void;
  selectedTier: MaterialTier;
  setSelectedTier: (t: MaterialTier) => void;
  llmResult: GenerationResult | null;
  gnnResult: GenerationResult | null;
  buildMessage: string;
  submitPrompt: (prompt: string) => Promise<void>;
  reset: () => void;
}

export function usePromptWorkflow(): UsePromptWorkflowResult {
  const [state, setState]               = useState<WorkflowState>("idle");
  const [currentPrompt, setCurrentPrompt] = useState("");
  const [mode, setMode]                 = useState<GeneratorMode>("both");
  const [selectedStyle, setSelectedStyle] = useState<StyleId>(DEFAULT_STYLE_ID);
  const [selectedTier, setSelectedTier]   = useState<MaterialTier>(DEFAULT_MATERIAL_TIER);
  const [llmResult, setLlmResult]       = useState<GenerationResult | null>(null);
  const [gnnResult, setGnnResult]       = useState<GenerationResult | null>(null);
  const [buildMessage, setBuildMessage] = useState("");
  const abortRef = useRef(false);

  const submitPrompt = useCallback(
    async (prompt: string) => {
      const cleaned = prompt.trim();
      if (!cleaned) { setState("error"); return; }

      // Capture style/tier at submission time so results are locked to them
      const lockedStyle = selectedStyle;
      const lockedTier  = selectedTier;

      abortRef.current = false;
      setCurrentPrompt(cleaned);
      setLlmResult(null);
      setGnnResult(null);
      setState("building");
      setBuildMessage("Starting generation...");

      try {
        const runLlm = mode === "llm" || mode === "both";
        const runGnn = mode === "gnn" || mode === "both";
        const jobs: Array<Promise<void>> = [];

        if (runLlm) {
          jobs.push(
            (async () => {
              setBuildMessage("Generating floor plan layout...");
              const jobId = await startJob(cleaned, "llm");
              const result = await pollUntilDone(jobId, lockedStyle, lockedTier);
              if (!abortRef.current) setLlmResult({ ...result, mode: "llm" });
            })(),
          );
        }

        if (runGnn) {
          jobs.push(
            (async () => {
              const jobId = await startJob(cleaned, "gnn");
              const result = await pollUntilDone(jobId, lockedStyle, lockedTier);
              if (!abortRef.current) setGnnResult({ ...result, mode: "gnn" });
            })(),
          );
        }

        await Promise.all(jobs);

        if (!abortRef.current) {
          setState("ready");
          setBuildMessage("");
        }
      } catch (err) {
        if (!abortRef.current) {
          setState("error");
          setBuildMessage(err instanceof Error ? err.message : "Generation failed");
        }
      }
    },
    [mode, selectedStyle, selectedTier],
  );

  const reset = useCallback(() => {
    abortRef.current = true;
    setState("idle");
    setCurrentPrompt("");
    setLlmResult(null);
    setGnnResult(null);
    setBuildMessage("");
  }, []);

  return {
    state, currentPrompt, mode, setMode,
    selectedStyle, setSelectedStyle,
    selectedTier, setSelectedTier,
    llmResult, gnnResult, buildMessage,
    submitPrompt, reset,
  };
}
