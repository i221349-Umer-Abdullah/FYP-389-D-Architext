# ArchiText - Text-to-BIM Conversion System

> **Final Year Project**: An AI-powered system that converts natural language building descriptions into Industry Foundation Classes (IFC) BIM models.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)
![IFC](https://img.shields.io/badge/IFC-2X3-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Overview

ArchiText is an end-to-end pipeline that transforms natural language descriptions of buildings into valid IFC (Industry Foundation Classes) files that can be opened in professional BIM software like Autodesk Revit, BlenderBIM, and others.

### Key Features

- **Natural Language Understanding**: Custom-trained T5 transformer model that extracts building specifications from text
- **Intelligent Layout Optimization**: Rule-based optimization layer that refines model outputs for architecturally valid floor plans
- **Graph-Based Room Placement**: Ensures connected rooms share walls with proper door placements
- **Bounded Area Generation**: Supports Pakistani/Indian land units (marla, kanal) alongside metric and imperial
- **Multi-Platform Support**: Generated IFC files compatible with Revit, BlenderBIM, FreeCAD
- **Blender Add-on**: Direct integration with Blender for real-time 3D visualization

## Architecture

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    ArchiText Pipeline                        │
                    └─────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: Natural Language Processing (Trained T5 Model)                            │
│  ─────────────────────────────────────────────────────────────────────────────────  │
│  Input: "Modern 3 bedroom house with 2 bathrooms and open kitchen"                  │
│  Output: {"bedrooms": 3, "bathrooms": 2, "kitchen": true, "living_room": true, ...} │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: Layout Optimization Engine (Rule-Based Enhancement)                       │
│  ─────────────────────────────────────────────────────────────────────────────────  │
│  • Applies architectural constraints and best practices                             │
│  • Ensures proper room adjacencies (kitchen near dining, en-suite in master)        │
│  • Validates room dimensions against real-world standards                           │
│  • Optimizes spatial layout for connectivity and flow                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: BIM Generation (IFC Export)                                               │
│  ─────────────────────────────────────────────────────────────────────────────────  │
│  • Creates IFC2X3 compliant building model                                          │
│  • Generates walls, spaces, and spatial hierarchy                                   │
│  • Supports Revit, BlenderBIM, FreeCAD, and other IFC viewers                       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.10 or higher
- CUDA-compatible GPU (recommended for training)
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

4. **Download pre-trained model** (optional)

   The trained NLP model checkpoint should be placed in:
   ```
   models/text_to_spec/
   ```

## Usage

### Command Line Interface

```bash
# Generate BIM from text description
python scripts/text_to_bim.py --text "Modern 3 bedroom house with 2 bathrooms and spacious living room"

# Generate with bounded area (5 marla plot)
python scripts/bounded_layout_generator.py --area "5 marla" --bedrooms 3 --bathrooms 2
```

### Python API

```python
from scripts.text_to_bim import TextToBIMPipeline

# Initialize pipeline
pipeline = TextToBIMPipeline()

# Generate BIM from natural language
result = pipeline.generate(
    "Modern 3 bedroom house with 2 bathrooms, open kitchen and study room",
    output_path="output/my_house.ifc"
)

print(f"Generated: {result['ifc_file']}")
```

### Blender Add-on

1. Package the add-on:
   ```bash
   python blender_addon/package_addon.py
   ```

2. Install in Blender:
   - Edit → Preferences → Add-ons → Install
   - Select `architext_addon.zip`
   - Enable "ArchiText - Text to BIM"

3. Use from Blender's sidebar (N panel) → ArchiText tab

## Project Structure

```
architext/
├── scripts/                    # Core Python modules
│   ├── text_to_bim.py         # Main pipeline orchestrator
│   ├── inference_nlp.py       # NLP model inference
│   ├── train_nlp_model.py     # Model training script
│   ├── generate_bim.py        # IFC/BIM generation engine
│   ├── layout_optimizer_rules.py  # Rule-based layout optimization
│   ├── graph_layout_optimizer.py  # Graph-based room placement
│   ├── bounded_layout_generator.py # Area-constrained generation
│   └── area_parser.py         # Multi-unit area parsing
│
├── blender_addon/             # Blender integration
│   ├── architext/            # Add-on source
│   │   └── __init__.py       # Blender operators and UI
│   └── package_addon.py      # Packaging script
│
├── models/                    # Trained model checkpoints
│   └── text_to_spec/         # NLP model weights
│
├── datasets/                  # Training data
│   ├── processed/            # Processed training pairs
│   └── raw/                  # Raw dataset sources
│
├── output/                    # Generated IFC files
├── tests/                     # Test suites
└── requirements.txt          # Python dependencies
```

## Supported Input Formats

### Natural Language
```
"3 bedroom house with 2 bathrooms and garage"
"Modern apartment with open kitchen and living room"
"5 marla house with 4 bedrooms, 3 bathrooms, study and lawn"
```

### Area Specifications
- **Pakistani/Indian**: `5 marla`, `1 kanal`, `10 marlas`
- **Imperial**: `2000 sq ft`, `60x80 feet`
- **Metric**: `200 sqm`, `20x25 meters`

## Model Training

### Training the NLP Model

```bash
python scripts/train_nlp_model.py \
    --train_data datasets/processed/train.json \
    --val_data datasets/processed/val.json \
    --epochs 10 \
    --batch_size 8
```

### Evaluation

```bash
python scripts/evaluate_nlp_model.py \
    --model_path models/text_to_spec/best_model.pt \
    --test_data datasets/processed/test.json
```

## Output Compatibility

Generated IFC files are compatible with:

| Software | Status | Notes |
|----------|--------|-------|
| Autodesk Revit | ✅ Tested | IFC2X3 import |
| BlenderBIM (Bonsai) | ✅ Tested | Native support |
| FreeCAD | ✅ Tested | IFC import |
| ArchiCAD | ✅ Expected | IFC2X3 standard |
| BIM Vision | ✅ Tested | Free IFC viewer |

## Technical Details

### NLP Model
- **Base Model**: T5-small (fine-tuned)
- **Task**: Text-to-JSON specification conversion
- **Training Data**: Synthetic + real estate descriptions

### Layout Optimization
- **Approach**: Constraint satisfaction with architectural rules
- **Room Types**: 30+ supported (bedrooms, bathrooms, kitchen, etc.)
- **Connectivity**: Graph-based wall sharing and door placement

### IFC Generation
- **Schema**: IFC2X3 (Revit compatible)
- **Elements**: IfcWallStandardCase, IfcSpace, IfcBuildingStorey
- **Units**: SI (meters)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [IfcOpenShell](https://ifcopenshell.org/) for IFC manipulation
- [Hugging Face Transformers](https://huggingface.co/transformers/) for T5 model
- [BlenderBIM](https://blenderbim.org/) for IFC visualization
- [RPLAN Dataset](http://staff.ustc.edu.cn/~fuxm/projects/DeepLayout/index.html) for floor plan data

## Contact

For questions or support, please open an issue on GitHub.

---

**ArchiText** - Transforming words into buildings.
