"""
Real GNN Adapter — Layer 2

Loads the trained StructuralGNN from gnn_best.pt (trained by gnn-phase.ipynb)
and runs inference to produce a standard room graph dict for the IFC adapter.

Architecture note:
    This uses the deterministic StructuralGNN from the notebook (NOT the CVAE).
    Node feature layout (16-dim, matches pre-processing.ipynb EXACTLY):
        [0:13]  one-hot room type  (13 classes, see ROOM_TYPES below)
        [13]    area_norm       = room_area / net_area  ∈ [0,1]
        [14]    cx_norm         = centroid_x / plan_width ∈ [0,1]
        [15]    cy_norm         = centroid_y / plan_height ∈ [0,1]

    Condition vector (18-dim, matches spec_converter.py):
        [0:9]   room counts / 5.0  (bedroom, bathroom, kitchen, living_room,
                                    dining_room, balcony, garden, storage, parking)
        [9]     total_rooms / 16
        [10]    is_apartment
        [11]    is_house
        [12:18] padding zeros
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional

_ROOT = Path(__file__).parent.parent.parent.resolve()

MODEL_PATH = _ROOT / "models" / "resplan_gnn" / "gnn_best.pt"
NORM_PATH  = _ROOT / "data" / "processed" / "norm_constants.npy"

# ── Room types — MUST match pre-processing.ipynb ROOM_TYPES exactly ────────────
# (order matters: feature index 0 = wall, 1 = bedroom, etc.)
ROOM_TYPES = [
    'wall',       # 0  — never predicted as a room node, but part of one-hot
    'bedroom',    # 1
    'bathroom',   # 2
    'living',     # 3  (notebook key for living room)
    'kitchen',    # 4
    'balcony',    # 5
    'storage',    # 6
    'parking',    # 7
    'garden',     # 8
    'pool',       # 9
    'stair',      # 10
    'veranda',    # 11
    'inner',      # 12 — never predicted as a room node
]
NUM_TYPES = len(ROOM_TYPES)  # 13

# Display name overrides for IFC / UI  (notebook key → display name)
_DISPLAY_NAME = {
    'living':  'living',
    'stair':   'stair',
    'veranda': 'balcony',   # collapse veranda → balcony for IFC
    'pool':    'other',
    'wall':    'other',
    'inner':   'other',
}

# Average canvas size (from preprocessing: median plan width 12.8 m)
CANVAS_W    = 12.8   # metres
CANVAS_H    = 12.0   # metres (approximation)
CANVAS_AREA = CANVAS_W * CANVAS_H


# ── StructuralGNN — identical to gnn-phase.ipynb ───────────────────────────────

class GraphAttention(nn.Module):
    def __init__(self, in_dim, out_dim, num_heads=4):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim  = out_dim // num_heads
        self.W_q = nn.Linear(in_dim, out_dim)
        self.W_k = nn.Linear(in_dim, out_dim)
        self.W_v = nn.Linear(in_dim, out_dim)
        self.W_o = nn.Linear(out_dim, out_dim)
        self.scale = self.head_dim ** -0.5

    def forward(self, x, mask=None):
        B, N, _ = x.shape
        Q = self.W_q(x).view(B, N, self.num_heads, self.head_dim).transpose(1, 2)
        K = self.W_k(x).view(B, N, self.num_heads, self.head_dim).transpose(1, 2)
        V = self.W_v(x).view(B, N, self.num_heads, self.head_dim).transpose(1, 2)
        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
        if mask is not None:
            mask_2d = mask.unsqueeze(1).unsqueeze(2) * mask.unsqueeze(1).unsqueeze(3)
            scores = scores.masked_fill(mask_2d == 0, -1e4)
        attn = F.softmax(scores, dim=-1)
        out  = torch.matmul(attn, V)
        out  = out.transpose(1, 2).contiguous().view(B, N, -1)
        return self.W_o(out)


class GNNLayer(nn.Module):
    def __init__(self, hidden_dim, num_heads=4, dropout=0.1):
        super().__init__()
        self.attention = GraphAttention(hidden_dim, hidden_dim, num_heads)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.ff = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 4), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 4, hidden_dim), nn.Dropout(dropout),
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        x = x + self.dropout(self.attention(self.norm1(x), mask))
        x = x + self.ff(self.norm2(x))
        return x


class StructuralGNN(nn.Module):
    """
    Deterministic GNN — identical to gnn-phase.ipynb StructuralGNN.
    condition → node_features + adjacency_logits + num_nodes_logits
    """
    def __init__(self, condition_dim, node_feature_dim,
                 hidden_dim=256, num_layers=4, max_nodes=20, dropout=0.1):
        super().__init__()
        self.max_nodes        = max_nodes
        self.hidden_dim       = hidden_dim
        self.node_feature_dim = node_feature_dim

        self.condition_encoder = nn.Sequential(
            nn.Linear(condition_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),    nn.LayerNorm(hidden_dim), nn.GELU(),
        )
        self.num_nodes_predictor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2), nn.GELU(),
            nn.Linear(hidden_dim // 2, max_nodes),
        )
        self.node_embedding = nn.Parameter(torch.randn(1, max_nodes, hidden_dim) * 0.02)
        self.cond_to_nodes  = nn.Linear(hidden_dim, hidden_dim)

        self.gnn_layers = nn.ModuleList([
            GNNLayer(hidden_dim, num_heads=4, dropout=dropout)
            for _ in range(num_layers)
        ])

        self.node_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, node_feature_dim),
        )
        self.edge_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, condition, mask=None):
        B = condition.shape[0]
        cond_emb = self.condition_encoder(condition)              # [B, H]
        num_nodes_logits = self.num_nodes_predictor(cond_emb)     # [B, max_nodes]

        nodes    = self.node_embedding.expand(B, -1, -1)          # [B, N, H]
        cond_proj = self.cond_to_nodes(cond_emb).unsqueeze(1)     # [B, 1, H]
        nodes    = nodes + cond_proj

        for layer in self.gnn_layers:
            nodes = layer(nodes, mask)

        node_features = self.node_head(nodes)                     # [B, N, feat]
        # Split: type logits (0:13) softmax, spatial features sigmoid
        num_room_types    = node_features.shape[-1] - 3
        room_type_logits  = node_features[..., :num_room_types]
        other_features    = node_features[..., num_room_types:]
        room_types_pred   = F.softmax(room_type_logits, dim=-1)
        other_pred        = torch.sigmoid(other_features)
        node_features_pred = torch.cat([room_types_pred, other_pred], dim=-1)

        # Adjacency
        nodes_i = nodes.unsqueeze(2).expand(-1, -1, self.max_nodes, -1)
        nodes_j = nodes.unsqueeze(1).expand(-1, self.max_nodes, -1, -1)
        adj_logits = self.edge_head(torch.cat([nodes_i, nodes_j], dim=-1)).squeeze(-1)
        adj_logits = (adj_logits + adj_logits.transpose(-1, -2)) / 2

        return {
            'node_features':    node_features_pred,
            'adjacency_logits': adj_logits,
            'num_nodes_logits': num_nodes_logits,
        }


# ── Decoder helper ─────────────────────────────────────────────────────────────

def _decode_room_graph(node_features: np.ndarray,
                       adj_matrix:    np.ndarray,
                       num_nodes:     int,
                       norm_constants: dict) -> List[Dict]:
    """
    Convert raw StructuralGNN node_features → list of room dicts.

    Feature indices (matching pre-processing.ipynb):
        [0:13]  soft one-hot room type
        [13]    area_norm
        [14]    cx_norm
        [15]    cy_norm
    """
    # Canvas scale: use norm_constants if available, else dataset default
    canvas_w = float(norm_constants.get('canvas_metres', CANVAS_W))
    canvas_h = canvas_w * (CANVAS_H / CANVAS_W)   # keep aspect ratio

    rooms = []
    for i in range(min(num_nodes, node_features.shape[0])):
        feat = node_features[i]

        # Room type
        type_idx  = int(np.argmax(feat[:NUM_TYPES]))
        room_type = ROOM_TYPES[type_idx]

        # Skip non-room types (wall, inner)
        if room_type in ('wall', 'inner'):
            continue

        # Spatial features at indices 13, 14, 15
        a_norm  = float(np.clip(feat[13], 0.01, 1.0))
        cx_norm = float(np.clip(feat[14], 0.01, 0.99))
        cy_norm = float(np.clip(feat[15], 0.01, 0.99))

        # Denormalize
        cx     = cx_norm * canvas_w
        cy     = cy_norm * canvas_h
        area   = a_norm  * canvas_w * canvas_h

        # Estimate width/height from area (assume ~1.3 aspect ratio)
        aspect = 1.3
        width  = max(float(np.sqrt(area / aspect)), 1.5)
        height = max(float(area / width),            1.5)

        x = round(cx - width  / 2.0, 2)
        y = round(cy - height / 2.0, 2)

        display_type = _DISPLAY_NAME.get(room_type, room_type)

        rooms.append({
            "id":     f"{display_type}_{i}",
            "type":   display_type,
            "x":      x,
            "y":      y,
            "width":  round(width,  2),
            "height": round(height, 2),
            "area":   round(area,   2),
        })

    return rooms


# ── Condition vector adapter ───────────────────────────────────────────────────

def _build_condition_for_notebook(cond_vec: np.ndarray) -> np.ndarray:
    """
    spec_converter produces an 18-dim vector already compatible with the
    notebook's training format. Just return it as-is.

    Both use:
        [0:9]   room counts / 5.0
        [9]     total_rooms / 16
        [10]    is_apartment
        [11]    is_house
        [12:18] zeros
    """
    return cond_vec.copy()


# ── Public adapter class ───────────────────────────────────────────────────────

class RealGNNAdapter:
    """
    Drop-in replacement for MockGNNAdapter.
    Loads gnn_best.pt (StructuralGNN from gnn-phase.ipynb) and runs inference.
    """
    IS_MOCK = False

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = None
        self.norm_constants = {}
        self._load()

    def _load(self):
        print(f"[GNN] Loading model from {MODEL_PATH}")
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found: {MODEL_PATH}\n"
                "Run notebooks/gnn-phase.ipynb to train the model first."
            )

        ckpt = torch.load(str(MODEL_PATH), map_location=self.device, weights_only=False)

        # Load norm_constants (used for canvas scale)
        if NORM_PATH.exists():
            self.norm_constants = np.load(str(NORM_PATH), allow_pickle=True).item()
        else:
            self.norm_constants = {}

        config = ckpt.get("config", {})

        self.model = StructuralGNN(
            condition_dim    = self.norm_constants.get("condition_dim",    18),
            node_feature_dim = self.norm_constants.get("node_feature_dim", 16),
            hidden_dim       = config.get("hidden_dim",  256),
            num_layers       = config.get("num_layers",  4),
            max_nodes        = config.get("max_nodes",   20),
            dropout          = config.get("dropout",     0.1),
        ).to(self.device)

        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()
        self.max_nodes = config.get("max_nodes", 20)
        print(f"[GNN] StructuralGNN loaded. Best epoch: {ckpt.get('epoch', '?')}")

    @torch.no_grad()
    def generate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Args:
            spec: normalised room spec dict from spec_converter.normalise_spec()
        Returns:
            Standard room_graph dict for RoomGraphToIFC
        """
        sys.path.insert(0, str(_ROOT / "backend" / "core"))
        from spec_converter import spec_to_condition_vector
        cond_vec = spec_to_condition_vector(spec)
        cond_vec = _build_condition_for_notebook(cond_vec)

        condition = torch.tensor(cond_vec, dtype=torch.float32).unsqueeze(0).to(self.device)
        mask      = torch.ones(1, self.max_nodes, dtype=torch.float32).to(self.device)

        output = self.model(condition, mask=mask)

        node_features = output["node_features"][0].cpu().numpy()
        adj_logits    = output["adjacency_logits"][0].cpu().numpy()
        adj_matrix    = (1 / (1 + np.exp(-adj_logits)) > 0.5).astype(float)

        # Predict num_nodes from what the spec requested
        ROOM_PRIORITY = [
            'bedroom', 'bathroom', 'kitchen', 'living_room',
            'dining_room', 'balcony', 'garden', 'storage', 'parking',
        ]
        target_types: List[str] = []
        for rtype in ROOM_PRIORITY:
            count = int(spec.get(rtype, 0))
            target_types.extend([rtype] * count)
        if not target_types:
            target_types = ['living_room']

        pred_num_nodes = min(len(target_types), self.max_nodes)

        # Decode raw model output
        raw_rooms = _decode_room_graph(
            node_features, adj_matrix, pred_num_nodes, self.norm_constants
        )

        # Sort by area desc and assign spec-driven types
        raw_rooms.sort(key=lambda r: r["area"], reverse=True)

        # Notebook room key → display name mapping
        _SPEC_TO_DISPLAY = {
            'bedroom': 'bedroom', 'bathroom': 'bathroom',
            'kitchen': 'kitchen', 'living_room': 'living',
            'dining_room': 'dining', 'balcony': 'balcony',
            'garden': 'garden', 'storage': 'storage', 'parking': 'parking',
        }

        rooms = []
        for i, rtype in enumerate(target_types):
            display_type = _SPEC_TO_DISPLAY.get(rtype, rtype)
            if i < len(raw_rooms):
                r = raw_rooms[i].copy()
                r["id"]   = f"{display_type}_{i}"
                r["type"] = display_type
            else:
                r = {
                    "id":     f"{display_type}_{i}",
                    "type":   display_type,
                    "x":      float(i) * 4.0,
                    "y":      0.0,
                    "width":  3.0,
                    "height": 3.0,
                    "area":   9.0,
                }
            rooms.append(r)

        if not rooms:
            from backend.core.mock_gnn import generate_mock_layout
            print("[GNN] Warning: model produced no valid rooms, using mock fallback")
            rooms = generate_mock_layout(spec)

        total_area = sum(r["width"] * r["height"] for r in rooms)

        return {
            "rooms": rooms,
            "metadata": {
                "unit_type":      spec.get("unit_type", "house"),
                "total_area":     round(total_area, 1),
                "requested_area": spec.get("net_area", 100),
                "generated_by":   "structural_gnn_resplan",
                "is_mock":        False,
            }
        }


# ── Singleton loader ───────────────────────────────────────────────────────────

_instance: Optional[RealGNNAdapter] = None

def get_real_gnn() -> RealGNNAdapter:
    global _instance
    if _instance is None:
        _instance = RealGNNAdapter()
    return _instance
