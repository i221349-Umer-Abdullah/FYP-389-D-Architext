# ArchiText — Frontend Partner Brief

## What Is This Project?

ArchiText is an AI system that converts a **natural language description** of a building into a professional **IFC BIM file** (the standard format used in Revit, ArchiCAD, BlenderBIM, etc.).

The full pipeline runs on the backend and is already working. Your job is to build the web interface that lets users talk to it.

---

## How It Works (What the Backend Does)

```
User types:  "3 bedroom house, 2 baths, garden, 5 marla plot"
                        ↓  POST /api/generate
Backend AI:  Layer 1 → Layer 2 → Layer 3 → Layer 4
                        ↓
Output:      Room layout JSON  +  .ifc file
```

That's it. The backend handles all the AI. The frontend just needs to call the API and display the results.

---

## Backend API (Already Running on Port 8000)

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check if server is up |
| `POST` | `/api/generate` | Submit text → get `job_id` |
| `GET` | `/api/status/{job_id}` | Poll progress (0–100%) |
| `GET` | `/api/preview/{job_id}` | Fetch room list JSON for 2D draw |
| `GET` | `/api/download/{job_id}` | Download the `.ifc` file |
| — | `/docs` | Auto-generated Swagger docs (open in browser) |

**Generate request:**
```json
POST /api/generate
{ "text": "3 bedroom house with 2 bathrooms and garden" }
```

**Status response (when done):**
```json
{
  "status": "done",
  "progress": 100,
  "spec": { "unit_type": "house", "bedroom": 3, "net_area": 135 },
  "preview": {
    "room_count": 7,
    "total_area_m2": 94.4,
    "rooms": [
      { "name": "Living Room", "type": "living", "area_m2": 22.0, "x": 0, "y": 0, "width": 5.5, "height": 4.0 },
      { "name": "Bedroom 1",   "type": "bedroom", ... },
      ...
    ]
  },
  "ifc_ready": true
}
```

**CORS is open** — no proxy needed, call the API directly from the frontend.

---

## What the Frontend Needs

### Three main views / sections:

---

### 1. Prompt Input
- Large text area: *"Describe your house..."*
- A **Generate** button
- Optional: quick presets (e.g. "5 Marla House", "2BHK Apartment")
- Show a loading/progress indicator while polling (use the `progress` field, 0–100)

---

### 2. 2D Floorplan Preview
After generation completes, draw the room layout from the `/api/preview` JSON.

Each room has: `x`, `y`, `width`, `height` (all in **metres**).

- Draw each room as a **labelled rectangle** (room name + area inside)
- Use different fill colours per room type (bedroom = blue, bathroom = teal, living = warm grey, kitchen = orange, etc.)
- The canvas should auto-scale to fit the full layout
- Clicking a room could highlight it and show its details in a sidebar

**Suggested library:** [Konva.js](https://konvajs.org/) or [Fabric.js](https://fabricjs.com/) — both are canvas-based and easy for this use case.

---

### 3. 3D IFC Viewer
After the `.ifc` file is ready (`ifc_ready == true`), load and render it in-browser in 3D.

- Fetch the file from `/api/download/{job_id}`
- Load it into a 3D viewer

**Recommended library:** [`web-ifc-viewer`](https://github.com/IFCjs/web-ifc-viewer) — open source, renders IFC directly in browser via WebGL, no Revit or Blender needed.

```bash
npm install web-ifc-viewer
```

Basic usage:
```js
import { IfcViewerAPI } from 'web-ifc-viewer';
const viewer = new IfcViewerAPI({ container });
await viewer.IFC.loadIfcUrl('/api/download/' + jobId);
```

---

## Recommended Tech Stack

| Layer | Choice | Why |
|---|---|---|
| **Framework** | Next.js 14 (TypeScript) | SSR, easy routing, great DX |
| **UI** | shadcn/ui + Tailwind CSS | Clean, fast to build, good component set |
| **2D Canvas** | Konva.js | Simple rect drawing with labels |
| **3D IFC Viewer** | web-ifc-viewer | Renders IFC natively, no external BIM tool |
| **HTTP Client** | `fetch` or `axios` | Standard |
| **State** | Zustand | Lightweight, no boilerplate |

---

## Suggested Page Layout

```
┌─────────────────────────────────────────────────────────┐
│  ArchiText           [Header / Nav]                      │
├──────────────────────┬──────────────────────────────────┤
│                      │                                   │
│  [ Text Prompt ]     │     2D FLOORPLAN CANVAS           │
│                      │     (rooms drawn as rectangles)   │
│  [ Generate ]        │                                   │
│                      │                                   │
│  Progress: 70%  ████ ├──────────────────────────────────┤
│                      │                                   │
│  Spec summary:       │     3D IFC VIEWER                 │
│  • 3 bedrooms        │     (web-ifc-viewer WebGL)        │
│  • 135 m²            │                                   │
│  • house             │                                   │
│                      │                                   │
│  [ Download IFC ]    │                                   │
└──────────────────────┴──────────────────────────────────┘
```

---

## What You Don't Need to Worry About

- The AI models — already running on the backend
- IFC generation — backend handles it
- Any Python code — it's all done

---

## Starting Point

```bash
git clone https://github.com/i221349-Umer-Abdullah/FYP-389-D-Architext.git
git checkout iteration3

# Backend is already running (or start it with):
cd architext
python -m venv venv && venv\Scripts\activate
pip install fastapi uvicorn
uvicorn backend.main:app --reload --port 8000

# Open http://localhost:8000/docs to explore the API
```

> **Note:** The current AI model is a placeholder. The real model will finish training and be swapped in — the API contract will stay exactly the same. Build against the current API and everything will work when we upgrade.
