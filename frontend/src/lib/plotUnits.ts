export type PlotUnit = "marla" | "kanal" | "sqm" | "mxm" | "ftxft";

const MARLA_TO_SQM  = 25.2929;   // 1 Marla = 25.2929 m²  (Pakistan standard)
const KANAL_TO_SQM  = 505.857;   // 1 Kanal = 20 Marla
const FT_TO_M       = 0.3048;
const PLOT_ASPECT   = 1.8;        // depth / width — standard DHA/LDA Punjab ratio

function round2(n: number) { return Math.round(n * 100) / 100; }

export interface PlotDims {
  width:  number;   // metres
  height: number;   // metres (depth of plot)
}

/** Convert user input values (for a given unit) to plot dims in metres.
 *  Returns null if the input is incomplete or invalid. */
export function toPlotDims(unit: PlotUnit, v1: string, v2: string): PlotDims | null {
  const n1 = parseFloat(v1);
  const n2 = parseFloat(v2);

  if (unit === "mxm") {
    if (!isFinite(n1) || !isFinite(n2) || n1 <= 0 || n2 <= 0) return null;
    return { width: round2(n1), height: round2(n2) };
  }

  if (unit === "ftxft") {
    if (!isFinite(n1) || !isFinite(n2) || n1 <= 0 || n2 <= 0) return null;
    return { width: round2(n1 * FT_TO_M), height: round2(n2 * FT_TO_M) };
  }

  // Single-value units → derive dims from area using standard aspect ratio
  if (!isFinite(n1) || n1 <= 0) return null;

  let areaSqm: number;
  if (unit === "marla") areaSqm = n1 * MARLA_TO_SQM;
  else if (unit === "kanal") areaSqm = n1 * KANAL_TO_SQM;
  else areaSqm = n1; // sqm

  const width  = Math.sqrt(areaSqm / PLOT_ASPECT);
  const height = width * PLOT_ASPECT;
  return { width: round2(width), height: round2(height) };
}

/** Human-readable summary of the plot dims */
export function plotSummary(dims: PlotDims): string {
  const area = dims.width * dims.height;
  return `≈ ${dims.width} × ${dims.height} m  ·  ${Math.round(area)} m²`;
}

export const UNIT_LABELS: Record<PlotUnit, string> = {
  marla:  "Marla",
  kanal:  "Kanal",
  sqm:    "m²",
  mxm:    "m × m",
  ftxft:  "ft × ft",
};

export const UNIT_PLACEHOLDERS: Record<PlotUnit, [string, string]> = {
  marla:  ["e.g. 5", ""],
  kanal:  ["e.g. 1", ""],
  sqm:    ["e.g. 200", ""],
  mxm:    ["Width", "Depth"],
  ftxft:  ["Width", "Depth"],
};
