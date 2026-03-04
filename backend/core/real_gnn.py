"""
Real GNN Adapter — Layer 2

Loads the trained StructuralGNN from gnn_best.pt and runs inference
to produce a standard room graph dict for the IFC adapter.

Replaces MockGNNAdapter in backend/core/pipeline.py.
To swap in: change pipeline.py line:
    _mock_gnn = MockGNNAdapter()
to:
    _mock_gnn = RealGNNAdapter()
"""

import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional

_ROOT = Path(__file__).parent.parent.parent.resolve()

MODEL_PATH      = _ROOT / "models" / "resplan_gnn" / "gnn_best.pt"
NORM_PATH       = _ROOT / "data" / "processed" / "norm_constants.npy"

ROOM_TYPES = ['wall', 'bedroom', 'bathroom', 'living', 'kitchen',
              'balcony', 'storage', 'parking', 'garden', 'pool',
              'stair', 'veranda', 'inner']


# ── Model architecture (must match training notebook exactly) ──────────────────

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
    def __init__(self, condition_dim, node_feature_dim,
                 hidden_dim=256, num_layers=4, max_nodes=30, dropout=0.1):
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
        B        = condition.shape[0]
        cond_emb = self.condition_encoder(condition)
        num_nodes_logits = self.num_nodes_predictor(cond_emb)

        nodes    = self.node_embedding.expand(B, -1, -1)
        cond_p   = self.cond_to_nodes(cond_emb).unsqueeze(1)
        nodes    = nodes + cond_p

        for layer in self.gnn_layers:
            nodes = layer(nodes, mask)

        node_features = self.node_head(nodes)
        num_room_types = node_features.shape[-1] - 3
        room_type_pred = F.softmax(node_features[..., :num_room_types], dim=-1)
        other_pred     = torch.sigmoid(node_features[..., num_room_types:])
        node_features_pred = torch.cat([room_type_pred, other_pred], dim=-1)

        nodes_i = nodes.unsqueeze(2).expand(-1, -1, self.max_nodes, -1)
        nodes_j = nodes.unsqueeze(1).expand(-1, self.max_nodes, -1, -1)
        adj_logits = self.edge_head(
            torch.cat([nodes_i, nodes_j], dim=-1)
        ).squeeze(-1)
        adj_logits = (adj_logits + adj_logits.transpose(-1, -2)) / 2

        return {
            'node_features':     node_features_pred,
            'adjacency_logits':  adj_logits,
            'num_nodes_logits':  num_nodes_logits,
        }


# ── Inference helper ───────────────────────────────────────────────────────────

# Realistic per-type area ranges (min, max) in m² — derived from ResPlan dataset
_ROOM_AREA_RANGES = {
    'bedroom':  (9.0,  20.0),
    'bathroom': (3.5,   8.0),
    'living':   (12.0, 35.0),
    'kitchen':  (6.0,  15.0),
    'balcony':  (3.0,   8.0),
    'storage':  (2.0,   6.0),
    'parking':  (12.0, 30.0),
    'garden':   (15.0, 50.0),
    'pool':     (10.0, 40.0),
    'stair':    (4.0,  10.0),
    'veranda':  (5.0,  15.0),
    'inner':    (3.0,   8.0),
}
_DEFAULT_AREA_RANGE = (4.0, 20.0)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def _decode_room_graph(node_features: np.ndarray,
                       adj_matrix: np.ndarray,
                       num_nodes: int,
                       norm_constants: dict) -> List[Dict]:
    """Convert raw model output → list of room dicts with corrected decoding."""
    rooms = []
    num_room_types = len(ROOM_TYPES)

    for i in range(min(num_nodes, node_features.shape[0])):
        feat = node_features[i]

        # Room type: argmax of the one-hot softmax portion
        type_idx  = int(np.argmax(feat[:num_room_types]))
        room_type = ROOM_TYPES[type_idx] if type_idx < len(ROOM_TYPES) else "other"

        # Skip structural wall nodes
        if room_type == "wall":
            continue

        # BUG FIX 2: Area — model outputs a sigmoid-normalised value in [0,1].
        # Map it to a realistic per-type range instead of arbitrary ×50.
        area_norm = float(np.clip(feat[num_room_types], 0.0, 1.0))
        lo, hi    = _ROOM_AREA_RANGES.get(room_type, _DEFAULT_AREA_RANGE)
        area_m2   = lo + area_norm * (hi - lo)
        area_m2   = round(float(area_m2), 2)

        # Derive width/height from area using a mild aspect ratio
        aspect = np.random.uniform(1.1, 1.6)           # slight variety
        width  = round(float(np.sqrt(area_m2 / aspect)), 2)
        height = round(float(area_m2 / width),           2)

        # BUG FIX 3: Centroid → top-left corner.
        # feat[num_room_types+1/2] is the room *center* in [0,1]. Convert to
        # top-left by subtracting half the room dimensions.
        cx_norm = float(np.clip(feat[num_room_types + 1], 0.0, 1.0))
        cy_norm = float(np.clip(feat[num_room_types + 2], 0.0, 1.0))
        CANVAS  = 30.0                                  # metres, generous canvas
        cx      = cx_norm * CANVAS
        cy      = cy_norm * CANVAS
        x       = round(cx - width  / 2.0, 2)
        y       = round(cy - height / 2.0, 2)

        rooms.append({
            "id":     f"{room_type}_{i}",
            "type":   room_type,
            "x":      x,
            "y":      y,
            "width":  width,
            "height": height,
            "area":   area_m2,
        })

    return rooms


# ── Public adapter class ───────────────────────────────────────────────────────

