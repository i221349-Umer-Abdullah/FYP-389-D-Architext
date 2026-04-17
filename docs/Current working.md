---

# SESSION LOG — 2026-04-17

## What We Did This Session

### 1. Strategic Decision — Dropped GNN retraining, switched to LLM-based generation
- Previous GNN (StructuralGNN trained on ResPlan) was producing unusable outputs: rooms 60–90 m² each, wrong positions, no variety.
- Evaluated ChatHouseDiffusion (CVPR 2024) as external alternative — rejected: requires RTX 3090 24 GB VRAM (we have 10 GB), outputs 64×64 px images, needs user to draw a boundary polygon first.
- Decision: replace Layers 1+2 (T5 NLP + GNN) with a single LLM API call that outputs a room layout JSON directly. Validated by ZURU Tech's published work achieving 109% improvement with Claude/LLM approach.

### 2. Pushed all pending code to `iteration3` branch
- Fixed `.gitignore` to exclude `data/processed/`, `data/processed_v2/`, `data/processed_v3/`, `*.pkl`, `*.npy` (was accidentally untracked, 105 MB of generated training artifacts).
- Committed: `docs/PROJECT_CONTEXT.md` (canonical handoff doc), 4 new scripts, removed 2 outdated docs.

### 3. Created `backend/core/llm_adapter.py` (new)
- Supports 3 providers via env vars: **OpenAI**, **Anthropic**, or any **OpenAI-compatible** endpoint (Groq, Ollama, OpenRouter).
- Contains a carefully engineered system prompt + 2 verified few-shot floor plan examples.
- Robust JSON extraction: handles raw JSON, markdown fences, and regex fallback.
- Validates all room fields and normalises room type aliases.
- `generate_room_layout(prompt)` — async, returns standard `room_graph` dict.
- `spec_from_room_graph(rg)` — derives spec dict from LLM output for Layer 3 compatibility.

### 4. Updated `backend/core/pipeline.py`
- Added `generator_mode` parameter: `"llm"` (default) or `"gnn"`.
- LLM mode: calls `generate_room_layout()` — replaces Layers 1+2 in one step.
- GNN mode: original T5 → spec → StructuralGNN path, still intact.
- `DEFAULT_GENERATOR_MODE` env var (`GENERATOR_MODE=llm` in `.env`).

### 5. Updated API to expose `generator_mode`
- `GenerateRequest` schema now has optional `generator_mode` field.
- `POST /api/generate` body: `{"text": "...", "generator_mode": "llm"}` or `"gnn"`.

### 6. Created `.env.example` + updated `requirements_modern.txt`
- `.env.example` documents all 4 provider options with copy-paste config.
- Added `openai`, `anthropic`, `python-dotenv` to requirements.
- Installed `openai` and `anthropic` packages into venv.

### 7. Recreated `scripts/generate_bim.py` (was deleted, only `.pyc` cache remained)
- Written from scratch using `ifcopenshell` 0.8.4 high-level API.
- `BIMGenerator` class: `create_project_structure(name)` + `create_simple_room(name, length, width, height, x_offset, y_offset)`.
- IFC4 hierarchy: Project → Site → Building → Storey → Space.
- Each room = `IfcSpace` with extruded box geometry (`IfcExtrudedAreaSolid`), correct metre coordinates, valid containment relations.

### 8. Created/updated `scripts/test_llm_pipeline.py`
- Full end-to-end test: prompt → LLM → validate → 2D PNG + IFC 3D model.
- Saves outputs to `output/comparison/`.
- `--llm-only` flag skips GNN (use when model not trained/available).
- `--gnn-only` flag for testing GNN alone.
- Side-by-side comparison PNG when both modes run.

### 9. Verified full pipeline runs end-to-end
- Groq API key configured in `.env` (free tier, llama-3.3-70b-versatile).
- Test prompt "3 bedroom house, 2 bathroom with a living room" produced:
  - 7 rooms, 80.5 m² — realistic sizes (living 22.5 m², bedrooms 12–16 m², bathrooms 4–5 m²)
  - Valid IFC4 file (7 KB, 7 IfcSpace entities with box geometry)
  - Clean 2D PNG floor plan

---

## Current Pipeline (as of this session)

```
User text prompt
    |
    v
LLM API (Groq/llama-3.3-70b or OpenAI/Anthropic)   [backend/core/llm_adapter.py]
    |
    v
Room layout JSON  {rooms: [{type, x, y, width, height}, ...]}
    |
    v
Layer 3 — validator: fix overlaps, enforce min sizes, snap disconnected rooms   [pipeline.py]
    |
    +---> 2D PNG  (matplotlib)                        [scripts/visualize_2d.py]
    |
    +---> IFC 3D model  (ifcopenshell, IFC4)          [backend/core/room_graph_to_ifc.py
                                                        scripts/generate_bim.py]
```

## How to Run

```powershell
cd d:\Work\Uni\FYP\architext

# Full pipeline test (LLM only):
.\venv\Scripts\python.exe scripts\test_llm_pipeline.py --llm-only "your prompt here"

# Start FastAPI backend:
.\venv\Scripts\uvicorn backend.main:app --reload --port 8000
# POST {"text": "3 bedroom house...", "generator_mode": "llm"} to http://localhost:8000/api/generate
```

