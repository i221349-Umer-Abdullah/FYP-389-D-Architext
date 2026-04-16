"""
test_generate.py — Quick interactive test for the trained CVAE-GNN.

Takes a Normal language prompt, converts it to an 11-dim condition vector
(matching processed_v3 format), runs inference, and prints the result.

Usage:
    .\\venv\\Scripts\\python.exe scripts\\test_generate.py "3 bedroom 2 bathroom house with balcony"
    .\\venv\\Scripts\\python.exe scripts\\test_generate.py "small 1 bed apartment"
    .\\venv\\Scripts\\python.exe scripts\\test_generate.py --interactive
"""

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import torch

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT / "data" / "processed_v3"
CKPT_DIR = ROOT / "models" / "cvae_gnn"

sys.path.insert(0, str(ROOT / "scripts"))
from train_cvae_gnn import (
    FloorplanCVAE, DEVICE, MAX_NODES, NUM_TYPES,
    CONDITION_DIM, ROOM_TYPES, BEST_PT, BEST_GEN_PT, BEST_RECON_PT, LATEST_PT,
    NODE_FEAT_DIM, build_model_from_checkpoint,
)

# ── Room types in the NEW 11-dim condition vector ──────────────────────────────
# [0] bedroom, [1] bathroom, [2] kitchen, [3] living, [4] balcony,
# [5] storage, [6] parking, [7] garden, [8] stair, [9] veranda, [10] total/max
COND_ROOM_KEYS = ROOM_TYPES  # matches preprocessing exactly

# Aliases for NLP parsing
ALIASES = {
    'bed': 'bedroom', 'beds': 'bedroom', 'br': 'bedroom', 'bhk': 'bedroom',
    'bath': 'bathroom', 'baths': 'bathroom', 'ba': 'bathroom', 'washroom': 'bathroom',
    'living room': 'living', 'lounge': 'living', 'drawing room': 'living',
    'terrace': 'balcony', 'patio': 'balcony',
    'garage': 'parking', 'carport': 'parking',
    'store room': 'storage', 'utility': 'storage', 'closet': 'storage',
    'yard': 'garden', 'lawn': 'garden',
    'porch': 'veranda',
    'stairs': 'stair',
}


def parse_prompt(text: str) -> dict:
    """Parse a natural language prompt into room counts."""
    t = text.lower()
    counts = {}

    # Pattern: "N bedrooms", "3 bed", "2 bathroom" etc.
    for pattern in [
        r'(\d+)\s*(?:bed(?:room)?s?|br)',
        r'(\d+)\s*(?:bath(?:room)?s?|ba\b|washroom)',
        r'(\d+)\s*(?:kitchen)',
        r'(\d+)\s*(?:living|lounge|drawing)',
        r'(\d+)\s*(?:balcon\w*|terrace|patio)',
        r'(\d+)\s*(?:storage|store\s*room|utility)',
        r'(\d+)\s*(?:parking|garage|car\s*port)',
        r'(\d+)\s*(?:garden|yard|lawn)',
        r'(\d+)\s*(?:stair)',
        r'(\d+)\s*(?:veranda|porch)',
    ]:
        m = re.search(pattern, t)
        # Map pattern to room type
        key_map = {
            'bed': 'bedroom', 'bath': 'bathroom', 'kitchen': 'kitchen',
            'living': 'living', 'lounge': 'living', 'drawing': 'living',
            'balcon': 'balcony', 'terrace': 'balcony', 'patio': 'balcony',
            'storage': 'storage', 'store': 'storage', 'utility': 'storage',
            'parking': 'parking', 'garage': 'parking', 'car': 'parking',
            'garden': 'garden', 'yard': 'garden', 'lawn': 'garden',
            'stair': 'stair', 'veranda': 'veranda', 'porch': 'veranda',
        }
        if m:
            for kw, rtype in key_map.items():
                if kw in pattern:
                    counts[rtype] = int(m.group(1))
                    break

    # Keyword presence (without count = 1)
    presence_checks = [
        ('balcon', 'balcony'), ('terrace', 'balcony'),
        ('garden', 'garden'), ('yard', 'garden'), ('lawn', 'garden'),
        ('parking', 'parking'), ('garage', 'parking'),
        ('storage', 'storage'), ('store room', 'storage'),
        ('stair', 'stair'), ('two stor', 'stair'), ('2 stor', 'stair'),
        ('veranda', 'veranda'), ('porch', 'veranda'),
    ]
    for kw, rtype in presence_checks:
        if kw in t and rtype not in counts:
            counts[rtype] = 1

    # Defaults
    if 'bedroom' not in counts:
        counts['bedroom'] = 2
    if 'bathroom' not in counts:
        counts['bathroom'] = max(1, counts.get('bedroom', 2) - 1)
    if 'kitchen' not in counts:
        counts['kitchen'] = 1
    if 'living' not in counts:
        counts['living'] = 1

    return counts


def counts_to_condition(counts: dict) -> torch.Tensor:
    """Convert room counts dict to 11-dim condition vector (matching processed_v3)."""
    cond = np.zeros(CONDITION_DIM, dtype=np.float32)

    total = 0
    for rtype, count in counts.items():
        if rtype in COND_ROOM_KEYS:
            idx = COND_ROOM_KEYS.index(rtype)
            cond[idx] = min(count / 5.0, 1.0)
            total += count

    cond[NUM_TYPES] = min(total / MAX_NODES, 1.0)
    return torch.tensor(cond, dtype=torch.float32)


