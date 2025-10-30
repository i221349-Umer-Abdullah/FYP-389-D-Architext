# Architext - AI Text-to-3D House Generator

**Final Year Project - Iteration 1**

Generate 3D house models from text descriptions using AI, designed for integration with BIM software like Autodesk Revit.

## Team
- **Umer Abdullah** (22i-1349) - AI/ML Module Lead
- **Jalal Sherazi** (22i-8755) - Revit Plugin Development
- **Arfeen Awan** (22i-2645) - Data Pipeline & Preprocessing

## Quick Start

### 1. Setup (First Time Only)

**Windows:**
```batch
setup.bat
```

This will:
- Create Python virtual environment
- Install PyTorch (with CUDA if available)
- Install all dependencies
- Create necessary directories

**Time:** 5-10 minutes (depending on internet speed)

### 2. Test Models

**Test Shap-E (recommended):**
```batch
test_shap_e.bat
```

**Test Point-E (alternative):**
```batch
test_point_e.bat
```

**Compare all models:**
```batch
compare_models.bat
```

**Time:** 5-15 minutes per model

### 3. Launch Demo

```batch
run_demo.bat
```

Opens a web interface at `http://localhost:7860`

## Project Structure

```
architext/
├── app/
│   ├── core_generator.py    # Main generation logic
│   └── demo_app.py          # Gradio web interface
├── tests/
│   ├── test_shap_e.py       # Shap-E model tests
│   ├── test_point_e.py      # Point-E model tests
│   └── model_comparison.py  # Automated comparison
├── outputs/                 # Generated 3D models
├── models/                  # Cached AI models
├── docs/
│   └── development_history.md
├── requirements.txt
└── setup.bat               # Setup script

```

## Features

### Current (Iteration 1)
- ✅ Text-to-3D house generation
- ✅ Multiple AI models (Shap-E, Point-E)
- ✅ Interactive web UI
- ✅ Multiple export formats (OBJ, PLY, STL)
- ✅ Automatic mesh scaling and post-processing
- ✅ Metadata tracking
- ✅ Model comparison framework

### Planned (Future Iterations)
- Revit plugin integration
- Custom model training on architectural dataset
- Room specification parsing
- Structural analysis
- Cost estimation
- Floor plan to 3D conversion

## Usage Examples

### Using the Demo UI

1. Launch: `run_demo.bat`
2. Enter a description: *"A modern two-story house with large windows"*
3. Select quality: Medium (recommended for testing)
4. Click "Generate House"
5. Download the OBJ file
6. Open in Blender/Revit

### Using Python API

```python
from app.core_generator import HouseGenerator

# Initialize generator
generator = HouseGenerator(model_name="shap-e")

# Generate house
mesh, spec = generator.generate_house(
    "a modern two-story house with garage",
    num_steps=64
)

# Export
generator.export_mesh(mesh, "my_house", format="obj")
```

## Supported Models

### Shap-E (Recommended)
- **Source:** OpenAI
- **Output:** 3D meshes
- **Quality:** High
- **Speed:** Medium (1-2 min)
- **Best for:** Detailed house models

### Point-E (Alternative)
- **Source:** OpenAI
- **Output:** Point clouds → Meshes
- **Quality:** Medium
- **Speed:** Fast (30-60 sec)
- **Best for:** Quick prototyping

## Export Formats

- **OBJ** - Universal 3D format (Blender, Maya, Revit)
- **PLY** - Preserves vertex colors
- **STL** - For 3D printing
- **JSON** - Metadata and specifications

## System Requirements

### Minimum
- Windows 10/11
- Python 3.8+
- 8GB RAM
- 5GB disk space

### Recommended
- NVIDIA GPU (CUDA-capable)
- 16GB RAM
- 10GB disk space
- Good internet (for first-time model download)

## Troubleshooting

### Setup fails
- Ensure Python 3.8+ is installed: `python --version`
- Run as administrator if permission errors occur

### Model download slow
- Models are ~2-3GB, first download takes time
- Models are cached in `models/` directory

### Generation fails
- Check if virtual environment is activated
- Verify GPU drivers if using CUDA
- Try "Low" quality setting first

### Out of memory
- Reduce quality setting to "Low"
- Close other applications
- Use CPU instead of GPU (slower but works)

## Development

### Manual Setup (Advanced)

```bash
# Create environment
python -m venv venv
venv\Scripts\activate

# Install PyTorch (CUDA)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
# Activate environment
venv\Scripts\activate

# Test Shap-E
python tests/test_shap_e.py

# Test Point-E
python tests/test_point_e.py

# Compare models
python tests/model_comparison.py

# Launch demo
python app/demo_app.py
```

## Documentation

- **Development History:** `docs/development_history.md`
- **Week 1 Plan:** `docs/iteration-1-week-plan.md`
- **API Documentation:** See docstrings in `app/core_generator.py`

## Known Limitations

1. **Generation Quality:** Pre-trained models may not produce perfect houses
2. **Architectural Details:** Fine details (windows, doors) may be abstract
3. **Revit Integration:** Not yet implemented (coming in Iteration 2)
4. **Training:** Using pre-trained models, not custom-trained on houses
5. **Speed:** High-quality generation can take 2+ minutes

## Next Steps

1. **Test models** with various prompts
2. **Evaluate quality** of generated houses
3. **Select best model** for demo
4. **Prepare examples** for presentation
5. **Refine UI** based on testing

## Contributing

This is an academic FYP project. For questions or collaboration:
- **Umer Abdullah:** 22i-1349@khi.iba.edu.pk

## License

Academic project for educational purposes.

## Acknowledgments

- OpenAI for Shap-E and Point-E models
- Hugging Face for Diffusers library
- Gradio for easy UI development

---

**Last Updated:** 2024-10-30
**Version:** 1.0.0 (Iteration 1)
