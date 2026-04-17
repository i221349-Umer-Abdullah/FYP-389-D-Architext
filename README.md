# ArchiText — Text-to-BIM Conversion System

> **Final Year Project (Iteration 3)**: An AI-powered system that converts natural language building descriptions into professional IFC BIM models, built on a 4-layer pipeline trained on the ResPlan dataset.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.7+-red.svg)
![IFC](https://img.shields.io/badge/IFC-4-green.svg)
![Dataset](https://img.shields.io/badge/Dataset-ResPlan%2017k-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## What is ArchiText?

ArchiText takes a plain English description of a building and generates a complete, standards-compliant IFC floor plan. The output opens directly in Revit, BlenderBIM, and AutoCAD — no manual modelling required.

Type something like:

> *"3 bedroom house with 2 bathrooms, open plan kitchen and living room, 5 marla plot"*

And get back a fully structured BIM model with correctly sized and positioned rooms, wall geometry, and proper IFC metadata.

---

## System Architecture

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
║                              │ condition vector                      ║
║                              ▼                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │  LAYER 2 — Conditional Graph Generator                        │   ║
║  │  Model   : CVAE-GNN trained on ResPlan (17,000 floor plans)   │   ║
║  │  Input   : Condition vector                                    │   ║
║  │  Output  : Room graph (nodes=rooms, edges=adjacencies)        │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                              │ room graph + geometry                 ║
║                              ▼                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │  LAYER 3 — Smart Validator & Corrector                        │   ║
║  │  Rules   : Minimum sizes, no overlaps, connectivity           │   ║
║  │  Output  : Validated, architecturally correct room graph      │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                              │ validated geometry                    ║
║                              ▼                                       ║
║  ┌───────────────────────────────────────────────────────────────┐   ║
║  │  LAYER 4 — IFC Export Engine                                  │   ║
║  │  Library : IfcOpenShell                                       │   ║
║  │  Schema  : IFC4                                               │   ║
║  │  Output  : .ifc file + 2D PNG preview                         │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                              │                                       ║
║                              ▼                                       ║
║  OUTPUT: building.ifc  +  Web Application Preview                   ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Project Structure

```
architext/
├── backend/                        # FastAPI backend server
│   ├── api/routes/                 # HTTP endpoints (generate, status, download, preview)
│   ├── core/                       # Pipeline orchestrator, GNN adapter, NLP adapter
│   └── models/                     # Pydantic schemas
│
├── frontend/                       # Next.js web application
│   └── src/
│       ├── app/                    # Pages (studio, library, dashboard, plugins)
│       ├── components/             # UI components + Three.js 3D viewer
│       └── hooks/                  # usePromptWorkflow (generation state machine)
│
├── scripts/                        # Training, preprocessing, and utility scripts
│   ├── preprocess_resplan_v3.py    # ResPlan dataset preprocessing
│   ├── gnn_train_cvae.py           # CVAE-GNN training
│   ├── generate_bim.py             # IFC generation engine
│   └── run_pipeline.py             # Blender addon entry point
│
├── models/
│   ├── nlp_t5/final_model/         # Trained T5 NLP model
│   └── resplan_gnn/                # Trained CVAE-GNN model
│
├── blender_addon/                  # Blender plugin (downloadable from web app)
├── docs/                           # Project documentation
└── output/                         # Generated IFC files
```

---

## What Was Built

- **CVAE-GNN trained on ResPlan** — 17,000 real residential floor plans preprocessed into graph format and used to train a Conditional Variational Autoencoder with graph convolutions. The model learns spatial relationships between rooms and generates realistic layouts conditioned on a room specification.

- **Full 4-layer pipeline** — NLP parsing (T5) → room graph generation (CVAE-GNN) → validation/correction → IFC export. Both a trained model approach and an LLM-based approach are available for comparison.

- **FastAPI backend with async job system** — accepts prompts, runs generation in the background, exposes polling endpoints so the UI stays responsive during the 10–60 second generation process.

- **Next.js web application** — real-time 3D viewer (Three.js/React Three Fiber), side-by-side comparison mode, 2D floor plan previews, a shared floor plan library backed by MongoDB, and user authentication.

- **Blender addon** — generates IFC floor plans directly inside Blender from a natural language prompt, bridging the pipeline with professional BIM tooling.

---

## Installation & Setup

### Backend

```bash
git clone https://github.com/i221349-Umer-Abdullah/FYP-389-D-Architext.git
cd FYP-389-D-Architext
git checkout iteration3

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Start the backend
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Branch Guide

| Branch | Contents |
|---|---|
| `main` | Stable release |
| `iteration1` | Initial NLP + rule-based layout prototype |
| `iteration3` | **Current** — CVAE-GNN on ResPlan + full web application |

---

## Acknowledgments

- [ResPlan Dataset](https://www.kaggle.com/datasets/) — 17,000 residential floor plans with native graph representation
- [IfcOpenShell](https://ifcopenshell.org/) — IFC file generation
- [Hugging Face Transformers](https://huggingface.co/transformers/) — T5 model
- [PyTorch](https://pytorch.org/) — Deep learning framework

---

**ArchiText** — Transforming words into buildings.
