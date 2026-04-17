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
      "Bring Architext layouts into Blender for fast visualization, presentation, and review.",
    description:
      "The Blender plugin is planned for lightweight 3D review and presentation. It helps move generated spatial data into Blender so designers can inspect massing, materials, and scene composition outside the browser studio.",
    details: [
      "Import generated layout data into a Blender scene.",
      "Create quick visual studies from Architext floor-plan geometry.",
      "Use Blender as a presentation and rendering companion for generated plans.",
    ],
    downloadHref: "/plugins/architext-blender-plugin.zip",
    downloadLabel: "Download Blender Plugin",
  },
];

export function getPlugin(slug: string) {
  return PLUGINS.find((plugin) => plugin.slug === slug);
}