def load_model():
    """Load the trained model from best checkpoint."""
    ckpt_path = None
    for path in [BEST_GEN_PT, LATEST_PT, BEST_PT, BEST_RECON_PT]:
        if path.exists():
            ckpt_path = path
            break
    if ckpt_path is None:
        print(f"No trained model found in {BEST_GEN_PT.parent}")
        print("Run training first: .\\venv\\Scripts\\python.exe scripts\\train_cvae_gnn.py")
        sys.exit(1)

    ckpt = torch.load(str(ckpt_path), map_location=DEVICE, weights_only=False)
    model = build_model_from_checkpoint(ckpt)

    epoch = ckpt.get('epoch', 0) + 1
    val_loss = ckpt.get('val_loss', 0)
    print(
        f"Loaded model from {ckpt_path.name} "
        f"(epoch {epoch}, val_loss={val_loss:.4f}, "
        f"val_recon={ckpt.get('val_recon_loss', float('nan')):.4f}, "
        f"gen_score={ckpt.get('gen_score', float('nan')):.4f})"
    )
    return model


def generate_floorplan(model, prompt: str, n_samples: int = 3):
    """Generate floorplan(s) from a text prompt and save as JSON."""
    counts = parse_prompt(prompt)
    cond = counts_to_condition(counts).to(DEVICE)

    # Output directory
    out_dir = CKPT_DIR / "samples"
    out_dir.mkdir(exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Prompt:  \"{prompt}\"")
    print(f"Parsed:  {counts}")
    print(f"Condition: {cond.cpu().numpy().round(3).tolist()}")
    print(f"{'='*60}")

    # Sanitize prompt for filename
    safe_name = re.sub(r'[^a-z0-9]+', '_', prompt.lower().strip())[:40].strip('_')

    for sample_idx in range(n_samples):
        output = model.generate(cond.unsqueeze(0))

        n_rooms = (output['num_logits'].argmax(dim=-1) + 1).item()
        types = output['type_logits'][0, :n_rooms].argmax(dim=-1).cpu().numpy()
        spatial = output['spatial'][0, :n_rooms].cpu().numpy()
        adj = (torch.sigmoid(output['adj_logits'][0, :n_rooms, :n_rooms]) > 0.5).cpu().numpy()

        print(f"\n--- Sample {sample_idx + 1} ({n_rooms} rooms) ---")
        rooms = []
        for j in range(n_rooms):
            rtype = ROOM_TYPES[types[j]]
            x0, y0, x1, y1, area = spatial[j]
            w, h = x1 - x0, y1 - y0
            print(f"  {rtype:10s}: pos=({x0:.2f},{y0:.2f})  size=({w:.2f}x{h:.2f})  area={area:.3f}")
            rooms.append({
                'type': rtype, 'x_min': float(x0), 'y_min': float(y0),
                'x_max': float(x1), 'y_max': float(y1),
                'width': float(w), 'height': float(h), 'area': float(area),
            })

        # Count overlaps
        n_overlaps = 0
        for a in range(n_rooms):
            for b in range(a + 1, n_rooms):
                ix = max(0, min(spatial[a, 2], spatial[b, 2]) - max(spatial[a, 0], spatial[b, 0]))
                iy = max(0, min(spatial[a, 3], spatial[b, 3]) - max(spatial[a, 1], spatial[b, 1]))
                if ix * iy > 0.001:
                    n_overlaps += 1

        n_edges = int(adj.sum()) // 2
        print(f"  Overlaps: {n_overlaps} | Edges: {n_edges}")

        # Room type summary
        type_summary = {}
        for j in range(n_rooms):
            rtype = ROOM_TYPES[types[j]]
            type_summary[rtype] = type_summary.get(rtype, 0) + 1
        print(f"  Summary: {type_summary}")

        # Save JSON
        result = {
            'prompt': prompt,
            'parsed_counts': counts,
            'n_rooms': n_rooms,
            'rooms': rooms,
            'adjacency': adj.astype(int).tolist(),
            'summary': type_summary,
            'overlaps': n_overlaps,
            'edges': n_edges,
        }
        json_path = out_dir / f"{safe_name}_s{sample_idx + 1}.json"
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)

    print(f"\nSaved {n_samples} samples to {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="Test CVAE-GNN floorplan generation")
    parser.add_argument('prompt', nargs='?', default=None, help="Text prompt describing the house")
    parser.add_argument('--interactive', '-i', action='store_true', help="Interactive mode")
    parser.add_argument('--samples', '-n', type=int, default=3, help="Number of samples per prompt")
    args = parser.parse_args()

    model = load_model()

    if args.interactive or args.prompt is None:
        print("\nInteractive mode. Type a house description and press Enter.")
        print("Type 'quit' to exit.\n")
        while True:
            try:
                prompt = input("Describe your house> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not prompt or prompt.lower() in ('quit', 'exit', 'q'):
                break
            generate_floorplan(model, prompt, args.samples)
    else:
        generate_floorplan(model, args.prompt, args.samples)


if __name__ == '__main__':
    main()
