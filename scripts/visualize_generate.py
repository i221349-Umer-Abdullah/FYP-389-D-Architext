"""
visualize_generate.py — Generate, visualize, and optionally export to IFC.

- Updated

Takes a user prompt, generates floorplan samples, saves:
  1. 2D floorplan PNG images (colored room boxes with labels)
  2. JSON room data
  3. Optionally: IFC 3D model via the existing Layer 4 pipeline

Usage:
    .\\venv\\Scripts\\python.exe scripts\\visualize_generate.py "3 bedroom house with balcony"
    .\\venv\\Scripts\\python.exe scripts\\visualize_generate.py "2 bed apartment" --ifc
    .\\venv\\Scripts\\python.exe scripts\\visualize_generate.py --interactive
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from train_cvae_gnn import (
    FloorplanCVAE, DEVICE, MAX_NODES, NUM_TYPES,
    CONDITION_DIM, ROOM_TYPES, BEST_PT, BEST_GEN_PT, BEST_RECON_PT, LATEST_PT,
    DATA_DIR, build_model_from_checkpoint,
)

# Load norm constants for denormalization
_norm = np.load(str(DATA_DIR / "norm_constants.npy"), allow_pickle=True).item()
CANVAS_METRES = _norm['canvas_metres']  # 12.8m — the real-world canvas size

OUT_DIR = ROOT / "output" / "generated_plans"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Room colors for visualization ──────────────────────────────────────────────
ROOM_COLORS = {
    'bedroom':  '#5B9BD5',  # blue
    'bathroom': '#70AD47',  # green
    'kitchen':  '#FFC000',  # gold
    'living':   '#ED7D31',  # orange
    'balcony':  '#A5D8E6',  # light blue
    'storage':  '#BF8F00',  # brown
    'parking':  '#7F7F7F',  # gray
    'garden':   '#92D050',  # lime green
    'stair':    '#9966CC',  # purple
    'veranda':  '#C5B0D5',  # light purple
}

# ── NLP parsing (same as test_generate.py) ─────────────────────────────────────

def parse_prompt(text):
    t = text.lower()
    counts = {}
    patterns = [
        (r'(\d+)\s*(?:bed(?:room)?s?|br)', 'bedroom'),
        (r'(\d+)\s*(?:bath(?:room)?s?|ba\b|washroom|toilet)', 'bathroom'),
        (r'(\d+)\s*(?:kitchen)', 'kitchen'),
        # living aliases + unsupported social rooms → living
        (r'(\d+)\s*(?:living|lounge|drawing\s*room|family\s*room|reception|sitting\s*room|hall)', 'living'),
        (r'(\d+)\s*(?:balcon\w*|terrace|patio)', 'balcony'),
        # storage aliases + unsupported utility-like rooms → storage
        (r'(\d+)\s*(?:storage|store\s*room|utility|library|study|home\s*office|office|gym|laundry|prayer\s*room|server\s*room)', 'storage'),
        (r'(\d+)\s*(?:parking|garage|car\s*port)', 'parking'),
        (r'(\d+)\s*(?:garden|yard|lawn)', 'garden'),
        (r'(\d+)\s*(?:stair)', 'stair'),
        (r'(\d+)\s*(?:veranda|porch)', 'veranda'),
    ]
    for pat, rtype in patterns:
        m = re.search(pat, t)
        if m:
            counts[rtype] = int(m.group(1))

    for kw, rtype in [('balcon', 'balcony'), ('garden', 'garden'), ('yard', 'garden'),
                       ('parking', 'parking'), ('garage', 'parking'), ('storage', 'storage'),
                       ('stair', 'stair'), ('veranda', 'veranda'), ('porch', 'veranda'),
                       # unsupported types — map to nearest supported equivalent
                       ('drawing room', 'living'), ('family room', 'living'), ('reception', 'living'),
                       ('sitting room', 'living'), ('lounge', 'living'),
                       ('library', 'storage'), ('study', 'storage'), ('home office', 'storage'),
                       ('office', 'storage'), ('gym', 'storage'), ('laundry', 'storage'),
                       ('prayer room', 'storage'), ('utility', 'storage')]:
        if kw in t and rtype not in counts:
            counts[rtype] = 1

    counts.setdefault('bedroom', 2)
    counts.setdefault('bathroom', max(1, counts.get('bedroom', 2) - 1))
    counts.setdefault('kitchen', 1)
    counts.setdefault('living', 1)
    return counts


def counts_to_condition(counts):
    cond = np.zeros(CONDITION_DIM, dtype=np.float32)
    total = 0
    for rtype, count in counts.items():
        if rtype in ROOM_TYPES:
            cond[ROOM_TYPES.index(rtype)] = min(count / 5.0, 1.0)
            total += count
    cond[NUM_TYPES] = min(total / MAX_NODES, 1.0)
    return torch.tensor(cond, dtype=torch.float32)


# ── Model loading ──────────────────────────────────────────────────────────────

def load_model():
    ckpt_path = None
    for path in [BEST_GEN_PT, LATEST_PT, BEST_PT, BEST_RECON_PT]:
        if path.exists():
            ckpt_path = path
            break
    if ckpt_path is None:
        print(f"No model found in {BEST_GEN_PT.parent}. Train first!")
        sys.exit(1)

    ckpt = torch.load(str(ckpt_path), map_location=DEVICE, weights_only=False)
    model = build_model_from_checkpoint(ckpt)
    print(
        f"Model loaded from {ckpt_path.name} "
        f"(epoch {ckpt.get('epoch',0)+1}, "
        f"val_loss={ckpt.get('val_loss',0):.4f}, "
        f"val_recon={ckpt.get('val_recon_loss', float('nan')):.4f}, "
        f"gen_score={ckpt.get('gen_score', float('nan')):.4f})"
    )
    return model


# ── Denormalize model output to metres ─────────────────────────────────────────

def denormalize_rooms(types, spatial, n_rooms):
    """
    Convert normalized model output to real-world room dicts in metres.

    Model outputs bbox corners in [0,1] normalized space where 1.0 = CANVAS_METRES (12.8m).
    IFC layer expects: {type, x, y, width, height} in metres.
    """
    rooms = []
    for j in range(n_rooms):
        rtype = ROOM_TYPES[types[j]]
        x_min = spatial[j, 0] * CANVAS_METRES
        y_min = spatial[j, 1] * CANVAS_METRES
        x_max = spatial[j, 2] * CANVAS_METRES
        y_max = spatial[j, 3] * CANVAS_METRES
        w = x_max - x_min
        h = y_max - y_min

        rooms.append({
            'id': f'{rtype}_{j}',
            'type': rtype,
            'x': round(float(x_min), 2),
            'y': round(float(y_min), 2),
            'width': round(float(w), 2),
            'height': round(float(h), 2),
            'area': round(float(w * h), 2),
        })
    return rooms


# ── 2D Visualization ──────────────────────────────────────────────────────────

def draw_floorplan(rooms, title, save_path):
    """Draw a 2D floorplan image using matplotlib."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
    except ImportError:
        print("  [SKIP] matplotlib not installed, cannot draw PNG")
        return False

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_aspect('equal')

    # Find bounds
    all_x = [r['x'] for r in rooms] + [r['x'] + r['width'] for r in rooms]
    all_y = [r['y'] for r in rooms] + [r['y'] + r['height'] for r in rooms]
    margin = 1.0
    x_min, x_max = min(all_x) - margin, max(all_x) + margin
    y_min, y_max = min(all_y) - margin, max(all_y) + margin
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # Draw rooms
    for r in rooms:
        color = ROOM_COLORS.get(r['type'], '#CCCCCC')
        rect = patches.Rectangle(
            (r['x'], r['y']), r['width'], r['height'],
            linewidth=2, edgecolor='#333333', facecolor=color, alpha=0.6,
        )
        ax.add_patch(rect)

        # Label
        cx = r['x'] + r['width'] / 2
        cy = r['y'] + r['height'] / 2
        label = f"{r['type']}\n{r['width']:.1f}x{r['height']:.1f}m"
        fontsize = max(6, min(10, int(r['width'] * 2.5)))
        ax.text(cx, cy, label, ha='center', va='center',
                fontsize=fontsize, fontweight='bold', color='#222222')

    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('metres')
    ax.set_ylabel('metres')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(str(save_path), dpi=150, bbox_inches='tight')
    plt.close(fig)
    return True


