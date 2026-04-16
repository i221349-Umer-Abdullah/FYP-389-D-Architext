"""
preprocess_resplan_v3.py — ArchiText ResPlan Preprocessing (clean rewrite)

Designed purely around ResPlan's own data structure. No legacy baggage.

────────────────────────────────────────────────────────────────────────
DATA-DRIVEN DESIGN DECISIONS:
────────────────────────────────────────────────────────────────────────

1. ROOM TYPES (10 classes)
   Only types that actually appear as room nodes in ResPlan.
   No dead slots (wall/inner/pool are NOT room nodes in ResPlan).

2. SPATIAL FEATURES — The Critical Part
   The previous model failed at positioning because:
   - Rooms outside the inner boundary were clipped to [0,1] → lost position
   - Bounding box corners are more informative than centroid+size

   This script stores BOTH representations:
   - x_min, y_min, x_max, y_max (bbox corners, normalized, NOT clipped)
   - area_norm (room area / plan area)
   - is_external flag

   The corner representation directly encodes WHERE each room edge is,
   making it easier for the model to learn non-overlapping placement.

3. EDGE TYPES preserved
   ResPlan graphs have 4 edge types with spatial meaning:
   - direct    (11.6%) — front door to living room
   - adjacency (38.9%) — rooms share a wall
   - via_door  (47.4%) — rooms connected through a door
   - via_window (2.1%) — rooms connected through a window

   We store a separate edge_type matrix so the model can learn
   that "via_door" means rooms MUST share a wall segment.

4. CONDITION VECTOR (11-dim)
   Just the room counts + total. No padding, no wasted dimensions.

5. NORMALIZATION
   All spatial coordinates are normalized relative to the inner polygon's
   bounding box but NOT CLIPPED. External rooms (balconies, gardens) can
   have values slightly outside [0,1], which is correct and important.

────────────────────────────────────────────────────────────────────────

Output files in data/processed_v3/:
    train/batch_NNNN.pt
    val/batch_NNNN.pt
    norm_constants.npy

Each batch .pt contains:
    node_features  [B, max_nodes, 16]    — room type + spatial
    adjacency      [B, max_nodes, max_nodes]  — binary adjacency
    edge_types     [B, max_nodes, max_nodes]  — edge type IDs (0-4)
    condition      [B, 11]               — room spec
    num_nodes      [B]                   — actual room count
    mask           [B, max_nodes]        — 1.0 for real nodes

Usage:
    .\\venv\\Scripts\\python.exe scripts\\preprocess_resplan_v3.py
    .\\venv\\Scripts\\python.exe scripts\\preprocess_resplan_v3.py --max-nodes 16 --batch-size 128
"""

import argparse
import pickle
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
import networkx as nx
from shapely.geometry import Polygon, MultiPolygon

# ── ResPlan dataset helpers ────────────────────────────────────────────────────
DATASET_DIR = Path(r"D:\Work\Uni\FYP\Dataset\ResPlan")
sys.path.insert(0, str(DATASET_DIR))
from resplan_utils import normalize_keys, get_geometries  # noqa: E402

ROOT     = Path(__file__).parent.parent.resolve()
DATA_PKL = DATASET_DIR / "ResPlan.pkl"


# ══════════════════════════════════════════════════════════════════════════════
# TYPE SYSTEM — 10 room types that actually appear in ResPlan
# ══════════════════════════════════════════════════════════════════════════════

ROOM_TYPES = [
    'bedroom',    # 0
    'bathroom',   # 1
    'kitchen',    # 2
    'living',     # 3
    'balcony',    # 4
    'storage',    # 5
    'parking',    # 6
    'garden',     # 7
    'stair',      # 8
    'veranda',    # 9
]
NUM_TYPES = len(ROOM_TYPES)       # 10
TYPE2IDX  = {t: i for i, t in enumerate(ROOM_TYPES)}

