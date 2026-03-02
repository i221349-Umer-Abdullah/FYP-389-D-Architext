"""
Smoke test for GNN training — uses correct data keys from pre-processing output.
  - Graph data:   data/processed/batches/graphs_*.pkl  -> keys: 'X' (list), 'A' (list)
  - Conditions:   data/processed/batches/batch_*.npz  -> key:  'conditions' (N,18)
"""
import os, gc, pickle
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

PROCESSED_PATH = Path("data/processed")
OUTPUT_PATH    = Path("models/resplan_gnn")
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device : {DEVICE}")
if torch.cuda.is_available():
    print(f"GPU    : {torch.cuda.get_device_name(0)}")
    print(f"VRAM   : {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")

norm           = np.load(PROCESSED_PATH/"norm_constants.npy", allow_pickle=True).item()
NODE_FEAT_DIM  = norm['node_feature_dim']   # 16
CONDITION_DIM  = norm['condition_dim']       # 18
MAX_NODES      = 30
print(f"\nnode_feature_dim={NODE_FEAT_DIM}  condition_dim={CONDITION_DIM}  max_nodes={MAX_NODES}")

# ── Dataset ────────────────────────────────────────────────────────────────────
class FloorplanDataset(Dataset):
    def __init__(self, processed_path, max_samples=200):
        self.path      = Path(processed_path)
        self.max_nodes = MAX_NODES
        self.items     = []   # list of (batch_idx, sample_idx)

        batch_files  = sorted(self.path.glob("batches/batch_*.npz"))
        graph_files  = sorted(self.path.glob("batches/graphs_*.pkl"))
        assert len(batch_files) > 0, "No batch_*.npz files found"
        assert len(graph_files) > 0, "No graphs_*.pkl files found"
        assert len(batch_files) == len(graph_files), \
            f"Mismatch: {len(batch_files)} npz vs {len(graph_files)} pkl"

        self.batch_files = batch_files
        self.graph_files = graph_files

        for bidx, bf in enumerate(batch_files):
            n_cond = np.load(bf, allow_pickle=True)['conditions'].shape[0]
            for sidx in range(n_cond):
                self.items.append((bidx, sidx))
            if len(self.items) >= max_samples:
                break

        self.items = self.items[:max_samples]

        # Simple cache for last loaded pair
        self._cache_bidx  = None
        self._cache_cond  = None
        self._cache_graph = None

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        bidx, sidx = self.items[idx]

        if self._cache_bidx != bidx:
            cond_data        = np.load(self.batch_files[bidx], allow_pickle=True)
            with open(self.graph_files[bidx], 'rb') as f:
                graph_data   = pickle.load(f)
            self._cache_cond  = cond_data
            self._cache_graph = graph_data
            self._cache_bidx  = bidx

        condition = torch.tensor(self._cache_cond['conditions'][sidx], dtype=torch.float32)
        X_raw     = self._cache_graph['X'][sidx]  # (num_nodes, feat_dim)
        A_raw     = self._cache_graph['A'][sidx]  # (num_nodes, num_nodes)

        num_nodes = X_raw.shape[0]

        X_pad  = torch.zeros(MAX_NODES, NODE_FEAT_DIM)
        A_pad  = torch.zeros(MAX_NODES, MAX_NODES)
        mask   = torch.zeros(MAX_NODES, dtype=torch.bool)

        n = min(num_nodes, MAX_NODES)
        X_pad[:n] = torch.tensor(X_raw[:n], dtype=torch.float32)
        A_pad[:n, :n] = torch.tensor(A_raw[:n, :n], dtype=torch.float32)
        mask[:n] = True

        return {'condition': condition, 'X': X_pad, 'A': A_pad, 'mask': mask, 'num_nodes': num_nodes}


def collate_fn(batch):
    return {
        'condition': torch.stack([b['condition'] for b in batch]),
        'X':         torch.stack([b['X']         for b in batch]),
        'A':         torch.stack([b['A']          for b in batch]),
        'mask':      torch.stack([b['mask']       for b in batch]),
        'num_nodes': [b['num_nodes']              for b in batch],
    }

