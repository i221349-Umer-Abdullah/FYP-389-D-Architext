export type StyleId =
  | "modern"
  | "mughal"
  | "mediterranean"
  | "victorian"
  | "haveli";

export type MaterialTier = "budget" | "standard" | "premium";

export interface StyleVisuals {
  wallColor: string;
  slabColor: string;
  edgeColor: string;
  wallRoughness: number;
  wallMetalness: number;
  slabRoughness: number;
  wallThickness: number;  // metres
  ceilingHeight: number;  // metres
  canvasBg: string;
}

export interface CostRange {
  low: number;   // PKR per sqm
  high: number;
}

export interface CostFactors {
  foundation: number;
  structure: number;
  electrical: number;
  plumbing: number;
  hvac: number;
  finishes: number;
  roofing: number;
  misc: number;
}

export interface ArchitectureStyle {
  id: StyleId;
  label: string;
  description: string;
  visuals: StyleVisuals;
  costPerSqm: CostRange;
  costFactors: CostFactors;
}

// highMultiplier: applied to style.costPerSqm.high to get the tier's ceiling price
// lowRatio: low = high × lowRatio  (controls how tight the range is)
export const MATERIAL_TIER_MULTIPLIERS: Record<MaterialTier, { label: string; highMultiplier: number; lowRatio: number }> = {
  budget:   { label: "Budget",   highMultiplier: 1.00, lowRatio: 0.58 },
  standard: { label: "Standard", highMultiplier: 1.95, lowRatio: 0.63 },
  premium:  { label: "Premium",  highMultiplier: 3.20, lowRatio: 0.69 },
};

export const ARCHITECTURE_STYLES: ArchitectureStyle[] = [
  {
    id: "modern",
    label: "Modern",
    description: "Clean lines, open spaces, glass & concrete",
    visuals: {
      wallColor: "#F2F2F2", slabColor: "#1C1C1E", edgeColor: "#CCCCCC",
      wallRoughness: 0.15, wallMetalness: 0.08, slabRoughness: 0.55,
      wallThickness: 0.10, ceilingHeight: 3.0, canvasBg: "#F5F5F5",
    },
    costPerSqm: { low: 35_000, high: 70_000 },
    costFactors: { foundation: 0.10, structure: 0.20, electrical: 0.09, plumbing: 0.09, hvac: 0.09, finishes: 0.28, roofing: 0.08, misc: 0.07 },
  },
  {
    id: "mughal",
    label: "Mughal",
    description: "Sandstone arches, ornate symmetry, high vaulted ceilings",
    visuals: {
      wallColor: "#E8D5A3", slabColor: "#5C3D1E", edgeColor: "#C4965A",
      wallRoughness: 0.82, wallMetalness: 0.02, slabRoughness: 0.88,
      wallThickness: 0.30, ceilingHeight: 3.5, canvasBg: "#FBF5E8",
    },
    costPerSqm: { low: 55_000, high: 100_000 },
    costFactors: { foundation: 0.12, structure: 0.24, electrical: 0.07, plumbing: 0.08, hvac: 0.05, finishes: 0.34, roofing: 0.06, misc: 0.04 },
  },
  {
    id: "mediterranean",
    label: "Mediterranean",
    description: "Stucco walls, terracotta roofs, warm earthy palette",
    visuals: {
      wallColor: "#F5ECD7", slabColor: "#7A4A2E", edgeColor: "#C8956A",
      wallRoughness: 0.80, wallMetalness: 0.01, slabRoughness: 0.85,
      wallThickness: 0.20, ceilingHeight: 2.8, canvasBg: "#FBF6EE",
    },
    costPerSqm: { low: 40_000, high: 78_000 },
    costFactors: { foundation: 0.12, structure: 0.21, electrical: 0.08, plumbing: 0.10, hvac: 0.06, finishes: 0.27, roofing: 0.11, misc: 0.05 },
  },
  {
    id: "victorian",
    label: "Victorian",
    description: "Ornate details, steep roofs, rich layered textures",
    visuals: {
      wallColor: "#FBF3E2", slabColor: "#2C1A0E", edgeColor: "#B8956A",
      wallRoughness: 0.65, wallMetalness: 0.03, slabRoughness: 0.75,
      wallThickness: 0.28, ceilingHeight: 3.2, canvasBg: "#FDFAF4",
    },
    costPerSqm: { low: 50_000, high: 95_000 },
    costFactors: { foundation: 0.11, structure: 0.22, electrical: 0.07, plumbing: 0.09, hvac: 0.06, finishes: 0.32, roofing: 0.08, misc: 0.05 },
  },
  {
    id: "haveli",
    label: "Haveli",
    description: "Traditional Pakistani courtyard house — brick, jharokhas, shaded verandas",
    visuals: {
      wallColor: "#D4956A", slabColor: "#3B1F0E", edgeColor: "#A0622A",
      wallRoughness: 0.88, wallMetalness: 0.01, slabRoughness: 0.90,
      wallThickness: 0.24, ceilingHeight: 2.6, canvasBg: "#FAF0E4",
    },
    costPerSqm: { low: 22_000, high: 45_000 },
    costFactors: { foundation: 0.13, structure: 0.25, electrical: 0.07, plumbing: 0.09, hvac: 0.05, finishes: 0.26, roofing: 0.10, misc: 0.05 },
  },
];

