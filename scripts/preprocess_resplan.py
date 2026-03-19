"""
preprocess_resplan.py — Extract GNN training data from ResPlan.pkl

Replaces preprocess_dataset.py (CubiCasa-based) with the actual ResPlan dataset.

Dataset: D:/Work/Uni/FYP/Dataset/ResPlan/ResPlan.pkl
  - 17,000 residential floor plan samples
  - Each plan: dict with Shapely polygon geometry per room type
  - 'inner' polygon = building footprint boundary (used for normalization)
  - 'graph' field = pre-built NetworkX adjacency graph

Output: data/processed_v2/ (same format as before — training script unchanged)
  - train/ and val/ batch_NNNN.pt files
  - norm_constants.npy

Node feature vector (16-dim) per room:
  [0:10]  one-hot room type (10 classes)
  [10]    cx_normalized   = (centroid.x - inner.minx) / inner.width
  [11]    cy_normalized   = (centroid.y - inner.miny) / inner.height
  [12]    width_norm      = bbox_width  / inner.width
  [13]    height_norm     = bbox_height / inner.height
  [14]    area_norm       = room.area   / inner.area
  [15]    is_external     (1 if balcony/garden/parking)

Condition vector (18-dim) — matches spec_converter.py EXACTLY:
  [0:9]   room counts / 5.0 (bedroom, bathroom, kitchen, living_room,
                              dining_room, balcony, garden, storage, parking)
  [9]     total_rooms / MAX_NODES
  [10]    is_apartment (0 — ResPlan is all houses)
  [11]    is_house     (1 always)
  [12:18] padding zeros

Usage:
    .\\venv\\Scripts\\python.exe scripts\\preprocess_resplan.py
"""

import sys
import pickle
import random
import json
import copy
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
import networkx as nx
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, Point
from shapely.ops import unary_union

# ── Add dataset utils to path ──────────────────────────────────────────────────
DATASET_DIR  = Path(r"D:\Work\Uni\FYP\Dataset\ResPlan")
sys.path.insert(0, str(DATASET_DIR))
from resplan_utils import normalize_keys, get_geometries, centroid  # noqa

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent.resolve()
DATA_PKL   = DATASET_DIR / "ResPlan.pkl"
OUT_DIR    = ROOT / "data" / "processed_v2"
NORM_PATH  = OUT_DIR / "norm_constants.npy"

# ── Config ─────────────────────────────────────────────────────────────────────
MAX_NODES     = 16      # covers p99 of real plans
BATCH_SIZE    = 128
VAL_SPLIT     = 0.15
RANDOM_SEED   = 42
MAX_PARTS     = 4       # max geometry parts per room type (prevents huge multi-polygon rooms)

# Room type vocabulary — MUST match spec_converter.py COND_ROOM_KEYS
ROOM_TYPES = [
    'bedroom', 'bathroom', 'kitchen', 'living_room',
    'dining_room', 'balcony', 'garden', 'storage', 'parking',
    'other',
]
NUM_TYPES   = len(ROOM_TYPES)          # 10
TYPE2IDX    = {t: i for i, t in enumerate(ROOM_TYPES)}
NODE_FEAT_DIM = NUM_TYPES + 6          # 10 type + cx+cy+w+h+area+is_ext = 16

# COND_ROOM_KEYS order — MUST match spec_converter.py exactly
COND_ROOM_KEYS = [
    'bedroom', 'bathroom', 'kitchen', 'living_room',
    'dining_room', 'balcony', 'garden', 'storage', 'parking',
]
CONDITION_DIM  = 18

# Dataset key → (canonical_type, is_room)
# Keys with is_room=False are not extracted as nodes
DATASET_KEY_MAP = {
    'bedroom':    ('bedroom',     True),
    'bathroom':   ('bathroom',    True),
    'kitchen':    ('kitchen',     True),
    'living':     ('living_room', True),
    'balcony':    ('balcony',     True),
    'garden':     ('garden',      True),
    'storage':    ('storage',     True),
    'parking':    ('parking',     True),
    'stair':      ('other',       True),
    'veranda':    ('other',       True),
    'pool':       ('other',       True),
    'inner':      (None,          False),  # building boundary — skip as node
    'wall':       (None,          False),
    'door':       (None,          False),
    'window':     (None,          False),
    'front_door': (None,          False),
    'land':       (None,          False),
    'wall_depth': (None,          False),
    'graph':      (None,          False),
}

# Room keys we extract (in priority order for node ordering)
ROOM_KEYS_ORDERED = [
    'bedroom', 'bathroom', 'kitchen', 'living',
    'balcony', 'garden', 'storage', 'parking',
    'stair', 'veranda', 'pool',
]


