export type WorkflowState = "idle" | "building" | "ready" | "error";
export type GeneratorMode = "llm" | "gnn" | "both";

export interface GenerationRoom {
  name: string;
  type: string;
  area_m2: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface GenerationResult {
  jobId: string;
  mode: "llm" | "gnn";
  rooms: GenerationRoom[];
  roomCount: number;
  totalAreaM2: number;
  previewUrl: string;
  ifcDownloadUrl: string;
}

export interface PromptSubmission {
  prompt: string;
  submittedAt: number;
}

export interface FloorPlanPart {
  id: string;
  position: [number, number, number];
  size: [number, number, number];
}

export interface StudioSceneProps {
  state: WorkflowState;
  disassemblyProgress: number;
}

export interface LineRevealTextProps {
  lines: string[];
  once?: boolean;
}

export interface FeatureCardItem {
  title: string;
  description: string;
}