# Which dataset keys map to our room types
# Keys not here (wall, inner, door, window, etc.) are skipped
DATASET_KEY_TO_TYPE = {
    'bedroom':  'bedroom',
    'bathroom': 'bathroom',
    'kitchen':  'kitchen',
    'living':   'living',
    'balcony':  'balcony',
    'storage':  'storage',
    'parking':  'parking',
    'garden':   'garden',
    'stair':    'stair',
    'veranda':  'veranda',
}

# Extraction order (most common first → fills max_nodes slots with important rooms)
ROOM_KEYS_ORDERED = [
    'living', 'bedroom', 'bathroom', 'kitchen', 'balcony',
    'storage', 'veranda', 'stair', 'garden', 'parking',
]

EXTERNAL_TYPES = {'balcony', 'garden', 'parking', 'veranda'}


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
#
# Node features: 16-dim
#   [0:10]   one-hot room type
#   [10]     x_min  (left edge,   normalized to inner bbox, NOT clipped)
#   [11]     y_min  (top edge,    normalized to inner bbox, NOT clipped)
#   [12]     x_max  (right edge,  normalized to inner bbox, NOT clipped)
#   [13]     y_max  (bottom edge, normalized to inner bbox, NOT clipped)
#   [14]     area_norm  (room area / inner area)
#   [15]     is_external  (1.0 for balcony/garden/parking/veranda)
#
# Why bbox corners (x_min, y_min, x_max, y_max) instead of (cx, cy, w, h)?
#   - Corners directly encode WHERE each wall is
#   - Non-overlapping constraint is easier to learn:
#     "room A's x_max < room B's x_min" means no horizontal overlap
#   - The model can derive centroid and size from corners, but not vice versa
#     for learning wall-sharing (adjacent rooms share an edge coordinate)
#
# The model can derive: cx = (x_min+x_max)/2, w = x_max-x_min
# But corners carry a bonus: adjacent rooms that share a wall will have
# matching edge coordinates (e.g. room_A.x_max ≈ room_B.x_min).

NODE_FEAT_DIM = NUM_TYPES + 6  # 10 + 6 = 16

# Condition vector: 11-dim
#   [0:10]  room counts per type / 5.0
#   [10]    total_rooms / max_nodes
CONDITION_DIM = NUM_TYPES + 1  # 11

# Edge types in the dataset's pre-built graphs
EDGE_TYPE_MAP = {
    'direct':     1,
    'adjacency':  2,
    'via_door':   3,
    'via_window': 4,
}
NUM_EDGE_TYPES = 5  # 0=none, 1-4=types above


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def get_inner_bounds(plan: Dict) -> Optional[Tuple[float, float, float, float, float]]:
    """
    Returns (minx, miny, width, height, area) of the inner (building footprint).
    Returns None if invalid.
    """
    inner = plan.get('inner')
    if inner is None or inner.is_empty:
        return None
    b = inner.bounds
    w, h = b[2] - b[0], b[3] - b[1]
    if w < 5.0 or h < 5.0:
        return None
    return b[0], b[1], w, h, inner.area


def extract_rooms(plan: Dict, max_nodes: int) -> List[Tuple[str, str, Polygon]]:
    """
    Extract individual room polygons from the plan.

    Returns list of (dataset_key, canonical_type, polygon), at most max_nodes.
    Each polygon part of a MultiPolygon/GeometryCollection becomes its own room.
    Rooms are extracted in priority order (living first) so that when max_nodes
    is hit, the most important rooms are kept.
    """
    rooms = []
    for dk in ROOM_KEYS_ORDERED:
        rtype = DATASET_KEY_TO_TYPE.get(dk)
        if rtype is None:
            continue

        geom = plan.get(dk)
        if geom is None:
            continue

        parts = get_geometries(geom)
        # Keep valid polygons, sort largest first
        polys = sorted(
            [p for p in parts
             if isinstance(p, (Polygon, MultiPolygon)) and not p.is_empty and p.area > 1.0],
            key=lambda p: p.area, reverse=True,
        )

        for poly in polys:
            if len(rooms) >= max_nodes:
                break
            # Extract largest sub-polygon if MultiPolygon
            if isinstance(poly, MultiPolygon):
                poly = max(poly.geoms, key=lambda g: g.area)
            rooms.append((dk, rtype, poly))

        if len(rooms) >= max_nodes:
            break

    return rooms