def get_inner_bounds(plan: Dict) -> Optional[Tuple[float, float, float, float, float, float]]:
    """
    Returns (minx, miny, width, height, area) of the inner (building footprint) polygon.
    Returns None if inner is missing or empty.
    """
    inner = plan.get('inner')
    if inner is None or inner.is_empty:
        return None
    b = inner.bounds   # (minx, miny, maxx, maxy)
    w = b[2] - b[0]
    h = b[3] - b[1]
    if w < 1.0 or h < 1.0:
        return None
    return b[0], b[1], w, h, inner.area


def geom_to_node_features(geom, canonical_type: str,
                           minx: float, miny: float,
                           plan_w: float, plan_h: float,
                           plan_area: float) -> np.ndarray:
    """Build a 16-dim node feature vector from a Shapely geometry + spatial context."""
    feat = np.zeros(NODE_FEAT_DIM, dtype=np.float32)

    # Type one-hot
    feat[TYPE2IDX.get(canonical_type, TYPE2IDX['other'])] = 1.0

    # Centroid (use largest sub-polygon centroid for MultiPolygon)
    if isinstance(geom, MultiPolygon):
        biggest = max(geom.geoms, key=lambda g: g.area)
        c = biggest.centroid
        b = biggest.bounds
    else:
        c = geom.centroid
        b = geom.bounds

    # Normalise to [0,1] using inner polygon bounds
    feat[NUM_TYPES]     = float(np.clip((c.x - minx) / plan_w, 0.0, 1.0))  # cx
    feat[NUM_TYPES + 1] = float(np.clip((c.y - miny) / plan_h, 0.0, 1.0))  # cy
    feat[NUM_TYPES + 2] = float(np.clip((b[2] - b[0]) / plan_w, 0.0, 1.0))  # w
    feat[NUM_TYPES + 3] = float(np.clip((b[3] - b[1]) / plan_h, 0.0, 1.0))  # h
    feat[NUM_TYPES + 4] = float(np.clip(geom.area / max(plan_area, 1.0), 0.0, 1.0))  # area
    feat[NUM_TYPES + 5] = 1.0 if canonical_type in {'balcony', 'garden', 'parking'} else 0.0

    return feat


def build_condition_vector(room_type_counts: Dict[str, int], total_rooms: int) -> np.ndarray:
    """18-dim condition vector that mirrors spec_converter.py exactly."""
    cond = np.zeros(CONDITION_DIM, dtype=np.float32)
    for i, key in enumerate(COND_ROOM_KEYS):
        cond[i] = min(room_type_counts.get(key, 0) / 5.0, 1.0)
    cond[9]  = min(total_rooms / MAX_NODES, 1.0)
    cond[10] = 0.0   # is_apartment — ResPlan is all houses
    cond[11] = 1.0   # is_house
    # [12:18] padding zeros
    return cond


