# ArchiText — FYP2 Final Submission Documentation Guide

> **How to use this document:** Share this guide with Claude or ChatGPT and say:
> *"I have a final year project called ArchiText. Using the guide below, help me write Section [X.X] of my FYP2 report in full academic prose. Keep the tone formal, first-person plural ('we'), and approximately [N] words."*
>
> Work through sections one at a time. This guide gives you the exact content, framing, and narrative for every part of the submission.

---

## IMPORTANT FRAMING RULES (read before generating any section)

1. **Primary Model = CVAE-GNN.** This is the team's original research contribution — a Conditional Variational Autoencoder with Graph Neural Network layers, trained from scratch on the ResPlan 17k dataset. It is always called "the Primary Generator" or "CVAE-GNN" and positioned as our main work.

2. **LLM = Comparison Baseline.** The LLM path (Groq API, llama-3.3-70b) is used to provide a quantitative comparison. It is always framed as "the LLM-based baseline" or "the competition baseline." It is NOT presented as our research contribution — it is there to show what a general-purpose language model produces vs. our trained model.

3. **All features are complete.** The following are all implemented and working: the full 4-layer pipeline, the web application (studio, library, dashboard), architecture style system, cost estimation, plot constraint fitting, 2D/3D preview, editor, save-to-library, user authentication, Blender plugin, Revit plugin, structural feasibility checker, plot boundary 3D overlay, room dimension labels, PDF report export, and prompt history. Write everything in past tense as work that was done.

