# Architext - Setup & Installation Guide

**Quick reference for installation and running the project**

---

## System Requirements

**Minimum:**
- GPU: 4GB VRAM (GTX 1650+)
- RAM: 8GB
- Storage: 10GB free
- Python: 3.10+

**Recommended (Our Setup):**
- GPU: RTX 3080 (10GB VRAM)
- RAM: 16GB
- CUDA: 11.8
- Python: 3.13

---

## Quick Setup

### 1. Virtual Environment
```bash
cd D:\Work\Uni\FYP\architext
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the App
```bash
python app\demo_app.py
```

Open: **http://localhost:7860**

---

## Dependencies

**Core:**
- PyTorch 2.0+ (with CUDA)
- diffusers (for Shap-E)
- trimesh (3D processing)
- gradio (web UI)

**Full list:** See `requirements.txt`

---

## Testing Models

### Test Shap-E (Selected Model):
```bash
python tests\test_shap_e.py
```

### Test Point-E (Comparison):
```bash
python tests\test_point_e_ultra_optimized.py
```

### Test TripoSR (Experimental):
```bash
python tests\test_multi_model.py
```

---

## Troubleshooting

**CUDA out of memory:**
- Close other GPU applications
- Reduce quality settings in app

**Model downloads slowly:**
- First run downloads ~2-4GB models
- Be patient, only happens once

**Import errors:**
- Make sure venv is activated
- Reinstall: `pip install -r requirements.txt --force-reinstall`

---

*For demo instructions, see: DEMO_GUIDE.md*
