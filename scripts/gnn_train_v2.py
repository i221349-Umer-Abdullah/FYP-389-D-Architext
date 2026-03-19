"""
gnn_train_v2.py — ArchiText GNN Training Script (v2)

Key improvements over v1 (gnn-phase.ipynb):
  - Loads from data/processed_v2 (properly normalized features)
  - max_nodes = 12 (fixes the argmax→30 bug)
  - 4 loss terms: adjacency + type + spatial + num_nodes
  - Spatial loss (MSE on cx/cy/w/h/area) weighted 3× — the main fix
  - Gradient clipping
  - Best checkpoint saved at models/resplan_gnn/gnn_best_v2.pt

Run:
    .\venv\Scripts\python.exe scripts\gnn_train_v2.py
"""
import os, sys, time, glob
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from torch.optim.lr_scheduler import CosineAnnealingLR

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent.resolve()
DATA_DIR   = ROOT / "data" / "processed_v2"
CKPT_DIR   = ROOT / "models" / "resplan_gnn"
BEST_PT    = CKPT_DIR / "gnn_best_v2.pt"
LATEST_PT  = CKPT_DIR / "gnn_latest_v2.pt"
NORM_PATH  = DATA_DIR / "norm_constants.npy"

CKPT_DIR.mkdir(parents=True, exist_ok=True)

# ── Hyperparameters ────────────────────────────────────────────────────────────
NUM_EPOCHS   = 300
LR           = 6e-4   # scaled up 2× to match batch_size=64 (linear scaling rule)
HIDDEN_DIM   = 256
NUM_LAYERS   = 4
DROPOUT      = 0.1
MAX_NODES    = 16   # MUST match preprocessing (covers p99 of dataset)

# Loss weights
W_ADJ     = 1.0   # adjacency BCE
W_TYPE    = 2.0   # room type cross-entropy
W_SPATIAL = 3.0   # spatial MSE (cx,cy,w,h,area) — highest weight
W_NUM     = 1.0   # num_nodes cross-entropy

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")

# ── Load norm constants ────────────────────────────────────────────────────────
norm = np.load(str(NORM_PATH), allow_pickle=True).item()
CONDITION_DIM    = norm['condition_dim']     # 18
NODE_FEATURE_DIM = norm['node_feature_dim']  # 16
NUM_TYPES        = 10   # 10 room types (9 functional + other; hallway → other)


# ── Model (same architecture as v1 for compatibility) ─────────────────────────
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
            m = mask.unsqueeze(1).unsqueeze(2) * mask.unsqueeze(1).unsqueeze(3)
            scores = scores.masked_fill(m == 0, -1e4)
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
                 hidden_dim=256, num_layers=4, max_nodes=12, dropout=0.1):
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
        B       = condition.shape[0]
        cond_emb = self.condition_encoder(condition)
        num_nodes_logits = self.num_nodes_predictor(cond_emb)

        nodes  = self.node_embedding.expand(B, -1, -1)
        cond_p = self.cond_to_nodes(cond_emb).unsqueeze(1)
        nodes  = nodes + cond_p

        for layer in self.gnn_layers:
            nodes = layer(nodes, mask)

        node_features = self.node_head(nodes)
        # Split: first NUM_TYPES → type logits (no activation), rest → sigmoid
        type_logits = node_features[..., :NUM_TYPES]
        other_pred  = torch.sigmoid(node_features[..., NUM_TYPES:])
        node_out    = torch.cat([type_logits, other_pred], dim=-1)

        nodes_i = nodes.unsqueeze(2).expand(-1, -1, self.max_nodes, -1)
        nodes_j = nodes.unsqueeze(1).expand(-1, self.max_nodes, -1, -1)
        adj_logits = self.edge_head(
            torch.cat([nodes_i, nodes_j], dim=-1)
        ).squeeze(-1)
        adj_logits = (adj_logits + adj_logits.transpose(-1, -2)) / 2

        return {
            'node_features':    node_out,
            'type_logits':      type_logits,
            'adjacency_logits': adj_logits,
            'num_nodes_logits': num_nodes_logits,
        }