def build_node_features(
    rooms: List[Tuple[str, str, Polygon]],
    inner_minx: float, inner_miny: float,
    inner_w: float, inner_h: float,
    inner_area: float,
) -> np.ndarray:
    """
    Build [n, 16] node feature matrix.

    Spatial features are normalized to the inner polygon's bounding box
    but NOT clipped — external rooms can have values outside [0,1].
    """
    n = len(rooms)
    feats = np.zeros((n, NODE_FEAT_DIM), dtype=np.float32)

    for i, (dk, rtype, poly) in enumerate(rooms):
        # Type one-hot
        feats[i, TYPE2IDX[rtype]] = 1.0

        # Bounding box corners (normalized to inner polygon)
        b = poly.bounds  # (minx, miny, maxx, maxy)
        feats[i, NUM_TYPES + 0] = (b[0] - inner_minx) / inner_w   # x_min
        feats[i, NUM_TYPES + 1] = (b[1] - inner_miny) / inner_h   # y_min
        feats[i, NUM_TYPES + 2] = (b[2] - inner_minx) / inner_w   # x_max
        feats[i, NUM_TYPES + 3] = (b[3] - inner_miny) / inner_h   # y_max

        # Area (normalized)
        feats[i, NUM_TYPES + 4] = poly.area / max(inner_area, 1.0)

        # External flag
        feats[i, NUM_TYPES + 5] = 1.0 if rtype in EXTERNAL_TYPES else 0.0

    return feats


