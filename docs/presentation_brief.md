# ArchiText — Presentation Brief

## What Is It

ArchiText converts a plain-English building description into a complete 2D floor plan and a 3D BIM model (IFC file), ready to open in Revit or Blender. The user types one prompt; the system outputs a downloadable architectural model.

---

## The Problem It Solves

Traditional BIM authoring (Revit, ArchiCAD) requires expert architects hours of manual work to produce even a basic floor plan. ArchiText reduces that to a single natural-language prompt — making early-stage design exploration instant and accessible.

---

## Tech Stack

### Frontend
- **Next.js 15** (React, TypeScript, App Router)
- **Three.js / React Three Fiber** — 3D scene canvas in the browser
- **Framer Motion** — scroll-driven animations, state transitions
- **NextAuth.js** — authentication (login / register)
- **MongoDB** — user accounts and saved floor plan library
- CSS Modules, custom design system

### Backend
- **Python 3.11 + FastAPI** — REST API (`/api/generate`, `/api/status`, `/api/download`)
- **PyTorch** — StructuralGNN training and inference (primary generator)
- **T5 (fine-tuned)** — natural language → structured spec (NLP layer)
- **ifcopenshell 0.8.4** — IFC 4 file construction (walls, spaces, storey hierarchy)
- **matplotlib** — 2D floor plan PNG rendering
- **Groq API** (llama-3.3-70b) — LLM generator (comparison baseline)

---

## System Architecture (Pipeline)

```
User types a prompt
        │
        ▼
  Layer 1 — T5 NLP Model (fine-tuned)
  — extracts room counts, sizes, style from text
  — outputs a structured spec (JSON)
        │
        ▼
  Layer 2 — StructuralGNN (CVAE, our primary model)
  — takes spec as condition vector
  — generates a room graph: type, position, area per node
        │
        ▼
  Layer 3 — Validator
  — enforces minimum room sizes
  — fixes overlaps, snaps disconnected rooms
        │
        ├──▶  2D Floor Plan PNG  (matplotlib)
        │
        └──▶  3D IFC Model  (ifcopenshell)
               — IfcWall geometry per room
               — IfcSpace tags for BIM room annotations
               — IFC 4 hierarchy: Project → Site → Building → Storey
               — Opens in Revit, BlenderBIM, FreeCAD
```

---

## Primary Approach — StructuralGNN

Our main research contribution is a trained Graph Neural Network for floor plan generation.

**Dataset**
- ResPlan — 17,000 annotated residential floor plans
- Each plan: room nodes with type, normalised position (cx, cy), and area
- Preprocessing: graph construction, normalisation, train/val/test split

**Model Architecture**
- **Type:** Conditional Variational Autoencoder (CVAE) + Graph Neural Network
- **Input:** 18-dimensional condition vector (room type counts from T5 spec)
- **Encoder:** GNN layers that embed the room graph into a latent space
- **Decoder:** Samples from latent space and generates room node features
- **Output per node:** room type (one-hot), normalised area, normalised centre position (cx, cy)

**Training**
- Framework: PyTorch
- Epochs: 200, with best-epoch checkpointing
- Loss: reconstruction loss (positions + area) + KL divergence (CVAE regularisation)
- Hardware: local GPU

**What It Does Well**
- Learns real residential floor plan distributions from 17k examples
- Produces structurally plausible room graphs (correct room types, connected layouts)
- Fully end-to-end: NLP prompt → GNN → IFC, no manual steps

**Limitations (honest assessment)**
- Room sizes are unrealistic — outputs tend toward 60–90 m² per room regardless of prompt
- Root cause: the CVAE latent space collapses under the room-count condition vector alone; richer conditioning (adjacency constraints, aspect ratios) would help

---

## Comparison — LLM Generator

To contextualise the GNN's limitations, we compare against an LLM-based approach where a single API call (llama-3.3-70b via Groq) generates the room layout JSON directly from the prompt.

| | StructuralGNN (primary) | LLM Generator (comparison) |
|---|---|---|
| Method | CVAE GNN trained on 17k floor plans | LLM prompt → JSON |
| Training | Yes — dataset, GPU, 200 epochs | None |
| Room sizes | 60–90 m² (unrealistic) | 10–25 m² (realistic) |
| Layout variety | Low (deterministic) | High |
| Research contribution | Yes — trained model, pipeline, BIM export | Reference implementation |
| Related work | Standard academic approach | ZURU Tech: 109% quality gain over GNN with Claude 3.5 |

This comparison demonstrates both the value and the current limitations of our trained model, and points to a clear direction for future improvement.

---

## Key Features of the Web App

- Type a prompt → get a 2D floor plan preview instantly
- Download a valid `.ifc` file (opens in Revit / BlenderBIM with full 3D wall geometry)
- Compare GNN output vs LLM output side-by-side
- Save generated plans to a personal library (dashboard)
- Download Revit and Blender plugins for direct BIM integration

---

## Academic Context

- Primary contribution: end-to-end NLP-to-BIM pipeline with a trained GNN at its core
- Honest evaluation against an LLM baseline reveals concrete limitations and future work
- IFC 4 compliant output — interoperable with industry-standard tools (Revit, BlenderBIM)
- References: ResPlan dataset, ZURU Tech (LLM-to-BIM), HouseDiffusion (CVPR 2024)