def plan_to_graph_data(plan: Dict) -> Optional[Dict]:
    """
    Convert one ResPlan sample to a graph dict with PyTorch tensors.
    Returns None if invalid (missing inner, too few rooms, etc.).
    """
    plan = normalize_keys(plan)

    # Get building boundary for normalisation
    bounds = get_inner_bounds(plan)
    if bounds is None:
        return None
    minx, miny, plan_w, plan_h, plan_area = bounds

    # ── Extract room nodes ─────────────────────────────────────────────────────
    node_feats    = []
    node_type_ids = []   # canonical type string per node (for cond vector)
    node_graph_ids = []  # dataset_key_idx strings (for adjacency lookup)

    for dk in ROOM_KEYS_ORDERED:
        canonical, is_room = DATASET_KEY_MAP.get(dk, (None, False))
        if not is_room:
            continue

        geom_data = plan.get(dk)
        if geom_data is None:
            continue

        parts = get_geometries(geom_data)
        # Sort by area descending, take at most MAX_PARTS
        parts = sorted([g for g in parts if isinstance(g, (Polygon, MultiPolygon)) and not g.is_empty],
                       key=lambda g: g.area, reverse=True)[:MAX_PARTS]

        for idx, geom in enumerate(parts):
            if len(node_feats) >= MAX_NODES:
                break
            feat = geom_to_node_features(geom, canonical, minx, miny, plan_w, plan_h, plan_area)
            node_feats.append(feat)
            node_type_ids.append(canonical)
            node_graph_ids.append(f"{dk}_{idx}")

    n = len(node_feats)
    if n < 2:
        return None   # skip degenerate single-room plans

    node_tensor = torch.tensor(np.stack(node_feats), dtype=torch.float32)  # [n, 16]

    # ── Build adjacency from the pre-computed graph field ─────────────────────
    adj = np.zeros((n, n), dtype=np.float32)
    G = plan.get('graph')
    if isinstance(G, nx.Graph) and G.number_of_nodes() > 0:
        # Map graph node IDs → our flat indices
        node_id_to_idx = {nid: i for i, nid in enumerate(node_graph_ids)}
        for u, v in G.edges():
            i = node_id_to_idx.get(u, -1)
            j = node_id_to_idx.get(v, -1)
            if 0 <= i < n and 0 <= j < n:
                adj[i, j] = 1.0
                adj[j, i] = 1.0

    # Fallback: spatial adjacency via intersection (buffer by 2% of plan width)
    if adj.sum() == 0:
        buf = plan_w * 0.02
        for i in range(n):
            for j in range(i + 1, n):
                # Use cx/cy distance as proxy (proper Shapely test is expensive at scale)
                ci = node_tensor[i, NUM_TYPES:NUM_TYPES+2].numpy()
                cj = node_tensor[j, NUM_TYPES:NUM_TYPES+2].numpy()
                wi = node_tensor[i, NUM_TYPES + 2].item()
                wj = node_tensor[j, NUM_TYPES + 2].item()
                hi = node_tensor[i, NUM_TYPES + 3].item()
                hj = node_tensor[j, NUM_TYPES + 3].item()
                # Check if bboxes overlap (with small buffer)
                overlap_x = abs(ci[0] - cj[0]) < (wi + wj) / 2 + 0.02
                overlap_y = abs(ci[1] - cj[1]) < (hi + hj) / 2 + 0.02
                if overlap_x and overlap_y:
                    adj[i, j] = 1.0
                    adj[j, i] = 1.0

    adj_tensor = torch.tensor(adj, dtype=torch.float32)

    # ── Condition vector ────────────────────────────────────────────────────────
    type_counts = {}
    for t in node_type_ids:
        type_counts[t] = type_counts.get(t, 0) + 1
    cond = build_condition_vector(type_counts, n)
    cond_tensor = torch.tensor(cond, dtype=torch.float32)

    return {
        'node_features': node_tensor,
        'adjacency':     adj_tensor,
        'condition':     cond_tensor,
        'num_nodes':     n,
        'sample_id':     plan.get('sample_id', 'resplan'),
    }


def augment_flip(graph: Dict, flip_h: bool, flip_v: bool) -> Dict:
    """
    Horizontal/vertical flip augmentation by mirroring cx and cy.
    Topology (adjacency) and type/size features are invariant.
    """
    nf = graph['node_features'].clone()
    if flip_h:
        nf[:, NUM_TYPES]     = 1.0 - nf[:, NUM_TYPES]       # cx → 1-cx
    if flip_v:
        nf[:, NUM_TYPES + 1] = 1.0 - nf[:, NUM_TYPES + 1]   # cy → 1-cy
    return {
        'node_features': nf,
        'adjacency':     graph['adjacency'],
        'condition':     graph['condition'],
        'num_nodes':     graph['num_nodes'],
        'sample_id':     str(graph['sample_id']) + f'_fh{int(flip_h)}fv{int(flip_v)}',
    }


def collate_batch(graphs: List[Dict]) -> Dict:
    """Pad all graphs in a batch to the same max_n, stack into tensors."""
    max_n = min(max(g['num_nodes'] for g in graphs), MAX_NODES)

    nf_batch, adj_batch, cond_batch, num_batch, mask_batch = [], [], [], [], []
    for g in graphs:
        n   = g['num_nodes']
        pad = max_n - n

        nf  = g['node_features']
        adj = g['adjacency']
        if pad > 0:
            nf  = torch.cat([nf, torch.zeros(pad, NODE_FEAT_DIM)], dim=0)
            adj = F.pad(adj, (0, pad, 0, pad))

        nf_batch.append(nf)
        adj_batch.append(adj)
        cond_batch.append(g['condition'])
        num_batch.append(g['num_nodes'])

        mask = torch.zeros(max_n)
        mask[:n] = 1.0
        mask_batch.append(mask)

    return {
        'node_features': torch.stack(nf_batch),
        'adjacency':     torch.stack(adj_batch),
        'condition':     torch.stack(cond_batch),
        'num_nodes':     torch.tensor(num_batch),
        'mask':          torch.stack(mask_batch),
    }