# ── IFC export ─────────────────────────────────────────────────────────────────

def export_ifc(rooms, prompt, save_path):
    """Export room graph to IFC file via the existing Layer 4 pipeline."""
    try:
        from backend.core.room_graph_to_ifc import RoomGraphToIFC
        from backend.core.pipeline import _validate_and_fix
    except ImportError as e:
        print(f"  [SKIP] IFC export unavailable: {e}")
        return None

    room_graph = {'rooms': rooms, 'metadata': {'unit_type': 'house', 'prompt': prompt}}

    # Run Layer 3 validator (push apart overlaps, snap isolated rooms)
    spec = {}
    for r in rooms:
        spec[r['type']] = spec.get(r['type'], 0) + 1
    room_graph = _validate_and_fix(room_graph, spec)

    # Run Layer 4 IFC export
    converter = RoomGraphToIFC()
    ifc_path = converter.convert(room_graph, output_path=str(save_path))
    return ifc_path


# ── Main generation ────────────────────────────────────────────────────────────

def generate(model, prompt, n_samples=3, do_ifc=False):
    counts = parse_prompt(prompt)
    cond = counts_to_condition(counts).to(DEVICE)
    safe_name = re.sub(r'[^a-z0-9]+', '_', prompt.lower().strip())[:40].strip('_')

    print(f"\nPrompt: \"{prompt}\"")
    print(f"Parsed: {counts}")

    for si in range(n_samples):
        output = model.generate(cond.unsqueeze(0))
        n_rooms = (output['num_logits'].argmax(dim=-1) + 1).item()
        types = output['type_logits'][0, :n_rooms].argmax(dim=-1).cpu().numpy()
        spatial = output['spatial'][0, :n_rooms].cpu().numpy()

        rooms = denormalize_rooms(types, spatial, n_rooms)

        # Type summary
        summary = {}
        for r in rooms:
            summary[r['type']] = summary.get(r['type'], 0) + 1
        print(f"\n  Sample {si+1}: {n_rooms} rooms — {summary}")
        for r in rooms:
            print(f"    {r['type']:10s}: ({r['x']:.1f}, {r['y']:.1f}) {r['width']:.1f}x{r['height']:.1f}m  area={r['area']:.1f}m2")

        # Save JSON
        json_path = OUT_DIR / f"{safe_name}_s{si+1}.json"
        with open(json_path, 'w') as f:
            json.dump({'prompt': prompt, 'counts': counts, 'rooms': rooms, 'summary': summary}, f, indent=2)
        print(f"    JSON: {json_path}")

        # Draw PNG
        png_path = OUT_DIR / f"{safe_name}_s{si+1}.png"
        title = f"\"{prompt}\" — Sample {si+1}"
        if draw_floorplan(rooms, title, png_path):
            print(f"    PNG:  {png_path}")

        # IFC export
        if do_ifc:
            ifc_path = OUT_DIR / f"{safe_name}_s{si+1}.ifc"
            result = export_ifc(rooms, prompt, ifc_path)
            if result:
                print(f"    IFC:  {result}")

    print(f"\nAll outputs saved to {OUT_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Visualize CVAE-GNN floorplan generation")
    parser.add_argument('prompt', nargs='?', default=None)
    parser.add_argument('--interactive', '-i', action='store_true')
    parser.add_argument('--samples', '-n', type=int, default=3)
    parser.add_argument('--ifc', action='store_true', help="Also export IFC 3D files")
    args = parser.parse_args()

    model = load_model()

    if args.interactive or args.prompt is None:
        print("\nInteractive mode. Type 'quit' to exit.\n")
        while True:
            try:
                prompt = input("Describe your house> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not prompt or prompt.lower() in ('quit', 'exit', 'q'):
                break
            generate(model, prompt, args.samples, args.ifc)
    else:
        generate(model, args.prompt, args.samples, args.ifc)


if __name__ == '__main__':
    main()
