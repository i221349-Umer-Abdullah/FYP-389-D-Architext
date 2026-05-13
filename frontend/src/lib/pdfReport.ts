import type { GenerationResult, GenerationRoom, PlotConstraint } from "@/lib/types";
import { computeCostBreakdown, getStyle, MATERIAL_TIER_MULTIPLIERS } from "@/lib/architectureStyles";

// ── Formatting helpers ────────────────────────────────────────────────────────

function pkr(n: number): string {
  if (n >= 10_000_000) return `Rs. ${(n / 10_000_000).toFixed(2)} Cr`;
  if (n >= 100_000)    return `Rs. ${(n / 100_000).toFixed(1)} L`;
  const s = Math.round(n).toString();
  const out: string[] = [];
  for (let i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 === 0) out.push(",");
    out.push(s[i]);
  }
  return `Rs. ${out.join("")}`;
}

function fmtNum(n: number): string {
  const s = Math.round(n).toString();
  const out: string[] = [];
  for (let i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 === 0) out.push(",");
    out.push(s[i]);
  }
  return out.join("");
}

// ── Image helpers ─────────────────────────────────────────────────────────────

async function toDataUrl(url: string): Promise<string | null> {
  try {
    const blob = await fetch(url).then((r) => r.blob());
    return await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror  = () => reject(new Error("FileReader failed"));
      reader.readAsDataURL(blob);
    });
  } catch {
    return null;
  }
}

async function getImageDims(dataUrl: string): Promise<{ w: number; h: number } | null> {
  return new Promise((resolve) => {
    const img = new window.Image();
    img.onload  = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => resolve(null);
    img.src     = dataUrl;
  });
}

// ── Public API ────────────────────────────────────────────────────────────────

export interface ExportPDFOptions {
  prompt:              string;
  plotConstraint:      PlotConstraint | null;
  llmResult:           GenerationResult | null;
  gnnResult:           GenerationResult | null;
  llmRooms:            GenerationRoom[]  | null;
  gnnRooms:            GenerationRoom[]  | null;
  llmPreviewOverride?: string;
  gnnPreviewOverride?: string;
}

