"""
gnn_train_cvae.py — ArchiText CVAE-GNN Training Script

Architecture: Conditional Variational Autoencoder (CVAE) + GNN
Purpose: Solves mode collapse in layout spatial prediction by learning a continuous latent space.

Run:
    .\\venv\\Scripts\\python.exe scripts\\gnn_train_cvae.py
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
BEST_PT    = CKPT_DIR / "gnn_cvae_best.pt"
LATEST_PT  = CKPT_DIR / "gnn_cvae_latest.pt"
NORM_PATH  = DATA_DIR / "norm_constants.npy"

CKPT_DIR.mkdir(parents=True, exist_ok=True)

# ── Hyperparameters ────────────────────────────────────────────────────────────
NUM_EPOCHS   = 300
LR           = 1e-3   # scaled up for batch_size=128
HIDDEN_DIM   = 256
NUM_LAYERS   = 4
DROPOUT      = 0.3    # increased to prevent overfitting
MAX_NODES    = 16
LATENT_DIM   = 64

# Loss weights
W_ADJ     = 1.0
W_TYPE    = 2.0
W_SPATIAL = 3.0
W_NUM     = 1.0
MAX_KL_W  = 0.1       # KL annealing max weight

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")

# ── Load norm constants ────────────────────────────────────────────────────────
norm = np.load(str(NORM_PATH), allow_pickle=True).item()
CONDITION_DIM    = norm['condition_dim']     # 18
NODE_FEATURE_DIM = norm['node_feature_dim']  # 16
NUM_TYPES        = 10


# ── Model Components ──────────────────────────────────────────────────────────
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
    def __init__(self, hidden_dim, num_heads=4, dropout=0.3):
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


class CVAEEncoder(nn.Module):
    def __init__(self, in_dim, hidden_dim, latent_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim * 2), nn.LayerNorm(hidden_dim * 2), nn.GELU(),
            nn.Linear(hidden_dim * 2, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()
        )
        self.to_mu = nn.Linear(hidden_dim, latent_dim)
        self.to_logvar = nn.Linear(hidden_dim, latent_dim)

    def forward(self, nodes, adj, condition, mask):
        B = nodes.shape[0]
        nodes_flat = (nodes * mask.unsqueeze(-1)).view(B, -1)
        adj_flat = (adj * (mask.unsqueeze(2) * mask.unsqueeze(1))).view(B, -1)
        x = torch.cat([nodes_flat, adj_flat, condition], dim=-1)
        h = self.net(x)
        return self.to_mu(h), self.to_logvar(h)


class CVAEGNN(nn.Module):
    def __init__(self, condition_dim, node_feature_dim,
                 hidden_dim=256, num_layers=4, max_nodes=16, dropout=0.3, latent_dim=64):
        super().__init__()
        self.max_nodes = max_nodes
        self.latent_dim = latent_dim
        
        # Encoder
        enc_in = (max_nodes * node_feature_dim) + (max_nodes * max_nodes) + condition_dim
        self.encoder = CVAEEncoder(enc_in, hidden_dim, latent_dim)
        
        # Decoder components
        self.condition_encoder = nn.Sequential(
            nn.Linear(condition_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),    nn.LayerNorm(hidden_dim), nn.GELU(),
        )
        self.z_proj = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.GELU()
        )
        self.num_nodes_predictor = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim // 2), nn.GELU(),
            nn.Linear(hidden_dim // 2, max_nodes),
        )
        self.node_embedding = nn.Parameter(torch.randn(1, max_nodes, hidden_dim) * 0.02)
        self.joint_to_nodes = nn.Linear(hidden_dim * 2, hidden_dim)
        
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

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, condition, nodes_gt=None, adj_gt=None, mask=None):
        B = condition.shape[0]
        
        if nodes_gt is not None and adj_gt is not None:
            mu, logvar = self.encoder(nodes_gt, adj_gt, condition, mask)
            z = self.reparameterize(mu, logvar)
        else:
            mu = torch.zeros(B, self.latent_dim, device=condition.device)
            logvar = torch.zeros(B, self.latent_dim, device=condition.device)
            z = torch.randn(B, self.latent_dim, device=condition.device)
            
        cond_emb = self.condition_encoder(condition)
        z_emb = self.z_proj(z)
        joint = torch.cat([cond_emb, z_emb], dim=-1)
        
        num_nodes_logits = self.num_nodes_predictor(joint)
        
        nodes = self.node_embedding.expand(B, -1, -1)
        joint_p = self.joint_to_nodes(joint).unsqueeze(1)
        nodes = nodes + joint_p
        
        for layer in self.gnn_layers:
            nodes = layer(nodes, mask)
            
        node_features = self.node_head(nodes)
        type_logits = node_features[..., :NUM_TYPES]
        other_pred = torch.sigmoid(node_features[..., NUM_TYPES:])
        node_out = torch.cat([type_logits, other_pred], dim=-1)
        
        nodes_i = nodes.unsqueeze(2).expand(-1, -1, self.max_nodes, -1)
        nodes_j = nodes.unsqueeze(1).expand(-1, self.max_nodes, -1, -1)
        adj_logits = self.edge_head(torch.cat([nodes_i, nodes_j], dim=-1)).squeeze(-1)
        adj_logits = (adj_logits + adj_logits.transpose(-1, -2)) / 2
        
        return {
            'node_features': node_out,
            'type_logits': type_logits,
            'adjacency_logits': adj_logits,
            'num_nodes_logits': num_nodes_logits,
            'mu': mu,
            'logvar': logvar
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
    curr = batch['node_features'].shape[1]
    pad = MAX_NODES - curr
    if pad <= 0: return batch
    return {
        'node_features': F.pad(batch['node_features'], (0, 0, 0, pad)),
        'adjacency':     F.pad(batch['adjacency'],     (0, pad, 0, pad)),
        'condition':     batch['condition'],
        'num_nodes':     batch['num_nodes'],
        'mask':          F.pad(batch['mask'],          (0, pad)),
    }


# ── Loss function ──────────────────────────────────────────────────────────────
def compute_loss(output, batch, epoch_ratio):
    mask          = batch['mask'].to(DEVICE)
    adj_target    = batch['adjacency'].to(DEVICE)
    node_target   = batch['node_features'].to(DEVICE)
    num_nodes_gt  = batch['num_nodes'].to(DEVICE)

    B, N = mask.shape

    # Adjacency
    adj_logits  = output['adjacency_logits']
    adj_mask    = mask.unsqueeze(2) * mask.unsqueeze(1)
    L_adj = F.binary_cross_entropy_with_logits(adj_logits, adj_target, reduction='none')
    L_adj = (L_adj * adj_mask).sum() / (adj_mask.sum() + 1e-8)

    # Type
    type_logits = output['type_logits']
    type_target = node_target[..., :NUM_TYPES].argmax(dim=-1)
    L_type = F.cross_entropy(type_logits.reshape(-1, NUM_TYPES), type_target.reshape(-1), reduction='none').view(B, N)
    L_type = (L_type * mask).sum() / (mask.sum() + 1e-8)

    # Spatial
    spatial_pred   = output['node_features'][..., NUM_TYPES:NUM_TYPES+5]
    spatial_target = node_target[..., NUM_TYPES:NUM_TYPES+5]
    L_spatial = F.mse_loss(spatial_pred * mask.unsqueeze(-1), spatial_target * mask.unsqueeze(-1), reduction='sum') / (mask.sum() * 5 + 1e-8)

    # Num nodes
    num_logits  = output['num_nodes_logits']
    num_targets = (num_nodes_gt - 1).clamp(0, MAX_NODES - 1).long()
    L_num = F.cross_entropy(num_logits, num_targets)

    # KL Divergence
    mu = output['mu']
    logvar = output['logvar']
    L_kl = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=-1).mean()
    
    # Annealing
    kl_weight = MAX_KL_W * min(1.0, epoch_ratio / 0.3)

    total = W_ADJ * L_adj + W_TYPE * L_type + W_SPATIAL * L_spatial + W_NUM * L_num + kl_weight * L_kl
    return total, {
        'adj': L_adj.item(), 'type': L_type.item(),
        'spatial': L_spatial.item(), 'num': L_num.item(), 'kl': L_kl.item()
    }


# ── Training loop ──────────────────────────────────────────────────────────────
def train():
    print("Loading data...")
    train_batches = load_batches("train")
    val_batches   = load_batches("val")
    print(f"  Train: {len(train_batches)} batches | Val: {len(val_batches)} batches")

    model = CVAEGNN(
        condition_dim    = CONDITION_DIM,
        node_feature_dim = NODE_FEATURE_DIM,
        hidden_dim  = HIDDEN_DIM,
        num_layers  = NUM_LAYERS,
        max_nodes   = MAX_NODES,
        dropout     = DROPOUT,
        latent_dim  = LATENT_DIM,
    ).to(DEVICE)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS, eta_min=LR * 0.01)

    start_epoch = 0
    best_val    = float('inf')

    config = {
        'condition_dim': CONDITION_DIM, 'node_feature_dim': NODE_FEATURE_DIM,
        'hidden_dim': HIDDEN_DIM, 'num_layers': NUM_LAYERS,
        'max_nodes': MAX_NODES, 'dropout': DROPOUT, 'latent_dim': LATENT_DIM,
        'batch_size': 128
    }

    print(f"\nTraining CVAE for {NUM_EPOCHS} epochs on {DEVICE}...")
    print(f"Loss weights: adj={W_ADJ} type={W_TYPE} spatial={W_SPATIAL} num={W_NUM} kl(max)={MAX_KL_W}")
    print("─" * 70)

    for epoch in range(start_epoch, NUM_EPOCHS):
        model.train()
        np.random.shuffle(train_batches)
        train_loss = 0.0
        epoch_ratio = epoch / max(1, NUM_EPOCHS - 1)

        for batch in train_batches:
            batch = pad_batch_to_max(batch)
            cond  = batch['condition'].to(DEVICE)
            nodes_gt = batch['node_features'].to(DEVICE)
            adj_gt = batch['adjacency'].to(DEVICE)
            mask  = batch['mask'].to(DEVICE)

            optimizer.zero_grad()
            out = model(cond, nodes_gt=nodes_gt, adj_gt=adj_gt, mask=mask)
            loss, _ = compute_loss(out, batch, epoch_ratio)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_batches)

        model.eval()
        val_loss  = 0.0
        val_comps = {'adj': 0, 'type': 0, 'spatial': 0, 'num': 0, 'kl': 0}

        with torch.no_grad():
            for batch in val_batches:
                batch = pad_batch_to_max(batch)
                cond  = batch['condition'].to(DEVICE)
                nodes_gt = batch['node_features'].to(DEVICE)
                adj_gt = batch['adjacency'].to(DEVICE)
                mask  = batch['mask'].to(DEVICE)
                
                out = model(cond, nodes_gt=nodes_gt, adj_gt=adj_gt, mask=mask)
                loss, comps = compute_loss(out, batch, epoch_ratio)
                val_loss += loss.item()
                for k in val_comps:
                    val_comps[k] += comps[k]

        val_loss /= len(val_batches)
        for k in val_comps:
            val_comps[k] /= len(val_batches)

        scheduler.step()

        ckpt = {
            'epoch':               epoch,
            'model_state_dict':    model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'train_loss':          train_loss,
            'val_loss':            val_loss,
            'best_val':            best_val,
            'config':              config,
        }

        if (epoch + 1) % 10 == 0:
            print(f"Ep {epoch+1:3d}/{NUM_EPOCHS} | "
                  f"train={train_loss:.4f} val={val_loss:.4f} | "
                  f"adj={val_comps['adj']:.3f} type={val_comps['type']:.3f} "
                  f"sp={val_comps['spatial']:.4f} num={val_comps['num']:.3f} kl={val_comps['kl']:.4f}")
            
            epoch_pt = CKPT_DIR / f"gnn_cvae_epoch_{epoch+1:03d}.pt"
            torch.save(ckpt, str(epoch_pt))

        # Save latest always
        torch.save(ckpt, str(LATEST_PT))

        if val_loss < best_val:
            best_val = val_loss
            ckpt['best_val'] = best_val
            torch.save(ckpt, str(BEST_PT))

    print(f"\n✅ Training complete! Best val loss: {best_val:.4f}")
    print(f"   Best model: {BEST_PT}")


if __name__ == '__main__':
    train()
