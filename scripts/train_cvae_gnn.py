"""
train_cvae_gnn.py — ArchiText CVAE-GNN Floorplan Generator

Graph-aware Conditional VAE for generating residential floor plans.
Trained on ResPlan 17k (x4) (processed_v3).

Architecture:
    Encoder:  3 GNN layers with edge-type embeddings on GT graph → μ, logσ²
    Decoder:  condition + z → 4 GNN self-attention layers → 4 output heads
              (room types, adjacency, spatial bbox, num_nodes)

Usage:
    .\\venv\\Scripts\\python.exe scripts\\train_cvae_gnn.py                 # full training
    .\\venv\\Scripts\\python.exe scripts\\train_cvae_gnn.py --smoke-test    # shape verification
    .\\venv\\Scripts\\python.exe scripts\\train_cvae_gnn.py --epochs 50     # short run
    .\\venv\\Scripts\\python.exe scripts\\train_cvae_gnn.py --generate 5    # generate samples
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim.lr_scheduler import CosineAnnealingLR

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.parent.resolve()
DATA_DIR = ROOT / "data" / "processed_v3"
CKPT_DIR = ROOT / "models" / "cvae_gnn"
CKPT_DIR.mkdir(parents=True, exist_ok=True)

BEST_PT        = CKPT_DIR / "best.pt"         # backward-compatible alias (best generation checkpoint)
BEST_GEN_PT    = CKPT_DIR / "best_gen.pt"     # best condition-only generation checkpoint
BEST_RECON_PT  = CKPT_DIR / "best_recon.pt"   # best reconstruction-style checkpoint (no KL term)
LATEST_PT      = CKPT_DIR / "latest.pt"
LOG_CSV        = CKPT_DIR / "training_log.csv"

# ── Load norm constants ────────────────────────────────────────────────────────
_norm = np.load(str(DATA_DIR / "norm_constants.npy"), allow_pickle=True).item()
NODE_FEAT_DIM = _norm['node_feature_dim']   # 16
CONDITION_DIM = _norm['condition_dim']       # 11
NUM_TYPES     = _norm['num_room_types']      # 10
MAX_NODES     = _norm['max_nodes']           # 16
NUM_EDGE_TYPES = _norm['num_edge_types']     # 5 (0=none, 1-4=types)
ROOM_TYPES    = _norm['room_types']

# Spatial feature indices within node features
SPATIAL_START = NUM_TYPES       # index 10
NUM_SPATIAL   = 4               # x_min, y_min, x_max, y_max
AREA_IDX      = SPATIAL_START + 4  # index 14
IS_EXT_IDX    = SPATIAL_START + 5  # index 15

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ══════════════════════════════════════════════════════════════════════════════
# MODEL COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

class MultiHeadAttention(nn.Module):
    """Multi-head self-attention with optional adjacency bias."""

    def __init__(self, dim, num_heads=4, dropout=0.1):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = dim // num_heads
        self.scale = self.head_dim ** -0.5

        self.qkv = nn.Linear(dim, dim * 3)
        self.out = nn.Linear(dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None, adj_bias=None):
        """
        x:        [B, N, dim]
        mask:     [B, N]         — node validity mask
        adj_bias: [B, N, N]      — per-pair attention bias (from edge types or binary adj)
        """
        B, N, _ = x.shape
        qkv = self.qkv(x).reshape(B, N, 3, self.num_heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # [3, B, heads, N, head_dim]
        q, k, v = qkv[0], qkv[1], qkv[2]

        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale  # [B, heads, N, N]

        # Adjacency/edge-type bias
        if adj_bias is not None:
            scores = scores + adj_bias.unsqueeze(1)  # [B, 1, N, N] broadcast to heads

        # Node validity mask
        if mask is not None:
            mask_2d = mask.unsqueeze(1).unsqueeze(2) * mask.unsqueeze(1).unsqueeze(3)
            scores = scores.masked_fill(mask_2d == 0, -1e4)

        attn = self.dropout(F.softmax(scores, dim=-1))
        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().reshape(B, N, -1)
        return self.out(out)


class GNNBlock(nn.Module):
    """Pre-norm Transformer block with optional adjacency-biased attention."""

    def __init__(self, dim, num_heads=4, dropout=0.1, ff_mult=4):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = MultiHeadAttention(dim, num_heads, dropout)
        self.norm2 = nn.LayerNorm(dim)
        self.ff = nn.Sequential(
            nn.Linear(dim, dim * ff_mult),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * ff_mult, dim),
            nn.Dropout(dropout),
        )

    def forward(self, x, mask=None, adj_bias=None):
        x = x + self.attn(self.norm1(x), mask, adj_bias)
        x = x + self.ff(self.norm2(x))
        return x


# ══════════════════════════════════════════════════════════════════════════════
# ENCODER — with edge-type embeddings
# ══════════════════════════════════════════════════════════════════════════════

class GraphEncoder(nn.Module):
    """
    Graph-aware CVAE encoder with learned edge-type attention biases.

    Edge types (direct, adjacency, via_door, via_window) are embedded as
    learned scalar biases for attention, so the encoder knows that
    "rooms connected via a door" is different from "rooms just sharing a wall".
    """

    def __init__(self, node_feat_dim, cond_dim, hidden_dim, latent_dim,
                 num_edge_types=5, num_layers=3, num_heads=4, dropout=0.1):
        super().__init__()

        # Edge type embedding: maps edge type ID → attention bias scalar
        # 0=no edge, 1=direct, 2=adjacency, 3=via_door, 4=via_window
        self.edge_type_bias = nn.Embedding(num_edge_types, 1)
        # Initialize: no-edge gets 0 bias, connected types get positive bias
        with torch.no_grad():
            self.edge_type_bias.weight.data = torch.tensor(
                [[0.0], [2.0], [1.5], [2.5], [1.0]]  # direct, adj, door, window
            )

        # Project node features + condition to hidden dim
        self.node_proj = nn.Linear(node_feat_dim, hidden_dim)
        self.cond_proj = nn.Sequential(
            nn.Linear(cond_dim, hidden_dim),
            nn.GELU(),
        )

        # GNN layers operating on GT graph
        self.layers = nn.ModuleList([
            GNNBlock(hidden_dim, num_heads, dropout)
            for _ in range(num_layers)
        ])

        # Latent projections
        self.to_mu     = nn.Linear(hidden_dim, latent_dim)
        self.to_logvar = nn.Linear(hidden_dim, latent_dim)

    def forward(self, node_features, edge_types, condition, mask):
        """
        node_features: [B, N, node_feat_dim]
        edge_types:    [B, N, N]  — edge type IDs (0-4)
        condition:     [B, cond_dim]
        mask:          [B, N]
        Returns: mu [B, latent_dim], logvar [B, latent_dim]
        """
        # Edge type → attention bias
        adj_bias = self.edge_type_bias(edge_types).squeeze(-1)  # [B, N, N]

        # Project node features
        h = self.node_proj(node_features)  # [B, N, H]

        # Inject condition
        cond_emb = self.cond_proj(condition).unsqueeze(1)  # [B, 1, H]
        h = h + cond_emb

        # GNN message passing with edge-type biased attention
        for layer in self.layers:
            h = layer(h, mask=mask, adj_bias=adj_bias)

        # Mean-pool over valid nodes
        mask_expanded = mask.unsqueeze(-1)
        h_pooled = (h * mask_expanded).sum(dim=1) / (mask_expanded.sum(dim=1) + 1e-8)

        return self.to_mu(h_pooled), self.to_logvar(h_pooled)


# ══════════════════════════════════════════════════════════════════════════════
# DECODER
# ══════════════════════════════════════════════════════════════════════════════

class FloorplanDecoder(nn.Module):
    """
    CVAE decoder: condition + z → room graph.

    Round 3 improvements:
        - Condition + z re-injected at EVERY GNN layer (not just first)
        - Teacher forcing: 50% of training, GT types guide spatial head
    """

    def __init__(self, cond_dim, latent_dim, hidden_dim, num_types,
                 max_nodes, num_layers=4, num_heads=4, dropout=0.1):
        super().__init__()
        self.max_nodes = max_nodes
        self.hidden_dim = hidden_dim
        self.num_types = num_types

        # Condition + z -> combined embedding
        self.cond_encoder = nn.Sequential(
            nn.Linear(cond_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )
        self.z_proj = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.GELU(),
        )

        # Num nodes predictor
        self.num_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, max_nodes),
        )

        # Learnable node position embeddings
        self.node_embed = nn.Parameter(torch.randn(1, max_nodes, hidden_dim) * 0.02)
        self.joint_to_nodes = nn.Linear(hidden_dim * 2, hidden_dim)

        # Per-layer condition re-injection: project joint → per-node bias
        self.layer_cond_proj = nn.ModuleList([
            nn.Linear(hidden_dim * 2, hidden_dim)
            for _ in range(num_layers)
        ])

        # GNN self-attention layers
        self.layers = nn.ModuleList([
            GNNBlock(hidden_dim, num_heads, dropout)
            for _ in range(num_layers)
        ])

        # Output heads
        self.type_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, num_types),
        )
        self.edge_head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )
        # Split spatial head into position and size, driven by different inputs:
        #   position_head(nodes)              → x_min, y_min
        #     slot/z variation OK — layout diversity comes from here
        #   size_head(type_emb, joint_proj)   → width, height
        #     type_emb: primary driver — bedroom vs bathroom vs living (no slot position)
        #     joint_proj: condition+z context — larger houses (more rooms in condition)
        #                 produce proportionally larger rooms of each type
        #     This directly handles 10-marla vs 2-kanal variation without any extra input.
        #   area_head(nodes)                  → area scalar
        #
        # Breaks slot-size bias without shuffle: node_embed[0] may memorise
        # "slot 0 = living room" for the type head but cannot make it output a huge room,
        # since size comes from type + house-scale context, not slot index.
        self.type_embed_for_spatial = nn.Embedding(num_types, hidden_dim // 2)
        # Project joint (cond+z) down to same dim as type_emb for concatenation
        self.joint_to_size = nn.Linear(hidden_dim * 2, hidden_dim // 2)
        self.position_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, 2),   # x_min, y_min
        )
        self.size_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 4),   # input: cat(type_emb H//2, joint_proj H//2)
            nn.GELU(),
            nn.Linear(hidden_dim // 4, 2),   # raw_w, raw_h  (softplus + floor applied later)
        )
        self.area_head = nn.Linear(hidden_dim, 1)

    def forward(self, condition, z, mask=None, gt_types=None, teacher_forcing_ratio=0.0):
        """
        Args:
            gt_types: [B, N] long tensor of GT type indices (for teacher forcing)
            teacher_forcing_ratio: probability of using GT types for spatial head
        """
        B = condition.shape[0]

        cond_emb = self.cond_encoder(condition)  # [B, H]
        z_emb = self.z_proj(z)                    # [B, H]
        joint = torch.cat([cond_emb, z_emb], dim=-1)  # [B, 2H]

        num_logits = self.num_head(joint)  # [B, max_nodes]

        nodes = self.node_embed.expand(B, -1, -1)  # [B, N, H]
        joint_proj = self.joint_to_nodes(joint).unsqueeze(1)
        nodes = nodes + joint_proj

        # Condition re-injection at every layer
        for i, layer in enumerate(self.layers):
            cond_bias = self.layer_cond_proj[i](joint).unsqueeze(1)  # [B, 1, H]
            nodes = nodes + cond_bias * 0.3  # scaled injection — stronger than 0.1
            nodes = layer(nodes, mask=mask)

        # Type prediction
        type_logits = self.type_head(nodes)  # [B, N, num_types]

        # Teacher forcing: decide which type signal goes to spatial head
        if gt_types is not None and self.training and torch.rand(1).item() < teacher_forcing_ratio:
            type_indices = gt_types  # use ground truth
        else:
            type_indices = type_logits.argmax(dim=-1)  # use predictions

        type_emb = self.type_embed_for_spatial(type_indices)  # [B, N, H//2]

        # Adjacency (pairwise)
        nodes_i = nodes.unsqueeze(2).expand(-1, -1, self.max_nodes, -1)
        nodes_j = nodes.unsqueeze(1).expand(-1, self.max_nodes, -1, -1)
        adj_logits = self.edge_head(
            torch.cat([nodes_i, nodes_j], dim=-1)
        ).squeeze(-1)
        adj_logits = (adj_logits + adj_logits.transpose(-1, -2)) / 2

        # Spatial — split head:
        #   position (x_min, y_min): from node hidden → slot/z-driven layout diversity
        #   size (width, height):    from type_emb + joint_proj
        #     type_emb drives per-type typical size (bedroom vs bathroom)
        #     joint_proj (cond+z) drives house-scale variation (10-marla vs 2-kanal):
        #     condition encodes total room count → more rooms = smaller rooms per type
        #   area: from node hidden
        # Hard minimum = 0.10 normalized = ~1.28m on 12.8m canvas
        # (was 0.05/~0.64m — too low; bathroom/kitchen converged to corridor-width)
        joint_size = self.joint_to_size(joint).unsqueeze(1).expand(-1, self.max_nodes, -1)  # [B, N, H//2]
        size_input = torch.cat([type_emb, joint_size], dim=-1)  # [B, N, H]
        pos_raw  = self.position_head(nodes)        # [B, N, 2]
        size_raw = self.size_head(size_input)       # [B, N, 2]
        x_min  = pos_raw[..., 0]
        y_min  = pos_raw[..., 1]
        width  = F.softplus(size_raw[..., 0]) + 0.10
        height = F.softplus(size_raw[..., 1]) + 0.10
        x_max  = x_min + width
        y_max  = y_min + height
        area   = torch.sigmoid(self.area_head(nodes).squeeze(-1))
        spatial_pred = torch.stack([x_min, y_min, x_max, y_max, area], dim=-1)

        return {
            'type_logits': type_logits,
            'adj_logits':  adj_logits,
            'spatial':     spatial_pred,
            'num_logits':  num_logits,
            'node_hidden': nodes,
        }


# ══════════════════════════════════════════════════════════════════════════════
# FULL CVAE MODEL
# ══════════════════════════════════════════════════════════════════════════════

class FloorplanCVAE(nn.Module):
    def __init__(self, hidden_dim=256, latent_dim=64, num_heads=4,
                 enc_layers=3, dec_layers=4, dropout=0.1):
        super().__init__()
        self.latent_dim = latent_dim

        self.encoder = GraphEncoder(
            node_feat_dim=NODE_FEAT_DIM,
            cond_dim=CONDITION_DIM,
            hidden_dim=hidden_dim,
            latent_dim=latent_dim,
            num_edge_types=NUM_EDGE_TYPES,
            num_layers=enc_layers,
            num_heads=num_heads,
            dropout=dropout,
        )
        self.decoder = FloorplanDecoder(
            cond_dim=CONDITION_DIM,
            latent_dim=latent_dim,
            hidden_dim=hidden_dim,
            num_types=NUM_TYPES,
            max_nodes=MAX_NODES,
            num_layers=dec_layers,
            num_heads=num_heads,
            dropout=dropout,
        )

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        return mu + torch.randn_like(std) * std

    def forward(self, batch, use_gt_encoder=True, teacher_forcing_ratio=0.0):
        condition = batch['condition'].to(DEVICE)
        mask = batch['mask'].to(DEVICE)
        B = condition.shape[0]

        # Prepare GT types for teacher forcing
        gt_types = None
        if teacher_forcing_ratio > 0 and 'node_features' in batch:
            nf = batch['node_features'].to(DEVICE)
            gt_types = nf[..., :NUM_TYPES].argmax(dim=-1)  # [B, N]

        if use_gt_encoder:
            node_features = batch['node_features'].to(DEVICE)
            edge_types = batch['edge_types'].to(DEVICE)
            mu, logvar = self.encoder(node_features, edge_types, condition, mask)
            z = self.reparameterize(mu, logvar)
        else:
            mu = torch.zeros(B, self.latent_dim, device=DEVICE)
            logvar = torch.zeros(B, self.latent_dim, device=DEVICE)
            z = torch.randn(B, self.latent_dim, device=DEVICE)

        output = self.decoder(condition, z, mask, gt_types=gt_types,
                              teacher_forcing_ratio=teacher_forcing_ratio)
        output['mu'] = mu
        output['logvar'] = logvar
        return output

    @staticmethod
    def _mask_from_num_logits(num_logits):
        """Build a [B, max_nodes] node-validity mask from num-node logits."""
        num_pred = (num_logits.argmax(dim=-1) + 1).clamp(1, MAX_NODES)
        node_idx = torch.arange(MAX_NODES, device=num_logits.device).unsqueeze(0)
        pred_mask = (node_idx < num_pred.unsqueeze(1)).float()
        return pred_mask

    @torch.no_grad()
    def generate(self, condition, mask=None, z=None, two_pass=True):
        """
        Condition-only generation.

        By default we run a two-pass decode:
          1) predict num_nodes with full mask
          2) re-decode with predicted mask for type/adj/spatial heads
        This matches training-time masking behavior much better than all-ones masking.
        """
        self.eval()
        B = condition.shape[0]
        if z is None:
            z = torch.randn(B, self.latent_dim, device=condition.device)

        if mask is not None:
            output = self.decoder(condition, z, mask)
            output['pred_mask'] = mask
            return output

        full_mask = torch.ones(B, MAX_NODES, device=condition.device)
        first_pass = self.decoder(condition, z, full_mask)

        if not two_pass:
            first_pass['pred_mask'] = full_mask
            return first_pass

        pred_mask = self._mask_from_num_logits(first_pass['num_logits'])
        second_pass = self.decoder(condition, z, pred_mask)
        second_pass['num_logits'] = first_pass['num_logits']
        second_pass['pred_mask'] = pred_mask
        return second_pass


# ══════════════════════════════════════════════════════════════════════════════
# LOSS FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def compute_overlap_penalty(spatial_pred, mask):
    """Differentiable pairwise bbox overlap penalty."""
    x_min, y_min = spatial_pred[..., 0], spatial_pred[..., 1]
    x_max, y_max = spatial_pred[..., 2], spatial_pred[..., 3]

    inter_x = torch.clamp(
        torch.min(x_max.unsqueeze(2), x_max.unsqueeze(1)) -
        torch.max(x_min.unsqueeze(2), x_min.unsqueeze(1)), min=0)
    inter_y = torch.clamp(
        torch.min(y_max.unsqueeze(2), y_max.unsqueeze(1)) -
        torch.max(y_min.unsqueeze(2), y_min.unsqueeze(1)), min=0)
    inter_area = inter_x * inter_y

    pair_mask = mask.unsqueeze(2) * mask.unsqueeze(1)
    pair_mask = pair_mask * (1.0 - torch.eye(MAX_NODES, device=mask.device).unsqueeze(0))
    return (inter_area * pair_mask).sum() / (pair_mask.sum() + 1e-8)


def build_pair_mask(mask, upper_only=True):
    """
    Build valid node-pair mask.
    upper_only=True keeps only i<j pairs (no diagonal and no duplicate i-j/j-i terms).
    """
    B, N = mask.shape
    pair_mask = mask.unsqueeze(2) * mask.unsqueeze(1)
    eye = torch.eye(N, device=mask.device).unsqueeze(0)
    pair_mask = pair_mask * (1.0 - eye)
    if upper_only:
        upper = torch.triu(torch.ones(N, N, device=mask.device), diagonal=1).unsqueeze(0)
        pair_mask = pair_mask * upper
    return pair_mask


def compute_recon_only_loss(components, config):
    """Weighted objective without KL; comparable across epochs despite KL warmup."""
    return (
        config['w_type'] * components['type']
        + config['w_adj'] * components['adj']
        + config['w_sp'] * components['spatial']
        + config['w_num'] * components['num']
        + config['w_ovlp'] * components['overlap']
        + config['w_cond'] * components['cond']
        + config.get('w_bound', 0.0) * components.get('bound', 0.0)
        + config.get('w_min_size', 2.0) * components.get('min_size', 0.0)
        + config.get('w_spread', 1.0) * components.get('spread', 0.0)
    )


def compute_loss(output, batch, epoch_ratio, config, is_train=True):
    """Loss with condition consistency on both GT-mask and predicted-mask paths."""
    mask       = batch['mask'].to(DEVICE)
    nf_target  = batch['node_features'].to(DEVICE)
    adj_target = batch['adjacency'].to(DEVICE)
    num_target = batch['num_nodes'].to(DEVICE)
    condition  = batch['condition'].to(DEVICE)
    B, N = mask.shape

    # 1. Type CE
    type_logits = output['type_logits']
    type_target = nf_target[..., :NUM_TYPES].argmax(dim=-1)
    L_type = F.cross_entropy(
        type_logits.reshape(-1, NUM_TYPES), type_target.reshape(-1), reduction='none'
    ).view(B, N)
    L_type = (L_type * mask).sum() / (mask.sum() + 1e-8)

    # 2. Adjacency BCE (upper-triangle pairs only) with positive-edge reweighting
    adj_logits = output['adj_logits']
    adj_mask = build_pair_mask(mask, upper_only=True)
    pos_weight = torch.tensor(
        float(config.get('adj_pos_weight', 1.0)),
        device=DEVICE,
        dtype=adj_logits.dtype,
    )
    L_adj = F.binary_cross_entropy_with_logits(
        adj_logits, adj_target, reduction='none', pos_weight=pos_weight
    )
    L_adj = (L_adj * adj_mask).sum() / (adj_mask.sum() + 1e-8)

    # 3. Spatial SmoothL1 (bbox corners + area)
    spatial_pred = output['spatial']
    spatial_target = torch.cat([
        nf_target[..., SPATIAL_START:SPATIAL_START + 4],
        nf_target[..., AREA_IDX:AREA_IDX + 1],
    ], dim=-1)
    spatial_mask = mask.unsqueeze(-1).expand_as(spatial_pred)
    L_spatial = F.smooth_l1_loss(
        spatial_pred * spatial_mask, spatial_target * spatial_mask, reduction='sum'
    ) / (mask.sum() * 5 + 1e-8)

    # Keep predicted boxes inside normalized canvas [0,1]
    x_min, y_min = spatial_pred[..., 0], spatial_pred[..., 1]
    x_max, y_max = spatial_pred[..., 2], spatial_pred[..., 3]
    bound_violation = (
        F.relu(-x_min) + F.relu(-y_min) + F.relu(x_max - 1.0) + F.relu(y_max - 1.0)
    )
    L_bound = (bound_violation * mask).sum() / (mask.sum() + 1e-8)

    # 4. Num nodes CE
    num_logits = output['num_logits']
    num_targets = (num_target - 1).clamp(0, MAX_NODES - 1).long()
    L_num = F.cross_entropy(num_logits, num_targets)

    # 5. KL divergence — very slow ramp, tiny weight ceiling.
    # free_bits=0.0 so no clamping (clamping at 0.5 silenced all 64 dims: 0.5×64=32, exact floor hit).
    # w_kl=0.01 is the ceiling — KL contribution stays ~0.1-1.0, never dominates type/spatial losses.
    # Ramp starts at 20% of training (encoder must learn types first) and reaches ceiling at 80%.
    # This prevents both the Run 5 problem (ramp too fast, KL=350 crushed encoder at ep16)
    # and the Run 6 problem (free_bits floor silenced encoder entirely for 293 epochs).
    mu, logvar = output['mu'], output['logvar']
    kl_per_dim = -0.5 * (1 + logvar - mu.pow(2) - logvar.exp())
    kl_per_dim = torch.clamp(kl_per_dim, min=config['free_bits'])
    L_kl = kl_per_dim.sum(dim=-1).mean()
    if epoch_ratio < 0.20:
        kl_weight = 0.0
    else:
        kl_weight = config['w_kl'] * min(1.0, (epoch_ratio - 0.20) / 0.60)

    # 6. Overlap
    L_overlap = compute_overlap_penalty(output['spatial'], mask)

    # 6b. Spatial spread — penalise all rooms clustering near the canvas centre.
    # Without this, a collapsed decoder outputs every room near (0.5, 0.5).
    # We measure variance of room centres over valid nodes; penalise low variance.
    _cx = ((output['spatial'][..., 0] + output['spatial'][..., 2]) / 2) * mask  # [B,N]
    _cy = ((output['spatial'][..., 1] + output['spatial'][..., 3]) / 2) * mask
    _n  = mask.sum(dim=1, keepdim=True).clamp(min=1)
    _mean_cx = _cx.sum(dim=1, keepdim=True) / _n
    _mean_cy = _cy.sum(dim=1, keepdim=True) / _n
    _var_cx = ((_cx - _mean_cx) ** 2 * mask).sum(dim=1) / _n.squeeze(-1)
    _var_cy = ((_cy - _mean_cy) ** 2 * mask).sum(dim=1) / _n.squeeze(-1)
    # Target variance >= 0.03 (centres spread at least ~0.17 units on avg)
    L_spread = (F.relu(0.03 - _var_cx) + F.relu(0.03 - _var_cy)).mean()

    # 6c. Minimum room size penalty — discourage degenerate tiny rooms
    # min_dim = 0.15 normalized (~1.92m); provides gradient pressure above the hard floor.
    # Hard floor in decoder is 0.10 (~1.28m); penalty at 0.15 fires on borderline rooms
    # (1.28-1.92m) and pushes them toward a more habitable minimum.
    # Previous value 0.05 sat at or below the floor so the penalty never fired (L=0.000 every epoch).
    x_min_s, y_min_s = output['spatial'][..., 0], output['spatial'][..., 1]
    x_max_s, y_max_s = output['spatial'][..., 2], output['spatial'][..., 3]
    width_s  = (x_max_s - x_min_s)
    height_s = (y_max_s - y_min_s)
    min_dim = 0.15
    size_penalty = (
        F.relu(min_dim - width_s) + F.relu(min_dim - height_s)
    )
    L_min_size = (size_penalty * mask).sum() / (mask.sum() + 1e-8)

    # 7. Condition consistency on GT mask + predicted-node mask paths
    tau = max(0.5, 2.0 - epoch_ratio * 3.0)  # anneal temperature: 2.0 -> 0.5
    if is_train:
        hard_probs = F.gumbel_softmax(type_logits, tau=tau, hard=True, dim=-1)  # [B, N, T]
    else:
        type_idx = type_logits.argmax(dim=-1)
        hard_probs = F.one_hot(type_idx, num_classes=NUM_TYPES).float()

    target_counts_norm = condition[:, :NUM_TYPES]

    pred_counts_gt = (hard_probs * mask.unsqueeze(-1)).sum(dim=1)
    L_cond_gt = F.mse_loss(pred_counts_gt / 5.0, target_counts_norm)

    num_probs = F.softmax(num_logits, dim=-1)  # classes correspond to [1..MAX_NODES]
    pred_valid_soft = torch.flip(
        torch.cumsum(torch.flip(num_probs, dims=[1]), dim=1),
        dims=[1],
    )  # p(node j exists) = p(num_nodes >= j+1)
    pred_counts_pred = (hard_probs * pred_valid_soft.unsqueeze(-1)).sum(dim=1)
    L_cond_pred = F.mse_loss(pred_counts_pred / 5.0, target_counts_norm)

    cond_pred_mix = float(config.get('cond_pred_mix', 0.5))
    L_cond = (1.0 - cond_pred_mix) * L_cond_gt + cond_pred_mix * L_cond_pred

    total = (config['w_type'] * L_type
           + config['w_adj']  * L_adj
           + config['w_sp']   * L_spatial
           + config['w_num']  * L_num
           + kl_weight        * L_kl
           + config['w_ovlp'] * L_overlap
           + config['w_cond'] * L_cond
           + config.get('w_bound', 0.0) * L_bound
           + config.get('w_min_size', 2.0) * L_min_size
           + config.get('w_spread', 1.0) * L_spread)

    return total, {
        'type': L_type.item(),
        'adj': L_adj.item(),
        'spatial': L_spatial.item(),
        'num': L_num.item(),
        'kl': L_kl.item(),
        'overlap': L_overlap.item(),
        'cond': L_cond.item(),
        'bound': L_bound.item(),
        'cond_gt': L_cond_gt.item(),
        'cond_pred': L_cond_pred.item(),
        'min_size': L_min_size.item(),
        'spread': L_spread.item(),
    }


@torch.no_grad()
def compute_metrics(output, batch):
    """
    Compute interpretable validation metrics beyond raw loss.

    Returns dict with:
        type_acc:   room type classification accuracy (valid nodes only)
        adj_f1:     adjacency prediction F1 score (valid node pairs only)
        adj_prec:   adjacency precision
        adj_recall: adjacency recall
        num_acc:    num_nodes prediction accuracy
        spatial_mae: mean absolute error on bbox corners (valid nodes only)
    """
    mask       = batch['mask'].to(DEVICE)
    nf_target  = batch['node_features'].to(DEVICE)
    adj_target = batch['adjacency'].to(DEVICE)
    num_target = batch['num_nodes'].to(DEVICE)
    B, N = mask.shape

    # Type accuracy
    type_pred = output['type_logits'].argmax(dim=-1)  # [B, N]
    type_gt   = nf_target[..., :NUM_TYPES].argmax(dim=-1)
    type_correct = ((type_pred == type_gt).float() * mask).sum()
    type_acc = (type_correct / (mask.sum() + 1e-8)).item()

    # Adjacency F1
    adj_pred = (torch.sigmoid(output['adj_logits']) > 0.5).float()
    adj_mask = build_pair_mask(mask, upper_only=True)

    tp = (adj_pred * adj_target * adj_mask).sum()
    fp = (adj_pred * (1 - adj_target) * adj_mask).sum()
    fn = ((1 - adj_pred) * adj_target * adj_mask).sum()

    precision = (tp / (tp + fp + 1e-8)).item()
    recall    = (tp / (tp + fn + 1e-8)).item()
    f1 = (2 * precision * recall / (precision + recall + 1e-8)) if (precision + recall) > 0 else 0.0

    # Num nodes accuracy
    num_pred = output['num_logits'].argmax(dim=-1) + 1
    num_acc = ((num_pred == num_target).float().mean()).item()

    # Spatial MAE (on bbox corners only, not area)
    spatial_pred = output['spatial'][..., :4]
    spatial_gt   = nf_target[..., SPATIAL_START:SPATIAL_START + 4]
    diff = (spatial_pred - spatial_gt).abs()
    spatial_mae = (diff * mask.unsqueeze(-1)).sum() / (mask.sum() * 4 + 1e-8)

    return {
        'type_acc':    type_acc,
        'adj_f1':      f1,
        'adj_prec':    precision,
        'adj_recall':  recall,
        'num_acc':     num_acc,
        'spatial_mae': spatial_mae.item(),
    }


@torch.no_grad()
def compute_generation_metrics(output, batch):
    """
    Evaluate condition-only generation behavior (decoder path used at inference).
    """
    gt_mask = batch['mask'].to(DEVICE)
    nf_target = batch['node_features'].to(DEVICE)
    adj_target = batch['adjacency'].to(DEVICE)

    pred_mask = output.get('pred_mask')
    if pred_mask is None:
        pred_mask = FloorplanCVAE._mask_from_num_logits(output['num_logits'])

    type_pred = output['type_logits'].argmax(dim=-1)
    type_gt = nf_target[..., :NUM_TYPES].argmax(dim=-1)

    n_pred = pred_mask.sum(dim=1).long()
    n_gt = gt_mask.sum(dim=1).long()
    B = n_gt.shape[0]

    num_acc = (n_pred == n_gt).float().mean().item()
    num_mae = (n_pred.float() - n_gt.float()).abs().mean().item()

    total_l1 = 0.0
    exact_count = 0

    tp = 0.0
    fp = 0.0
    fn = 0.0

    spatial_abs = 0.0
    spatial_count = 0

    for i in range(B):
        ng = int(n_gt[i].item())
        npred = int(n_pred[i].item())

        gt_counts = torch.bincount(type_gt[i, :ng], minlength=NUM_TYPES)
        pred_counts = torch.bincount(type_pred[i, :npred], minlength=NUM_TYPES)
        l1 = (gt_counts - pred_counts).abs().sum().item()
        total_l1 += l1
        if l1 == 0:
            exact_count += 1

        n_eval = min(ng, npred)
        if n_eval >= 2:
            adj_p = (torch.sigmoid(output['adj_logits'][i, :n_eval, :n_eval]) > 0.5).float()
            adj_t = adj_target[i, :n_eval, :n_eval]
            upper = torch.triu(torch.ones(n_eval, n_eval, device=DEVICE), diagonal=1)
            tp += (adj_p * adj_t * upper).sum().item()
            fp += (adj_p * (1 - adj_t) * upper).sum().item()
            fn += ((1 - adj_p) * adj_t * upper).sum().item()

        if n_eval > 0:
            sp_pred = output['spatial'][i, :n_eval, :4]
            sp_gt = nf_target[i, :n_eval, SPATIAL_START:SPATIAL_START + 4]
            spatial_abs += (sp_pred - sp_gt).abs().sum().item()
            spatial_count += n_eval * 4

    precision = tp / (tp + fp + 1e-8)
    recall = tp / (tp + fn + 1e-8)
    f1 = 2 * precision * recall / (precision + recall + 1e-8) if (precision + recall) > 0 else 0.0

    overlap = compute_overlap_penalty(output['spatial'], pred_mask).item()
    spatial_mae = spatial_abs / (spatial_count + 1e-8)

    return {
        'num_acc': num_acc,
        'num_mae': num_mae,
        'type_count_l1': total_l1 / max(B, 1),
        'type_count_exact': exact_count / max(B, 1),
        'adj_f1': f1,
        'adj_prec': precision,
        'adj_recall': recall,
        'spatial_mae': spatial_mae,
        'overlap': overlap,
    }


def compute_generation_score(gen_metrics):
    """Lower is better. Balances count correctness, structure, and geometry."""
    return (
        2.0 * (1.0 - gen_metrics['type_count_exact'])
        + 0.5 * gen_metrics['type_count_l1']
        + 1.0 * gen_metrics['num_mae']
        + 1.0 * (1.0 - gen_metrics['adj_f1'])
        + 1.0 * gen_metrics['spatial_mae']
        + 2.0 * gen_metrics['overlap']
    )


# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING + NODE-ORDER SHUFFLE AUGMENTATION
# ══════════════════════════════════════════════════════════════════════════════

def shuffle_node_order(batch):
    """
    Randomly permute the order of valid nodes within each sample.

    Padding nodes stay at the end. node_features, adjacency, and edge_types are
    all permuted consistently so the graph structure is preserved — only the slot
    index each room occupies changes.

    This breaks the slot-position bias where node_embed[0] memorises "big room"
    because the dataset always stores rooms in canonical order (living first,
    largest-first within type). Applied during training only, not validation.

    Safe to use once type_acc is stable (>=90%): the decoder must learn types
    from the condition signal, not from slot position.
    """
    node_features = batch['node_features'].clone()  # [B, N, F]
    adjacency     = batch['adjacency'].clone()       # [B, N, N]
    edge_types    = batch['edge_types'].clone()      # [B, N, N]
    mask          = batch['mask']                    # [B, N]

    B = mask.shape[0]
    for b in range(B):
        n_valid = int(mask[b].sum().item())
        if n_valid < 2:
            continue
        perm = torch.randperm(n_valid)
        node_features[b, :n_valid] = node_features[b, perm]
        adjacency[b, :n_valid, :]  = adjacency[b, perm, :]
        adjacency[b, :, :n_valid]  = adjacency[b, :, perm]
        edge_types[b, :n_valid, :] = edge_types[b, perm, :]
        edge_types[b, :, :n_valid] = edge_types[b, :, perm]

    return {**batch, 'node_features': node_features,
            'adjacency': adjacency, 'edge_types': edge_types}


def load_batches(split):
    folder = DATA_DIR / split
    files = sorted(folder.glob("batch_*.pt"))
    if not files:
        raise FileNotFoundError(f"No batch files in {folder}")
    return [torch.load(str(f), map_location='cpu', weights_only=False) for f in files]


def estimate_adj_pos_weight(batches, cap=8.0):
    """
    Estimate class-imbalance weight for adjacency BCE: neg_edges / pos_edges.
    """
    pos = 0.0
    total = 0.0
    for batch in batches:
        mask = batch['mask'].float()
        adj = batch['adjacency'].float()
        pair_mask = build_pair_mask(mask, upper_only=True)
        pos += (adj * pair_mask).sum().item()
        total += pair_mask.sum().item()

    neg = max(total - pos, 0.0)
    if pos <= 1e-8:
        return 1.0
    weight = neg / pos
    return float(min(max(weight, 1.0), cap))


# ══════════════════════════════════════════════════════════════════════════════
# CSV LOGGER
# ══════════════════════════════════════════════════════════════════════════════

class CSVLogger:
    """Append-mode CSV logger for training curves."""

    FIELDS = [
        'epoch', 'train_loss', 'val_loss', 'val_recon_loss', 'gen_score', 'lr',
        'type', 'adj', 'spatial', 'num', 'kl', 'overlap', 'cond', 'bound', 'cond_gt', 'cond_pred', 'min_size', 'spread',
        'type_acc', 'adj_f1', 'adj_prec', 'adj_recall', 'num_acc', 'spatial_mae',
        'gen_num_acc', 'gen_num_mae', 'gen_type_count_l1', 'gen_type_count_exact',
        'gen_adj_f1', 'gen_adj_prec', 'gen_adj_recall', 'gen_spatial_mae', 'gen_overlap',
        'elapsed_s',
    ]

    def __init__(self, path, resume=False):
        self.path = path
        if resume and path.exists():
            with open(path, 'r', newline='') as f:
                reader = csv.reader(f)
                existing_header = next(reader, [])
            if existing_header != self.FIELDS:
                self.path = path.with_name(f"{path.stem}_v2{path.suffix}")
                print(f"[LOG] Existing header mismatch; writing new log to {self.path}")

        if not resume or not self.path.exists():
            with open(self.path, 'w', newline='') as f:
                csv.writer(f).writerow(self.FIELDS)

    def log(self, row_dict):
        with open(self.path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([row_dict.get(k, '') for k in self.FIELDS])


# ══════════════════════════════════════════════════════════════════════════════
# SMOKE TEST
# ══════════════════════════════════════════════════════════════════════════════

def smoke_test():
    print("=" * 60)
    print("SMOKE TEST")
    print("=" * 60)
    print(f"\nConfig: device={DEVICE}, max_nodes={MAX_NODES}, "
          f"node_feat={NODE_FEAT_DIM}, cond={CONDITION_DIM}, types={NUM_TYPES}")

    model = FloorplanCVAE(hidden_dim=512, latent_dim=64, num_heads=8,
                          enc_layers=4, dec_layers=6).to(DEVICE)
    params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {params:,}")

    batches = load_batches("train")
    batch = batches[0]
    print(f"\nBatch shapes:")
    for k, v in batch.items():
        if isinstance(v, torch.Tensor):
            print(f"  {k}: {v.shape} {v.dtype}")

    model.train()
    output = model(batch, use_gt_encoder=True)
    print(f"\nOutput shapes:")
    for k, v in output.items():
        if isinstance(v, torch.Tensor):
            print(f"  {k}: {v.shape}")

    # Spatial validity
    sp = output['spatial']
    for i in range(3):
        v = sp[0, i].detach().cpu().numpy()
        assert v[2] > v[0] and v[3] > v[1], f"Invalid bbox at node {i}"
    print("\n  x_max > x_min and y_max > y_min: PASS")

    # Loss
    cfg = {
        'w_type': 2.0, 'w_adj': 1.0, 'w_sp': 5.0, 'w_num': 1.0,
        'w_kl': 0.5, 'w_ovlp': 2.0, 'w_cond': 5.0, 'w_bound': 2.0,
        'free_bits': 0.1, 'adj_pos_weight': 3.0, 'cond_pred_mix': 0.5,
    }
    loss, comps = compute_loss(output, batch, epoch_ratio=0.5, config=cfg)
    print(f"\nLoss: {loss.item():.4f}")
    for k, v in comps.items():
        print(f"  {k}: {v:.4f}")

    loss.backward()
    print("\nBackward pass: PASS")

    # Metrics
    model.eval()
    with torch.no_grad():
        output_eval = model(batch, use_gt_encoder=True)
    metrics = compute_metrics(output_eval, batch)
    print(f"\nMetrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    # Generation
    cond = batch['condition'][:4].to(DEVICE)
    gen = model.generate(cond)
    print(f"\nGeneration shapes:")
    for k, v in gen.items():
        if isinstance(v, torch.Tensor):
            print(f"  {k}: {v.shape}")

    print(f"\n{'='*60}")
    print("ALL SMOKE TESTS PASSED")
    print(f"{'='*60}")


# ══════════════════════════════════════════════════════════════════════════════
# TRAINING LOOP
# ══════════════════════════════════════════════════════════════════════════════

def train(args):
    config = {
        'w_type': 2.0,
        'w_adj': 1.0,
        'w_sp': 5.0,
        'w_num': 1.0,
        'w_kl': 0.01,           # very small — KL must never dominate spatial loss
        'w_ovlp': 2.0,
        'w_cond': 5.0,
        'w_bound': args.w_bound,
        'w_min_size': 2.0,      # penalises rooms thinner than 0.15 normalized (~1.92m); fires above hard floor of 0.10
        'w_spread': 1.0,        # penalises all rooms clustering near canvas centre
        'free_bits': args.free_bits,
        'cond_pred_mix': float(min(max(args.cond_pred_mix, 0.0), 1.0)),
        'adj_pos_weight': 1.0,  # set below (auto or CLI override)
    }
    accum_steps = args.accum_steps

    print(f"Device: {DEVICE}")
    print(f"Data:   {DATA_DIR}")
    print(f"Base loss config: {config}")
    print(f"Gradient accumulation: {accum_steps} steps (effective batch {128 * accum_steps})")

    # Data
    print("\nLoading data...")
    train_batches = load_batches("train")
    val_batches = load_batches("val")
    print(f"  Train: {len(train_batches)} batches | Val: {len(val_batches)} batches")

    # Auto class-imbalance weighting for adjacency, unless user overrides
    if args.adj_pos_weight > 0:
        config['adj_pos_weight'] = float(args.adj_pos_weight)
        print(f"  Adjacency pos_weight (manual): {config['adj_pos_weight']:.3f}")
    else:
        config['adj_pos_weight'] = estimate_adj_pos_weight(train_batches, cap=8.0)
        print(f"  Adjacency pos_weight (auto):   {config['adj_pos_weight']:.3f}")

    # Model
    model = FloorplanCVAE(
        hidden_dim=args.hidden_dim,
        latent_dim=args.latent_dim,
        num_heads=args.num_heads,
        enc_layers=args.enc_layers,
        dec_layers=args.dec_layers,
        dropout=args.dropout,
    ).to(DEVICE)
    params = sum(p.numel() for p in model.parameters())
    print(f"  Model params: {params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=args.lr * 0.01)

    # Resume
    start_epoch = 0
    best_recon = float('inf')
    best_gen = float('inf')
    if args.resume and LATEST_PT.exists():
        print(f"  Resuming from {LATEST_PT}")
        ckpt = torch.load(str(LATEST_PT), map_location=DEVICE, weights_only=False)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        start_epoch = ckpt.get('epoch', 0) + 1
        best_recon = ckpt.get('best_recon', float('inf'))
        best_gen = ckpt.get('best_gen', float('inf'))

        # Keep latest config values unless explicitly resumed config is needed.
        if 'loss_config' in ckpt:
            prev_cfg = ckpt['loss_config']
            if args.adj_pos_weight <= 0 and 'adj_pos_weight' in prev_cfg:
                config['adj_pos_weight'] = prev_cfg['adj_pos_weight']
        print(f"  Resumed at epoch {start_epoch}, best_recon={best_recon:.4f}, best_gen={best_gen:.4f}")

    logger = CSVLogger(LOG_CSV, resume=args.resume)

    print(f"\nTraining for {args.epochs} epochs...")
    print("-" * 120)

    train_comp_keys = ['type', 'adj', 'spatial', 'num', 'kl', 'overlap', 'cond', 'bound', 'cond_gt', 'cond_pred', 'min_size', 'spread']
    metric_keys = ['type_acc', 'adj_f1', 'adj_prec', 'adj_recall', 'num_acc', 'spatial_mae']
    gen_keys = ['num_acc', 'num_mae', 'type_count_l1', 'type_count_exact', 'adj_f1', 'adj_prec', 'adj_recall', 'spatial_mae', 'overlap']

    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()
        epoch_ratio = epoch / max(1, args.epochs - 1)
        lr_now = optimizer.param_groups[0]['lr']

        # Train
        model.train()
        np.random.shuffle(train_batches)
        train_loss = 0.0
        train_comps = {k: 0.0 for k in train_comp_keys}

        # Teacher forcing ratio: start at 50%, decay to 0 by 60% of training
        tf_ratio = max(0.0, 0.5 * (1.0 - epoch_ratio / 0.6))

        optimizer.zero_grad()
        for step_i, batch in enumerate(train_batches):
            output = model(batch, use_gt_encoder=True, teacher_forcing_ratio=tf_ratio)
            loss, comps = compute_loss(output, batch, epoch_ratio, config, is_train=True)
            loss = loss / accum_steps
            loss.backward()

            if (step_i + 1) % accum_steps == 0 or step_i == len(train_batches) - 1:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                optimizer.zero_grad()

            train_loss += loss.item() * accum_steps
            for k in train_comps:
                train_comps[k] += comps[k]

        nt = len(train_batches)
        train_loss /= nt
        for k in train_comps:
            train_comps[k] /= nt

        # Validate
        model.eval()
        val_loss = 0.0
        val_comps = {k: 0.0 for k in train_comps}
        tf_metrics = {k: 0.0 for k in metric_keys}
        gen_metrics = {k: 0.0 for k in gen_keys}

        with torch.no_grad():
            for batch in val_batches:
                # Teacher-forced/encoder-path validation
                output = model(batch, use_gt_encoder=True)
                loss, comps = compute_loss(output, batch, epoch_ratio, config, is_train=False)
                val_loss += loss.item()
                for k in val_comps:
                    val_comps[k] += comps[k]
                metrics = compute_metrics(output, batch)
                for k in tf_metrics:
                    tf_metrics[k] += metrics[k]

                # Inference-path validation (condition-only, deterministic z=0)
                cond = batch['condition'].to(DEVICE)
                z = torch.zeros(cond.shape[0], model.latent_dim, device=DEVICE)
                gen_out = model.generate(cond, z=z, two_pass=True)
                gm = compute_generation_metrics(gen_out, batch)
                for k in gen_metrics:
                    gen_metrics[k] += gm[k]

        nv = len(val_batches)
        val_loss /= nv
        for k in val_comps:
            val_comps[k] /= nv
        for k in tf_metrics:
            tf_metrics[k] /= nv
        for k in gen_metrics:
            gen_metrics[k] /= nv

        val_recon_loss = compute_recon_only_loss(val_comps, config)
        gen_score = compute_generation_score(gen_metrics)

        scheduler.step()
        elapsed = time.time() - t0

        # Log to CSV
        logger.log({
            'epoch': epoch + 1,
            'train_loss': f"{train_loss:.6f}",
            'val_loss': f"{val_loss:.6f}",
            'val_recon_loss': f"{val_recon_loss:.6f}",
            'gen_score': f"{gen_score:.6f}",
            'lr': f"{lr_now:.6f}",
            **{k: f"{v:.6f}" for k, v in val_comps.items()},
            **{k: f"{v:.6f}" for k, v in tf_metrics.items()},
            **{f"gen_{k}": f"{v:.6f}" for k, v in gen_metrics.items()},
            'elapsed_s': f"{elapsed:.1f}",
        })

        # Console output
        if (epoch + 1) % 10 == 0 or epoch == 0:
            eta = elapsed * (args.epochs - epoch - 1) / 60
            print(
                f"Ep {epoch+1:3d}/{args.epochs} ({elapsed:.0f}s, ETA {eta:.0f}m) | "
                f"loss train={train_loss:.4f} val={val_loss:.4f} recon={val_recon_loss:.4f} gen={gen_score:.4f} | "
                f"tf: ty={tf_metrics['type_acc']:.1%} adj_f1={tf_metrics['adj_f1']:.1%} num={tf_metrics['num_acc']:.1%} sp={tf_metrics['spatial_mae']:.4f} | "
                f"gen: cnt_exact={gen_metrics['type_count_exact']:.1%} cnt_l1={gen_metrics['type_count_l1']:.3f} "
                f"adj_f1={gen_metrics['adj_f1']:.1%} num={gen_metrics['num_acc']:.1%} sp={gen_metrics['spatial_mae']:.4f} ovlp={gen_metrics['overlap']:.4f} | "
                f"lr={lr_now:.1e}"
            )

        # Checkpoints
        ckpt_data = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'train_loss': train_loss,
            'val_loss': val_loss,
            'val_recon_loss': val_recon_loss,
            'gen_score': gen_score,
            'best_recon': best_recon,
            'best_gen': best_gen,
            'config': {
                'hidden_dim': args.hidden_dim,
                'latent_dim': args.latent_dim,
                'enc_layers': args.enc_layers,
                'dec_layers': args.dec_layers,
                'num_heads': args.num_heads,
                'dropout': args.dropout,
                'max_nodes': MAX_NODES,
                'num_types': NUM_TYPES,
                'node_feat_dim': NODE_FEAT_DIM,
                'condition_dim': CONDITION_DIM,
                'num_edge_types': NUM_EDGE_TYPES,
            },
            'loss_config': config,
            'room_types': ROOM_TYPES,
            'metrics': {
                **{f"tf_{k}": v for k, v in tf_metrics.items()},
                **{f"gen_{k}": v for k, v in gen_metrics.items()},
            },
        }
        torch.save(ckpt_data, str(LATEST_PT))

        if val_recon_loss < best_recon:
            best_recon = val_recon_loss
            ckpt_data['best_recon'] = best_recon
            torch.save(ckpt_data, str(BEST_RECON_PT))

        # Only consider saving best_gen after warmup (epoch 30+) so KL spike
        # in early epochs doesn't cause a low-gen_score to lock in a bad checkpoint.
        if gen_score < best_gen and (epoch + 1) >= 30:
            best_gen = gen_score
            ckpt_data['best_gen'] = best_gen
            torch.save(ckpt_data, str(BEST_GEN_PT))
            # Keep backward-compatible alias for inference scripts expecting best.pt
            torch.save(ckpt_data, str(BEST_PT))

    print(f"\nTraining complete!")
    print(f"Best recon loss: {best_recon:.4f} -> {BEST_RECON_PT}")
    print(f"Best gen score:  {best_gen:.4f} -> {BEST_GEN_PT} (alias: {BEST_PT})")
    print(f"Latest:          {LATEST_PT}")
    print(f"Training log:    {logger.path}")


def infer_num_layers_from_state_dict(state_dict, prefix):
    indices = []
    base_len = len(prefix)
    for key in state_dict.keys():
        if not key.startswith(prefix):
            continue
        suffix = key[base_len:]
        idx_str = suffix.split('.', 1)[0]
        if idx_str.isdigit():
            indices.append(int(idx_str))
    return (max(indices) + 1) if indices else None


def build_model_from_checkpoint(ckpt):
    cfg = ckpt.get('config', {})
    state_dict = ckpt['model_state_dict']

    hidden_dim = int(cfg.get('hidden_dim', state_dict['decoder.node_embed'].shape[-1]))
    latent_dim = int(cfg.get('latent_dim', state_dict['encoder.to_mu.weight'].shape[0]))
    enc_layers = infer_num_layers_from_state_dict(state_dict, "encoder.layers.") or int(cfg.get('enc_layers', 3))
    dec_layers = (
        infer_num_layers_from_state_dict(state_dict, "decoder.layers.")
        or infer_num_layers_from_state_dict(state_dict, "decoder.layer_cond_proj.")
        or int(cfg.get('dec_layers', 4))
    )

    model = FloorplanCVAE(
        hidden_dim=hidden_dim,
        latent_dim=latent_dim,
        num_heads=int(cfg.get('num_heads', 4)),
        enc_layers=enc_layers,
        dec_layers=dec_layers,
        dropout=float(cfg.get('dropout', 0.1)),
    ).to(DEVICE)
    model.load_state_dict(state_dict)
    model.eval()
    return model


def resolve_generation_checkpoint():
    for path in [BEST_GEN_PT, LATEST_PT, BEST_PT, BEST_RECON_PT]:
        if path.exists():
            return path
    return None


def generate_samples(n_samples):
    """Generate floorplan samples from the best available generation checkpoint."""
    ckpt_path = resolve_generation_checkpoint()
    if ckpt_path is None:
        print("No checkpoint found. Train first!")
        return

    print(f"Loading model from {ckpt_path}...")
    ckpt = torch.load(str(ckpt_path), map_location=DEVICE, weights_only=False)
    model = build_model_from_checkpoint(ckpt)

    print(
        f"Loaded model from epoch {ckpt.get('epoch', 0) + 1}, "
        f"val_loss={ckpt.get('val_loss', 0):.4f}, "
        f"val_recon={ckpt.get('val_recon_loss', float('nan')):.4f}, "
        f"gen_score={ckpt.get('gen_score', float('nan')):.4f}"
    )

    # Create sample conditions: typical 2BR/2BA apartment
    conditions = []
    specs = [
        {'name': '2BR/2BA',    'beds': 2, 'baths': 2, 'kitch': 1, 'living': 1, 'balc': 1},
        {'name': '3BR/2BA',    'beds': 3, 'baths': 2, 'kitch': 1, 'living': 1, 'balc': 2},
        {'name': '1BR/1BA',    'beds': 1, 'baths': 1, 'kitch': 1, 'living': 1, 'balc': 0},
        {'name': '4BR/3BA',    'beds': 4, 'baths': 3, 'kitch': 1, 'living': 2, 'balc': 1},
        {'name': '2BR/1BA sm', 'beds': 2, 'baths': 1, 'kitch': 1, 'living': 1, 'balc': 0},
    ]

    for spec in specs[:n_samples]:
        cond = torch.zeros(CONDITION_DIM)
        cond[0] = spec['beds']  / 5.0    # bedroom
        cond[1] = spec['baths'] / 5.0    # bathroom
        cond[2] = spec['kitch'] / 5.0    # kitchen
        cond[3] = spec['living'] / 5.0   # living
        cond[4] = spec['balc']  / 5.0    # balcony
        total = spec['beds'] + spec['baths'] + spec['kitch'] + spec['living'] + spec['balc']
        cond[NUM_TYPES] = total / MAX_NODES
        conditions.append((spec['name'], cond))

    print(f"\nGenerating {len(conditions)} samples...")
    print("-" * 70)

    out_dir = CKPT_DIR / "samples"
    out_dir.mkdir(exist_ok=True)

    for i, (name, cond) in enumerate(conditions):
        cond_batch = cond.unsqueeze(0).to(DEVICE)
        output = model.generate(cond_batch)

        # Decode outputs
        n_rooms = (output['num_logits'].argmax(dim=-1) + 1).item()
        types = output['type_logits'][0, :n_rooms].argmax(dim=-1).cpu().numpy()
        adj = (torch.sigmoid(output['adj_logits'][0, :n_rooms, :n_rooms]) > 0.5).cpu().numpy()
        spatial = output['spatial'][0, :n_rooms].cpu().numpy()

        print(f"\n  [{name}] -> {n_rooms} rooms:")
        for j in range(n_rooms):
            rtype = ROOM_TYPES[types[j]]
            x0, y0, x1, y1, area = spatial[j]
            print(f"    {rtype:10s}: x=[{x0:.2f},{x1:.2f}] y=[{y0:.2f},{y1:.2f}] area={area:.3f}")

        # Check overlaps
        n_overlaps = 0
        for a in range(n_rooms):
            for b in range(a + 1, n_rooms):
                ix = max(0, min(spatial[a,2], spatial[b,2]) - max(spatial[a,0], spatial[b,0]))
                iy = max(0, min(spatial[a,3], spatial[b,3]) - max(spatial[a,1], spatial[b,1]))
                if ix * iy > 0.001:
                    n_overlaps += 1
        print(f"    Overlapping pairs: {n_overlaps}")
        print(f"    Adjacency edges:   {int(adj.sum()) // 2}")

        # Save as JSON for downstream use
        result = {
            'condition': name,
            'n_rooms': n_rooms,
            'rooms': [
                {
                    'type': ROOM_TYPES[types[j]],
                    'x_min': float(spatial[j, 0]),
                    'y_min': float(spatial[j, 1]),
                    'x_max': float(spatial[j, 2]),
                    'y_max': float(spatial[j, 3]),
                    'area':  float(spatial[j, 4]),
                }
                for j in range(n_rooms)
            ],
            'adjacency': adj.astype(int).tolist(),
        }
        json_path = out_dir / f"sample_{i:02d}_{name.replace('/', '_').replace(' ', '_')}.json"
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)

    print(f"\nSamples saved to {out_dir}")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Train CVAE-GNN floorplan generator")
    parser.add_argument('--smoke-test', action='store_true', help="Run shape verification only")
    parser.add_argument('--generate',   type=int, default=0, metavar='N',
                        help="Generate N sample floorplans from best checkpoint")
    parser.add_argument('--epochs',      type=int,   default=200)
    parser.add_argument('--lr',          type=float, default=5e-4)
    parser.add_argument('--hidden-dim',  type=int,   default=512)
    parser.add_argument('--latent-dim',  type=int,   default=64)
    parser.add_argument('--num-heads',   type=int,   default=8)
    parser.add_argument('--enc-layers',  type=int,   default=4)
    parser.add_argument('--dec-layers',  type=int,   default=6)
    parser.add_argument('--dropout',     type=float, default=0.1)
    parser.add_argument('--adj-pos-weight', type=float, default=3.0,
                        help="Adjacency BCE positive class weight. <=0 uses auto-estimation.")
    parser.add_argument('--w-bound', type=float, default=2.0,
                        help="Weight for bounding-box in-canvas penalty.")
    parser.add_argument('--free-bits', type=float, default=0.0,
                        help="KL free-bits floor per latent dimension.")
    parser.add_argument('--cond-pred-mix', type=float, default=0.5,
                        help="Mix for condition loss: 0=GT-mask only, 1=pred-mask only.")
    parser.add_argument('--accum-steps', type=int,   default=2,
                        help="Gradient accumulation steps (effective batch = 128 * N)")
    parser.add_argument('--resume',      action='store_true', help="Resume from latest")
    args = parser.parse_args()

    if args.smoke_test:
        smoke_test()
    elif args.generate > 0:
        generate_samples(args.generate)
    else:
        train(args)


if __name__ == '__main__':
    main()