# ── Data loading ───────────────────────────────────────────────────────────────
def load_batches(split: str):
    folder = DATA_DIR / split
    files  = sorted(folder.glob("batch_*.pt"))
    batches = []
    for f in files:
        b = torch.load(str(f), map_location='cpu', weights_only=False)
        batches.append(b)
    return batches


def pad_batch_to_max(batch: dict) -> dict:
    """
    Pad all per-node tensors in a batch to exactly MAX_NODES.
    This ensures model output shapes always align with batch target shapes.
    """
    cur_n = batch['mask'].shape[1]
    if cur_n == MAX_NODES:
        return batch
    pad = MAX_NODES - cur_n
    return {
        'node_features': F.pad(batch['node_features'], (0, 0, 0, pad)),  # [B, N+pad, feat]
        'adjacency':     F.pad(batch['adjacency'],     (0, pad, 0, pad)), # [B, N+pad, N+pad]
        'condition':     batch['condition'],
        'num_nodes':     batch['num_nodes'],
        'mask':          F.pad(batch['mask'],           (0, pad)),         # [B, N+pad]
    }


# ── Loss function ──────────────────────────────────────────────────────────────
def compute_loss(output, batch):
    """
    4-term loss:
      L_adj     = BCE on adjacency
      L_type    = Cross-entropy on room type (argmax of first NUM_TYPES feats)
      L_spatial = MSE on (cx, cy, width, height, area) normalised
      L_num     = Cross-entropy on num_nodes (as class index)
    """
    mask          = batch['mask'].to(DEVICE)          # [B, MAX_NODES]
    adj_target    = batch['adjacency'].to(DEVICE)     # [B, MAX_NODES, MAX_NODES]
    node_target   = batch['node_features'].to(DEVICE) # [B, MAX_NODES, 17]
    num_nodes_gt  = batch['num_nodes'].to(DEVICE)     # [B]

    B, N = mask.shape  # N == MAX_NODES after padding

    # ── Adjacency loss ─────────────────────────────────────────────────────────
    adj_logits  = output['adjacency_logits']           # [B, max_n, max_n]
    adj_mask    = mask.unsqueeze(2) * mask.unsqueeze(1)
    L_adj = F.binary_cross_entropy_with_logits(
        adj_logits, adj_target, reduction='none'
    )
    L_adj = (L_adj * adj_mask).sum() / (adj_mask.sum() + 1e-8)

    # ── Type loss (cross-entropy per node) ────────────────────────────────────
    type_logits = output['type_logits']                # [B, max_n, NUM_TYPES]
    type_target = node_target[..., :NUM_TYPES].argmax(dim=-1)  # [B, max_n]
    L_type = F.cross_entropy(
        type_logits.reshape(-1, NUM_TYPES),
        type_target.reshape(-1),
        reduction='none'
    ).view(B, N)
    L_type = (L_type * mask).sum() / (mask.sum() + 1e-8)

    # ── Spatial loss (MSE on normalized cx, cy, w, h, area) ──────────────────
    # node_target[:, :, 10:15] = [cx, cy, width, height, area]
    # model outputs sigmoid → should predict these directly
    spatial_pred   = output['node_features'][..., NUM_TYPES:NUM_TYPES+5]  # [B, N, 5]
    spatial_target = node_target[..., NUM_TYPES:NUM_TYPES+5]
    L_spatial = F.mse_loss(
        spatial_pred * mask.unsqueeze(-1),
        spatial_target * mask.unsqueeze(-1),
        reduction='sum'
    ) / (mask.sum() * 5 + 1e-8)

    # ── Num nodes loss ────────────────────────────────────────────────────────
    num_logits  = output['num_nodes_logits']           # [B, max_nodes]
    num_targets = (num_nodes_gt - 1).clamp(0, MAX_NODES - 1).long()
    L_num = F.cross_entropy(num_logits, num_targets)

    total = W_ADJ * L_adj + W_TYPE * L_type + W_SPATIAL * L_spatial + W_NUM * L_num
    return total, {
        'adj': L_adj.item(), 'type': L_type.item(),
        'spatial': L_spatial.item(), 'num': L_num.item(),
    }


