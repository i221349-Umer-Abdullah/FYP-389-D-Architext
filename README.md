# ArchiText — Text-to-BIM Conversion System

> **Final Year Project (Iteration 3)**: An AI-powered system that converts natural language building descriptions into professional IFC BIM models, now with a redesigned 4-layer architecture trained on the ResPlan large-scale dataset.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.7+-red.svg)
![IFC](https://img.shields.io/badge/IFC-2X3-green.svg)
![Dataset](https://img.shields.io/badge/Dataset-ResPlan%2017k-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## What's New in Iteration 3

> **Previous iterations** used a 5-layer pipeline trained on CubiCasa5k (~5,000 floorplans) with a Blender/Revit add-on as the target output.
>
> **Iteration 3** is a major architectural overhaul. See the comparison below.

### Architecture Changes: 5 Layers → 4 Layers

| | Iteration 1 & 2 | Iteration 3 |
|---|---|---|
| **Training Dataset** | CubiCasa5k (~5,000 plans) | **ResPlan (17,000 plans)** |
| **Dataset Format** | Raster images, manual conversion | Native vector + graph format |
| **Layer 2 Model** | Simple GNN (10 room types) | **GNN + CVAE (13 room types, ResPlan-aligned)** |
| **Layer 3** | Rule-based fixer (separate) | Merged into Smart Validator |
| **Layer 4 (old)** | Quality control (separate) | Merged into Smart Validator |
| **Layer 5 → Layer 4** | IFC export | IFC export (same, rewired adapter) |
| **Deployment Target** | Blender/Revit add-on | **Standalone web application** |
| **NLP Training Data** | Generic synthetic pairs | **ResPlan-aligned pairs (13 types + marla/sqm area + Pakistani locale)** |

### New Components Added This Iteration

| File | Purpose |
|---|---|
| `scripts/room_graph_to_ifc.py` | Generic model-agnostic IFC adapter (replaces old hardwired pipeline) |
| `scripts/generate_resplan_training_data.py` | ResPlan-aligned NLP training data generator |
| `scripts/smoke_test_gnn.py` | Data validation + pre-training smoke test |
| `notebooks/pre-processing.ipynb` | ResPlan data preprocessing (graph extraction, normalization) |
| `notebooks/gnn-phase.ipynb` | GNN+CVAE training notebook on ResPlan |
| `data/processed/` | 17,000 processed floorplans (batch NPZ + graph PKL files) |
| `datasets/processed/text_pairs/resplan_pairs.jsonl` | 3,000 ResPlan-aligned NLP training pairs |

---

## System Architecture (Iteration 3)

```
╔══════════════════════════════════════════════════════════════════════╗
║              ARCHITEXT — ITERATION 3 ARCHITECTURE                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  INPUT: "3 bedroom house with 2 baths, 5 marla plot, Bahria style"  ║
║                              │                                       ║
║                              ▼                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │  LAYER 1 — NLP Intent Parser                                  │   ║
║  │  Model   : Fine-tuned T5-small transformer                    │   ║
║  │  Input   : Natural language (English + Pakistani locale)      │   ║
║  │  Output  : Structured spec {unit_type, net_area, room_counts} │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                              │ condition vector (dim 18)             ║
║                              ▼                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │  LAYER 2 — Conditional Graph Generator             [NEW]      │   ║
║  │  Model   : GNN + CVAE (trained on ResPlan 17,000 plans)       │   ║
║  │  Input   : Condition vector                                    │   ║
║  │  Output  : Room graph (nodes=rooms, edges=adjacencies)        │   ║
║  │  Types   : 13 room types (bedroom, bathroom, living,          │   ║
║  │            kitchen, balcony, storage, parking, garden,        │   ║
║  │            pool, stair, veranda, inner, wall)                 │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                              │ room graph + geometry                 ║
║                              ▼                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │  LAYER 3 — Smart Validator & Corrector             [NEW]      │   ║
║  │  Rules   : Minimum sizes, no overlaps, connectivity           │   ║
║  │  Scorer  : ML quality score — loops back if below threshold   │   ║
║  │  Output  : Validated, architecturally correct room graph      │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                              │ validated geometry                    ║
║                              ▼                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │  LAYER 4 — IFC Export Engine                  [REWIRED]      │   ║
║  │  Library : IfcOpenShell                                       │   ║
║  │  Schema  : IFC 2x3 (Revit / ArchiCAD / BlenderBIM)           │   ║
║  │  Output  : .ifc file + room summary JSON for frontend         │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                              │                                       ║
║                              ▼                                       ║
║  OUTPUT: building.ifc  +  Web App Preview                           ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Project Structure (Iteration 3)

```
architext/
├── scripts/
│   ├── inference_nlp.py                # Layer 1: T5 NLP inference
│   ├── train_nlp_model.py              # Layer 1: NLP model training
│   ├── generate_resplan_training_data.py  # Layer 1: ResPlan-aligned training data [NEW]
│   ├── room_graph_to_ifc.py            # Layer 4: Generic IFC adapter  [NEW]
│   ├── generate_bim.py                 # Layer 4: IFC generation engine
│   ├── smoke_test_gnn.py               # Data + training smoke test    [NEW]
│   └── ...
│
├── notebooks/
│   ├── pre-processing.ipynb            # ResPlan graph preprocessing   [NEW]
│   ├── gnn-phase.ipynb                 # GNN+CVAE training             [NEW]
│   └── vae-evaluation.ipynb            # VAE geometry evaluation       [NEW]
│
├── data/
│   └── processed/                      # 17,000 processed floorplans
│       ├── batches/batch_*.npz         # Image + condition batches
│       ├── batches/graphs_*.pkl        # Room graph batches (X, A)
│       └── norm_constants.npy          # Normalization constants
│
├── models/
│   ├── nlp_t5/final_model/             # Trained T5 NLP model
│   └── resplan_gnn/                    # GNN model (training in progress)
│
├── datasets/
│   └── processed/text_pairs/
│       ├── resplan_pairs.jsonl         # 3,000 ResPlan-aligned NLP pairs [NEW]
│       └── text_pairs.jsonl            # Previous training pairs
│
└── output/                             # Generated IFC files
```

---

## Pre-Processing Validation Results (Iteration 3)

The ResPlan dataset was processed and validated with the following results:

| Metric | Result | Assessment |
|---|---|---|
| Room Count Accuracy | **100%** | ✅ Perfect |
| Node Count Accuracy | **91.1%** | ✅ Good (degenerate rooms pruned) |
| Edge Recall | **86.6%** | ✅ Good |
| Edge Precision | **100%** | ✅ Perfect — no false edges |
| Mean Area Error | **0.0004** | ✅ Excellent |
| Mean Position Error | **0.093** | ✅ Fine |

---

## Installation & Setup

```bash
git clone https://github.com/i221349-Umer-Abdullah/FYP-389-D-Architext.git
cd FYP-389-D-Architext
git checkout iteration3

python -m venv venv
venv\Scripts\activate          # Windows
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install transformers ifcopenshell shapely tqdm numpy scipy scikit-learn networkx matplotlib
```

### Running the Pre-processing

```bash
# Open Jupyter and run notebooks in order
jupyter notebook --notebook-dir=notebooks

# 1. pre-processing.ipynb   (~15–20 min on RTX 3080)
# 2. gnn-phase.ipynb        (~8–14 hrs on RTX 3080, leave overnight)
```

### Testing the IFC Adapter

```bash
python scripts/room_graph_to_ifc.py
# Generates output/adapter_test.ifc
```

### Generating NLP Training Data

```bash
python scripts/generate_resplan_training_data.py 3000
# Outputs datasets/processed/text_pairs/resplan_pairs.jsonl
```

---

## Branch Guide

| Branch | Contents |
|---|---|
| `main` | Stable release |
| `iteration1` | Initial NLP + rule-based layout prototype |
| `dev` | Development work from Iteration 2 |
| `iteration3` | **Current** — ResPlan GNN architecture + webapp target |

---

## Roadmap (Iteration 3)

- [x] Redesign pipeline: 5 layers → 4 layers
- [x] Switch dataset: CubiCasa5k → ResPlan (17,000 plans)
- [x] Pre-process ResPlan → graph batches (17k floorplans)
- [x] Validate pre-processing quality
- [x] Rewire IFC adapter (model-agnostic)
- [x] Generate ResPlan-aligned NLP training data (3,000 pairs)
- [ ] Train GNN+CVAE on ResPlan *(in progress — training overnight)*
- [ ] Build NLP → condition vector adapter
- [ ] Build Layer 3 Smart Validator
- [ ] Build FastAPI backend
- [ ] Build Next.js frontend (web app)

---

## Acknowledgments

- [ResPlan Dataset](https://www.kaggle.com/datasets/) — 17,000 residential floorplans with native graph representation
- [IfcOpenShell](https://ifcopenshell.org/) — IFC file generation
- [Hugging Face Transformers](https://huggingface.co/transformers/) — T5 model
- [PyTorch](https://pytorch.org/) — Deep learning framework

---

## Current Status (as of March 2026 — where to resume)

### What has actually been built and works end-to-end
- **Full 4-layer API pipeline** is running (`uvicorn backend.main:app --port 8000`). User types a prompt → NLP extracts a spec → GNN generates a room graph → Validator fixes overlaps/missing rooms → IFC file exported.
- **Layer 1 (NLP):** T5-small fine-tuned model, deployed and working.
- **Layer 3 (Validator):** Push-apart overlap resolver + required-room-type injector, both implemented in `backend/core/pipeline.py`.
- **Layer 4 (IFC export):** Working, outputs valid `.ifc` files openable in BlenderBIM.

### What is broken / not yet trained correctly
- **Layer 2 (GNN) — the core problem.** The current model at `models/resplan_gnn/gnn_best.pt` was **never trained on ResPlan**. It was accidentally trained on a CubiCasa-derived JSON dataset (`data/layout_training/cubicasa_train_full.json`), which is why floor plan outputs look wrong (rooms scattered, wrong counts, no real spatial layout).

### What we have just done (the fix)
- Discovered the mismatch: `ResPlan.pkl` (17,000 samples, `D:\Work\Uni\FYP\Dataset\ResPlan\`) was sitting unused.
- Wrote `scripts/preprocess_resplan.py` — reads actual ResPlan.pkl, extracts Shapely polygon geometry, normalises positions per-plan using the `inner` building footprint, uses the dataset's pre-built NetworkX adjacency graph. Outputs batches to `data/processed_v2/`.
- Wrote `scripts/gnn_train_v2.py` — same GNN architecture but with 4 loss terms (adjacency + type + **spatial MSE** + num_nodes). Spatial MSE was the critical missing piece before.
- Also fixed `backend/core/spec_converter.py` — it was building the wrong condition vector format, so the model was receiving meaningless input at inference time.

### What still needs to happen
1. **Run training** (start with `.\venv\Scripts\python.exe scripts\gnn_train_v2.py`, trains for 300 epochs, ~2–3 hours on GPU, saves best model to `models/resplan_gnn/gnn_best_v2.pt`)
2. **Update inference decoder** (`backend/core/real_gnn.py`) to load `gnn_best_v2.pt` with `canvas_metres=12.8` from `norm_constants.npy`
3. **Test end-to-end** with `python C:\tmp\test_api.py "3 bedroom house..."` and check `C:\tmp\floorplan_preview.png`
4. If outputs are still not realistic enough → consider fine-tuning on RPLAN or CubiCasa5k (datasets are all in `D:\Work\Uni\FYP\Dataset\`)

---

**ArchiText** — Transforming words into buildings.
