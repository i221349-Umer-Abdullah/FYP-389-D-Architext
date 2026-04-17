import { FeatureCardItem, FloorPlanPart } from "@/lib/types";

export const APP_TITLE = "Architext";

export const SIMULATED_BUILD_MS = 2200;

export const HERO_HEADLINE = [
  "From natural language",
  "to IFC-ready BIM.",
];

export const HERO_SUBTEXT =
  "Describe your building intent once. Architext presents a premium flow from prompt to room layout JSON and downloadable IFC output.";

export const STORY_LINES = [
  "The AI extracts rooms, sizes, adjacencies, and constraints from one prompt.",
  "Spatial reasoning turns requirements into a connected floor-plan structure.",
  "Generated data stays ready for preview, refinement, and BIM export.",
];

export const FEATURE_CARDS: FeatureCardItem[] = [
  {
    title: "Prompt Understanding",
    description:
      "Parse natural language into rooms, counts, relationships, and practical planning constraints.",
  },
  {
    title: "Spatial Intelligence",
    description:
      "Reason about adjacency, circulation, proportions, and layout hierarchy before generating the plan.",
  },
  {
    title: "BIM-Ready Output",
    description:
      "Prepare structured room JSON and IFC-oriented data for downstream Revit, Blender, and review workflows.",
  },
];

export const FLOOR_PLAN_PARTS: FloorPlanPart[] = [
  { id: "slab-core", position: [0, -0.2, 0], size: [8.4, 0.35, 6.4] },
  { id: "wall-north", position: [0, 1.05, -3], size: [8.2, 2.1, 0.22] },
  { id: "wall-south", position: [0, 1.05, 3], size: [8.2, 2.1, 0.22] },
  { id: "wall-west", position: [-4.1, 1.05, 0], size: [0.22, 2.1, 6] },
  { id: "wall-east", position: [4.1, 1.05, 0], size: [0.22, 2.1, 6] },
  { id: "core-partition-a", position: [-1.15, 1.05, 0], size: [0.18, 2.1, 6] },
  { id: "core-partition-b", position: [1.4, 1.05, 0.5], size: [0.18, 2.1, 5.1] },
  { id: "room-divider-a", position: [0.2, 1.05, -1.6], size: [2.7, 2.1, 0.16] },
  { id: "room-divider-b", position: [-2.25, 1.05, 1.2], size: [3.2, 2.1, 0.16] },
  { id: "room-divider-c", position: [2.45, 1.05, 1.5], size: [2.6, 2.1, 0.16] },
  { id: "volume-block-a", position: [-2.7, 0.35, -1.9], size: [2, 0.7, 1.8] },
  { id: "volume-block-b", position: [2.15, 0.35, -1.25], size: [1.8, 0.7, 2.2] },
];
