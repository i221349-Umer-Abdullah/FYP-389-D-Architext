# Architext — Project Architecture Overview

## What is Architext?

Architext is a **text-to-BIM (Building Information Modelling)** system. You type a natural language description of a building (e.g. *"3 bedroom apartment with open plan kitchen and 2 bathrooms"*) and the system generates a full 3D floor plan — both as a visual 3D model in the browser and as a downloadable IFC file that opens in professional tools like Blender, Revit, and AutoCAD.

The project has three major components that connect together: the **Backend (FastAPI)**, the **Generator (the AI pipeline)**, and the **Frontend (Next.js)**.

---

## 1. The Backend (FastAPI)

**Location:** `architext/backend/`

The backend is a Python web server built with FastAPI. It acts as the bridge between the frontend and the AI generation pipeline. It runs locally on `http://localhost:8000`.

### How it works

The backend exposes a small set of HTTP endpoints:

| Endpoint | What it does |
|---|---|
| `POST /api/generate` | Accepts a text prompt + mode (`llm` or `gnn`), starts a background generation job, returns a `job_id` immediately |
| `GET /api/status/{job_id}` | Returns current status (`pending`, `processing`, `done`, `failed`) and progress percentage |
| `GET /api/preview/{job_id}` | Returns the 2D floor plan PNG image for a completed job |
| `GET /api/download/{job_id}` | Returns the IFC file for download |
| `POST /api/ifc-from-rooms` | Converts stored room data directly to IFC (used by the library viewer) |

### The job system

When the frontend sends a prompt, the backend creates a **Job object** in memory (tracked by `job_manager.py`) and immediately kicks off the generation pipeline as a background async task. The frontend then polls `/api/status/{job_id}` every 1.5 seconds until the job is done. This async/polling pattern means the UI never freezes — it keeps updating while generation runs.

---

## 2. The Generator (The AI Pipeline)

**Location:** `architext/backend/core/` and `architext/scripts/`

This is the core academic contribution of the project. There are **two separate generators**, and they run in parallel when "Compare Both" mode is selected.

### Generator A — LLM (Competition)

**File:** `backend/core/llm_adapter.py`

