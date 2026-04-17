import { FLOOR_PLAN_PARTS } from "@/lib/constants";

const PROJECT_ROOMS = [
  {
    id: "living-room",
    name: "Living Room",
    type: "social",
    areaSqm: 28,
    level: 0,
    position: { x: 0, y: 0 },
    size: { width: 4.8, depth: 5.8 },
  },
  {
    id: "kitchen",
    name: "Kitchen",
    type: "service",
    areaSqm: 14,
    level: 0,
    position: { x: -3.2, y: 1.8 },
    size: { width: 3.2, depth: 4.4 },
  },
  {
    id: "bedroom-primary",
    name: "Primary Bedroom",
    type: "private",
    areaSqm: 18,
    level: 0,
    position: { x: 3.1, y: -1.4 },
    size: { width: 3.6, depth: 5 },
  },
  {
    id: "bathroom",
    name: "Bathroom",
    type: "service",
    areaSqm: 6,
    level: 0,
    position: { x: -3.1, y: -2.1 },
    size: { width: 2, depth: 3 },
  },
];

function createProjectId() {
  return `architext-${Date.now().toString(36)}`;
}

export function createFileSlug(value: string) {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 42);

  return slug || "generated-plan";
}

export function createStudioProject(prompt: string) {
  const generatedAt = new Date().toISOString();

  return {
    format: "architext-studio-project",
    version: 1,
    projectId: createProjectId(),
    generatedAt,
    prompt,
    units: "meters",
    aiSummary: {
      intent: "Natural-language floor plan converted into structured spatial data.",
      status: "frontend-simulated",
      exportTargets: ["Revit", "Blender", "IFC BIM workflow"],
    },
    floorPlan: {
      levels: 1,
      rooms: PROJECT_ROOMS,
      parts: FLOOR_PLAN_PARTS,
    },
  };
}

export function downloadStudioProject(prompt: string) {
  const project = createStudioProject(prompt);
  const contents = JSON.stringify(project, null, 2);
  const blob = new Blob([contents], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = `${createFileSlug(prompt)}.architext-project.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