def save_batches(graphs: List[Dict], out_folder: Path, split_name: str) -> int:
    n_batches = 0
    for i in range(0, len(graphs), BATCH_SIZE):
        batch  = graphs[i:i + BATCH_SIZE]
        tensors = collate_batch(batch)
        torch.save(tensors, out_folder / f"batch_{n_batches:04d}.pt")
        n_batches += 1
    print(f"  {split_name}: {n_batches} batches saved → {out_folder}")
    return n_batches


def main():
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    print(f"Loading {DATA_PKL} ...")
    with open(DATA_PKL, 'rb') as f:
        raw_data = pickle.load(f)
    print(f"  Loaded {len(raw_data)} raw samples")

    # Compute dataset canvas_metres statistics from inner polygon widths
    plan_widths_m = []

    # Convert to graphs
    graphs  = []
    skipped = 0
    for idx, plan in enumerate(raw_data):
        # Attach sample_id for debugging
        plan['sample_id'] = str(idx)

        # Collect plan width for stats (assuming 1px ≈ 0.05m = 5cm)
        inner = plan.get('inner')
        if inner is not None and not inner.is_empty:
            b = inner.bounds
            pw_px = max(b[2] - b[0], b[3] - b[1])
            plan_widths_m.append(pw_px * 0.05)

        g = plan_to_graph_data(plan)
        if g is None:
            skipped += 1
        else:
            graphs.append(g)

        if (idx + 1) % 2000 == 0:
            print(f"  Processed {idx+1}/{len(raw_data)} ... ({len(graphs)} valid)")

    print(f"\n  Valid graphs: {len(graphs)}  (skipped {skipped})")

    node_counts = [g['num_nodes'] for g in graphs]
    print(f"  Node counts: min={min(node_counts)}, max={max(node_counts)}, "
          f"mean={np.mean(node_counts):.1f}, median={np.median(node_counts):.0f}")

    # canvas_metres: median plan width in metres
    canvas_m = float(np.median(plan_widths_m)) if plan_widths_m else 15.0
    print(f"  Median plan width: {canvas_m:.1f}m  (scale: 1 norm unit = {canvas_m:.1f}m)")

    # Shuffle and split
    random.shuffle(graphs)
    split  = int(len(graphs) * (1 - VAL_SPLIT))
    train_graphs = graphs[:split]
    val_graphs   = graphs[split:]

    # 4× augmentation on train only
    aug_train = []
    for g in train_graphs:
        aug_train.append(g)
        aug_train.append(augment_flip(g, True,  False))
        aug_train.append(augment_flip(g, False, True))
        aug_train.append(augment_flip(g, True,  True))
    random.shuffle(aug_train)
    print(f"\n  Train (after 4× aug): {len(aug_train)} graphs")
    print(f"  Val:                  {len(val_graphs)} graphs")

    # Save
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train_dir = OUT_DIR / "train"
    val_dir   = OUT_DIR / "val"
    train_dir.mkdir(exist_ok=True)
    val_dir.mkdir(exist_ok=True)

    # Clear old batches
    for f in train_dir.glob("batch_*.pt"):
        f.unlink()
    for f in val_dir.glob("batch_*.pt"):
        f.unlink()

    n_train = save_batches(aug_train,  train_dir, "Train")
    n_val   = save_batches(val_graphs, val_dir,   "Val")

    # Save norm_constants.npy
    norm = {
        'condition_dim':    CONDITION_DIM,    # 18
        'node_feature_dim': NODE_FEAT_DIM,    # 16
        'max_nodes':        MAX_NODES,        # 16
        'canvas_metres':    canvas_m,
        'room_types':       ROOM_TYPES,
        'cond_room_keys':   COND_ROOM_KEYS,
        'num_train_batches': n_train,
        'num_val_batches':   n_val,
        'source_dataset':   'ResPlan',
        'version':          3,
    }
    np.save(str(NORM_PATH), norm)

    print(f"\n  norm_constants saved → {NORM_PATH}")
    print(f"  canvas_metres={canvas_m:.1f}m, max_nodes={MAX_NODES}, "
          f"node_feat={NODE_FEAT_DIM}, cond={CONDITION_DIM}")
    print(f"\n✅ Preprocessing complete!")
    print(f"   Train batches: {n_train} × {BATCH_SIZE} = ~{n_train*BATCH_SIZE} samples")
    print(f"   Val batches:   {n_val}  × {BATCH_SIZE} = ~{n_val*BATCH_SIZE} samples")
    print(f"   Output: {OUT_DIR}")


if __name__ == '__main__':
    main()
