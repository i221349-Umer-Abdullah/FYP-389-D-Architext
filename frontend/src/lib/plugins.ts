export type PluginSlug = "revit" | "blender";

export type PluginInfo = {
  slug: PluginSlug;
  name: string;
  eyebrow: string;
  summary: string;
  description: string;
  details: string[];
  downloadHref: string;
  downloadLabel: string;
};

export const PLUGINS: PluginInfo[] = [
  {
    slug: "revit",
    name: "Revit Plugin",
    eyebrow: "BIM authoring",
    summary:
      "Send Architext floor-plan output into Revit and prepare model data for BIM workflows.",
    description:
      "The Revit plugin is the desktop bridge between generated Architext layouts and native Revit model authoring. It calls the local FastAPI backend, generates a Primary GNN or LLM baseline floor plan, downloads the IFC output, and imports or opens it in Autodesk Revit.",
    details: [
      "Generate a floor plan from a prompt directly inside Revit.",
      "Defaults to the Primary GNN generator with an LLM Baseline option for comparison.",
      "Downloads the generated IFC and imports or opens it in Revit for BIM review.",
      "Requires the Architext backend running locally at localhost:8000.",
    ],
    downloadHref: "/plugins/architext-revit-plugin.zip",
    downloadLabel: "Download Revit Plugin",
  },
  {
    slug: "blender",
    name: "Blender Plugin",
    eyebrow: "3D visualization",
    summary:
      "Generate IFC floor plans directly inside Blender using natural language prompts.",
    description:
      "The Blender addon connects Architext's generation pipeline to Blender. Type a prompt, click Generate Building, and the addon calls the backend, exports an IFC file, and imports it into your scene — all without leaving Blender. Requires the Architext backend running locally and BlenderBIM for best IFC results.",
    details: [
      "Type a natural language prompt and generate a full IFC building model in one click.",
      "Auto-imports the generated IFC into the current Blender scene.",
      "Quick Generate mode: specify room counts directly for faster iteration.",
      "Compatible with BlenderBIM for full IFC visibility and editing.",
      "Requires Architext backend (localhost:8000) and Python venv configured in addon preferences.",
    ],
    downloadHref: "/plugins/architext-blender-plugin.zip",
    downloadLabel: "Download Blender Plugin",
  },
];

export function getPlugin(slug: string) {
  return PLUGINS.find((plugin) => plugin.slug === slug);
}