export async function exportFloorplanPDF(opts: ExportPDFOptions): Promise<void> {
  // Dynamic import keeps the heavy library out of the initial bundle
  const [{ jsPDF }, { autoTable }] = await Promise.all([
    import("jspdf"),
    import("jspdf-autotable"),
  ]);

  const [llmImg, gnnImg] = await Promise.all([
    opts.llmResult
      ? toDataUrl(opts.llmPreviewOverride ?? opts.llmResult.previewUrl)
      : Promise.resolve(null),
    opts.gnnResult
      ? toDataUrl(opts.gnnPreviewOverride ?? opts.gnnResult.previewUrl)
      : Promise.resolve(null),
  ]);

  const doc  = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const PW   = doc.internal.pageSize.getWidth();   // 210
  const PH   = doc.internal.pageSize.getHeight();  // 297
  const M    = 18;                                  // margin
  const cW   = PW - 2 * M;                         // content width (174mm)
  const date = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });

  // ── Colour shortcuts ──────────────────────────────────────────────────────
  type RGB = [number, number, number];
  const INK:    RGB = [17,  17,  17];
  const MUTED:  RGB = [140, 140, 140];
  const BORDER: RGB = [220, 220, 220];
  const BG:     RGB = [249, 250, 251];
  const GREEN:  RGB = [21,  128,  61];
  const DARK:   RGB = [17,  24,  39];
  const WHITE:  RGB = [255, 255, 255];

  const setT = (...c: RGB) => doc.setTextColor(...c);
  const setF = (...c: RGB) => doc.setFillColor(...c);
  const setD = (...c: RGB) => doc.setDrawColor(...c);

  // ── Reusable drawing helpers ──────────────────────────────────────────────

  function hr(y: number) {
    setD(...BORDER);
    doc.setLineWidth(0.3);
    doc.line(M, y, PW - M, y);
  }

  function miniHeader(subtitle: string) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    setT(...DARK);
    doc.text("ARCHITEXT", M, 14);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    setT(...MUTED);
    doc.text(subtitle, M + 40, 14);
    hr(18.5);
  }

  function footer(label: string) {
    const y = PH - 9;
    doc.setFont("helvetica", "normal");
    doc.setFontSize(6.5);
    setT(...MUTED);
    doc.text("ArchiText · AI-Assisted Floor Plan Generator", M, y);
    doc.text(`${date} · ${label}`, PW - M, y, { align: "right" });
  }

  // Chip drawing (tag-like label with rounded rect background)
  function chip(text: string, x: number, y: number): number {
    const w = doc.getTextWidth(text) + 10;
    setF(...BG);
    setD(...BORDER);
    doc.setLineWidth(0.3);
    doc.roundedRect(x, y - 4.2, w, 6.2, 1.5, 1.5, "FD");
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    setT(...INK);
    doc.text(text, x + 5, y);
    return w;
  }

  // ── PAGE 1: Cover ─────────────────────────────────────────────────────────
  {
    // Large brand
    doc.setFont("helvetica", "bold");
    doc.setFontSize(24);
    setT(...DARK);
    doc.text("ARCHITEXT", M, 27);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    setT(...MUTED);
    doc.text("FLOOR PLAN ANALYSIS REPORT", M, 34);

    hr(40);

    let y = 48;

    // Design brief
    doc.setFont("helvetica", "bold");
    doc.setFontSize(6.5);
    setT(...MUTED);
    doc.text("DESIGN BRIEF", M, y);
    y += 5.5;

    doc.setFont("helvetica", "italic");
    doc.setFontSize(10.5);
    setT(...INK);
    const promptLines = doc.splitTextToSize(`“${opts.prompt}”`, cW) as string[];
    doc.text(promptLines, M, y);
    y += promptLines.length * 5.8 + 7;

    // Meta chips
    const chips: string[] = [
      `Generated ${date}`,
      ...(opts.plotConstraint ? [`Plot: ${opts.plotConstraint.width}m × ${opts.plotConstraint.height}m`] : []),
    ];
    const anyResult = opts.llmResult ?? opts.gnnResult;
    if (anyResult) {
      chips.push(`Style: ${getStyle(anyResult.styleId).label}`);
      chips.push(`Tier: ${MATERIAL_TIER_MULTIPLIERS[anyResult.materialTier].label}`);
    }
    if (opts.llmResult) chips.push(`Primary: ${opts.llmResult.roomCount} rooms`);
    if (opts.gnnResult) chips.push(`Competition: ${opts.gnnResult.roomCount} rooms`);

    let cx = M;
    for (const c of chips) {
      const w = doc.getTextWidth(c) + 10;
      if (cx + w > PW - M) { cx = M; y += 8.5; }
      chip(c, cx, y);
      cx += w + 5;
    }
    y += 12;

    hr(y);
    y += 10;

    // Summary stat cards
    const cards: Array<{ tag: string; stat: string; sub: string }> = [];
    if (opts.llmResult) {
      const rooms = opts.llmRooms ?? opts.llmResult.rooms;
      cards.push({
        tag:  "PRIMARY GENERATOR",
        stat: `${opts.llmResult.roomCount} rooms`,
        sub:  `${rooms.reduce((s, r) => s + r.area_m2, 0).toFixed(1)} m² total floor area`,
      });
    }
    if (opts.gnnResult) {
      const rooms = opts.gnnRooms ?? opts.gnnResult.rooms;
      cards.push({
        tag:  "COMPETITION (CVAE-GNN)",
        stat: `${opts.gnnResult.roomCount} rooms`,
        sub:  `${rooms.reduce((s, r) => s + r.area_m2, 0).toFixed(1)} m² total floor area`,
      });
    }

    if (cards.length > 0) {
      const cardW = (cW - (cards.length - 1) * 6) / cards.length;
      cards.forEach((card, ci) => {
        const cx2 = M + ci * (cardW + 6);
        setF(...BG);
        setD(...BORDER);
        doc.setLineWidth(0.3);
        doc.roundedRect(cx2, y, cardW, 32, 2, 2, "FD");

        doc.setFont("helvetica", "bold");
        doc.setFontSize(6.5);
        setT(...MUTED);
        doc.text(card.tag, cx2 + 7, y + 8);

        doc.setFont("helvetica", "bold");
        doc.setFontSize(18);
        setT(...DARK);
        doc.text(card.stat, cx2 + 7, y + 20);

        doc.setFont("helvetica", "normal");
        doc.setFontSize(7.5);
        setT(...MUTED);
        doc.text(card.sub, cx2 + 7, y + 27);
      });
      y += 42;
    }

    // Disclaimer note
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    setT(...MUTED);
    const note = "Cost estimates are based on architecture style, material tier, and room areas. Actual costs vary by region, contractor, and site conditions.";
    doc.text(doc.splitTextToSize(note, cW) as string[], M, y);

    footer("Page 1 of " + (1 + (opts.llmResult ? 1 : 0) + (opts.gnnResult ? 1 : 0)));
  }

  // ── Generator page builder ────────────────────────────────────────────────

  async function addGeneratorPage(
    pageLabel: string,
    headerSub: string,
    result: GenerationResult,
    rooms: GenerationRoom[],
    imgDataUrl: string | null,
    pageNum: number,
    totalPages: number,
  ) {
    miniHeader(headerSub);

    let y = 26;

    // Section heading
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    setT(...DARK);
    doc.text(pageLabel, M, y);
    y += 5;

    const style  = getStyle(result.styleId);
    const tier   = MATERIAL_TIER_MULTIPLIERS[result.materialTier].label;
    const cost   = computeCostBreakdown(rooms, result.styleId, result.materialTier);

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    setT(...MUTED);
    doc.text(
      `${rooms.length} rooms · ${cost.totalAreaM2.toFixed(1)} m² · ${style.label} Style · ${tier} Materials · Ceiling ${style.visuals.ceilingHeight}m`,
      M, y,
    );
    y += 7;

    // Floor plan image (aspect-ratio-correct)
    if (imgDataUrl) {
      const dims = await getImageDims(imgDataUrl);
      const MAX_H = 68;
      let imgW = cW, imgH = MAX_H;
      if (dims && dims.w > 0 && dims.h > 0) {
        const ratio = dims.w / dims.h;
        imgW = Math.min(cW, MAX_H * ratio);
        imgH = imgW / ratio;
      }
      const imgX = M + (cW - imgW) / 2;
      doc.addImage(imgDataUrl, "PNG", imgX, y, imgW, imgH);
      y += imgH + 7;
    }

    // ── Room breakdown table ──
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    setT(...DARK);
    doc.text("Room Breakdown", M, y);
    y += 3;

    autoTable(doc, {
      startY: y,
      head: [["Room", "Type", "W × H (m)", "Area (m²)", "Cost Estimate (PKR)"]],
      body: rooms.map((room, i) => {
        const cr = cost.perRoom[i];
        return [
          room.name.replace(/_/g, " "),
          room.type,
          `${room.width.toFixed(1)} × ${room.height.toFixed(1)}`,
          room.area_m2.toFixed(1),
          cr ? `${pkr(cr.low)} – ${pkr(cr.high)}` : "—",
        ];
      }),
      styles: {
        fontSize: 7.5,
        cellPadding: 2.4,
        textColor: [17, 17, 17] as RGB,
        lineColor: [235, 235, 235] as RGB,
        lineWidth: 0.2,
      },
      headStyles: {
        fillColor: [17, 24, 39] as RGB,
        textColor: [255, 255, 255] as RGB,
        fontStyle: "bold",
        fontSize: 7,
      },
      alternateRowStyles: { fillColor: [249, 250, 251] as RGB },
      columnStyles: { 4: { halign: "right" as const } },
      margin: { left: M, right: M },
      theme: "grid",
    });

    y = ((doc as any).lastAutoTable?.finalY ?? y + 30) + 8;

    // Check if cost section would overflow; add new page if needed
    if (y > PH - 80) {
      footer(`Page ${pageNum} of ${totalPages}`);
      doc.addPage();
      miniHeader(`${headerSub} — COST`);
      y = 26;
    }

    // ── Construction cost estimate ──
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    setT(...DARK);
    doc.text("Construction Cost Estimate", M, y);
    y += 7;

    // Total range hero
    doc.setFont("helvetica", "bold");
    doc.setFontSize(15);
    setT(...GREEN);
    doc.text(`${pkr(cost.totalLow)} – ${pkr(cost.totalHigh)}`, M, y);
    y += 5;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    setT(...MUTED);
    doc.text(
      `Rs. ${fmtNum(cost.costPerSqmLow)} – Rs. ${fmtNum(cost.costPerSqmHigh)} / m²  ·  ${cost.totalAreaM2.toFixed(1)} m² total  ·  ${cost.styleLabel} / ${cost.tierLabel}`,
      M, y,
    );
    y += 7;

    // Category breakdown
    autoTable(doc, {
      startY: y,
      head: [["Cost Category", "Low Estimate", "High Estimate"]],
      body: cost.categories.map((c) => [c.name, pkr(c.low), pkr(c.high)]),
      styles: {
        fontSize: 7.5,
        cellPadding: 2.4,
        textColor: [17, 17, 17] as RGB,
        lineColor: [235, 235, 235] as RGB,
        lineWidth: 0.2,
      },
      headStyles: {
        fillColor: [17, 24, 39] as RGB,
        textColor: [255, 255, 255] as RGB,
        fontStyle: "bold",
        fontSize: 7,
      },
      alternateRowStyles: { fillColor: [249, 250, 251] as RGB },
      columnStyles: {
        1: { halign: "right" as const },
        2: { halign: "right" as const },
      },
      margin: { left: M, right: M },
      theme: "grid",
    });

    footer(`Page ${pageNum} of ${totalPages}`);
  }

  // ── Add generator pages ───────────────────────────────────────────────────
  const totalPages = 1 + (opts.llmResult ? 1 : 0) + (opts.gnnResult ? 1 : 0);
  let pageNum = 2;

  if (opts.llmResult) {
    doc.addPage();
    await addGeneratorPage(
      "Primary Generator",
      "PRIMARY GENERATOR",
      opts.llmResult,
      opts.llmRooms ?? opts.llmResult.rooms,
      llmImg,
      pageNum++,
      totalPages,
    );
  }

  if (opts.gnnResult) {
    doc.addPage();
    await addGeneratorPage(
      "Competition (CVAE-GNN)",
      "COMPETITION (CVAE-GNN)",
      opts.gnnResult,
      opts.gnnRooms ?? opts.gnnResult.rooms,
      gnnImg,
      pageNum++,
      totalPages,
    );
  }

  doc.save(`architext-report-${Date.now()}.pdf`);
}