---

## What Is Left To Do

### High Priority (needed for FYP demo)
- [ ] **NextJS frontend** — web app where user types a prompt and sees the 2D floor plan + downloads the IFC
  - Pages: home (prompt input), results (2D preview + IFC download button)
  - Calls FastAPI backend: POST `/api/generate`, polls `/api/status/{id}`, GET `/api/download/{id}`
  - Show a loading indicator while generating (LLM call takes ~2–4 seconds)
- [ ] **2D preview endpoint** — `/api/preview/{job_id}` should return a PNG image, not just a JSON summary
  - Currently `job.preview` holds room summary dict, not an image
  - Need to render the matplotlib PNG and serve it via the API
- [ ] **Wire both generator modes in UI** — let user choose LLM vs GNN from the frontend for comparison

### Medium Priority
- [ ] **IFC viewer in browser** — embed a lightweight IFC viewer (e.g. `web-ifc-viewer` or `ifcjs`) so user sees the 3D model in-browser, not just a download
- [ ] **Multiple layout variants** — call LLM 3× with temperature variation, let user pick
- [ ] **Kitchen missing from some outputs** — LLM occasionally omits kitchen when not explicitly stated; tighten the system prompt or add a post-generation check

### Nice to Have (if time permits)
- [ ] **Revit plugin** — IFC → Revit integration (was original plan, deprioritised for web app)
- [ ] **CVAE GNN improvements** — rotation augmentation, `other` room type support (was deferred earlier, still deferred)
- [ ] **Interactive 2D editor** — let user drag/resize rooms before generating IFC

---

## Key Files Reference

| File | Purpose |
|---|---|
| `backend/core/llm_adapter.py` | LLM provider abstraction, prompt + JSON parsing |
| `backend/core/pipeline.py` | 4-layer orchestrator, `generator_mode` param |
| `backend/core/room_graph_to_ifc.py` | Room graph → IFC conversion (Layer 4) |
| `scripts/generate_bim.py` | `BIMGenerator` using ifcopenshell 0.8.4 |
| `scripts/test_llm_pipeline.py` | End-to-end test: prompt → PNG + IFC |
| `.env` | LLM API key + provider config (gitignored) |
| `.env.example` | Config template with all 4 provider options |
| `docs/PROJECT_CONTEXT.md` | Full architecture + handoff reference |

---

<!-- BELOW THIS LINE: old session notes kept for reference -->
---

📊 Dataset Summary
Dataset	Status	Use For
CubiCasa5k	✅ Downloaded	Layout AI (5000 plans)
FloorPlanCAD	✅ Downloaded	Layout AI (diversifies data)
ResBIM	⭐ MUST DOWNLOAD	BIM training (1000+ RVT files!)
BIMNet	❌ Not applicable	Scan-to-BIM (different problem)
RPLAN	⏳ Pending request	Nice-to-have, not critical
HouseExpo	❌ Skip	Interior navigation, not useful
🤖 AI Training Modules (3 total)
Text-to-Spec AI - T5 fine-tuning (NLP)
Layout Generator AI - HouseDiffusion or CNN
BIM Generation Engine - Rules + ML optimization
🎯 Critical Next Step
Download ResBIM dataset NOW (7GB): Google Drive Link

This is the ONLY dataset with actual Revit .RVT files paired with 2D floor plans - essential for your Revit-focused approach!

❓ Quick Answers
IfcOpenShell? Not needed for Revit (use Revit API instead)
CubiCasa5k sufficient? Yes, 5000 samples is enough
Why fine-tune? Domain vocabulary + structured output = unique contribution
Please review the implementation plan and let me know if you'd like any changes before I proceed with execution.


Answers to Your Questions
1. What T5 Was Trained On
The T5 model was trained on 599 text-spec pairs in this format:

Input (Natural Language)	Output (JSON Spec)
"A modern 2-bedroom home with 1 bathroom, living room, kitchen, totaling 62 sqm."	{"bedrooms": 2, "bathrooms": 1, "living_room": true, "kitchen": true, "total_area_sqm": 62, "style": "modern"}
Data sources:

499 pairs from CubiCasa5k (real floor plan layouts → text descriptions)
100 pairs from synthetic generation

3. FloorPlanCAD Dataset Analysis
I analyzed FloorPlanCAD - it has different structure than CubiCasa5k:

✅ Has layers: WALL, WINDOW, COLUMN, etc. with semantic-id attributes
❌ No room type labels (Bedroom, Kitchen, etc.) - only structural elements
Verdict: FloorPlanCAD is not useful for Text-to-Spec (NLP training) but will be valuable for Layout Optimizer later


BlenderBIM Integration Setup
Tested end-to-end Text-to-BIM pipeline. Pipeline completed (exit code 0). Verifying IFC file generation and preparing final walkthrough.

Files Edited
generate_bim.py
text_to_bim.py
inference_nlp.py
Task
Progress Updates
1
Updating task checklist and installing dependencies

2
Creating T5 inference script and IFC generation engine

3
Testing end-to-end Text-to-BIM pipeline

4
Checking pipeline output and creating demonstration