def build_adjacency(
    plan: Dict,
    rooms: List[Tuple[str, str, Polygon]],
    inner_w: float, inner_h: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build adjacency matrix and edge type matrix from the pre-built graph.

    Returns:
        adj:        [n, n]  binary adjacency (0 or 1)
        edge_types: [n, n]  edge type IDs (0=none, 1=direct, 2=adjacency,
                             3=via_door, 4=via_window)
    """
    n = len(rooms)
    adj = np.zeros((n, n), dtype=np.float32)
    edge_types = np.zeros((n, n), dtype=np.int64)

    G = plan.get('graph')

    if isinstance(G, nx.Graph) and G.number_of_edges() > 0:
        # Map our room indices to graph node IDs.
        # Graph node IDs are like 'living_0', 'bedroom_1', 'bathroom_0'.
        # We reconstruct these by counting parts per dataset_key.
        type_counters: Dict[str, int] = {}
        idx_to_gid: Dict[int, str] = {}

        for i, (dk, rtype, poly) in enumerate(rooms):
            count = type_counters.get(dk, 0)
            gid = f"{dk}_{count}"
            type_counters[dk] = count + 1
            idx_to_gid[i] = gid

        gid_to_idx = {gid: i for i, gid in idx_to_gid.items()}

        for u, v, data in G.edges(data=True):
            i = gid_to_idx.get(u, -1)
            j = gid_to_idx.get(v, -1)
            if 0 <= i < n and 0 <= j < n and i != j:
                adj[i, j] = 1.0
                adj[j, i] = 1.0
                etype = EDGE_TYPE_MAP.get(data.get('type', ''), 1)
                edge_types[i, j] = etype
                edge_types[j, i] = etype

    # Fallback: spatial adjacency if graph gave us nothing
    if adj.sum() == 0:
        buf = max(inner_w, inner_h) * 0.02
        for i in range(n):
            poly_i = rooms[i][2].buffer(buf)
            for j in range(i + 1, n):
                if poly_i.intersects(rooms[j][2].buffer(buf)):
                    adj[i, j] = 1.0
                    adj[j, i] = 1.0
                    edge_types[i, j] = 2  # adjacency
                    edge_types[j, i] = 2

    return adj, edge_types


def build_condition(rooms: List[Tuple[str, str, Polygon]], max_nodes: int) -> np.ndarray:
    """
    Build 11-dim condition vector.
    [0:10] room counts / 5.0,  [10] total / max_nodes
    """
    cond = np.zeros(CONDITION_DIM, dtype=np.float32)

    type_counts: Dict[str, int] = {}
    for _, rtype, _ in rooms:
        type_counts[rtype] = type_counts.get(rtype, 0) + 1

    for rtype, count in type_counts.items():
        idx = TYPE2IDX.get(rtype)
        if idx is not None:
            cond[idx] = min(count / 5.0, 1.0)

    cond[NUM_TYPES] = min(len(rooms) / max_nodes, 1.0)
    return cond


def plan_to_graph(plan: Dict, max_nodes: int, sample_id: int) -> Optional[Dict]:
    """
    Convert one ResPlan sample to a training-ready graph dict.
    Returns None if invalid.
    """
    plan = normalize_keys(plan)

    bounds = get_inner_bounds(plan)
    if bounds is None:
        return None
    inner_minx, inner_miny, inner_w, inner_h, inner_area = bounds

    rooms = extract_rooms(plan, max_nodes)
    if len(rooms) < 2:
        return None

    node_features = build_node_features(
        rooms, inner_minx, inner_miny, inner_w, inner_h, inner_area
    )
    adj, edge_types = build_adjacency(plan, rooms, inner_w, inner_h)
    condition = build_condition(rooms, max_nodes)

    return {
        'node_features': torch.tensor(node_features, dtype=torch.float32),
        'adjacency':     torch.tensor(adj, dtype=torch.float32),
        'edge_types':    torch.tensor(edge_types, dtype=torch.long),
        'condition':     torch.tensor(condition, dtype=torch.float32),
        'num_nodes':     len(rooms),
        'sample_id':     sample_id,
    }


# ══════════════════════════════════════════════════════════════════════════════
# AUGMENTATION
# ══════════════════════════════════════════════════════════════════════════════

def augment_flip(graph: Dict, flip_h: bool, flip_v: bool) -> Dict:
    """
    Flip augmentation. Mirrors bbox corner coordinates.

    For horizontal flip:  x_min' = 1 - x_max,  x_max' = 1 - x_min
    For vertical flip:    y_min' = 1 - y_max,  y_max' = 1 - y_min

    Adjacency and types are invariant under flips.
    """
    nf = graph['node_features'].clone()

    if flip_h:
        old_xmin = nf[:, NUM_TYPES + 0].clone()
        old_xmax = nf[:, NUM_TYPES + 2].clone()
        nf[:, NUM_TYPES + 0] = 1.0 - old_xmax  # new x_min = 1 - old x_max
        nf[:, NUM_TYPES + 2] = 1.0 - old_xmin   # new x_max = 1 - old x_min

    if flip_v:
        old_ymin = nf[:, NUM_TYPES + 1].clone()
        old_ymax = nf[:, NUM_TYPES + 3].clone()
        nf[:, NUM_TYPES + 1] = 1.0 - old_ymax  # new y_min = 1 - old y_max
        nf[:, NUM_TYPES + 3] = 1.0 - old_ymin   # new y_max = 1 - old y_min

    return {
        'node_features': nf,
        'adjacency':     graph['adjacency'],
        'edge_types':    graph['edge_types'],
        'condition':     graph['condition'],
        'num_nodes':     graph['num_nodes'],
        'sample_id':     graph['sample_id'],
    }


# ══════════════════════════════════════════════════════════════════════════════
# BATCHING
# ══════════════════════════════════════════════════════════════════════════════

def collate_batch(graphs: List[Dict], max_nodes: int) -> Dict:
    """Pad graphs to max_nodes, stack into batch tensors."""
    nf_list, adj_list, et_list, cond_list = [], [], [], []
    num_list, mask_list = [], []

    for g in graphs:
        n = g['num_nodes']
        pad = max_nodes - n

        nf  = g['node_features']
        adj = g['adjacency']
        et  = g['edge_types']

        if pad > 0:
            nf  = torch.cat([nf,  torch.zeros(pad, NODE_FEAT_DIM)], dim=0)
            adj = F.pad(adj, (0, pad, 0, pad))
            et  = F.pad(et,  (0, pad, 0, pad))
        elif pad < 0:
            nf  = nf[:max_nodes]
            adj = adj[:max_nodes, :max_nodes]
            et  = et[:max_nodes, :max_nodes]

        mask = torch.zeros(max_nodes, dtype=torch.float32)
        mask[:min(n, max_nodes)] = 1.0

        nf_list.append(nf)
        adj_list.append(adj)
        et_list.append(et)
        cond_list.append(g['condition'])
        num_list.append(min(n, max_nodes))
        mask_list.append(mask)

    return {
        'node_features': torch.stack(nf_list),
        'adjacency':     torch.stack(adj_list),
        'edge_types':    torch.stack(et_list),
        'condition':     torch.stack(cond_list),
        'num_nodes':     torch.tensor(num_list),
        'mask':          torch.stack(mask_list),
    }


def save_batches(graphs, out_dir, name, batch_size, max_nodes):
    n_batches = 0
    for i in range(0, len(graphs), batch_size):
        batch = collate_batch(graphs[i:i+batch_size], max_nodes)
        torch.save(batch, out_dir / f"batch_{n_batches:04d}.pt")
        n_batches += 1
    print(f"  {name}: {n_batches} batches → {out_dir}")
    return n_batches


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION — Verify processed data reconstructs positions accurately
# ══════════════════════════════════════════════════════════════════════════════

def validate_reconstruction(graphs: List[Dict], raw_data: list, n_verify: int = 50):
    """
    Spot-check that the processed spatial features can reconstruct the
    original room positions. This ensures normalization is correct.
    """
    print(f"\n  ── Reconstruction Verification ({n_verify} samples) ──")

    cx_errors, cy_errors, w_errors, h_errors = [], [], [], []

    for g in graphs[:n_verify]:
        sid = g['sample_id']
        plan = normalize_keys(raw_data[sid])
        bounds = get_inner_bounds(plan)
        if bounds is None:
            continue
        inner_minx, inner_miny, inner_w, inner_h, inner_area = bounds

        rooms = extract_rooms(plan, g['num_nodes'] + 5)  # generous max
        nf = g['node_features'].numpy()

        for i in range(min(g['num_nodes'], len(rooms))):
            dk, rtype, poly = rooms[i]
            b = poly.bounds  # original bounds

            # Reconstruct from features
            x_min_recon = nf[i, NUM_TYPES + 0] * inner_w + inner_minx
            y_min_recon = nf[i, NUM_TYPES + 1] * inner_h + inner_miny
            x_max_recon = nf[i, NUM_TYPES + 2] * inner_w + inner_minx
            y_max_recon = nf[i, NUM_TYPES + 3] * inner_h + inner_miny

            # Compare with original
            cx_errors.append(abs((x_min_recon + x_max_recon)/2 - (b[0]+b[2])/2))
            cy_errors.append(abs((y_min_recon + y_max_recon)/2 - (b[1]+b[3])/2))
            w_errors.append(abs((x_max_recon - x_min_recon) - (b[2] - b[0])))
            h_errors.append(abs((y_max_recon - y_min_recon) - (b[3] - b[1])))

    if cx_errors:
        print(f"  Position error (pixels):  cx={np.mean(cx_errors):.4f}  cy={np.mean(cy_errors):.4f}")
        print(f"  Size error (pixels):      w={np.mean(w_errors):.4f}   h={np.mean(h_errors):.4f}")
        if np.mean(cx_errors) < 0.01 and np.mean(w_errors) < 0.01:
            print(f"  ✅ Reconstruction is accurate (errors < 0.01 px)")
        else:
            print(f"  ⚠ Reconstruction shows errors — check normalization!")
    else:
        print(f"  ⚠ Could not verify (no matching samples)")


def print_stats(graphs: List[Dict]):
    """Print dataset statistics."""
    node_counts = np.array([g['num_nodes'] for g in graphs])
    print(f"\n  ── Dataset Statistics ──")
    print(f"  Valid graphs:     {len(graphs)}")
    print(f"  Node counts:      min={node_counts.min()}, max={node_counts.max()}, "
          f"mean={node_counts.mean():.1f}, median={np.median(node_counts):.0f}")
    print(f"                    p90={np.percentile(node_counts, 90):.0f}, "
          f"p95={np.percentile(node_counts, 95):.0f}, "
          f"p99={np.percentile(node_counts, 99):.0f}")

    # Edge stats
    edges = [int(g['adjacency'].numpy()[:g['num_nodes'], :g['num_nodes']].sum() / 2) for g in graphs]
    earr = np.array(edges)
    print(f"  Edges per graph:  min={earr.min()}, max={earr.max()}, mean={earr.mean():.1f}")
    no_edge = (earr == 0).sum()
    if no_edge:
        print(f"  ⚠ Graphs with 0 edges: {no_edge}")

    # Edge type distribution
    et_counts = Counter()
    et_names = {v: k for k, v in EDGE_TYPE_MAP.items()}
    for g in graphs:
        et = g['edge_types'].numpy()
        n = g['num_nodes']
        for val in et[:n, :n].flatten():
            if val > 0:
                et_counts[et_names.get(int(val), f'type_{val}')] += 1
    print(f"  Edge types:")
    for k, c in et_counts.most_common():
        print(f"    {k:12s}: {c//2:6d} edges")

    # Room type distribution
    type_counts = Counter()
    for g in graphs:
        nf = g['node_features'].numpy()
        for i in range(g['num_nodes']):
            tidx = int(np.argmax(nf[i, :NUM_TYPES]))
            type_counts[ROOM_TYPES[tidx]] += 1
    print(f"  Room types:")
    total = sum(type_counts.values())
    for rtype, count in type_counts.most_common():
        print(f"    {rtype:12s}: {count:6d} ({100*count/total:.1f}%)")

    # Spatial feature ranges
    all_feats = np.concatenate([g['node_features'].numpy()[:g['num_nodes']] for g in graphs[:500]])
    names = ['x_min', 'y_min', 'x_max', 'y_max', 'area', 'is_ext']
    print(f"  Spatial features (500 samples):")
    for j, name in enumerate(names):
        col = all_feats[:, NUM_TYPES + j]
        print(f"    {name:8s}: [{col.min():.3f}, {col.max():.3f}]  mean={col.mean():.3f}  std={col.std():.3f}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Preprocess ResPlan for ArchiText")
    parser.add_argument('--max-nodes',  type=int,   default=16)
    parser.add_argument('--batch-size', type=int,   default=128)
    parser.add_argument('--val-split',  type=float, default=0.15)
    parser.add_argument('--seed',       type=int,   default=42)
    parser.add_argument('--no-augment', action='store_true')
    parser.add_argument('--out-dir',    type=str,   default=None)
    args = parser.parse_args()

    MAX_NODES  = args.max_nodes
    BATCH_SIZE = args.batch_size
    OUT_DIR    = Path(args.out_dir) if args.out_dir else ROOT / "data" / "processed_v3"

    random.seed(args.seed)
    np.random.seed(args.seed)

    # ── Load ───────────────────────────────────────────────────────────────────
    print(f"Loading {DATA_PKL} ...")
    t0 = time.time()
    with open(DATA_PKL, 'rb') as f:
        raw_data = pickle.load(f)
    print(f"  Loaded {len(raw_data)} samples in {time.time()-t0:.1f}s")

    # ── Convert ────────────────────────────────────────────────────────────────
    print(f"\nExtracting graphs (max_nodes={MAX_NODES}) ...")
    graphs = []
    skipped = 0

    for idx, plan in enumerate(raw_data):
        g = plan_to_graph(plan, MAX_NODES, sample_id=idx)
        if g is None:
            skipped += 1
        else:
            graphs.append(g)

        if (idx + 1) % 2000 == 0:
            print(f"  {idx+1}/{len(raw_data)} → {len(graphs)} valid, {skipped} skipped")

    print(f"\n  Valid: {len(graphs)} | Skipped: {skipped}")

    # ── Stats ──────────────────────────────────────────────────────────────────
    print_stats(graphs)

    # ── Verify reconstruction ──────────────────────────────────────────────────
    validate_reconstruction(graphs, raw_data)

    # ── Split ──────────────────────────────────────────────────────────────────
    random.shuffle(graphs)
    split = int(len(graphs) * (1 - args.val_split))
    train_graphs = graphs[:split]
    val_graphs   = graphs[split:]
    print(f"\n  Train (raw): {len(train_graphs)} | Val: {len(val_graphs)}")

    # ── Augment ────────────────────────────────────────────────────────────────
    if not args.no_augment:
        aug = []
        for g in train_graphs:
            aug.append(g)
            aug.append(augment_flip(g, True,  False))
            aug.append(augment_flip(g, False, True))
            aug.append(augment_flip(g, True,  True))
        random.shuffle(aug)
        train_graphs = aug
        print(f"  Train (4× augmented): {len(train_graphs)}")

    # ── Save ───────────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train_dir = OUT_DIR / "train"
    val_dir   = OUT_DIR / "val"
    train_dir.mkdir(exist_ok=True)
    val_dir.mkdir(exist_ok=True)

    for f in train_dir.glob("batch_*.pt"):
        f.unlink()
    for f in val_dir.glob("batch_*.pt"):
        f.unlink()

    print(f"\nSaving batches (batch_size={BATCH_SIZE}) ...")
    n_train = save_batches(train_graphs, train_dir, "Train", BATCH_SIZE, MAX_NODES)
    n_val   = save_batches(val_graphs,   val_dir,   "Val",   BATCH_SIZE, MAX_NODES)

    # ── Norm constants ─────────────────────────────────────────────────────────
    # Compute canvas scale for denormalization at inference time
    plan_widths = []
    for plan in raw_data[:2000]:
        inner = plan.get('inner')
        if inner is not None and not inner.is_empty:
            b = inner.bounds
            plan_widths.append(max(b[2] - b[0], b[3] - b[1]))
    canvas_px = float(np.median(plan_widths)) if plan_widths else 256.0
    canvas_metres = canvas_px * 0.05  # ResPlan: ~1px ≈ 5cm

    norm = {
        # Dimensions
        'node_feature_dim':   NODE_FEAT_DIM,     # 16
        'condition_dim':      CONDITION_DIM,      # 11
        'max_nodes':          MAX_NODES,
        'num_room_types':     NUM_TYPES,          # 10
        'num_edge_types':     NUM_EDGE_TYPES,     # 5

        # Type system
        'room_types':         ROOM_TYPES,

        # Feature layout
        'spatial_start':      NUM_TYPES,          # index 10
        'spatial_names':      ['x_min', 'y_min', 'x_max', 'y_max', 'area_norm', 'is_external'],

        # Denormalization constants
        'canvas_px':          canvas_px,          # median plan size in pixels
        'canvas_metres':      canvas_metres,      # median plan size in metres

        # Dataset info
        'num_train_batches':  n_train,
        'num_val_batches':    n_val,
        'num_train_samples':  len(train_graphs),
        'num_val_samples':    len(val_graphs),
        'source':             'ResPlan',
        'version':            'v3_fresh',
    }
    norm_path = OUT_DIR / "norm_constants.npy"
    np.save(str(norm_path), norm)

    # ── Done ───────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"✅ Preprocessing complete!")
    print(f"   Output:       {OUT_DIR}")
    print(f"   Train:        {n_train} batches × {BATCH_SIZE} = ~{len(train_graphs)} samples")
    print(f"   Val:          {n_val} batches × {BATCH_SIZE} = ~{len(val_graphs)} samples")
    print(f"   Node feat:    {NODE_FEAT_DIM}-dim ({NUM_TYPES} type + 6 spatial)")
    print(f"   Condition:    {CONDITION_DIM}-dim ({NUM_TYPES} counts + total)")
    print(f"   Edge types:   {NUM_EDGE_TYPES} (none + {list(EDGE_TYPE_MAP.keys())})")
    print(f"   Max nodes:    {MAX_NODES}")
    print(f"   Canvas:       {canvas_px:.0f}px = {canvas_metres:.1f}m")
    print(f"   Norm:         {norm_path}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
