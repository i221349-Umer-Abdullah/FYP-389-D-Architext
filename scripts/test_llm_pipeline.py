"""
LLM Pipeline Test — full end-to-end: prompt -> 2D PNG + IFC 3D model

Outputs per run:
  output/comparison/llm_<slug>.png        2D floor plan
  output/comparison/llm_<slug>.ifc        3D IFC model
  output/comparison/gnn_<slug>.png        (if --no-llm-only)
  output/comparison/gnn_<slug>.ifc        (if --no-llm-only)
  output/comparison/compare_<slug>.png    side-by-side 2D

Usage (from d:\\Work\\Uni\\FYP\\architext):
  .\\venv\\Scripts\\python.exe scripts\\test_llm_pipeline.py --llm-only
  .\\venv\\Scripts\\python.exe scripts\\test_llm_pipeline.py --llm-only "3 bedroom house with 2 bathrooms"
  .\\venv\\Scripts\\python.exe scripts\\test_llm_pipeline.py   (runs both LLM + GNN comparison)
"""

import sys
import asyncio
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.cm as cm


# ── Room colour map ────────────────────────────────────────────────────────────
ROOM_COLOURS = {
    "living":   "#AED6F1",   # light blue
    "kitchen":  "#A9DFBF",   # mint green
    "dining":   "#D5F5E3",   # pale green
    "bedroom":  "#F9E79F",   # yellow
    "bathroom": "#FADBD8",   # pink
    "hallway":  "#D7DBDD",   # grey
    "balcony":  "#A9CCE3",   # steel blue
    "garden":   "#82E0AA",   # green
    "parking":  "#CCD1D1",   # cool grey
    "storage":  "#D2B4DE",   # lavender
    "stair":    "#F0B27A",   # orange
    "veranda":  "#85C1E9",   # sky blue
    "other":    "#EAECEE",   # off-white
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower())[:40]


def plot_rooms(ax, rooms: list, title: str, generated_by: str = ""):
    """Draw rooms as labelled coloured rectangles on ax."""
    if not rooms:
        ax.text(0.5, 0.5, "No rooms generated", transform=ax.transAxes,
                ha="center", va="center", fontsize=12, color="red")
        ax.set_title(title)
        return

    xs = [r["x"] for r in rooms]
    ys = [r["y"] for r in rooms]
    xe = [r["x"] + r["width"]  for r in rooms]
    ye = [r["y"] + r["height"] for r in rooms]

    margin = 1.0
    ax.set_xlim(min(xs) - margin, max(xe) + margin)
    ax.set_ylim(min(ys) - margin, max(ye) + margin)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", alpha=0.3, color="#999")
    ax.set_xlabel("metres", fontsize=8)
    ax.set_ylabel("metres", fontsize=8)

    for r in rooms:
        rtype  = r.get("type", "other")
        colour = ROOM_COLOURS.get(rtype, "#EAECEE")
        rect   = patches.Rectangle(
            (r["x"], r["y"]), r["width"], r["height"],
            linewidth=1.5, edgecolor="#333", facecolor=colour, alpha=0.85
        )
        ax.add_patch(rect)

        label = rtype.replace("_", " ").title()
        area  = round(r.get("area", r["width"] * r["height"]), 1)
        ax.text(
            r["x"] + r["width"]  / 2,
            r["y"] + r["height"] / 2,
            f"{label}\n{area} m²",
            ha="center", va="center", fontsize=7.5, fontweight="bold", color="#222",
            wrap=True,
        )

    total = sum(r.get("area", r["width"] * r["height"]) for r in rooms)
    subtitle = f"{len(rooms)} rooms · {round(total, 1)} m²"
    if generated_by:
        subtitle += f"\n[{generated_by}]"
    ax.set_title(f"{title}\n{subtitle}", fontsize=10, pad=6)


def export_ifc(room_graph: dict, ifc_path: Path, prompt: str) -> bool:
    """Run Layer 4 — export room_graph to an IFC file. Returns True on success."""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from backend.core.room_graph_to_ifc import RoomGraphToIFC
        adapter = RoomGraphToIFC()
        adapter.convert(room_graph, output_path=str(ifc_path), project_name=prompt[:60])
        kb = ifc_path.stat().st_size // 1024
        print(f"  IFC  -> {ifc_path}  ({kb} KB)")
        return True
    except Exception as e:
        print(f"  IFC FAILED: {e}")
        return False