export const DEFAULT_STYLE_ID: StyleId = "modern";
export const DEFAULT_MATERIAL_TIER: MaterialTier = "standard";

export function getStyle(id: StyleId): ArchitectureStyle {
  return ARCHITECTURE_STYLES.find((s) => s.id === id) ?? ARCHITECTURE_STYLES[0];
}

// ── Cost computation (frontend-only, deterministic from room data + style + tier) ──

export interface CostCategory {
  name: string;
  low: number;
  high: number;
}

export interface RoomCostRow {
  name: string;
  type: string;
  area_m2: number;
  low: number;
  high: number;
}

export interface CostBreakdown {
  totalLow: number;
  totalHigh: number;
  totalAreaM2: number;
  costPerSqmLow: number;
  costPerSqmHigh: number;
  styleLabel: string;
  tierLabel: string;
  categories: CostCategory[];
  perRoom: RoomCostRow[];
}

const ROOM_COST_MULT: Record<string, number> = {
  bathroom: 1.65,
  kitchen:  1.45,
  parking:  0.50,
  balcony:  0.40,
  garden:   0.35,
  storage:  0.60,
  stair:    0.70,
};

export function computeCostBreakdown(
  rooms: Array<{ name?: string; type: string; area_m2: number }>,
  styleId: StyleId,
  tier: MaterialTier,
): CostBreakdown {
  const style    = getStyle(styleId);
  const tierInfo = MATERIAL_TIER_MULTIPLIERS[tier];
  const area     = rooms.reduce((s, r) => s + r.area_m2, 0);

  const baseHigh = area * style.costPerSqm.high * tierInfo.highMultiplier;
  const baseLow  = baseHigh * tierInfo.lowRatio;

  // Build category breakdown
  const f = style.costFactors;
  const rawCats = [
    { name: "Foundation & Site",   fraction: f.foundation },
    { name: "Structure & Framing", fraction: f.structure  },
    { name: "Electrical",          fraction: f.electrical },
    { name: "Plumbing",            fraction: f.plumbing   },
    { name: "HVAC",                fraction: f.hvac       },
    { name: "Interior Finishes",   fraction: f.finishes   },
    { name: "Roofing",             fraction: f.roofing    },
    { name: "Miscellaneous",       fraction: f.misc       },
  ];
  const totalFrac = rawCats.reduce((s, c) => s + c.fraction, 0);
  const categories: CostCategory[] = rawCats.map((c) => ({
    name: c.name,
    low:  Math.round(baseLow  * (c.fraction / totalFrac)),
    high: Math.round(baseHigh * (c.fraction / totalFrac)),
  }));

  // Per-room breakdown (weighted by area + room-type multiplier)
  const perRoom: RoomCostRow[] = rooms.map((r) => {
    const mul  = ROOM_COST_MULT[r.type] ?? 1.0;
    const frac = area > 0 ? r.area_m2 / area : 0;
    return {
      name:    r.name ?? r.type.replace(/_/g, " "),
      type:    r.type,
      area_m2: r.area_m2,
      low:     Math.round(baseLow  * frac * mul),
      high:    Math.round(baseHigh * frac * mul),
    };
  });

  return {
    totalLow:      Math.round(baseLow),
    totalHigh:     Math.round(baseHigh),
    totalAreaM2:   area,
    costPerSqmHigh: Math.round(style.costPerSqm.high * tierInfo.highMultiplier),
    costPerSqmLow:  Math.round(style.costPerSqm.high * tierInfo.highMultiplier * tierInfo.lowRatio),
    styleLabel: style.label,
    tierLabel:  MATERIAL_TIER_MULTIPLIERS[tier].label,
    categories,
    perRoom,
  };
}
