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
      "The Revit plugin is planned as the desktop bridge between generated floor-plan data and native Revit model authoring. It gives the team one place to import Architext output, review rooms and wall intent, then continue the BIM workflow in Autodesk Revit.",
    details: [
      "Import generated room and wall structure from Architext output.",
      "Prepare the imported layout for Revit families, levels, and BIM documentation.",
      "Keep the generated model workflow close to the tools architects already use.",
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
