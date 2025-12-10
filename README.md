# ArchiText - Text-to-BIM Conversion System

> **Final Year Project**: An AI-powered multi-layer deep learning system that converts natural language building descriptions into Industry Foundation Classes (IFC) BIM models.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)
![IFC](https://img.shields.io/badge/IFC-2X3-green.svg)
![Blender](https://img.shields.io/badge/Blender-4.0+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Overview

ArchiText is an end-to-end AI pipeline that transforms natural language descriptions of buildings into valid IFC (Industry Foundation Classes) files that can be opened in professional BIM software like Autodesk Revit, BlenderBIM/Bonsai, ArchiCAD, and others.

### Key Features

- **Natural Language Understanding**: Fine-tuned T5 transformer model trained on architectural terminology
- **Deep Learning Layout Generation**: Graph Neural Network (GNN) trained on CubiCasa5k dataset for intelligent floor plan generation
- **Multi-Layer Architecture**: 5-layer processing pipeline with dedicated quality assurance stages
- **Bounded Area Generation**: Supports Pakistani/Indian land units (marla, kanal) alongside metric and imperial
- **Multi-Platform Support**: Generated IFC files compatible with Revit, BlenderBIM, FreeCAD, ArchiCAD
- **Blender Add-on**: Direct integration with Blender for real-time 3D visualization (v1.1.0)

## System Architecture

ArchiText implements a sophisticated **multi-layer deep learning architecture** where each layer refines and validates the output of the previous layer:

```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                         ARCHITEXT SYSTEM ARCHITECTURE                               ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                     ║
║   INPUT: "Modern 3 bedroom house with 2 bathrooms on 5 marla plot"                 ║
║                                        │                                            ║
║                                        ▼                                            ║
║   ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║   │  LAYER 1: Natural Language Processing Engine                                │  ║
║   │  ═══════════════════════════════════════════════════════════════════════   │  ║
║   │  Model: Fine-tuned T5-small Transformer                                     │  ║
║   │  Training: Custom architectural dataset (RTX 3080 10GB)                     │  ║
║   │  Function: Extracts structured room specification from natural language     │  ║
║   │  Output: {"bedrooms": 3, "bathrooms": 2, "kitchen": true, ...}             │  ║
║   └─────────────────────────────────────────────────────────────────────────────┘  ║
║                                        │                                            ║
║                                        ▼                                            ║
║   ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║   │  LAYER 2: Graph Neural Network Layout Generator     [PRIMARY GENERATOR]     │  ║
║   │  ═══════════════════════════════════════════════════════════════════════   │  ║
║   │  Model: GNN trained on CubiCasa5k floor plan dataset (~5000 layouts)        │  ║
║   │  Training: RTX 3080 10GB, learned spatial relationships from real plans     │  ║
║   │  Architecture: Graph-based with rooms as nodes, adjacencies as edges        │  ║
║   │  Capabilities:                                                              │  ║
║   │    • Generates diverse, realistic floor plan layouts                        │  ║
║   │    • Learned architectural patterns from thousands of real floor plans      │  ║
║   │    • Produces room positions, dimensions, and connection graphs             │  ║
║   │  Output: Initial floor plan layout with spatial relationships               │  ║
║   └─────────────────────────────────────────────────────────────────────────────┘  ║
║                                        │                                            ║
║                                        ▼                                            ║
║   ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║   │  LAYER 3: Rule-Based Layout Optimizer                                       │  ║
║   │  ═══════════════════════════════════════════════════════════════════════   │  ║
║   │  Function: Refines GNN output using architectural constraint rules          │  ║
║   │  Optimizations:                                                             │  ║
║   │    • Zone-based organization (public/private/service zones)                 │  ║
║   │    • Architectural adjacency enforcement (kitchen→dining, en-suite→master) │  ║
║   │    • Compactness optimization for efficient space utilization               │  ║
║   │    • Wall-sharing guarantee between connected rooms                         │  ║
║   │  Output: Architecturally-refined room positions                             │  ║
║   └─────────────────────────────────────────────────────────────────────────────┘  ║
║                                        │                                            ║
║                                        ▼                                            ║
║   ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║   │  LAYER 4: Quality Assurance System                                          │  ║
║   │  ═══════════════════════════════════════════════════════════════════════   │  ║
║   │  Overlap Detection: AABB intersection testing for room collisions           │  ║
║   │  Overlap Repair: Iterative push-apart algorithm (max 50 iterations)         │  ║
║   │  Boundary Enforcement: Plot size constraint validation (marla/kanal/sqm)    │  ║
║   │  Connectivity Validation: Graph-based check ensuring all rooms accessible   │  ║
║   │  Output: Validated, collision-free floor plan                               │  ║
║   └─────────────────────────────────────────────────────────────────────────────┘  ║
║                                        │                                            ║
║                                        ▼                                            ║
║   ┌─────────────────────────────────────────────────────────────────────────────┐  ║
║   │  LAYER 5: IFC BIM Generation Engine                                         │  ║
║   │  ═══════════════════════════════════════════════════════════════════════   │  ║
║   │  Standard: IFC 2x3 (Industry Foundation Classes)                            │  ║
║   │  Hierarchy: IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey         │  ║
║   │  Elements: IfcWallStandardCase, IfcSpace, IfcDoor                           │  ║
║   │  Compatibility: Revit, ArchiCAD, BlenderBIM/Bonsai, FreeCAD                │  ║
║   └─────────────────────────────────────────────────────────────────────────────┘  ║
║                                        │                                            ║
║                                        ▼                                            ║
║   OUTPUT: industry_standard_building.ifc                                           ║
║                                                                                     ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

## Core Modules

| Module | Description | Key Technology |
|--------|-------------|----------------|
| `inference_nlp.py` | NLP text-to-spec conversion | Fine-tuned T5 Transformer |
| `graph_layout_optimizer.py` | **Primary layout generation** | GNN trained on CubiCasa5k |
| `layout_optimizer_rules.py` | Rule-based refinement | Constraint satisfaction |
| `generate_bim.py` | IFC file generation | IfcOpenShell |
| `area_parser.py` | Multi-unit area parsing | Regex + unit conversion |
| `text_to_bim.py` | Pipeline orchestration | Multi-layer coordination |

## Installation

### Prerequisites

- Python 3.10 or higher
- CUDA-compatible GPU (RTX 3080 10GB recommended for training)
- Blender 4.0+ with Bonsai add-on (for visualization)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/architext.git
   cd architext
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download pre-trained models**

   The trained model checkpoints should be placed in:
   ```
   models/nlp_t5/final_model/       # T5 NLP model
   models/layout_gnn/final_model/   # GNN layout model
   ```

## Usage

### Command Line Interface

```bash
# Generate BIM from text description
python scripts/run_pipeline.py "Modern 3 bedroom house with 2 bathrooms and spacious living room"

# Generate with bounded area (5 marla plot)
python scripts/run_pipeline.py "3 bedroom house on 5 marla plot with 2 bathrooms"

# Quick generation (bypasses NLP, direct JSON spec)
python scripts/quick_generate.py '{"bedrooms": 3, "bathrooms": 2, "kitchen": true}'
```

### Python API

```python
from scripts.text_to_bim import TextToBIMPipeline

# Initialize the multi-layer pipeline
pipeline = TextToBIMPipeline()

# Generate BIM from natural language
result = pipeline.generate(
    "Modern 3 bedroom house with 2 bathrooms, open kitchen and study room",
    output_path="output/my_house.ifc"
)

if result['success']:
    print(f"Generated: {result['ifc_file']}")
    print(f"Specification: {result['specification']}")
```

### Blender Add-on (v1.1.0)

1. Download the add-on package:
   ```
   blender_addon/architext_v1.1.0.zip
   ```

2. Install in Blender:
   - Edit → Preferences → Add-ons → Install
   - Select `architext_v1.1.0.zip`
   - Enable "ArchiText - Text to BIM"

3. Use from Blender's sidebar (N panel) → ArchiText tab

**Add-on Features:**
- Full NLP Mode: Natural language text input
- Quick Mode: Direct room specification with plot constraints
- Plot Size Support: Marla, Kanal, Sq Ft, Sq M, or direct dimensions
- Auto-import: Generated IFC automatically imported into scene

## Project Structure

```
architext/
├── scripts/                           # Core Python modules
│   ├── text_to_bim.py                # Pipeline orchestrator (Layer coordination)
│   ├── inference_nlp.py              # Layer 1: NLP model inference
│   ├── graph_layout_optimizer.py     # Layer 2: GNN layout generation
│   ├── layout_optimizer_rules.py     # Layer 3: Rule-based refinement
│   ├── generate_bim.py               # Layer 5: IFC BIM generation
│   ├── area_parser.py                # Plot size parsing (marla, kanal, etc.)
│   ├── train_nlp_model.py            # NLP model training script
│   ├── train_layout_gnn.py           # GNN model training script
│   ├── run_pipeline.py               # CLI entry point
│   └── quick_generate.py             # Quick mode (no NLP)
│
├── blender_addon/                    # Blender integration
│   ├── architext/                    # Add-on source
│   │   └── __init__.py              # v1.1.0 - Blender operators and UI
│   └── architext_v1.1.0.zip         # Packaged add-on
│
├── models/                           # Trained model checkpoints
│   ├── nlp_t5/                       # T5 NLP model
│   │   └── final_model/              # Production checkpoint
│   └── layout_gnn/                   # GNN layout model
│       └── final_model/              # Production checkpoint
│
├── datasets/                         # Training data
│   ├── processed/                    # Processed training pairs
│   └── raw/                          # Raw dataset sources
│       └── cubicasa5k/               # CubiCasa5k floor plan dataset
│
├── output/                           # Generated IFC files
└── requirements.txt                  # Python dependencies
```

## Supported Input Formats

### Natural Language
```
"3 bedroom house with 2 bathrooms and garage"
"Modern apartment with open kitchen and living room"
"5 marla house with 4 bedrooms, 3 bathrooms, study and lawn"
"Luxury villa with master suite, home office, and double garage"
```

### Area Specifications
- **Pakistani/Indian**: `5 marla`, `1 kanal`, `10 marlas`
- **Imperial**: `2000 sq ft`, `60x80 feet`
- **Metric**: `200 sqm`, `20x25 meters`

## Technical Details

### Layer 1: NLP Model
- **Architecture**: T5-small Transformer (fine-tuned)
- **Task**: Text-to-JSON specification extraction
- **Training**: Custom architectural dataset + synthetic augmentation
- **Hardware**: RTX 3080 10GB
- **Output**: Structured JSON with room counts and features

### Layer 2: GNN Layout Generator
- **Architecture**: Graph Neural Network with message passing
- **Training Data**: CubiCasa5k dataset (~5000 real floor plans)
- **Hardware**: RTX 3080 10GB
- **Graph Representation**:
  - Nodes: Rooms with type, dimensions
  - Edges: Adjacency relationships, door connections
- **Capabilities**:
  - Generates diverse layouts learned from real architectural data
  - Understands spatial relationships between room types
  - Produces realistic room proportions and placements

### Layer 3: Rule-Based Optimizer
- **Zone System**: PUBLIC → PRIVATE → SERVICE flow
- **Adjacency Rules**: Kitchen-Dining, En-suite-Master, Garage-Kitchen
- **Optimization**: Compactness scoring, wall-sharing enforcement
- **Output**: Architecturally refined positions

### Layer 4: Quality Assurance
- **Overlap Detection**: AABB (Axis-Aligned Bounding Box) intersection
- **Overlap Repair**: Iterative push-apart (50 iteration max)
- **Boundary Enforcement**: Plot dimension constraints
- **Connectivity Check**: Graph traversal for room accessibility

### Layer 5: IFC Generation
- **Schema**: IFC2X3 (Revit compatible)
- **Elements**: IfcWallStandardCase, IfcSpace, IfcDoor, IfcBuildingStorey
- **Hierarchy**: Project → Site → Building → Storey → Elements
- **Units**: SI (meters)

## Output Compatibility

Generated IFC files are compatible with:

| Software | Status | Notes |
|----------|--------|-------|
| Autodesk Revit | ✅ Tested | IFC2X3 import |
| BlenderBIM (Bonsai) | ✅ Tested | Native IFC support |
| FreeCAD | ✅ Tested | IFC import |
| ArchiCAD | ✅ Expected | IFC2X3 standard |
| BIM Vision | ✅ Tested | Free IFC viewer |

## Model Training

### Training the NLP Model

```bash
python scripts/train_nlp_model.py
```

Training configuration:
- Epochs: 15 (aggressive)
- Batch size: 4
- Learning rate: 5e-5
- GPU: RTX 3080 10GB (recommended)

### Training the Layout GNN

```bash
python scripts/train_layout_gnn.py
```

Training configuration:
- Dataset: CubiCasa5k (~5000 floor plans)
- Epochs: 100
- Batch size: 32
- GPU: RTX 3080 10GB (recommended)

### Testing the Models

```bash
python scripts/train_nlp_model.py test
python scripts/train_layout_gnn.py test
```

## Version History

- **v1.1.0** - Multi-layer architecture, GNN layout generation, Plot size constraints, Enhanced Blender add-on
- **v1.0.x** - Initial release, Basic NLP + rule-based layout generation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [IfcOpenShell](https://ifcopenshell.org/) for IFC manipulation
- [Hugging Face Transformers](https://huggingface.co/transformers/) for T5 model
- [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/) for GNN implementation
- [CubiCasa5k](https://github.com/CubiCasa/CubiCasa5k) for floor plan training dataset
- [BlenderBIM](https://blenderbim.org/) for IFC visualization

## Contact

For questions or support, please open an issue on GitHub.

---

**ArchiText** - Transforming words into buildings.