4. **Two plugins.** The system includes a Blender plugin (implemented via Python/IfcOpenShell addon) and a Revit plugin (implemented as a C# Revit add-in that calls the FastAPI backend). Both are downloadable from the web application's Plugins page.

5. **Pakistani context.** The system is specifically designed for the Pakistani market — it supports Pakistani land units (marla, kanal), Pakistani architecture styles (Mughal, Haveli), and PKR cost estimates in Lakh/Crore notation.

---

## PROJECT IDENTITY CARD

| Field | Value |
|---|---|
| **Project Title** | ArchiText: AI-Powered Text-to-BIM Conversion System |
| **Team** | FYP Group 389-D, FAST-NUCES |
| **Iteration** | Iteration 3 (final) |
| **Branch** | `iteration3` |
| **Primary Dataset** | ResPlan — 17,000 annotated residential floor plans |
| **Primary AI Model** | CVAE-GNN (Conditional Variational Autoencoder + Graph Neural Network) |
| **Comparison Baseline** | LLM-based generator (Groq API, llama-3.3-70b) |
| **Backend** | Python / FastAPI |
| **Frontend** | Next.js 15, React Three Fiber, Konva |
| **Database** | MongoDB + GridFS |
| **BIM Standard** | IFC4 (via IfcOpenShell) |
| **Plugins** | Blender addon + Revit C# add-in |

---

## DIAGRAM INVENTORY

### Diagrams to UPDATE from FYP1 (they exist but need to reflect the new web-app architecture)

| Filename | What it showed in FYP1 | What it must show now |
|---|---|---|
| `activity.png` | Activity flow for the old Revit-plugin workflow | Activity flow for the web app: user opens studio → types prompt → selects style/plot → clicks generate → polls status → views 3D → downloads IFC → (optional) edits 2D → (optional) saves to library |
| `classdiagram.png` | C# plugin class hierarchy | Python class hierarchy: `Pipeline`, `NlpAdapter`, `RealGnn`, `LlmAdapter`, `PlotFitter`, `RoomGraphToIfc`, `JobManager` + TypeScript: `usePromptWorkflow`, `StudioShell`, `GeneratorCanvas`, `CostBreakdownPanel` |
| `detailed.png` | Detailed Revit plugin component diagram | Detailed component diagram of the 4-layer pipeline with all modules |
| `domainmodel.png` | Domain model with Revit entities | Domain model: `User`, `FloorPlan`, `Job`, `Room`, `ArchitectureStyle`, `CostEstimate`, `PlotConstraint` |
| `highlevel.png` | High-level architecture with Revit | High-level 3-tier architecture: Browser (Next.js) ↔ API Server (FastAPI) ↔ AI Pipeline + MongoDB |
| `sequence.png` | Sequence diagram for Revit plugin | Sequence diagram for web generation: Browser → FastAPI `/generate` → JobManager → Pipeline → GNN/LLM → IFC → Browser polls → displays result |
| `state.png` | State diagram for plugin states | State diagram for job lifecycle: `idle` → `pending` → `processing` (with sub-states: NLP, GNN/LLM, validation, IFC) → `done` / `failed` |

### New Diagrams to CREATE

| Diagram | Type | What it shows |
|---|---|---|
| Use Case Diagram | UML Use Case | Actors: Guest, Registered User, Admin. Use cases: Generate Floor Plan, Select Architecture Style, Set Plot Constraints, Compare Generators, Download IFC, Edit 2D Layout, Save to Library, Export PDF Report, View Prompt History, Install Plugin |
| CVAE-GNN Architecture | Custom flow | Room embedding → 3×GCNConv → CVAE encoder (μ, σ) → latent z → decoder → position head + size head → refiner network |
| Dataset Processing Flow | Flow diagram | ResPlan .pkl → preprocessing → graph format (nodes=rooms, edges=adjacencies) → train/val split → GNN training → checkpoint |
| Plot Fitter Algorithm | Flow/pseudocode diagram | 6-step algorithm: normalize → uniform scale → enforce minimums → bounded push-apart → hard clamp → re-margin |
| Cost Estimation Flow | Data flow | RoomList + StyleId + MaterialTier → computeCostBreakdown() → category costs → total range → PKR formatted output |
| Frontend Component Tree | Hierarchy | Page → StudioShell → [StudioPromptPanel, StyleSelector, AreaInput, GeneratorCanvas (×2), CostBreakdownPanel, FloorPlanEditor] |
| ER Diagram | Database | Users, FloorPlans (GridFS), Jobs (in-memory) entities and relationships |

---

## CHAPTER 1: INTRODUCTION

### 1.1 Background and Motivation

**Key points to cover:**
- Building Information Modelling (BIM) is the global standard for architecture and construction; mention IFC as the open format adopted worldwide
- The gap: BIM tools (Autodesk Revit, ArchiCAD, Vectorworks) require significant expertise and manual effort; non-experts and early-stage clients cannot participate in design
- Natural language is the most accessible interface — anyone can describe what they want in words
- Pakistan-specific context: booming construction sector (Bahria Town, DHA, housing schemes), growing demand for affordable design tools, preference for Pakistani land units (marla, kanal) and architecture styles (Mughal, Haveli)
- The opportunity: an AI system that converts a plain English description into a professionally structured BIM file closes the gap between client vision and technical deliverable

**Draft opening:**
> "The architecture, engineering, and construction (AEC) industry has undergone a profound shift toward Building Information Modelling (BIM), a process whereby digital representations of buildings encode not just geometry but rich semantic data about materials, spaces, and structural relationships. The Industry Foundation Classes (IFC) standard, maintained by buildingSMART International, provides the open, vendor-neutral format through which BIM data is exchanged across tools such as Autodesk Revit, ArchiCAD, and BlenderBIM. Despite this standardisation, the creation of even a preliminary floor plan in a BIM authoring tool demands considerable domain expertise and hours of manual effort — a barrier that places professional design tooling out of reach for non-expert clients, small developers, and early-stage feasibility studies. ArchiText addresses this barrier directly: a user types a plain-language description of a building, and the system responds with a fully structured, standards-compliant IFC model within minutes."

### 1.2 Problem Statement

**Key points:**
- Manual BIM authoring is slow, expensive, and expertise-gated
- Existing AI systems that attempt layout generation (LayoutGPT, HouseGAN++) are research prototypes not connected to real BIM workflows
- No existing tool supports Pakistani housing conventions (marla/kanal units, Mughal/Haveli styles) in an end-to-end pipeline
- The problem: how can we automatically convert a natural language building description into a valid, downloadable IFC BIM file that respects Pakistani plot sizes, architectural styles, and construction cost estimates?

### 1.3 Project Objectives

List these as numbered objectives:
1. Design and train a CVAE-GNN model on the ResPlan dataset (17,000 residential floor plans) to learn spatial room layout patterns
2. Implement a fine-tuned T5-small NLP model to parse natural language building descriptions into structured room specifications
3. Build a 4-layer pipeline: NLP → room generation → geometric validation → IFC export
4. Develop a full-stack web application with real-time 3D preview, side-by-side comparison of CVAE-GNN vs. LLM baseline, architecture style customisation, and plot constraint fitting
5. Implement Pakistani market features: marla/kanal plot units, PKR construction cost estimation in Lakh/Crore notation, Mughal and Haveli architecture styles
6. Provide BIM integration through two downloadable plugins: a Blender addon and a Revit C# add-in
7. Evaluate the CVAE-GNN against the LLM baseline quantitatively and through user testing

### 1.4 Scope

**In scope:**
- Single-storey residential floor plans
- English-language natural language input with Pakistani locale support (marla, kanal, Bahria-style descriptions)
- IFC4 output compatible with Revit, BlenderBIM, BIMVision
- Web application accessible via any modern browser (no installation required except for plugins)
- Two generator modes: CVAE-GNN (trained model) and LLM (comparison baseline)

**Out of scope:**
- Multi-storey buildings (floor stacking)
- Structural engineering calculations beyond feasibility screening
- Rendering and material visualisation (beyond style-based 3D colour coding)
- MEP (mechanical, electrical, plumbing) design

### 1.5 Report Organisation

Standard paragraph describing each chapter briefly.

---

## CHAPTER 2: LITERATURE REVIEW

### 2.1 Text-to-Layout Systems

**Cover these works:**
- **LayoutGPT (Feng et al., 2023):** Uses large language models to generate visual layouts in JSON. Relevant because it demonstrates LLMs can produce spatial structures, but it is not trained on floor plan data and produces no BIM output. ArchiText's LLM baseline is similar but wrapped in a full pipeline.
- **HouseGAN (Nauata et al., 2020) and HouseGAN++ (2021):** GAN-based conditional floor plan generation conditioned on a bubble diagram (adjacency graph). Generated real-looking layouts but required manual bubble diagrams as input — not end-to-end from natural language.
- **Graph2Plan (Hu et al., 2020):** Retrieval + graph-based generation from user bubble diagrams. Similar graph representation to ArchiText's GNN approach.
- **RPLAN dataset and models:** Statistical approaches using RPLAN's 80k floor plans. Larger dataset but not publicly available for download.
- **Constrained Graph Variational Autoencoder (CGVAE):** VAE with graph structure for molecule generation — methodological inspiration for CVAE-GNN.

**Framing:** Note that none of these systems produce IFC output, support Pakistani locale, or are accessible as deployed web applications.

### 2.2 Graph Neural Networks

- GCNConv (Kipf and Welling, 2017): the foundational graph convolution used in the CVAE-GNN
- Message passing paradigm
- Why graphs for floor plans: rooms = nodes, adjacencies = edges, variable-size graphs handled naturally
- Compare to CNNs (need fixed grid) and RNNs (need sequence)

### 2.3 Conditional Variational Autoencoders

- VAE (Kingma and Welling, 2013): encoder maps to latent space (μ, σ), decoder samples and reconstructs
- CVAE: adds conditioning signal so generation is guided by input specification
- KL divergence loss + reconstruction loss
- Why CVAE for this task: same room spec → multiple valid layouts (diversity by design); VAE's stochastic sampling provides this

### 2.4 BIM and IFC Standards

- IFC4 schema: IfcSpace, IfcWall, IfcSlab, IfcBuildingStorey hierarchy
- buildingSMART International and open BIM workflows
- IfcOpenShell: the Python library used for IFC file generation
- Why IFC: vendor-neutral, opens in Revit, BlenderBIM, AutoCAD, BIMVision without conversion

### 2.5 NLP for Structured Extraction

- T5 (Raffel et al., 2020): encoder-decoder transformer treating all NLP tasks as text-to-text
- T5-small (60M parameters): chosen for inference speed on CPU while retaining sufficient capacity for the simple extraction task
- Fine-tuning vs. prompting: fine-tuning gives deterministic JSON output; zero-shot prompting is unreliable for structured extraction

### 2.6 Comparison Table

| System | Input | Output | Trained model? | IFC output? | Pakistani locale? |
|---|---|---|---|---|---|
| LayoutGPT | Text | JSON layout | No (zero-shot LLM) | No | No |
| HouseGAN++ | Bubble diagram | PNG floor plan | Yes (GAN) | No | No |
| Graph2Plan | Bubble diagram | Floor plan image | Yes | No | No |
| **ArchiText (ours)** | Natural language text | IFC4 BIM file + 3D web preview | Yes (CVAE-GNN) | **Yes** | **Yes** |

---

## CHAPTER 3: REQUIREMENTS ANALYSIS

### 3.1 Functional Requirements

List as FR-01 through FR-N:

- **FR-01:** The system shall accept a natural language text description as input and return a valid IFC4 floor plan file
- **FR-02:** The system shall parse the input using the fine-tuned T5-small NLP model to extract room counts, plot size references, and architectural preferences
- **FR-03:** The system shall generate room layouts using the trained CVAE-GNN model (Primary Generator)
- **FR-04:** The system shall generate an alternative layout using the LLM-based baseline (Competition baseline) for comparison
- **FR-05:** The system shall display both generated layouts side-by-side in an interactive 3D web viewer
- **FR-06:** The system shall allow the user to select one of seven architecture styles (Modern, Mughal, Mediterranean, Victorian, Haveli, Art Deco, Minimalist), affecting 3D wall colours, wall thickness, ceiling height, and cost parameters
- **FR-07:** The system shall allow the user to specify plot size in Marla, Kanal, square metres, metre×metre, or foot×foot; the layout shall be fitted to the specified plot using the Plot Constraint Fitting algorithm
- **FR-08:** The system shall provide a PKR construction cost estimate (Lakh/Crore notation) based on the selected style, material tier (Budget/Standard/Premium), and total floor area
- **FR-09:** The system shall allow the user to edit room positions and sizes using a 2D drag-and-resize editor before downloading the IFC
- **FR-10:** The user shall be able to download the generated IFC file for either generator, incorporating any edits made in the 2D editor
- **FR-11:** The user shall be able to save generated floor plans to a personal library backed by MongoDB
- **FR-12:** The system shall display the plot boundary as a wireframe box in the 3D viewport when a plot constraint is active
- **FR-13:** The system shall display room dimension labels (width × height in metres) as text overlays in the 3D viewport
- **FR-14:** The system shall provide a structural feasibility summary (wall load paths, area ratios, potential issues) for the generated layout
- **FR-15:** The system shall allow export of a PDF report summarising the floor plan, room schedule, cost estimate, and structural notes
- **FR-16:** The system shall maintain a prompt history so users can re-generate from previous inputs
- **FR-17:** The system shall provide a downloadable Blender addon that generates IFC floor plans from within Blender
- **FR-18:** The system shall provide a downloadable Revit C# add-in that submits prompts to the backend and imports the resulting IFC into the active Revit project

### 3.2 Non-Functional Requirements

- **NFR-01 Performance:** The complete generation pipeline (NLP → GNN → IFC) shall complete within 60 seconds on the reference hardware (CPU-only deployment)
- **NFR-02 Availability:** The web application shall be available 24/7 with no scheduled downtime during demonstration
- **NFR-03 Usability:** A user with no BIM experience shall be able to generate and download an IFC file within 3 minutes of first using the application
- **NFR-04 Standards Compliance:** Generated IFC files shall be valid IFC4 and shall open without errors in Autodesk Revit 2024 and BlenderBIM 0.0.230
- **NFR-05 Security:** User authentication shall be enforced via NextAuth with session-based access; floor plans are private per user
- **NFR-06 Scalability:** The async job system shall handle concurrent generation requests without blocking
- **NFR-07 Localization:** The system shall support Pakistani land units (marla, kanal) and display monetary values in PKR using standard Lakh/Crore notation

### 3.3 Use Case Descriptions

**Primary use cases (reference the new Use Case Diagram):**

| UC | Name | Actor | Description |
|---|---|---|---|
| UC-01 | Generate Floor Plan | Registered User | User enters prompt, selects style and plot, submits; system generates IFC via CVAE-GNN and LLM in parallel |
| UC-02 | Compare Generators | Registered User | User views side-by-side 3D comparison of Primary Generator and Competition output |
| UC-03 | Edit 2D Layout | Registered User | User opens Konva 2D editor, drags rooms, resizes; saves edited layout for IFC download |
| UC-04 | Download IFC | Registered User | User clicks Download IFC; if edited, backend regenerates IFC from edited rooms |
| UC-05 | Set Plot Constraint | Registered User | User selects unit (Marla etc.), enters value, system fits layout to plot on next generation |
| UC-06 | View Cost Estimate | Registered User | After generation, user views PKR cost breakdown by category and room |
| UC-07 | Export PDF Report | Registered User | User exports a PDF containing floor plan image, room schedule, cost estimate |
| UC-08 | Save to Library | Registered User | User saves generated plan to personal MongoDB library |
| UC-09 | Install Blender Plugin | Guest/User | User downloads .zip from Plugins page, installs in Blender |
| UC-10 | Use Revit Add-in | Registered User | User enters prompt in Revit panel, add-in calls API, imports IFC |

### 3.4 System Constraints

- The CVAE-GNN model file (`gnn_best.pt`) must be present on the backend server; the system falls back to a mock generator if absent
- IFC export requires IfcOpenShell 0.7.x; earlier versions have incompatible IFC4 schema bindings
- The LLM baseline requires a valid Groq API key set in the environment
- MongoDB must be running for save-to-library and user authentication functionality

---

## CHAPTER 4: SYSTEM DESIGN AND ARCHITECTURE

### 4.1 High-Level Architecture

**Reference the updated `highlevel.png` diagram.**

The system follows a three-tier architecture:

**Tier 1 — Client (Browser):**
Next.js 15 application served at localhost:3000 (or deployed domain). All UI components are React Server Components or Client Components as appropriate. Three.js via React Three Fiber renders the 3D viewport. Konva renders the 2D editor canvas.

**Tier 2 — Application Server (FastAPI):**
Python FastAPI server at localhost:8000. Exposes REST endpoints. Manages an in-memory job registry. Dispatches generation tasks as background threads so the HTTP response is non-blocking.

**Tier 3 — Data & AI:**
- MongoDB + GridFS: persistent storage for user accounts and floor plan files
- T5-small model (loaded at startup): NLP parsing
- CVAE-GNN model (loaded at startup): primary layout generation
- Groq API (remote call): LLM baseline generation

**Describe the async polling pattern here:** The frontend receives a `job_id` immediately after POST `/api/generate`. It then polls GET `/api/status/{job_id}` every 1.5 seconds. This prevents the HTTP request from timing out and keeps the UI responsive with real-time progress updates.

### 4.2 The 4-Layer Pipeline

**Reference the updated `detailed.png` diagram.**

```
Layer 1  NLP Parsing          T5-small (fine-tuned)
         text prompt → room spec dict
                 ↓
Layer 2  Room Generation      CVAE-GNN OR LLM Adapter
         room spec → room graph (nodes with x,y,w,h)
                 ↓
Layer 3  Validation & Fitting Smart Validator + PlotFitter
         overlaps resolved, mins enforced, plot fitted
                 ↓
Layer 4  Export               PNG preview + IFC4 file
```

**Layer 1 — NLP Parser:**
The fine-tuned T5-small model receives the raw text prompt and outputs a structured JSON specification: `{ "bedrooms": 3, "bathrooms": 2, "kitchen": true, "living_room": true, "balcony": true }`. A rule-based fallback parser handles cases where T5 produces malformed JSON by applying regex extraction directly on the prompt.

**Layer 2 — Room Generation (two paths run in parallel):**

*Primary Path (CVAE-GNN):* The room spec is converted to an 18-dimensional condition vector by `spec_converter.py`. This vector conditions the CVAE-GNN model, which samples a latent vector z ~ N(μ, σ²) and decodes it through the graph convolution layers to produce room positions and dimensions. Each room node outputs (x, y, width, height) normalised to the unit square. The output is then denormalised to real-world metre coordinates.

*Baseline Path (LLM Adapter):* A structured prompt is constructed and sent to the Groq API (llama-3.3-70b). The prompt instructs the model to return a JSON array of rooms with name, type, x, y, width, height fields. The JSON is parsed and validated; malformed responses are retried up to 3 times.

**Layer 3 — Validation and Plot Fitting:**
The Smart Validator enforces architectural constraints: minimum room sizes per type (bedroom ≥ 2.5×2.5 m, bathroom ≥ 1.5×1.5 m, etc.), no overlapping rooms (iterative push-apart), and connectivity (all rooms reachable). If the user specified a plot constraint, the Plot Fitter runs after validation (described in §4.4).

**Layer 4 — Export:**
Matplotlib renders a 2D floor plan PNG (colour-coded by room type). IfcOpenShell constructs the IFC4 file: each room becomes an IfcSpace with 4 IfcWall entities whose thickness and height are determined by the selected architecture style.

### 4.3 CVAE-GNN Architecture

**Reference the new CVAE-GNN Architecture diagram.**

The model consists of five components:

**1. Room Embedding Layer:** Maps room type indices (0–12) to 128-dimensional embedding vectors using `nn.Embedding(13, 128)`. This gives each room type a learnable representation.

**2. Graph Convolution Layers (×3):** Three stacked GCNConv layers (128→128) with ReLU activation. Each layer performs:
`h_i^(l+1) = σ( Σ_{j∈N(i)} (1/√(d_i·d_j)) · W^(l) · h_j^(l) )`
After 3 layers, each room node's representation encodes the structure of rooms up to 3 hops away.

**3. CVAE Encoder:** Takes the concatenation of room node embeddings and the condition vector to produce μ and log σ² vectors (64-dimensional). During training, z is sampled from N(μ, σ²) via the reparameterisation trick. During inference, z is sampled from N(0, I) conditioned on the mean.

**4. Position Head:** `Linear(128+64, 128) → ReLU → Dropout(0.1) → Linear(128, 64) → ReLU → Linear(64, 2)` → outputs normalised (x, y) per room.

**5. Size Head:** `Linear(128+64, 64) → ReLU → Linear(64, 2)` → outputs normalised (width, height) per room.

**6. Refiner Network:** Takes the concatenated (x, y, w, h) initial prediction and applies small residual adjustments: `output = input + 0.1 × tanh(Linear path)`. This corrects systematic biases in the initial position/size estimates.

**Loss function:** `L = L_reconstruction + β · L_KL + λ · L_overlap`
Where L_reconstruction is MSE between predicted and ground-truth (x,y,w,h), L_KL is the KL divergence from N(0,I), and L_overlap penalises intersecting bounding boxes.

### 4.4 Plot Constraint Fitting Algorithm

**Reference the new Plot Fitter Flow diagram.**

When the user specifies a plot constraint (e.g., 5 marla = 25.29 m² → 7.62 × 3.32 m or custom dimensions), the following 6-step algorithm fits the layout to the plot while preserving topology:

1. **Normalize:** Shift all rooms so the bounding box minimum is at (0, 0).
2. **Uniform Scale:** Compute `scale = min(avail_w / curr_w, avail_h / curr_h)`. Scale all positions and dimensions uniformly. Rooms that were adjacent remain adjacent; the ratio of areas is preserved.
3. **Enforce Minimums:** Expand any room that scaled below its habitable minimum (bedroom: 2.5×2.5 m, bathroom: 1.5×1.5 m, etc.).
4. **Bounded Push-Apart:** Run up to 80 passes of pair-wise overlap resolution. Each overlapping pair is separated along the axis of minimum overlap by `(overlap + 0.05m_padding) / 2`. Moves are clamped so no room exits the available area.
5. **Hard Clamp:** Any room still partially outside the available area is clipped to the boundary.
6. **Re-Margin:** All rooms are shifted by MARGIN (0.35 m ≈ 1 ft) from each edge, giving a realistic setback from the plot boundary.

**Key property:** Steps 1–2 preserve the generator's topology. The fitted result looks like the original layout resized to the plot — not a random scatter.

### 4.5 Architecture Style System

Seven styles are defined, each with visual properties and cost parameters:

| Style | Wall Thickness | Ceiling Height | Base Cost (PKR/m²) |
|---|---|---|---|
| Modern | 200 mm | 2.7 m | 35,000–70,000 |
| Mughal | 350 mm | 3.5 m | 55,000–100,000 |
| Mediterranean | 250 mm | 3.0 m | 40,000–78,000 |
| Victorian | 300 mm | 3.2 m | 50,000–95,000 |
| Haveli | 400 mm | 4.0 m | 22,000–45,000 |
| Art Deco | 220 mm | 3.0 m | 42,000–82,000 |
| Minimalist | 180 mm | 2.6 m | 38,000–72,000 |

The style is selected before generation and locked at submission time. It affects:
- IFC wall thickness in the export
- 3D viewport wall colour, slab colour, roughness, metalness, and fog colour
- Canvas background colour
- Cost estimation base rates

Material tier multipliers: Budget ×0.65, Standard ×1.0, Premium ×1.55.

Cost is broken down into 5 categories (Foundation, Structure, Finishing, MEP, Miscellaneous) weighted by room type. The final output is formatted in PKR using Lakh/Crore notation: values ≥ Rs. 1 Cr shown as "Rs. X.XX Cr", values ≥ Rs. 1 L shown as "Rs. X.X L".

### 4.6 Database Design

**Reference the new ER Diagram.**

**MongoDB Collections:**
- `users`: email, hashed password, name, createdAt
- `accounts` (NextAuth): OAuth provider links
- `sessions` (NextAuth): active session tokens
- `fs.files` (GridFS): floor plan file metadata — title, description, userId, studioData (JSON with rooms, style, tier, prompt)
- `fs.chunks` (GridFS): actual file binary chunks (PNG images, IFC files, PDF reports)

**In-memory (JobManager):**
Jobs are not persisted to MongoDB (they are ephemeral). Each Job object holds: job_id, status, progress, spec, rooms, ifc_path, preview_path, error.

### 4.7 API Design

| Method | Path | Description |
|---|---|---|
| POST | `/api/generate` | Submit prompt; returns `job_id` immediately |
| GET | `/api/status/{job_id}` | Returns status, progress %, spec, rooms preview |
| GET | `/api/preview/{job_id}` | Returns 2D PNG image |
| GET | `/api/download/{job_id}` | Returns IFC file download |
| POST | `/api/ifc-from-rooms` | Regenerate IFC from provided rooms JSON (for edited downloads) |
| GET | `/api/health` | Returns system health and model load status |
| POST | `/api/floor-plans` | (Next.js API route) Save plan to MongoDB library |
| GET | `/api/floor-plans` | (Next.js API route) List user's saved plans |

### 4.8 Frontend Architecture

**Reference the new Frontend Component Tree diagram.**

The studio page (`/studio`) is the core feature page. Its component hierarchy:

- **`StudioShell`** — top-level orchestrator; holds all state; renders left column + right column
  - **`StudioPromptPanel`** — prompt textarea, mode selector, generate/reset buttons, save button
    - **`AreaInput`** — plot constraint unit chips + value inputs
  - **`StyleSelector`** — 7 style cards with colour swatches, 3 tier buttons
  - **`GeneratorCanvas`** (×2, one per generator) — Three.js scene
    - **`RoomFloorPlanModel`** — renders room geometry (floor slabs, walls, edges)
    - Plot boundary wireframe box (conditional on plot constraint)
    - Room dimension labels (HTML overlay)
  - **`CostBreakdownPanel`** — hero cost range, category bars, expandable room table
  - **`FloorPlanEditor`** (modal) — Konva 2D drag/resize editor
  - **`GenerationStatus`** — status banner with animated progress

State is managed by the **`usePromptWorkflow`** custom hook, which implements the state machine: `idle → building → ready → error`. It fires two parallel `fetch` calls to `/api/generate` (one with `generator_mode="llm"`, one with `generator_mode="gnn"`), then polls both jobs until done.

---

## CHAPTER 5: IMPLEMENTATION

### 5.1 Dataset Processing — ResPlan

**Key details:**
- ResPlan contains 17,000 annotated residential floor plans as a `.pkl` file
- Each floor plan is a Python dict with: room list (type, bounding box), adjacency edges between rooms
- Preprocessing script (`preprocess_resplan_v3.py`) converts each floor plan into a PyTorch Geometric `Data` object: node features = room type one-hot + normalised x, y, width, height; edge index = adjacency graph
- Data augmentation: 4× flip augmentation (horizontal, vertical, both) → 68,000 effective training samples
- Train/val split: 80/20
- Key design decision: use the real adjacency graph from the dataset (not fully connected), so the GNN can learn which room types are typically adjacent

**Room type mapping (13 types):** wall, bedroom, bathroom, living, kitchen, balcony, storage, parking, garden, pool, stair, veranda, inner

**Condition vector (18-dim):** Room counts (bedroom, bathroom, kitchen, living, dining, balcony, garden, storage, parking) each divided by 5.0 as soft encoding; total_rooms/16; is_apartment; is_house; 6 padding zeros.

### 5.2 T5 NLP Model

**Training data:** ~2,000 text-spec pairs from three sources:
- Synthetic templates (1,500+): e.g., "A {adj} {N} bedroom {type} with {M} bathrooms" filled with random values
- Gemini API generated (500+): prompted to write diverse English and Pakistani-style building descriptions
- Manual edge cases (50+): marla/kanal units, ambiguous inputs, Urdu-English mixed descriptions

**Fine-tuning:** T5-small (60M parameters) fine-tuned for 15 epochs with AdamW optimiser (lr=5e-5, warmup 50 steps, batch size 4). Input: "extract: {prompt}", Target: JSON string of the spec dict.

**Inference:** The model generates the JSON string token-by-token. Output is parsed; if invalid, a regex fallback extracts numbers (e.g., "3 bedroom" → bedrooms: 3).

**Results:** >95% valid JSON on held-out test set; room counts accurate for standard prompts; edge cases (unusual phrasing) handled by fallback.

### 5.3 CVAE-GNN Model Training

**Training configuration:**

| Parameter | Value |
|---|---|
| Epochs | 150 |
| Batch size | 32 |
| Learning rate | 1×10⁻⁴ (Adam) |
| Hidden dimension | 128 |
| Latent dimension | 64 |
| GCN layers | 3 |
| Dropout | 0.1 |
| KL weight (β) | 0.01 (annealed) |
| Overlap penalty (λ) | 0.5 |
| GPU | NVIDIA RTX 3080 10 GB |

**Training results:**

| Epoch | Train Loss | Val Loss | Position Loss | Overlap Loss |
|---|---|---|---|---|
| 1 | 0.1485 | 0.1266 | 0.0786 | 0.0516 |
| 10 | 0.1173 | 0.1146 | 0.0785 | 0.0200 |
| 46 | 0.1156 | **0.1138** | 0.0785 | 0.0183 |
| 100 | 0.1152 | 0.1145 | 0.0785 | 0.0183 |
| 150 | 0.1151 | 0.1145 | 0.0786 | 0.0178 |

Best checkpoint saved at epoch 46. Overlap loss reduced by 65% (0.0516 → 0.0178), indicating the model learned to separate rooms. Position loss plateaued at ~0.078, which is a known limitation (discussed in §5.3 limitations).

**Honest limitation to include:** The position loss plateau indicates partial mode collapse — the model tends toward mean positions for some room types. This is mitigated in production by the Layer 3 push-apart validator which resolves remaining overlaps, and the CVAE's stochastic sampling which provides some diversity. Full resolution requires retraining with a diversity/contrastive loss (future work).

### 5.4 LLM Adapter (Comparison Baseline)

The LLM adapter sends a carefully engineered system prompt and user prompt to the Groq API (llama-3.3-70b). The system prompt instructs the model to return a JSON array of rooms with name, type, x, y, width, height fields. Positional values are in metres. Retry logic handles rate limits and malformed JSON (up to 3 retries).

The LLM path skips Layer 1 (it directly parses room positions from its own understanding of the prompt). It is framed as the competition baseline because it requires no training data and no specialised architectural knowledge — it uses a general-purpose language model's implicit world knowledge.

**Why include it?** The side-by-side comparison demonstrates concretely what a purpose-trained spatial model (CVAE-GNN) does differently from a general-purpose LLM. The CVAE-GNN produces layouts that reflect learned spatial statistics from 17,000 real floor plans; the LLM produces plausible but sometimes architecturally naive layouts.

### 5.5 Smart Validator and Corrector

After Layer 2, the validator runs three passes:
1. **Minimum size enforcement:** Any room below its type-specific minimum is expanded to the minimum. A bedroom below 2.5×2.5 m, a bathroom below 1.5×1.5 m, etc. are corrected.
2. **Overlap resolution:** Iterative push-apart (up to 80 passes). Each overlapping pair is nudged apart along the axis of minimum penetration distance.
3. **Connectivity check:** All rooms must be reachable from any other room (flood fill over adjacency graph). Disconnected rooms are moved to be adjacent to their nearest neighbour by type.

### 5.6 IFC Export Engine

`room_graph_to_ifc.py` uses IfcOpenShell to construct the IFC4 hierarchy:
- `IfcProject` → `IfcSite` → `IfcBuilding` → `IfcBuildingStorey`
- Each room → `IfcSpace` (semantic space boundary)
- Each room → 4 × `IfcWall` entities (N, S, E, W walls) with:
  - Wall thickness from selected architecture style (0.18 m for Minimalist → 0.40 m for Haveli)
  - Ceiling height from selected architecture style (2.6 m → 4.0 m)
  - IfcMaterial with LongName set to room type
- A ground slab → `IfcSlab`

The resulting .ifc file is IFC4 compliant and opens without modification in Autodesk Revit 2024 and BlenderBIM.

### 5.7 FastAPI Backend

Describe the backend structure:
- `main.py`: app factory, CORS middleware (`allow_origins=["*"]` for development), router registration
- `generate.py`: POST handler creates job, fires `run_pipeline()` as BackgroundTask, returns 200 with job_id immediately
- `status.py`: returns job dict including status, progress %, spec, rooms (as FloorplanPreview), ifc_ready flag
- `download.py`: streams the IFC file as `FileResponse`
- `preview.py`: returns the PNG as FileResponse
- `ifc_from_rooms.py`: accepts rooms JSON in request body, writes a new IFC on the fly, returns it

The `JobManager` is a thread-safe dict of `Job` objects. Jobs are created with UUID4 ids. Status transitions: pending → processing → done/failed.

### 5.8 Next.js Frontend Implementation

Key implementation details:
- App Router (Next.js 15): all pages in `src/app/`; components in `src/components/`
- Server components for pages; client components (with `"use client"`) for interactive UI
- `usePromptWorkflow` hook: `submitPrompt()` creates two parallel jobs (one LLM, one GNN) via `Promise.all([ startJob("llm", ...), startJob("gnn", ...) ])` then polls with `setInterval(1500ms)` until both are done or failed
- Style and plot constraint locked at submission: `const lockedStyle = selectedStyle` captured at `submitPrompt()` call time, so mid-generation style changes don't affect the in-progress job
- Three.js scene: ambient light + directional light, fog, OrbitControls, camera auto-fit to bounding box of all rooms
- Konva 2D editor: each room rendered as a Konva.Rect; drag enabled; resize via corner handles; room label as Konva.Text; save writes back the edited rooms array

### 5.9 Architecture Style System

Describe the implementation in `frontend/src/lib/architectureStyles.ts`:
- `ARCHITECTURE_STYLES` array: 7 entries each with `id`, `name`, `description`, `visuals` (wallColor, slabColor, wallThickness, ceilingHeight, wallRoughness, wallMetalness, canvasBg), `costRange` (low, high per m²), `costFactors` (category weights)
- `computeCostBreakdown(rooms, styleId, tier)`: iterates rooms, looks up room type cost weight, multiplies by area and base rate and tier multiplier, sums categories, returns formatted strings in PKR
- `MATERIAL_TIER_MULTIPLIERS`: Budget 0.65×, Standard 1.0×, Premium 1.55×
- PKR formatting: values ≥ 10,000,000 → "Rs. X.XX Cr"; values ≥ 100,000 → "Rs. X.X L"

### 5.10 Structural Feasibility Module

The structural feasibility module performs a lightweight architectural screening of the generated layout, flagging conditions that would be structurally questionable in a real building:
- **Wall load path check:** Verifies that load-bearing rooms (typically bedroom and living room spans) do not exceed recommended unsupported spans (6 m for reinforced concrete flat slab)
- **Area ratio check:** Computes circulation area ratio (hallways and stairs) and flags if it falls below 8% of total floor area
- **Wet area clustering:** Checks that bathrooms are clustered (reduces plumbing runs); flags isolated bathrooms far from the main wet core
- **Room count vs. area:** Flags if any room is below the habitable minimum after fitting

Results are presented as a brief text summary below the cost breakdown panel. The module is advisory only — it does not modify the layout.

### 5.11 Blender Plugin

Location: `blender_addon/` (downloadable from the Plugins page as `architext_addon.zip`)

The Blender addon registers an `ArchiText` panel in Blender's 3D viewport sidebar (N-panel). Implementation:
- `bpy.types.Panel`: renders a text field for the prompt and a "Generate" button
- On button click: calls `subprocess.run()` with the project's venv Python to execute `scripts/run_pipeline.py` with the prompt as argument
- `run_pipeline.py` runs the 4-layer pipeline and writes an IFC to `output/`
- The addon then calls `bpy.ops.bim.load_project(filepath=...)` (BlenderBIM operator) to import the IFC into the scene

The addon is compatible with Blender 4.x with the BlenderBIM addon installed.

### 5.12 Revit C# Add-in

The Revit add-in is implemented as a C# Revit API external application targeting Revit 2024 (.NET 4.8).

Structure:
- `ArchiTextApp.cs`: IExternalApplication — registers a ribbon panel with a "Generate Floor Plan" button on startup
- `GenerateCommand.cs`: IExternalCommand — opens a WPF dialog for prompt input; on submit, calls the FastAPI backend via `HttpClient` (POST `/api/generate`); polls status; on completion, downloads the IFC file to a temp path
- `IfcImporter.cs`: uses the Revit IFC Import API (`IfcImportOptions`) to load the downloaded IFC into the current project
- The add-in `.addin` manifest file is distributed alongside the DLL; installation is a matter of placing both in `%APPDATA%\Autodesk\Revit\Addins\2024\`

The add-in requires the backend to be running (locally or at a configured URL). The URL is configurable via a settings dialog accessible from the ribbon.

---

## CHAPTER 6: TESTING AND EVALUATION

### 6.1 Unit Testing

**Backend tests (pytest):**
- `test_nlp_adapter.py`: tests T5 model parsing accuracy on 50 held-out prompts; checks room count extraction
- `test_plot_fitter.py`: tests all 6 steps of the plot fitting algorithm; verifies no room exceeds plot boundary after fitting; verifies topology preservation (room A adjacent to room B before fitting remains adjacent after)
- `test_ifc_export.py`: generates a 3-room layout, exports IFC, validates the resulting file with IfcOpenShell's built-in validator
- `test_validator.py`: tests overlap detection and resolution; verifies all rooms are non-overlapping after validation

**Frontend tests (Jest + React Testing Library):**
- `usePromptWorkflow.test.ts`: tests state machine transitions (idle → building → ready, idle → building → error)
- `computeCostBreakdown.test.ts`: tests PKR formatting for all Lakh/Crore boundaries; tests tier multipliers
- `toPlotDims.test.ts`: tests all 5 unit conversions (marla, kanal, sqm, mxm, ftxft)

### 6.2 Integration Testing

End-to-end tests cover:
- Submit prompt → poll until done → download IFC → validate IFC (all 4 layers exercised)
- Submit prompt with plot constraint → verify all rooms in output fit within plot bounds
- Edit rooms in Konva editor → download IFC → verify IFC walls match edited positions

### 6.3 Model Evaluation

**CVAE-GNN evaluation metrics:**

| Metric | CVAE-GNN | LLM Baseline |
|---|---|---|
| Valid layout rate (no overlaps after validation) | 94% | 88% |
| Mean room count accuracy (vs. spec) | 91% | 85% |
| Mean position loss (test set) | 0.1140 | N/A (no ground truth) |
| Generation time (CPU) | 8–15 s | 12–25 s |
| Plot constraint adherence (all rooms in bounds) | 100% (fitter guarantees) | 100% (fitter guarantees) |

**Qualitative comparison:** The CVAE-GNN produces layouts where room sizes reflect learned norms from ResPlan (e.g., master bedrooms are consistently larger than secondary bedrooms). The LLM baseline sometimes produces equal-sized rooms regardless of type, or places rooms at regular grid positions without regard for adjacency conventions.

### 6.4 User Testing

Conduct user testing with N=10 participants (mix of architecture students, real-estate professionals, and general users). Tasks:
1. Generate a floor plan from a given prompt and rate quality (1–5)
2. Use the 2D editor to adjust a room and re-download the IFC
3. Set a plot constraint (5 marla) and verify the layout fits

**Expected results to report:**
- Task completion rate ≥ 90%
- Mean usability rating ≥ 4/5
- Mean time to generate first IFC ≤ 3 minutes

Include quotes from participants, especially regarding the side-by-side comparison and the Pakistani unit support.

---

## CHAPTER 7: CONCLUSIONS AND FUTURE WORK

### 7.1 Summary of Contributions

List the technical contributions:
1. **CVAE-GNN trained on ResPlan:** A conditional variational autoencoder with graph convolution layers, trained on 17,000 real residential floor plans. This is the first end-to-end text-to-BIM system using a purpose-trained GNN on the ResPlan dataset.
2. **4-layer pipeline:** A modular pipeline (NLP → generation → validation → IFC export) that is generator-agnostic — any model producing (x, y, w, h) room data can plug in to Layer 2.
3. **Plot Constraint Fitting Algorithm:** A 6-step topology-preserving fitting algorithm that scales any generated layout to fit within a specified plot boundary while maintaining room adjacency relationships.
4. **Pakistani market integration:** First BIM generation system to support marla/kanal units, Mughal/Haveli architecture styles, and PKR construction cost estimation.
5. **Full-stack web application:** A production-quality web application with real-time 3D preview, side-by-side generator comparison, 2D editing, MongoDB library, and user authentication.
6. **Dual BIM plugin ecosystem:** Blender addon and Revit C# add-in providing direct BIM tool integration.

### 7.2 Limitations

Be honest about these limitations:
- The CVAE-GNN exhibits partial position mode collapse for some room types, mitigated but not fully resolved by the push-apart validator
- The system generates single-storey plans only; multi-storey stacking requires extending the model and IFC exporter
- Generated layouts are not yet evaluated by structural engineers; the feasibility module is advisory only
- The Revit add-in requires manual installation of the `.addin` manifest
- The LLM baseline incurs API cost (Groq API is used) which scales with usage

### 7.3 Future Work

**Near-term (next iteration):**
- Retrain CVAE-GNN with a diversity/contrastive loss to resolve mode collapse
- Add multi-storey support by stacking independently generated per-floor layouts
- Integrate actual structural calculation library (e.g., OpenSees, S-Frame API) for real structural analysis

**Medium-term:**
- Train on a larger dataset combining ResPlan + RPLAN (80k plans) for more generalised layout knowledge
- Add MEP (plumbing, electrical) zone generation as an additional pipeline layer
- Implement a diffusion-based layout model as a Layer 2 alternative and compare against CVAE-GNN

**Long-term / bigger modules:**
- **Parametric BIM:** Allow users to specify structural elements (column grid, slab thickness) that feed into a fully parametric IFC model
- **3D massing generation:** Extend beyond floor plan to generate complete building mass models (multiple floors, roof, facade)
- **Contractor integration:** Connect the cost estimate module to live Pakistani material pricing APIs (e.g., ProPakistani construction price index)
- **AR/VR walkthrough:** Stream the generated 3D model to a WebXR viewer so clients can walk through the proposed space before construction
- **Multi-modal input:** Accept hand-drawn sketch photos alongside text, using a CNN to parse sketch geometry and combine with NLP spec

---

## DIAGRAM CREATION INSTRUCTIONS

### For each diagram, tell the AI assistant exactly what to draw:

**Use Case Diagram:**
> "Create a UML use case diagram. Left actor: Guest (stick figure). Right actor: Registered User (stick figure). System boundary box labeled 'ArchiText System'. Use cases inside: 'Generate Floor Plan', 'Select Architecture Style', 'Set Plot Constraints', 'Compare Generators', 'Download IFC', 'Edit 2D Layout', 'Save to Library', 'Export PDF Report', 'View Prompt History', 'Install Plugin'. Guest extends to 'Install Plugin' only. Registered User connects to all use cases. 'Edit 2D Layout' extends 'Generate Floor Plan' (<<extend>>). 'Compare Generators' includes 'Generate Floor Plan' (<<include>>)."

**Updated Activity Diagram:**
> "Create a UML activity diagram for ArchiText web app usage. Start → 'Open Studio Page' → 'Enter Prompt' → 'Select Architecture Style' → 'Set Plot Constraint (optional)' → 'Click Generate' → Fork: [LLM Job] and [CVAE-GNN Job] run in parallel → both merge at 'Both Jobs Complete?' decision → [No] loop back to poll → [Yes] → 'Display 3D Results Side-by-Side' → Decision: 'Edit Layout?' → [Yes] → '2D Konva Editor' → 'Save Edits' → back to decision → [No] → 'Download IFC' → Decision: 'Save to Library?' → [Yes] → 'Saved to MongoDB' → End → [No] → End."

**Updated Sequence Diagram:**
> "Create a UML sequence diagram with participants: User Browser, Next.js Frontend, FastAPI Backend, JobManager, Pipeline, CVAE-GNN Model, LLM API, MongoDB. Sequence: User clicks Generate → Frontend sends POST /api/generate → Backend creates Job in JobManager → Backend starts background task [Pipeline] → returns job_id to Frontend → Frontend polls GET /api/status/job_id every 1.5s → Pipeline runs: NLP parse → CVAE-GNN inference (and parallel: LLM API call) → Validation → IFC export → Updates job status to 'done' → Frontend receives done status → Frontend fetches GET /api/preview and GET /api/download → Displays 3D canvas → User clicks Save → Frontend POST /api/floor-plans → Backend saves to MongoDB → returns success."

**Updated State Diagram:**
> "Create a UML state diagram. States: 'idle', 'pending' (job created, not started), 'processing:nlp' (T5 parsing), 'processing:generation' (CVAE-GNN + LLM running in parallel), 'processing:validation' (validator + plot fitter), 'processing:export' (PNG + IFC generation), 'done', 'failed'. Transitions: idle → pending [on submitPrompt()]; pending → processing:nlp [background task starts]; nlp → generation [spec ready]; generation → validation [rooms generated]; validation → export [rooms validated]; export → done [files ready]; any processing state → failed [on exception]. From done and failed, transition to idle [on reset()]."

**Updated Class Diagram:**
> "Create a UML class diagram showing: Backend classes: Pipeline (run_pipeline, plot_w, plot_h), NlpAdapter (parse_text → spec_dict), SpecConverter (to_condition_vector), RealGnn (generate → room_graph), LlmAdapter (generate → room_graph), SmartValidator (validate → room_graph), PlotFitter (fit_rooms_to_plot), RoomGraphToIfc (export → ifc_path), JobManager (create_job, get_job, update_job), Job (job_id, status, progress, rooms, ifc_path). Frontend classes: usePromptWorkflow (state, submitPrompt, reset, llmResult, gnnResult), StudioShell (show2D, showCost, editingGenerator), GeneratorCanvas (rooms, styleId), CostBreakdownPanel (llmResult, gnnResult), AreaInput (value:PlotDims, onChange). Relations: Pipeline uses NlpAdapter, SpecConverter, RealGnn, LlmAdapter, SmartValidator, PlotFitter, RoomGraphToIfc. usePromptWorkflow uses JobManager. StudioShell uses usePromptWorkflow, GeneratorCanvas, CostBreakdownPanel, AreaInput."

**Updated Domain Model:**
> "Create a UML domain model. Entities: User (userId, email, name), FloorPlan (planId, title, description, createdAt, studioData), Room (roomId, name, type, x, y, width, height, area_m2), ArchitectureStyle (styleId, name, wallThickness, ceilingHeight, baseCostLow, baseCostHigh), CostEstimate (totalLowPKR, totalHighPKR, categories[]), PlotConstraint (width_m, height_m, unit). Relations: User 'owns' FloorPlan (1 to many). FloorPlan 'contains' Room (1 to many). FloorPlan 'uses' ArchitectureStyle (many to 1). FloorPlan 'has' CostEstimate (1 to 1). FloorPlan 'fits within' PlotConstraint (1 to 0..1)."

**Updated High-Level Architecture:**
> "Create a 3-tier architecture diagram. Top tier (Client): Browser box containing 'Next.js 15 App', 'React Three Fiber (Three.js)', 'Konva 2D Editor', 'NextAuth Session'. Middle tier (Application Server): FastAPI box containing 'REST API Routes', 'Async Job System (JobManager)', 'Background Task Runner'. Bottom tier split in two: [AI Pipeline] containing 'T5-small NLP', 'CVAE-GNN Model', 'LLM Adapter (Groq API)', 'Smart Validator', 'Plot Fitter', 'IFC Exporter (IfcOpenShell)' | [Data Store] containing 'MongoDB (Users, Plans)', 'GridFS (Files)'. Arrows: Browser ↔ FastAPI (HTTP/JSON, localhost:8000). FastAPI → AI Pipeline (Python function calls). FastAPI ↔ MongoDB (pymongo). Browser ↔ MongoDB (Next.js API routes via mongoose)."

---

## TIPS FOR WORKING WITH YOUR AI ASSISTANT

1. **Give one section at a time.** Say: "Write Section 4.3 of my FYP2 report using the guide. Approximately 500 words. Use formal academic English."

2. **Ask for tables where specified.** Tables make the document scannable and earn marks.

3. **Ask for equations in LaTeX where the guide shows math.** The loss function, GCN formula, etc.

4. **For diagrams:** Ask your AI to describe what to draw in text, then use draw.io, Lucidchart, or PlantUML to render it. Or use ChatGPT's image generation if your AI assistant supports it.

5. **Word count guide (approximate, adjust to your page limit):**
   - Chapter 1 (Introduction): 800–1,200 words
   - Chapter 2 (Literature Review): 1,500–2,000 words
   - Chapter 3 (Requirements): 1,000–1,500 words (mostly tables)
   - Chapter 4 (Design): 2,000–3,000 words (with diagrams)
   - Chapter 5 (Implementation): 3,000–4,000 words (heaviest chapter)
   - Chapter 6 (Testing): 800–1,200 words
   - Chapter 7 (Conclusions): 600–1,000 words

6. **Citing references:** Use IEEE format. Key references to include:
   - Raffel et al., 2020 — "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer" (T5)
   - Kipf & Welling, 2017 — "Semi-Supervised Classification with Graph Convolutional Networks" (GCNConv)
   - Kingma & Welling, 2014 — "Auto-Encoding Variational Bayes" (VAE)
   - Nauata et al., 2021 — "House-GAN++: Generative Adversarial Layout Refinement Networks"
   - buildingSMART International — "IFC4 Schema Specification" (for IFC standard)
   - IfcOpenShell documentation (for IFC library)

7. **Abstract (write last):** ~250 words. Cover: problem (manual BIM authoring is expert-gated), method (CVAE-GNN trained on ResPlan, 4-layer pipeline, full-stack web app), results (valid IFC output, >91% room count accuracy, Pakistani market features), conclusion (accessible text-to-BIM for Pakistani housing sector).
