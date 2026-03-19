# ArchiText - Complete System Documentation

## Table of Contents
1. [Dataset Compression Impact](#1-dataset-compression-impact)
2. [Model Details](#2-model-details)
   - [T5 NLP Model](#t5-nlp-model-layer-1)
   - [GNN Layout Model](#gnn-layout-model)
3. [Blender Transformers Issue Solution](#3-blender-transformers-issue-solution)
4. [Layer 4: Overlap Fixing](#4-layer-4-overlap-fixing-quality-assurance)
5. [Layer-to-File Mapping](#5-layer-to-file-mapping)

---

## 1. Dataset Compression Impact

### What Was Removed from CubiCasa5k

The lite dataset (`cubicasa_train_lite.json`) was compressed from the full dataset to reduce file size:

| Data Type | Full Dataset | Lite Dataset | Impact |
|-----------|--------------|--------------|--------|
| **File Size** | 22.60 MB | 3.68 MB (16.3%) | Faster loading |
| **Samples** | 3,966 floor plans | 3,966 floor plans | Same count |

### Removed Data Fields

#### At Floor Plan Level:
| Field | What It Was | Impact of Removal |
|-------|-------------|-------------------|
| `adjacencies` | Room connectivity graph (18,369 total connections, avg 4.6 per plan) | **CRITICAL** - GNN cannot learn which rooms should be adjacent |
| `spec` | Bedroom/bathroom counts, kitchen/dining flags | Cannot condition on user requirements |
| `num_rooms` | Room count per floor plan | Minor loss |
| `sample_id` | CubiCasa5k source ID | Traceability lost |

#### At Room Level:
| Field | Example Value | Impact of Removal |
|-------|---------------|-------------------|
| `polygon` | 6 coordinate pairs defining exact shape | Cannot learn L-shaped/irregular rooms (45% of dataset) |
| `bbox` | [1474.05, 1137.48, 1712.49, 1478.05] | Lost bounding box reference |
| `center` | [1593.27, 1307.76] | Lost absolute positioning |
| `width` | 238.44 pixels | Lost absolute dimensions (range: 42-1298 px) |
| `height` | 340.57 pixels | Lost absolute dimensions (range: 34-1400 px) |
| `area` | 81,205.51 sq pixels | Lost area information (range: 3,818-872,958 sq px) |

### What Remained in Lite Dataset:
- `type`: Room type (kitchen, bedroom, etc.)
- `center_normalized`: Position as 0-1 value
- `width_normalized`: Width as 0-1 value
- `height_normalized`: Height as 0-1 value

### Root Cause of Mode Collapse

The GNN training suffered from **mode collapse** because:

1. **No adjacency signal**: Without explicit `adjacencies` data, edges were created as FULLY CONNECTED
   - Kitchen-bathroom edge = Kitchen-living edge = same weight
   - Model couldn't learn "kitchen should be near dining room"

2. **Only normalized values**: Lost room-type-specific sizing patterns
   - A 3m x 3m bathroom looks same as 6m x 6m bedroom when normalized

3. **Training result**:
   - Best val loss: 0.1138 (epoch 46)
   - Final val loss: 0.1145 (epoch 150)
   - Last 10 epochs variance: **0.000000** (completely stuck)
   - All rooms output nearly identical positions (~12.5, ~9.2 in 20m scale)

### Panel-Ready Answer:
> "The dataset compression was a trade-off between training speed and model capability. The lite version enables faster iteration but the adjacency information loss is the primary factor limiting the GNN's spatial learning. Future work would include adjacency-aware training with the full dataset."

---

## 2. Model Details

### T5 NLP Model (Layer 1)

**Purpose**: Convert natural language building descriptions to JSON specifications

#### Model Architecture
| Component | Value |
|-----------|-------|
| Base Model | `t5-small` from HuggingFace |
| Architecture | T5ForConditionalGeneration (Encoder-Decoder Transformer) |
| Model Type | Pre-trained, then **fine-tuned** on our dataset |
| d_model | 512 |
| d_ff | 2048 |
| d_kv | 64 |
| num_heads | 8 |
| num_encoder_layers | 6 |
| num_decoder_layers | 6 |
| vocab_size | 32,128 |
| max_position_embeddings | 512 |
| dropout_rate | 0.1 |

#### Model Files
| File | Size | Description |
|------|------|-------------|
| `model.safetensors` | 230.8 MB | Model weights |
| `config.json` | 1.5 KB | Architecture config |
| `spiece.model` | 773.1 KB | SentencePiece tokenizer |
| `tokenizer_config.json` | 21.3 KB | Tokenizer settings |

#### Training Configuration
| Parameter | Value |
|-----------|-------|
| num_train_epochs | 15 |
| per_device_train_batch_size | 4 |
| per_device_eval_batch_size | 4 |
| learning_rate | 5e-05 |
| weight_decay | 0.01 |
| warmup_steps | 50 |
| optimizer | AdamW (PyTorch) |
| lr_scheduler_type | linear |
| eval_strategy | steps (every 50) |
| save_strategy | steps (every 100) |
| load_best_model_at_end | True |
| metric_for_best_model | loss |
| gradient_accumulation_steps | 1 |
| max_grad_norm | 1.0 |
| seed | 42 |

#### Example Input/Output
```
Input:  "3 bedroom house with 2 bathrooms on 5 marla plot"
Output: {"bedrooms": 3, "bathrooms": 2, "kitchen": true, "living_room": true}
```

---

### GNN Layout Model

**Purpose**: Generate room layouts from JSON specifications (currently exhibits mode collapse)

#### Model Architecture (from trained checkpoint)

**Main GNN Model (LayoutGNN):**
```
room_embedding:     Embedding(10, 128)     - 1,280 params
conv_layers.0:      GCNConv(128, 128)      - 16,512 params
conv_layers.1:      GCNConv(128, 128)      - 16,512 params
conv_layers.2:      GCNConv(128, 128)      - 16,512 params
position_head:      Sequential             - 24,898 params
  - Linear(128, 128) + ReLU + Dropout(0.1)
  - Linear(128, 64) + ReLU
  - Linear(64, 2)
size_head:          Sequential             - 8,386 params
  - Linear(128, 64) + ReLU
  - Linear(64, 2)
                                    TOTAL: 84,100 params
```

**Refiner Network (LayoutRefiner):**
```
refiner:            Sequential             - 4,740 params
  - Linear(4, 64) + ReLU
  - Linear(64, 64) + ReLU
  - Linear(64, 4)
```

**Grand Total: 88,840 parameters**

#### Room Types Supported (10 types)
```python
['living_room', 'kitchen', 'bedroom', 'bathroom', 'dining_room',
 'study', 'garage', 'hallway', 'balcony', 'other']
```

#### Training History
| Metric | Value |
|--------|-------|
| Total Epochs | 150 |
| Initial train loss | 0.148535 |
| Initial val loss | 0.126604 |
| Best val loss | **0.113797** (epoch 46) |
| Final train loss | 0.115145 |
| Final val loss | 0.114471 |
| Last 10 epochs variance | 0.000000 (stuck) |

#### Loss Progression
| Epoch | Train Loss | Val Loss |
|-------|------------|----------|
| 1 | 0.1485 | 0.1266 |
| 26 | 0.1162 | 0.1141 |
| 46 | - | **0.1138** (best) |
| 51 | 0.1154 | 0.1142 |
| 76 | 0.1153 | 0.1144 |
| 101 | 0.1152 | 0.1145 |
| 126 | 0.1151 | 0.1145 |
| 150 | 0.1151 | 0.1145 |

#### Model Output (Mode Collapse Evidence)
All rooms output nearly identical values:
- Positions cluster around: (~12.5, ~9.2) in 20m scale
- Sizes cluster around: (~3.6, ~4.2) regardless of room type

---

## 3. Blender Transformers Issue Solution

### The Problem
Blender has its own bundled Python environment that **does not include** the `transformers` library (or PyTorch, IfcOpenShell, etc.). Importing these packages directly in Blender would fail.

### The Solution: Subprocess Architecture

The Blender addon uses **subprocess calls** to an external Python environment (the project's venv) that has all the required dependencies.

#### Key Implementation (from `blender_addon/architext/__init__.py`)

```python
# Lines 10-13 - Documentation explaining the approach:
"""
IMPORTANT: This add-on uses subprocess to call an external Python environment
that has all required dependencies (transformers, torch, ifcopenshell).
It does NOT import these packages directly into Blender's Python.
"""

# Lines 131-143 - Addon preferences for path configuration:
class ARCHITEXT_Preferences(AddonPreferences):
    python_path: StringProperty(
        name="Python Executable",
        description="Path to Python executable in your ArchiText venv",
        default="",
    )
    scripts_path: StringProperty(
        name="Scripts Path",
        description="Path to ArchiText scripts folder",
        default="",
    )
```

#### How It Works

1. **User configures paths** in addon preferences:
   - Python executable: `D:/Work/Uni/FYP/architext/venv/Scripts/python.exe`
   - Scripts path: `D:/Work/Uni/FYP/architext/scripts`

2. **Generate button triggers subprocess** (lines 375-386):
```python
process = subprocess.Popen(
    [prefs.python_path, run_script, props.prompt],
    stdout=stdout_file,
    stderr=stderr_file,
    cwd=project_root,
    startupinfo=startupinfo,
    creationflags=creationflags
)
```

3. **External Python runs the pipeline**:
   - Loads transformers, torch, ifcopenshell in the venv
   - Runs full NLP + layout + IFC generation
   - Writes IFC file to output folder

4. **Blender imports the result**:
   - Addon finds the generated IFC file
   - Uses BlenderBIM or native IFC import

#### Configuration Test (lines 265-292)
```python
# Test if transformers is available in the venv
result = subprocess.run(
    [prefs.python_path, "-c",
     "import transformers; print('transformers OK:', transformers.__version__)"],
    capture_output=True,
    text=True,
    timeout=30
)
```

### Panel-Ready Answer:
> "Blender's Python doesn't have ML libraries. We solved this by using subprocess to call our external Python venv that has all dependencies. The addon sends the user's text to the external pipeline, which generates the IFC file, then Blender imports the result."

---

## 4. Layer 4: Overlap Fixing (Quality Assurance)

### Location
`scripts/graph_layout_optimizer.py` - `_repair_overlaps()` method (lines 861-911)

### How Overlap Detection Works

```python
def _check_overlap(self, room1: RoomNode, room2: RoomNode, margin: float = 0.01) -> bool:
    """Check if two rooms overlap using AABB (Axis-Aligned Bounding Box)."""
    r1_x1, r1_y1 = room1.x, room1.y
    r1_x2, r1_y2 = room1.x + room1.width, room1.y + room1.height
    r2_x1, r2_y1 = room2.x, room2.y
    r2_x2, r2_y2 = room2.x + room2.width, room2.y + room2.height

    # Check for overlap (with small margin for floating point errors)
    overlap_x = r1_x1 < r2_x2 - margin and r1_x2 > r2_x1 + margin
    overlap_y = r1_y1 < r2_y2 - margin and r1_y2 > r2_y1 + margin

    return overlap_x and overlap_y
```

### How Overlap Repair Works (Iterative Push-Apart Algorithm)

```python
def _repair_overlaps(self, rooms: List[RoomNode], max_iterations: int = 50):
    """Detect and repair overlapping rooms by repositioning them."""
    for iteration in range(max_iterations):
        overlaps_found = False

        for i, room1 in enumerate(rooms):
            for room2 in rooms[i+1:]:
                if self._check_overlap(room1, room2):
                    overlaps_found = True
                    overlap_x, overlap_y = self._get_overlap_amount(room1, room2)

                    # Push rooms apart in direction of LEAST overlap
                    if overlap_x < overlap_y:
                        # Push horizontally
                        push = overlap_x / 2 + 0.1  # Extra margin
                        if room1.x < room2.x:
                            room1.x -= push
                            room2.x += push
                        else:
                            room1.x += push
                            room2.x -= push
                    else:
                        # Push vertically
                        push = overlap_y / 2 + 0.1
                        if room1.y < room2.y:
                            room1.y -= push
                            room2.y += push
                        else:
                            room1.y += push
                            room2.y -= push

        if not overlaps_found:
            break  # All overlaps resolved

    # Normalize: shift layout so minimum is at origin
    min_x = min(r.x for r in rooms)
    min_y = min(r.y for r in rooms)
    for room in rooms:
        room.x -= min_x
        room.y -= min_y
```

### Algorithm Summary

1. **Detection**: Uses AABB (Axis-Aligned Bounding Box) intersection test
2. **Direction**: Calculates overlap in both X and Y axes
3. **Resolution**: Pushes apart in the direction of **least overlap** (minimal displacement)
4. **Iteration**: Repeats up to 50 times until no overlaps remain
5. **Normalization**: Shifts entire layout so minimum coordinates are at origin

### Other Quality Checks

| Check | Method | Description |
|-------|--------|-------------|
| Overlap Detection | `_check_overlap()` | AABB intersection test |
| Overlap Amount | `_get_overlap_amount()` | Calculates overlap in X/Y |
| Overlap Repair | `_repair_overlaps()` | Iterative push-apart |
| Bounds Check | `_adjust_rooms_for_bounds()` | Scales rooms to fit plot |
| Position Jitter | `_add_position_jitter()` | Adds variety (0.3m) |

---

## 5. Layer-to-File Mapping

### Complete Pipeline Architecture

```
USER INPUT: "3 bedroom house with 2 bathrooms"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: NLP Text Processing                                │
│ File: scripts/inference_nlp.py                              │
│ Model: models/nlp_t5/final_model/                           │
│ Training: scripts/train_nlp_model.py                        │
│ Output: {"bedrooms": 3, "bathrooms": 2, ...}               │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Graph-Based Layout Generation                      │
│ File: scripts/graph_layout_optimizer.py                     │
│ Alternative: scripts/layout_optimizer_rules.py              │
│ GNN Model: models/layout_gnn/final_model.pt (not used)     │
│ Output: Room positions + connection graph                   │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: Quality Assurance                                  │
│ File: scripts/graph_layout_optimizer.py                     │
│ Methods: _repair_overlaps(), _check_overlap()              │
│ Output: Validated layout with no overlaps                   │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: IFC BIM Generation                                 │
│ File: scripts/generate_bim.py                               │
│ Library: ifcopenshell                                       │
│ Output: .ifc file (IFC2X3 format)                          │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: Visualization/Integration                          │
│ File: blender_addon/architext/__init__.py                   │
│ Output: 3D model in Blender/Revit                          │
└─────────────────────────────────────────────────────────────┘
```

### Detailed File Mapping

#### Layer 1: NLP Processing
| Purpose | File |
|---------|------|
| Inference (runtime) | `scripts/inference_nlp.py` |
| Training | `scripts/train_nlp_model.py` |
| Evaluation | `scripts/evaluate_nlp_model.py` |
| Model weights | `models/nlp_t5/final_model/model.safetensors` |
| Model config | `models/nlp_t5/final_model/config.json` |
| Tokenizer | `models/nlp_t5/final_model/spiece.model` |
| Training data | `data/nlp_training/` |

#### Layer 2: Layout Generation
| Purpose | File |
|---------|------|
| Graph-based optimizer (PRIMARY) | `scripts/graph_layout_optimizer.py` |
| Rule-based optimizer (FALLBACK) | `scripts/layout_optimizer_rules.py` |
| Area/plot parser | `scripts/area_parser.py` |
| GNN model (unused due to mode collapse) | `models/layout_gnn/final_model.pt` |
| GNN inference test | `scripts/gnn_to_ifc_pipeline.py` |
| Training data | `data/layout_training/cubicasa_train_lite.json` |

#### Layer 3: Quality Assurance
| Purpose | File | Function |
|---------|------|----------|
| Overlap detection | `scripts/graph_layout_optimizer.py` | `_check_overlap()` |
| Overlap repair | `scripts/graph_layout_optimizer.py` | `_repair_overlaps()` |
| Bounds enforcement | `scripts/graph_layout_optimizer.py` | `_adjust_rooms_for_bounds()` |
| Position validation | `scripts/graph_layout_optimizer.py` | `_find_best_position()` |

#### Layer 4: IFC Generation
| Purpose | File |
|---------|------|
| BIM generator class | `scripts/generate_bim.py` |
| IFC entity creation | `scripts/generate_bim.py` (uses ifcopenshell) |
| Output files | `output/*.ifc` |

#### Layer 5: Visualization
| Purpose | File |
|---------|------|
| Blender addon | `blender_addon/architext/__init__.py` |
| Quick generate (no NLP) | `scripts/quick_generate.py` |

### Pipeline Orchestration
| Purpose | File |
|---------|------|
| Main pipeline class | `scripts/text_to_bim.py` |
| CLI entry point | `scripts/run_pipeline.py` |

### Dataset Processing
| Purpose | File |
|---------|------|
| CubiCasa5k parser | `scripts/parse_cubicasa_dataset.py` |
| Create lite dataset | `scripts/create_lightweight_dataset.py` |
| Full dataset | `data/layout_training/cubicasa_train_full.json` |
| Lite dataset | `data/layout_training/cubicasa_train_lite.json` |

---

---

## 6. Data Formats at Each Layer

### Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER INPUT                                                                  │
│ Format: STRING (natural language)                                           │
│ Example: "3 bedroom house with 2 bathrooms on 5 marla plot"                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: NLP Processing (inference_nlp.py)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ INPUT FORMAT:  STRING                                                       │
│   "3 bedroom house with 2 bathrooms"                                       │
│                                                                             │
│ PROCESSING:                                                                 │
│   1. Tokenize text → PyTorch tensor [batch, seq_len]                       │
│   2. T5 encoder processes tokens → hidden states                           │
│   3. T5 decoder generates output tokens (beam search)                      │
│   4. Decode tokens → JSON string                                           │
│   5. Parse JSON string → Python dict                                       │
│                                                                             │
│ OUTPUT FORMAT: PYTHON DICT (JSON specification)                            │
│   {                                                                         │
│       "bedrooms": 3,                                                        │
│       "bathrooms": 2,                                                       │
│       "kitchen": true,                                                      │
│       "living_room": true,                                                  │
│       "dining_room": false,                                                 │
│       "study": false                                                        │
│   }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: Graph-Based Layout (graph_layout_optimizer.py)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ INPUT FORMAT:  PYTHON DICT (from Layer 1)                                  │
│   {"bedrooms": 3, "bathrooms": 2, "kitchen": true, ...}                    │
│                                                                             │
│ PROCESSING:                                                                 │
│   1. Create FloorPlanGraph object                                          │
│   2. Add RoomNode objects (id, type, width, height, zone)                  │
│   3. Add RoomEdge connections (room1_id, room2_id, connection_type)        │
│   4. Place rooms using constraint satisfaction                             │
│   5. Calculate positions (x, y coordinates)                                │
│                                                                             │
│ INTERNAL FORMAT: GRAPH STRUCTURE                                           │
│   FloorPlanGraph:                                                          │
│     nodes: Dict[str, RoomNode]                                             │
│       - RoomNode(id="living_room", room_type="living_room",                │
│                  width=5.5, height=4.5, x=0.0, y=0.0, zone=PUBLIC)        │
│     edges: List[RoomEdge]                                                  │
│       - RoomEdge(room1_id="living_room", room2_id="kitchen",               │
│                  connection_type=OPEN)                                     │
│                                                                             │
│ OUTPUT FORMAT: Tuple[FloorPlanGraph, List[RoomNode]]                       │
│   List of RoomNode objects with populated x, y positions                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: Quality Assurance (graph_layout_optimizer.py)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ INPUT FORMAT:  List[RoomNode] (from Layer 2)                               │
│   [RoomNode(id="living_room", x=0.0, y=0.0, width=5.5, height=4.5), ...]  │
│                                                                             │
│ PROCESSING:                                                                 │
│   1. _check_overlap() - AABB intersection test between room pairs          │
│   2. _get_overlap_amount() - Calculate overlap in X and Y                  │
│   3. _repair_overlaps() - Iterative push-apart (up to 50 iterations)       │
│   4. Normalize positions (shift so min x,y = 0)                            │
│                                                                             │
│ OUTPUT FORMAT: List[RoomNode] (same format, positions adjusted)            │
│   [RoomNode(id="living_room", x=0.0, y=0.0, width=5.5, height=4.5), ...]  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: IFC Generation (generate_bim.py)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ INPUT FORMAT:  List[RoomNode]                                              │
│   Each room has: id, room_type, width, height, x, y                        │
│                                                                             │
│ PROCESSING (for each room):                                                │
│   1. Create IfcSpace entity (room volume)                                  │
│      - IfcLocalPlacement at (x, y, 0)                                      │
│      - Name from room.id                                                   │
│                                                                             │
│   2. Create 4 IfcWallStandardCase entities (room boundaries)               │
│      For each wall:                                                        │
│      a. Calculate wall endpoints from room bounds                          │
│      b. Create IfcArbitraryClosedProfileDef (wall cross-section)          │
│         - Rectangle: length × thickness (0.2m)                             │
│      c. Create IfcExtrudedAreaSolid (3D wall geometry)                    │
│         - Extrude profile by wall height (2.7m)                           │
│      d. Create IfcShapeRepresentation → IfcProductDefinitionShape         │
│      e. Create IfcWallStandardCase with placement and shape               │
│      f. Create IfcRelContainedInSpatialStructure (assign to storey)       │
│                                                                             │
│ IFC HIERARCHY CREATED:                                                     │
│   IfcProject                                                               │
│     └─ IfcSite                                                             │
│          └─ IfcBuilding                                                    │
│               └─ IfcBuildingStorey                                         │
│                    ├─ IfcSpace (Living Room)                               │
│                    │    └─ IfcWallStandardCase × 4                         │
│                    ├─ IfcSpace (Kitchen)                                   │
│                    │    └─ IfcWallStandardCase × 4                         │
│                    └─ ... more rooms                                       │
│                                                                             │
│ OUTPUT FORMAT: .ifc FILE (IFC2X3 STEP format)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: Visualization (blender_addon/__init__.py)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ INPUT FORMAT:  .ifc FILE                                                   │
│   IFC2X3 STEP format (text-based, ISO 10303-21)                           │
│                                                                             │
│ PROCESSING:                                                                 │
│   Option A: BlenderBIM/Bonsai addon                                        │
│     bpy.ops.bim.load_project(filepath=ifc_path)                           │
│                                                                             │
│   Option B: Native Blender IFC import (4.0+)                               │
│     bpy.ops.import_scene.ifc(filepath=ifc_path)                           │
│                                                                             │
│ OUTPUT FORMAT: BLENDER MESH OBJECTS                                        │
│   - Mesh objects for each wall                                             │
│   - IFC metadata preserved as custom properties                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### IFC Conversion Details (Layer 4)

The IFC file is created using **IfcOpenShell** library. Here's exactly how room data becomes IFC:

#### Step 1: Create Project Hierarchy
```python
# IFC2X3 for Revit compatibility
self.ifc = ifcopenshell.file(schema="IFC2X3")

# Hierarchy: Project → Site → Building → Storey
self.project = self.ifc.createIfcProject(...)
self.site = self.ifc.createIfcSite(...)
self.building = self.ifc.createIfcBuilding(...)
self.storey = self.ifc.createIfcBuildingStorey(...)

# Link them with IfcRelAggregates
self.ifc.createIfcRelAggregates(..., self.project, [self.site])
self.ifc.createIfcRelAggregates(..., self.site, [self.building])
self.ifc.createIfcRelAggregates(..., self.building, [self.storey])
```

#### Step 2: Create Room Space
```python
# For each RoomNode from Layer 3:
space_placement = self.ifc.createIfcLocalPlacement(
    self.storey.ObjectPlacement,
    self.create_axis2placement_3d([room.x, room.y, 0.0])
)

space = self.ifc.createIfcSpace(
    guid,
    self.owner_history,
    room.id,           # Name: "living_room"
    ...,
    space_placement,
    "INTERNAL"         # Interior space
)
```

#### Step 3: Create Wall Geometry
```python
# For each wall (4 per room):
# 1. Create 2D profile (wall cross-section)
points = [
    IfcCartesianPoint((0.0, -0.1)),      # Half thickness below
    IfcCartesianPoint((length, -0.1)),
    IfcCartesianPoint((length, 0.1)),    # Half thickness above
    IfcCartesianPoint((0.0, 0.1)),
]
profile = IfcArbitraryClosedProfileDef("AREA", "WallProfile", polyline)

# 2. Extrude to 3D
extruded_solid = IfcExtrudedAreaSolid(
    profile,                    # 2D cross-section
    placement,                  # Origin
    IfcDirection((0,0,1)),     # Extrude direction (up)
    2.7                         # Height in meters
)

# 3. Wrap in representation
shape_rep = IfcShapeRepresentation(context, "Body", "SweptSolid", [extruded_solid])
product_shape = IfcProductDefinitionShape(None, None, [shape_rep])

# 4. Create wall entity
wall = IfcWallStandardCase(guid, owner_history, name, ..., placement, product_shape)
```

#### Step 4: Write to File
```python
self.ifc.write(str(output_path))  # Writes IFC2X3 STEP format
```

### IFC File Format (Sample)
```
ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('building.ifc','2024-12-11T10:30:00',('AI Generator'),('ArchiText'),'IfcOpenShell','Text-to-BIM AI','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCPROJECT('2XrR...',#2,'AI Generated House',$,$,$,$,(#3),#4);
#2=IFCOWNERHISTORY(#5,#6,$,.ADDED.,$,$,$,1733911800);
#3=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-5,#7,$);
...
#50=IFCWALLSTANDARDCASE('3Abc...',#2,'Living Room - South Wall',$,$,#51,#52,$);
#51=IFCLOCALPLACEMENT(#30,#53);
#52=IFCPRODUCTDEFINITIONSHAPE($,$,(#54));
#53=IFCAXIS2PLACEMENT3D(#55,#56,#57);
#54=IFCSHAPEREPRESENTATION(#3,'Body','SweptSolid',(#58));
#55=IFCCARTESIANPOINT((0.,0.,0.));
#56=IFCDIRECTION((0.,0.,1.));
#57=IFCDIRECTION((1.,0.,0.));
#58=IFCEXTRUDEDAREASOLID(#59,#60,#61,2.7);
...
ENDSEC;
END-ISO-10303-21;
```

### Summary Table: Format at Each Layer

| Layer | Input Format | Output Format | Key Data |
|-------|--------------|---------------|----------|
| **1 - NLP** | `str` (text) | `dict` (JSON) | `{"bedrooms": 3, "bathrooms": 2, ...}` |
| **2 - Layout** | `dict` | `List[RoomNode]` | `[RoomNode(x=0, y=0, w=5.5, h=4.5), ...]` |
| **3 - QA** | `List[RoomNode]` | `List[RoomNode]` | Same format, positions adjusted |
| **4 - IFC** | `List[RoomNode]` | `.ifc` file | IFC2X3 STEP format |
| **5 - Viz** | `.ifc` file | Blender meshes | 3D geometry |

---

## Quick Reference Card

### For Panel Demo:

1. **T5 Model**: Pre-trained HuggingFace model, fine-tuned 15 epochs on our data
2. **GNN Model**: 88,840 params, 150 epochs, mode collapse (not used in production)
3. **Blender Issue**: Solved with subprocess to external venv
4. **Overlap Fixing**: Iterative push-apart algorithm, max 50 iterations
5. **Output**: IFC2X3 format, compatible with Revit/Blender/FreeCAD

### Key Files to Remember:
- NLP: `inference_nlp.py`
- Layout: `graph_layout_optimizer.py`
- BIM: `generate_bim.py`
- Pipeline: `text_to_bim.py`
- Blender: `blender_addon/architext/__init__.py`