# ── Minimal GNN ────────────────────────────────────────────────────────────────
class SmokeGNN(nn.Module):
    def __init__(self):
        super().__init__()
        H = 128
        self.cond_proj  = nn.Linear(CONDITION_DIM, H)
        self.node_enc   = nn.Linear(NODE_FEAT_DIM, H)
        self.gnn1       = nn.Linear(H, H)
        self.gnn2       = nn.Linear(H, H)
        self.feat_head  = nn.Linear(H, NODE_FEAT_DIM)
        self.adj_head   = nn.Bilinear(H, H, 1)

    def forward(self, condition, X, A, mask):
        B, N, _ = X.shape
        c = F.relu(self.cond_proj(condition))               # [B, H]
        h = F.relu(self.node_enc(X)) + c.unsqueeze(1)      # [B, N, H]
        An = A / (A.sum(-1, keepdim=True).clamp(min=1))
        h  = F.relu(self.gnn1(torch.bmm(An, h)))
        h  = F.relu(self.gnn2(torch.bmm(An, h)))
        pred_X = self.feat_head(h)
        hi = h.unsqueeze(2).expand(-1, -1, N, -1).reshape(-1, h.shape[-1])
        hj = h.unsqueeze(1).expand(-1, N, -1, -1).reshape(-1, h.shape[-1])
        pred_A = torch.sigmoid(self.adj_head(hi, hj)).reshape(B, N, N)
        return pred_X, pred_A

# ── Run ────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SMOKE TEST — 3 epochs, 200 samples, batch_size=8")
print("="*60)

dataset = FloorplanDataset(PROCESSED_PATH, max_samples=200)
sample  = dataset[0]
print(f"\nSample shapes:")
print(f"  condition : {sample['condition'].shape}")
print(f"  X         : {sample['X'].shape}")
print(f"  A         : {sample['A'].shape}")
print(f"  mask      : {sample['mask'].shape} active={sample['mask'].sum().item()}")
print(f"  num_nodes : {sample['num_nodes']}")

assert sample['condition'].shape[0] == CONDITION_DIM
assert sample['X'].shape == (MAX_NODES, NODE_FEAT_DIM)
print("✓ Data shapes correct")

loader    = DataLoader(dataset, batch_size=8, shuffle=True, num_workers=0, collate_fn=collate_fn)
model     = SmokeGNN().to(DEVICE)
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
print(f"Model params: {sum(p.numel() for p in model.parameters()):,}")

losses = []
for epoch in range(1, 4):
    model.train()
    total = 0.0
    for batch in loader:
        C = batch['condition'].to(DEVICE)
        X = batch['X'].to(DEVICE)
        A = batch['A'].to(DEVICE)
        mask = batch['mask'].to(DEVICE)

        optimizer.zero_grad()
        px, pa = model(C, X, A, mask)

        feat_loss = F.mse_loss(px[mask], X[mask])
        m2 = mask.unsqueeze(2) & mask.unsqueeze(1)
        adj_loss  = F.binary_cross_entropy(pa[m2], A[m2])
        loss = feat_loss + adj_loss
        loss.backward()
        optimizer.step()
        total += loss.item()

    avg = total / len(loader)
    losses.append(avg)
    print(f"Epoch {epoch}/3 | Loss: {avg:.4f}")

print(f"\nLoss trajectory: {' -> '.join(f'{l:.4f}' for l in losses)}")
assert losses[-1] < losses[0], f"Loss did not decrease: {losses}"
print("✓ Loss is decreasing")

# Checkpoint save
ckpt = OUTPUT_PATH / "smoke_test_ckpt.pt"
torch.save({'epoch': 3, 'model_state_dict': model.state_dict(), 'loss': losses[-1]}, ckpt)
print(f"✓ Checkpoint saved: {ckpt}")

# Checkpoint load
loaded = torch.load(ckpt, map_location=DEVICE)
model2 = SmokeGNN().to(DEVICE)
model2.load_state_dict(loaded['model_state_dict'])
print(f"✓ Checkpoint loaded (epoch {loaded['epoch']}, loss {loaded['loss']:.4f})")

if torch.cuda.is_available():
    used  = torch.cuda.memory_allocated() / 1e9
    total_vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"\nVRAM used: {used:.2f} GB / {total_vram:.1f} GB ({100*used/total_vram:.1f}%)")

print("\n" + "="*60)
print("ALL SMOKE TESTS PASSED — safe to run overnight training")
print("="*60)
