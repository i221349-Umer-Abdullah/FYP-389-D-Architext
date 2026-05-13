import {
  type StyleId,
  type MaterialTier,
  MATERIAL_TIER_MULTIPLIERS,
  getStyle,
} from "./architectureStyles";

export type MaterialCategory = "structure" | "finishes" | "services";

export interface MaterialItem {
  key: string;
  name: string;
  unit: string;
  quantity: number;
  category: MaterialCategory;
}

export interface MaterialsBreakdown {
  items: MaterialItem[];
  totalAreaM2: number;
  styleLabel: string;
  tierLabel: string;
}

// ── Base quantities per m² of total covered floor area ────────────────────────
// Baseline: Modern / Standard tier — Pakistani RCC frame + brick infill construction
const BASE: Record<string, number> = {
  // Structure (grey structure)
  cement_bags:        10.5,   // 50 kg bags — foundation, columns/beams, slab, plaster
  sand_tonnes:         1.90,  // fine aggregate, metric tonnes
  aggregate_tonnes:    1.45,  // coarse crush, metric tonnes
  steel_kg:           45.0,   // rebar for all RCC elements
  bricks:            450,     // standard Pakistani brick 9"×4.5"×3"
  // Finishes
  floor_sqm:           1.10,  // floor tiles/marble (incl. 10 % wastage)
  wall_tiles_sqm:      0.35,  // bathroom + kitchen wall tiles per m² total
  timber_cft:          3.50,  // doors, windows, shutters, frames
  glass_sqft:          2.20,  // windows and glass panels
  paint_litres:        0.55,  // interior + exterior
  // Services rough-in
  pvc_pipes_m:         0.85,  // plumbing conduit
  elec_conduit_m:      1.25,  // electrical conduit + wiring
  waterproofing_m2:    0.18,  // roof waterproofing membrane
};

// ── Style-specific multipliers on the base quantities ────────────────────────
interface StyleExtras {
  key: string;
  name: string;
  unit: string;
  category: MaterialCategory;
  perSqm: number;
}

interface StyleMults {
  [key: string]: number | StyleExtras[] | undefined;
  extras?: StyleExtras[];
}

const STYLE_MULTS: Record<string, StyleMults> = {
  modern: {
    // More glass + steel, less brick (open-plan, curtain walls)
    cement_bags: 1.00, sand_tonnes: 0.85, aggregate_tonnes: 1.10,
    steel_kg: 1.35, bricks: 0.55,
    floor_sqm: 1.15, wall_tiles_sqm: 1.10, timber_cft: 0.65,
    glass_sqft: 2.20, paint_litres: 1.10,
    pvc_pipes_m: 1.10, elec_conduit_m: 1.20, waterproofing_m2: 1.10,
  },

  mughal: {
    // Heavy masonry load-bearing, no structural steel frame,
    // lime plaster replaces cement plaster, stone/mosaic floor instead of tiles
    cement_bags: 0.72, sand_tonnes: 1.55, aggregate_tonnes: 0.62,
    steel_kg: 0.28, bricks: 1.72,
    floor_sqm: 0.45, wall_tiles_sqm: 0.18, timber_cft: 0.88,
    glass_sqft: 0.20, paint_litres: 0.12,
    pvc_pipes_m: 0.85, elec_conduit_m: 0.80, waterproofing_m2: 1.15,
    extras: [
      { key: "lime_bags",   name: "Lime — Khaki Chuna",            unit: "50 kg bags", category: "structure", perSqm: 10.0 },
      { key: "stone_cladding", name: "Sandstone / Marble Cladding", unit: "sq ft",     category: "finishes",  perSqm: 3.20 },
    ],
  },

  mediterranean: {
    // Stucco exterior, terracotta roof tiles, tile-heavy finishes
    cement_bags: 1.05, sand_tonnes: 1.15, aggregate_tonnes: 1.00,
    steel_kg: 0.95, bricks: 1.05,
    floor_sqm: 1.55, wall_tiles_sqm: 1.35, timber_cft: 0.88,
    glass_sqft: 1.05, paint_litres: 1.38,
    pvc_pipes_m: 1.00, elec_conduit_m: 1.05, waterproofing_m2: 1.25,
    extras: [
      { key: "terracotta", name: "Terracotta Roof Tiles", unit: "m²", category: "finishes", perSqm: 0.88 },
    ],
  },

  victorian: {
    // Timber-heavy (roof trusses + ornate joinery), minimal RCC,
    // clay/slate roof, hardwood or parquet floor instead of tiles
    cement_bags: 0.70, sand_tonnes: 0.90, aggregate_tonnes: 0.62,
    steel_kg: 0.38, bricks: 1.30,
    floor_sqm: 0.22, wall_tiles_sqm: 0.80, timber_cft: 4.30,
    glass_sqft: 1.32, paint_litres: 1.42,
    pvc_pipes_m: 0.90, elec_conduit_m: 0.98, waterproofing_m2: 1.40,
    extras: [
      { key: "struct_timber", name: "Structural Timber — Roof Trusses & Framing", unit: "cft", category: "structure", perSqm: 3.80 },
      { key: "clay_roof",     name: "Clay / Slate Roof Tiles",                    unit: "m²",  category: "finishes",  perSqm: 0.92 },
    ],
  },

  haveli: {
    // Very heavy brick masonry, lime mortar, thick walls, minimal steel,
    // brick/stone floor, timber for jharokhas and verandas
    cement_bags: 0.52, sand_tonnes: 1.32, aggregate_tonnes: 0.48,
    steel_kg: 0.20, bricks: 1.92,
    floor_sqm: 0.35, wall_tiles_sqm: 0.22, timber_cft: 1.90,
    glass_sqft: 0.25, paint_litres: 0.15,
    pvc_pipes_m: 0.80, elec_conduit_m: 0.75, waterproofing_m2: 0.90,
    extras: [
      { key: "lime_bags", name: "Lime — Khaki Chuna / Surki", unit: "50 kg bags", category: "structure", perSqm: 14.0 },
    ],
  },
};