async def run_llm(prompt: str, ifc_path: Path) -> dict:
    from backend.core.llm_adapter import generate_room_layout, spec_from_room_graph
    from backend.core.pipeline    import _validate_and_fix

    print(f"\n{'='*60}")
    print(f"[LLM]  {prompt}")
    print('='*60)

    rg   = await generate_room_layout(prompt)
    spec = spec_from_room_graph(rg)
    rg   = _validate_and_fix(rg, spec)
    export_ifc(rg, ifc_path, prompt)
    return rg


def run_gnn(prompt: str, ifc_path: Path) -> dict:
    from backend.core.nlp_adapter    import get_nlp_adapter
    from backend.core.spec_converter import normalise_spec
    from backend.core.real_gnn       import get_real_gnn
    from backend.core.pipeline       import _validate_and_fix

    print(f"\n{'='*60}")
    print(f"[GNN]  {prompt}")
    print('='*60)

    nlp  = get_nlp_adapter()
    spec = normalise_spec(nlp.parse(prompt))
    gnn  = get_real_gnn()
    rg   = gnn.generate(spec)
    rg   = _validate_and_fix(rg, spec)
    export_ifc(rg, ifc_path, prompt)
    return rg


def save_single(rooms: list, title: str, path: Path, generated_by: str = ""):
    fig, ax = plt.subplots(figsize=(8, 8))
    plot_rooms(ax, rooms, title, generated_by)
    plt.tight_layout()
    plt.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved -> {path}")


def save_comparison(llm_rooms, gnn_rooms, prompt: str, path: Path):
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle(f'Prompt: "{prompt}"', fontsize=11, y=1.01, wrap=True)

    plot_rooms(axes[0], llm_rooms, "LLM Generator", "LLM")
    plot_rooms(axes[1], gnn_rooms, "GNN Generator", "StructuralGNN")

    plt.tight_layout()
    plt.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Comparison -> {path}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?",
                        default="A 3 bedroom house with 2 bathrooms, living room, kitchen, dining, and a garden")
    parser.add_argument("--llm-only", action="store_true",
                        help="Skip GNN comparison (use when model not trained)")
    parser.add_argument("--gnn-only", action="store_true",
                        help="Skip LLM comparison (use to test GNN alone)")
    args = parser.parse_args()

    prompt = args.prompt
    slug   = _slug(prompt)

    out_dir = ROOT / "output" / "comparison"
    out_dir.mkdir(parents=True, exist_ok=True)

    llm_rooms = None
    gnn_rooms = None

    # ── Run LLM ────────────────────────────────────────────────────────────────
    if not args.gnn_only:
        try:
            rg = await run_llm(prompt, out_dir / f"llm_{slug}.ifc")
            llm_rooms = rg["rooms"]
            save_single(llm_rooms, f'LLM: "{prompt}"',
                        out_dir / f"llm_{slug}.png", "LLM")
            print(f"\n[LLM] OK  {len(llm_rooms)} rooms generated")
            for r in llm_rooms:
                print(f"       {r['type']:12s}  {r['width']:.1f} x {r['height']:.1f} m  "
                      f"@ ({r['x']:.1f}, {r['y']:.1f})")
        except Exception as e:
            print(f"\n[LLM] FAILED  {e}")

    # ── Run GNN ────────────────────────────────────────────────────────────────
    if not args.llm_only:
        try:
            rg = run_gnn(prompt, out_dir / f"gnn_{slug}.ifc")
            gnn_rooms = rg["rooms"]
            save_single(gnn_rooms, f'GNN: "{prompt}"',
                        out_dir / f"gnn_{slug}.png", "StructuralGNN")
            print(f"\n[GNN] OK  {len(gnn_rooms)} rooms generated")
            for r in gnn_rooms:
                print(f"       {r['type']:12s}  {r['width']:.1f} x {r['height']:.1f} m  "
                      f"@ ({r['x']:.1f}, {r['y']:.1f})")
        except Exception as e:
            print(f"\n[GNN] FAILED  {e}")

    # ── Side-by-side comparison ────────────────────────────────────────────────
    if llm_rooms and gnn_rooms:
        save_comparison(llm_rooms, gnn_rooms, prompt,
                        out_dir / f"compare_{slug}.png")

    print(f"\nDone. Outputs in: {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