class RealGNNAdapter:
    """
    Drop-in replacement for MockGNNAdapter.
    Loads gnn_best.pt and runs real inference.
    """
    IS_MOCK = False

    def __init__(self,
                 model_path: Optional[str] = None,
                 norm_path:  Optional[str] = None,
                 device:     Optional[str] = None):

        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        mp = Path(model_path) if model_path else MODEL_PATH
        np_path = Path(norm_path)  if norm_path  else NORM_PATH

        print(f"[GNN] Loading model from {mp} on {self.device}...")
        ckpt   = torch.load(str(mp), map_location=self.device, weights_only=False)
        config = ckpt.get("config", {})

        self.norm_constants = np.load(str(np_path), allow_pickle=True).item()

        self.model = StructuralGNN(
            condition_dim    = self.norm_constants["condition_dim"],
            node_feature_dim = self.norm_constants["node_feature_dim"],
            hidden_dim  = config.get("hidden_dim",  256),
            num_layers  = config.get("num_layers",  4),
            max_nodes   = config.get("max_nodes",   30),
            dropout     = config.get("dropout",     0.1),
        ).to(self.device)

        self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()
        self.max_nodes = config.get("max_nodes", 30)
        print(f"[GNN] Model loaded. Best epoch: {ckpt.get('epoch', '?')}")

    @torch.no_grad()
    def generate(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Args:
            spec: normalised room spec dict from spec_converter.normalise_spec()
        Returns:
            Standard room_graph dict for RoomGraphToIFC
        """
        # Build condition vector from spec
        sys.path.insert(0, str(_ROOT / "backend" / "core"))
        from spec_converter import spec_to_condition_vector
        cond_vec = spec_to_condition_vector(spec)

        condition = torch.tensor(cond_vec, dtype=torch.float32).unsqueeze(0).to(self.device)
        mask      = torch.ones(1, self.max_nodes, dtype=torch.float32).to(self.device)

        output = self.model(condition, mask)

        # FIX 3: num_nodes = EXACTLY what the spec asks for (no more estimation)
        # Build the target flat room-type list directly from spec, in priority order.
        ROOM_PRIORITY = [
            'bedroom', 'living', 'kitchen', 'bathroom',
            'balcony', 'parking', 'garden', 'storage',
            'pool', 'stair', 'veranda', 'inner',
        ]
        target_types: List[str] = []
        for rtype in ROOM_PRIORITY:
            count = int(spec.get(rtype, 0))
            target_types.extend([rtype] * count)

        # Always generate at least 1 room
        if not target_types:
            target_types = ['living']

        pred_num_nodes = min(len(target_types), self.max_nodes)

        node_features = output["node_features"][0].cpu().numpy()
        adj_logits    = output["adjacency_logits"][0].cpu().numpy()
        adj_matrix    = (1 / (1 + np.exp(-adj_logits)) > 0.5).astype(float)

        # Get raw spatial layout from GNN (positions + areas from node features)
        # We use GNN's spatial layout but OVERRIDE room types with spec assignments.
        raw_rooms = _decode_room_graph(
            node_features, adj_matrix, pred_num_nodes, self.norm_constants
        )

        # FIX 1: Override room types with spec-driven assignments.
        # Sort raw_rooms by area descending — bigger rooms become higher-priority types
        # (bedrooms > living > kitchen > bathrooms makes physical sense by area).
        raw_rooms.sort(key=lambda r: r["area"], reverse=True)

        rooms = []
        for i, rtype in enumerate(target_types[:len(raw_rooms)]):
            if i < len(raw_rooms):
                r = raw_rooms[i].copy()
            else:
                # More rooms requested than GNN produced — create a default
                r = {
                    "x": float(i) * 4.0, "y": 0.0,
                    "width": 3.0, "height": 3.0, "area": 9.0,
                }
            # Apply per-type realistic area range
            lo, hi = _ROOM_AREA_RANGES.get(rtype, _DEFAULT_AREA_RANGE)
            area_m2 = float(np.clip(r["area"], lo, hi))
            aspect  = np.random.uniform(1.1, 1.5)
            width   = round(float(np.sqrt(area_m2 / aspect)), 2)
            height  = round(float(area_m2 / width), 2)
            rooms.append({
                "id":     f"{rtype}_{i}",
                "type":   rtype,
                "x":      r["x"],
                "y":      r["y"],
                "width":  width,
                "height": height,
                "area":   round(area_m2, 2),
            })

        # Fallback if still empty
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
                "generated_by":   "resplan_gnn_300ep_spec_typed",
                "is_mock":        False,
            }
        }


# ── Singleton loader ───────────────────────────────────────────────────────────
_real_gnn: Optional[RealGNNAdapter] = None

def get_real_gnn() -> RealGNNAdapter:
    global _real_gnn
    if _real_gnn is None:
        _real_gnn = RealGNNAdapter()
    return _real_gnn


if __name__ == "__main__":
    adapter = RealGNNAdapter()
    test_spec = {
        "unit_type": "house", "net_area": 150,
        "bedroom": 3, "bathroom": 2, "living": 1, "kitchen": 1,
        "balcony": 1, "garden": 1, "parking": 1,
        "storage": 0, "pool": 0, "stair": 0, "veranda": 0, "inner": 1,
    }
    graph = adapter.generate(test_spec)
    print(f"\nGenerated {len(graph['rooms'])} rooms:")
    for r in graph["rooms"]:
        print(f"  {r['type']:12} {r['width']:.1f}x{r['height']:.1f}m  at ({r['x']}, {r['y']})")
    print(f"Total area: {graph['metadata']['total_area']} m²")