// ── Tier quantity multipliers ─────────────────────────────────────────────────
// Grey structure is nearly unchanged; finishes and joinery shift more.
const TIER_MULTS: Record<MaterialTier, Partial<Record<string, number>>> = {
  budget: {
    cement_bags: 0.97, aggregate_tonnes: 0.95, steel_kg: 0.92, bricks: 0.95,
    floor_sqm: 0.90, wall_tiles_sqm: 0.88,
    timber_cft: 0.80, glass_sqft: 0.75, paint_litres: 0.82,
  },
  standard: {},
  premium: {
    cement_bags: 1.06, steel_kg: 1.05,
    floor_sqm: 1.08, wall_tiles_sqm: 1.15,
    timber_cft: 1.48, glass_sqft: 1.38, paint_litres: 1.22,
  },
};

// ── Tier-aware label overrides ────────────────────────────────────────────────
const FLOOR_LABEL: Record<MaterialTier, string> = {
  budget:   "Floor Tiles — Cement Mosaic",
  standard: "Floor Tiles — Ceramic / Porcelain",
  premium:  "Marble Flooring",
};

const PAINT_LABEL: Record<MaterialTier, string> = {
  budget:   "Distemper Paint",
  standard: "Emulsion Paint",
  premium:  "Premium Emulsion / Textured Finish",
};

const TIMBER_LABEL: Partial<Record<string, string>> = {
  victorian: "Timber — Structural + Doors & Windows",
  haveli:    "Timber — Jharokhas, Shutters & Frames",
  mughal:    "Timber — Doors & Ornate Panels",
};

// ── Core items definition ─────────────────────────────────────────────────────
// Each entry: [key, label-override-fn | string, unit, category]
type CoreDef = [string, string, string, MaterialCategory];

function getCoreItems(styleId: string, tier: MaterialTier): CoreDef[] {
  return [
    // Structure
    ["cement_bags",       "Cement (50 kg bags)",              "bags",   "structure"],
    ["sand_tonnes",       "Sand — Fine Aggregate",            "tonnes", "structure"],
    ["aggregate_tonnes",  "Coarse Aggregate — Crush",         "tonnes", "structure"],
    ["steel_kg",          "Steel Rebar",                      "kg",     "structure"],
    ["bricks",            "Bricks (Standard 9\"×4.5\"×3\")", "units",  "structure"],
    // Finishes
    ["floor_sqm",         FLOOR_LABEL[tier],                  "m²",     "finishes"],
    ["wall_tiles_sqm",    "Wall Tiles — Bathroom & Kitchen",  "m²",     "finishes"],
    ["timber_cft",        TIMBER_LABEL[styleId] ?? "Timber — Doors, Windows & Frames", "cft", "finishes"],
    ["glass_sqft",        "Glass — Windows & Panels",         "sq ft",  "finishes"],
    ["paint_litres",      PAINT_LABEL[tier],                  "litres", "finishes"],
    // Services
    ["pvc_pipes_m",       "PVC Plumbing Pipes",               "metres", "services"],
    ["elec_conduit_m",    "Electrical Conduit & Wiring",      "metres", "services"],
    ["waterproofing_m2",  "Waterproofing Membrane",           "m²",     "services"],
  ];
}

// ── Main export ───────────────────────────────────────────────────────────────
export function computeMaterialsBreakdown(
  rooms: Array<{ type: string; area_m2: number }>,
  styleId: StyleId,
  tier: MaterialTier,
): MaterialsBreakdown {
  const style  = getStyle(styleId);
  const sMults = STYLE_MULTS[styleId] ?? {};
  const tMults = TIER_MULTS[tier];
  const area   = rooms.reduce((s, r) => s + r.area_m2, 0);

  function qty(key: string): number {
    const base = BASE[key] ?? 0;
    const sm   = (sMults as Record<string, number>)[key] ?? 1.0;
    const tm   = tMults[key] ?? 1.0;
    return Math.round(base * sm * tm * area * 10) / 10;
  }

  const coreItems: MaterialItem[] = getCoreItems(styleId, tier).map(
    ([key, name, unit, category]) => ({ key, name, unit, quantity: qty(key), category }),
  );

  const extras = (sMults.extras as StyleExtras[] | undefined) ?? [];
  const extraItems: MaterialItem[] = extras.map((e) => ({
    key:      e.key,
    name:     e.name,
    unit:     e.unit,
    quantity: Math.round(e.perSqm * area * 10) / 10,
    category: e.category,
  }));

  // Interleave extras into correct category order
  const byCategory = (cat: MaterialCategory) => [
    ...coreItems.filter((i) => i.category === cat),
    ...extraItems.filter((i) => i.category === cat),
  ];

  const items: MaterialItem[] = [
    ...byCategory("structure"),
    ...byCategory("finishes"),
    ...byCategory("services"),
  ];

  return {
    items,
    totalAreaM2: area,
    styleLabel: style.label,
    tierLabel:  MATERIAL_TIER_MULTIPLIERS[tier].label,
  };
}