# ── Training loop ──────────────────────────────────────────────────────────────
def train():
    print("Loading data...")
    train_batches = load_batches("train")
    val_batches   = load_batches("val")
    print(f"  Train: {len(train_batches)} batches | Val: {len(val_batches)} batches")

    model = StructuralGNN(
        condition_dim    = CONDITION_DIM,
        node_feature_dim = NODE_FEATURE_DIM,
        hidden_dim  = HIDDEN_DIM,
        num_layers  = NUM_LAYERS,
        max_nodes   = MAX_NODES,
        dropout     = DROPOUT,
    ).to(DEVICE)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS, eta_min=LR * 0.01)

    # Resume from checkpoint if present
    start_epoch = 0
    best_val    = float('inf')
    if LATEST_PT.exists():
        print(f"Resuming from {LATEST_PT}")
        ckpt = torch.load(str(LATEST_PT), map_location=DEVICE, weights_only=False)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        start_epoch = ckpt.get('epoch', 0) + 1
        best_val    = ckpt.get('best_val', float('inf'))
        print(f"  Resumed at epoch {start_epoch}, best_val={best_val:.4f}")

    config = {
        'condition_dim': CONDITION_DIM, 'node_feature_dim': NODE_FEATURE_DIM,
        'hidden_dim': HIDDEN_DIM, 'num_layers': NUM_LAYERS,
        'max_nodes': MAX_NODES, 'dropout': DROPOUT,
    }

    print(f"\nTraining for {NUM_EPOCHS} epochs on {DEVICE}...")
    print(f"Loss weights: adj={W_ADJ} type={W_TYPE} spatial={W_SPATIAL} num={W_NUM}")
    print("─" * 60)

    for epoch in range(start_epoch, NUM_EPOCHS):
        # ── Train ──────────────────────────────────────────────────────────────
        model.train()
        np.random.shuffle(train_batches)
        train_loss = 0.0

        for batch in train_batches:
            batch = pad_batch_to_max(batch)
            cond  = batch['condition'].to(DEVICE)
            mask  = batch['mask'].to(DEVICE)

            optimizer.zero_grad()
            out = model(cond, mask)
            loss, _ = compute_loss(out, batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_batches)

        # ── Validate ───────────────────────────────────────────────────────────
        model.eval()
        val_loss  = 0.0
        val_comps = {'adj': 0, 'type': 0, 'spatial': 0, 'num': 0}

        with torch.no_grad():
            for batch in val_batches:
                batch = pad_batch_to_max(batch)
                cond = batch['condition'].to(DEVICE)
                mask = batch['mask'].to(DEVICE)
                out  = model(cond, mask)
                loss, comps = compute_loss(out, batch)
                val_loss += loss.item()
                for k in val_comps:
                    val_comps[k] += comps[k]

        val_loss /= len(val_batches)
        for k in val_comps:
            val_comps[k] /= len(val_batches)

        scheduler.step()

        if (epoch + 1) % 10 == 0:
            print(f"Ep {epoch+1:3d}/{NUM_EPOCHS} | "
                  f"train={train_loss:.4f} val={val_loss:.4f} | "
                  f"adj={val_comps['adj']:.3f} type={val_comps['type']:.3f} "
                  f"spatial={val_comps['spatial']:.4f} num={val_comps['num']:.3f}")

        # Save latest always
        ckpt = {
            'epoch':               epoch,
            'model_state_dict':    model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'train_loss':          train_loss,
            'val_loss':            val_loss,
            'best_val':            best_val,
            'config':              config,
        }
        torch.save(ckpt, str(LATEST_PT))

        # Save best
        if val_loss < best_val:
            best_val = val_loss
            ckpt['best_val'] = best_val
            torch.save(ckpt, str(BEST_PT))

    print(f"\n✅ Training complete! Best val loss: {best_val:.4f}")
    print(f"   Best model: {BEST_PT}")


if __name__ == '__main__':
    train()
