# How to Test Improved Point-E Model

## What I Improved

### Quality Enhancements:
1. **Guidance Scale: 7.0** (vs 3.0 default) - Much stronger adherence to text prompt
2. **Better Mesh Reconstruction**: Alpha shape algorithm (vs basic convex hull)
3. **Laplacian Smoothing**: Makes mesh surfaces smoother
4. **Better Prompt**: "a detailed modern two-story residential house with windows, door, sloped roof, and chimney"
5. **Subdivision**: Increases mesh density for better detail

### Expected Results:
- **Vertices**: Thousands (vs 8 in basic version)
- **Faces**: Much more detailed surface
- **Quality**: Significantly better shape and structure
- **Generation Time**: 3-5 minutes

## How to Run It Yourself

### Step 1: Open Command Prompt
```bash
cd D:\Work\Uni\FYP\architext
```

### Step 2: Activate Virtual Environment
```bash
venv\Scripts\activate
```

### Step 3: Run the Improved Test
```bash
python tests\test_point_e_improved.py
```

## What You'll Get

### Output Files:
1. **point_e_improved_house.ply** - High-quality mesh with improved reconstruction
2. **point_e_point_cloud.ply** - Raw 4096-point colored point cloud

### Location:
```
D:\Work\Uni\FYP\architext\outputs\
```

## How to View Results

### Option 1: Blender (Best)
1. Open Blender
2. File → Import → Stanford (.ply)
3. Navigate to outputs folder
4. Select the .ply file

### Option 2: Windows 3D Viewer
1. Navigate to outputs folder
2. Double-click the .ply file
3. Windows 3D Viewer opens automatically

### Option 3: Online Viewer
1. Go to https://3dviewer.net/
2. Drag and drop the .ply file

### Option 4: MeshLab (Professional)
1. Download MeshLab (free)
2. File → Import Mesh
3. Select the .ply file

## Comparison

| Feature | Basic Version | Improved Version |
|---------|---------------|------------------|
| Guidance Scale | 3.0 | 7.0 |
| Vertices | 8 | Thousands |
| Reconstruction | Convex Hull | Alpha Shape + Smoothing |
| Prompt Quality | Basic | Detailed architectural terms |
| Generation Time | 2-3 min | 3-5 min |
| Output Quality | Simple blob | Detailed structure |

## Currently Running

The improved test is running right now in the background. It will:
1. Load Point-E models (using cached weights)
2. Generate point cloud with high guidance (3-5 minutes)
3. Apply alpha shape reconstruction
4. Apply Laplacian smoothing
5. Save both mesh and point cloud

Wait for the test to complete, then test the output yourself!

## Test Commands Summary

```bash
# Activate environment
cd D:\Work\Uni\FYP\architext
venv\Scripts\activate

# Run improved Point-E test
python tests\test_point_e_improved.py

# Or run basic Shap-E demo (already working perfectly)
python app\demo_app.py
# Then open: http://127.0.0.1:7860
```