This generator calls an external Large Language Model API (Groq, running Meta's `llama-3.3-70b` model). A carefully engineered prompt is sent to the LLM asking it to return structured JSON describing a floor plan — room names, types, sizes, and positions. The LLM handles the "understanding" of the natural language request and invents a reasonable spatial layout.

**Flow:**
```
Text prompt → Groq API (LLM) → JSON room data → Validation → IFC export
```

### Generator B — GNN (Primary Generator)

**Files:** `backend/core/real_gnn.py`, `architext/models/resplan_gnn/`

This is the trained machine learning model — our primary research contribution. It's a **Structural Graph Neural Network (CVAE-GNN)** trained on 17,000+ real residential floor plans from the ResPlan dataset.

**How it works:**
1. The text prompt is first parsed by a **T5 NLP model** (`backend/core/nlp_adapter.py`) into a structured spec: `{ bedrooms: 3, bathrooms: 2, living: 1, ... }`
2. This spec is fed into the GNN, which was trained to learn the spatial relationships between rooms (which rooms tend to be adjacent, typical room sizes, how layouts are structured)
3. The GNN outputs a room graph — a set of rooms with positions and dimensions

The GNN model is a **Conditional Variational Autoencoder** with graph convolutions. It was trained to generate diverse, realistic floor plan layouts conditioned on the room count specification. Training code is in `scripts/gnn_train_cvae.py`.

**Flow:**
```
Text prompt → T5 NLP → Room spec → CVAE-GNN → Room graph → Validation → IFC export
```

### The Shared Pipeline (4 Layers)

**File:** `backend/core/pipeline.py`

Both generators feed into the same shared post-processing pipeline:

| Layer | What it does |
|---|---|
| **Layer 1** | NLP parsing (GNN path only — LLM skips this) |
| **Layer 2** | Room generation (LLM or GNN) |
| **Layer 3** | Validation & fixing — enforces minimum room sizes, resolves overlapping rooms, ensures all rooms are connected |
| **Layer 4a** | Renders a 2D floor plan PNG using matplotlib |
| **Layer 4b** | Exports an IFC file using `ifcopenshell` |

### IFC Export

**File:** `backend/core/room_graph_to_ifc.py` and `scripts/generate_bim.py`

The room graph (list of rooms with x, y, width, height) is converted to an IFC4 file. Each room becomes:
- An `IfcSpace` (the room boundary, visible as 2D fill in BIM tools)
- 4 `IfcWall` entities (physical 3D walls, 200mm thick, 2700mm ceiling height)

This is what opens correctly in Blender (with BlenderBIM plugin) and Autodesk Revit.

---

## 3. The Frontend (Next.js)

**Location:** `architext/frontend/`

The frontend is a modern React web application built with Next.js 15 (App Router). It handles everything the user sees and interacts with.

### Key Pages

| Page | Route | Purpose |
|---|---|---|
| **Home** | `/` | Landing page with hero animation |
| **Studio** | `/studio` | Main generation interface |
| **Library** | `/floor-plans` | Browse and download saved plans |
| **Dashboard** | `/dashboard` | Your saved plans, upload new ones |
| **Plugins** | `/plugins` | Download the Blender addon |

### The Studio Page (Core Feature)

**Files:** `src/components/studio/StudioShell.tsx`, `src/hooks/usePromptWorkflow.ts`

This is where generation happens. The flow from the user's perspective:

1. User types a prompt
2. User selects mode: **Compare Both / Primary Only / Competition Only**
3. Clicks Generate → two jobs start in parallel (one LLM, one GNN)
4. Two 3D viewports show a particle animation while generating
5. When done, actual 3D models appear (walls + floor slabs rendered in Three.js)
6. User can toggle to see the 2D floor plan images
7. User can download the IFC files
8. User can save to library

**The `usePromptWorkflow` hook** manages all state: idle → building → ready → error. It starts both jobs simultaneously with `Promise.all()` and polls both until done.

### The 3D Viewer

**Files:** `src/components/studio/GeneratorCanvas.tsx`, `src/components/three/RoomFloorPlanModel.tsx`

Built with **React Three Fiber** (Three.js for React). Each room from the generation result is rendered as:
- A dark floor slab (thin box)
- 4 white walls (box geometry, 120mm thick, 2.7m high)
- Edge outlines for definition

The camera auto-fits to the size of the generated layout. Users can orbit, zoom, and pan.

### Save to Library

When saving, the frontend:
1. Fetches the 2D PNG from the backend's preview URL
2. Saves it to MongoDB as the primary file (so it's visible in the library)
3. Also stores the room JSON as `studioData` alongside it

### The Library Viewer

**File:** `src/app/dashboard/DashboardClient.tsx`

When you open a saved studio plan in the library:
- **Default view**: Shows the 2D floor plan image
- **"View in 3D" button**: Switches to a Three.js 3D preview rendered from the stored room data
- **"Download IFC" button**: Calls `/api/ifc-from-rooms` on the backend which regenerates and returns the IFC file instantly

### Authentication & Database

- **NextAuth** handles login (sessions stored in cookies)
- **MongoDB** stores user accounts and floor plan metadata
- **MongoDB GridFS** stores the actual files (PNG images, IFC files, uploaded PDFs, etc.)

### The Blender Addon

**Location:** `architext/blender_addon/`

A separate Blender plugin (downloadable from the Plugins page) that:
1. Adds an "ArchiText" panel to Blender's 3D viewport
2. User types a prompt inside Blender
3. Addon calls `scripts/run_pipeline.py` via subprocess using the project's Python venv
4. The pipeline generates and saves an IFC file
5. Addon imports the IFC directly into the Blender scene

---

## How the Three Components Connect

```
┌─────────────────────────────────────────────────────┐
│                   FRONTEND (Next.js)                 │
│  User types prompt → Studio page                    │
│  POST /api/generate (prompt + mode)                 │
└─────────────────────┬───────────────────────────────┘
                      │ HTTP (localhost:8000)
┌─────────────────────▼───────────────────────────────┐
│                  BACKEND (FastAPI)                   │
│  Creates Job → starts background task               │
│  Frontend polls GET /api/status/{job_id}            │
└─────────────────────┬───────────────────────────────┘
                      │ Python function call
┌─────────────────────▼───────────────────────────────┐
│              GENERATOR PIPELINE                      │
│  LLM path:  Groq API → rooms JSON                   │
│  GNN path:  T5 NLP → spec → CVAE-GNN → rooms        │
│  Both:      Validation → PNG preview → IFC export   │
└─────────────────────┬───────────────────────────────┘
                      │ Job done
         ┌────────────┴────────────┐
         ▼                         ▼
  GET /api/preview/{id}    GET /api/download/{id}
  (PNG image)              (IFC file)
         │                         │
         └────────────┬────────────┘
                      ▼
            Frontend renders:
            - 3D viewport (Three.js)
            - 2D floor plan (img tag)
            - Download IFC button
            - Save to Library → MongoDB
```

---

## Key Technical Choices (for Presentation)

- **Why two generators?** The GNN is our trained model (the research contribution). The LLM serves as a baseline comparison. Running both side-by-side lets us demonstrate what a purpose-trained spatial model does differently from a general-purpose LLM.
- **Why IFC?** IFC (Industry Foundation Classes) is the universal open standard for BIM. Any professional architecture tool opens it — this makes the output practically usable, not just a demo.
- **Why async/polling?** Generation takes 10–60 seconds. Async jobs mean the server handles many requests simultaneously and the UI stays responsive.
- **Why GNN + CVAE?** Floor plans are naturally graph-structured (rooms = nodes, adjacency = edges). The CVAE (Variational Autoencoder) adds controlled randomness — the same prompt produces different valid layouts each time, mimicking how human designers explore options.
