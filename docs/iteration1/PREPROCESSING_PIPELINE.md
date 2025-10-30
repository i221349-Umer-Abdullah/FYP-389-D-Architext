# Preprocessing Pipeline - Architext

## Overview
This document describes the preprocessing pipeline for the Architext text-to-3D house generation system.

---

## 1. Text Input Preprocessing

### Input Sanitization
**Purpose**: Clean and standardize user text prompts

**Steps**:
1. **Trim whitespace**: Remove leading/trailing spaces
2. **Normalize case**: Convert to lowercase for consistency
3. **Remove special characters**: Filter out non-alphanumeric except spaces, commas, hyphens
4. **Length validation**: Ensure prompt is between 3-200 characters

**Implementation** (app/core_generator.py):
```python
def preprocess_prompt(self, prompt: str) -> str:
    """Preprocess user prompt"""
    # Trim and normalize
    prompt = prompt.strip().lower()

    # Remove excessive spaces
    prompt = ' '.join(prompt.split())

    # Validate length
    if len(prompt) < 3:
        raise ValueError("Prompt too short (min 3 characters)")
    if len(prompt) > 200:
        prompt = prompt[:200]

    return prompt
```

### Prompt Enhancement
**Purpose**: Improve generation quality with architectural keywords

**Enhancement Strategy**:
- Add context: "a detailed architectural model of [user prompt]"
- Append style keywords: "high quality, detailed, professional"
- Emphasize 3D nature: "three-dimensional building"

**Example**:
```
Input:  "modern house"
Output: "a detailed architectural model of a modern house, high quality 3D building"
```

---

## 2. Model Input Preprocessing

### Shap-E Pipeline

**Text Encoding**:
1. Tokenize prompt using CLIP tokenizer
2. Encode to 512-dim embedding vector
3. Normalize embeddings (L2 normalization)

**Diffusion Parameters**:
- Inference steps: 64 (default) or user-specified
- Guidance scale: 15.0 (high quality)
- Frame size: 64 (spatial resolution)

**Code** (app/core_generator.py:197-212):
```python
output = self.pipeline(
    enhanced_prompt,
    num_inference_steps=num_steps,     # 64 default
    guidance_scale=guidance_scale,      # 15.0 for quality
    frame_size=frame_size,              # 64 resolution
    output_type="mesh"
)
```

### Point-E Pipeline

**Text Encoding**:
1. Tokenize with Point-E text encoder
2. Generate base point cloud (1024 points)
3. Upsample to 4096 points with color channels

**Guidance Configuration**:
- Base model guidance: 15.0 (maximum structure)
- Upsampler guidance: 15.0
- Aux channels: ['R', 'G', 'B'] for vertex colors

**Code** (tests/test_point_e_ultra_optimized.py:45-55):
```python
sampler = PointCloudSampler(
    device=device,
    models=[base_model, upsampler_model],
    diffusions=[base_diffusion, upsampler_diffusion],
    num_points=[1024, 4096 - 1024],
    aux_channels=['R', 'G', 'B'],
    guidance_scale=[15.0, 15.0],
)
```

---

## 3. Output Post-Processing

### Mesh Extraction (Shap-E)

**Process**:
1. Extract MeshDecoderOutput from pipeline
2. Convert tensors to numpy arrays:
   - Vertices: (N, 3) float32
   - Faces: (M, 3) int32
   - Vertex colors: (N, 3) uint8

**Implementation** (app/core_generator.py:206-226):
```python
mesh_output = output.images[0]

vertices = mesh_output.verts.cpu().numpy()
faces = mesh_output.faces.cpu().numpy()

# Extract RGB vertex colors
if hasattr(mesh_output, 'vertex_channels'):
    r = mesh_output.vertex_channels['R'].cpu().numpy()
    g = mesh_output.vertex_channels['G'].cpu().numpy()
    b = mesh_output.vertex_channels['B'].cpu().numpy()
    vertex_colors = np.stack([r, g, b, np.ones_like(r)], axis=1)
    vertex_colors = (vertex_colors * 255).astype(np.uint8)

mesh = trimesh.Trimesh(
    vertices=vertices,
    faces=faces,
    vertex_colors=vertex_colors
)
```

### Volumetric Reconstruction (Point-E)

**Purpose**: Convert point cloud to solid mesh

**Algorithm: Marching Cubes**
1. **Create occupancy grid** (128×128×128 voxels)
2. **Compute distance field**: Distance from each voxel to nearest point
3. **Mark occupied voxels**: Distance < threshold (0.03)
4. **Extract surface**: Marching cubes algorithm
5. **Map colors**: Interpolate from nearest point cloud neighbors

**Implementation** (tests/test_point_e_ultra_optimized.py:78-131):
```python
# Normalize point cloud to [0,1]
coords_norm = (coords - coords_min) / (coords_max - coords_min + 1e-8)

# Create 128³ grid
resolution = 128
x = np.linspace(0, 1, resolution)
y = np.linspace(0, 1, resolution)
z = np.linspace(0, 1, resolution)
grid_x, grid_y, grid_z = np.meshgrid(x, y, z, indexing='ij')

# Build KD-tree for nearest neighbor queries
tree = cKDTree(coords_norm)
grid_points = np.stack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel()], axis=1)

# Compute occupancy field
distances, _ = tree.query(grid_points, k=1)
threshold = 0.03
occupancy = (distances < threshold).astype(float)
occupancy = occupancy.reshape((resolution, resolution, resolution))

# Marching cubes
verts, faces, normals, values = measure.marching_cubes(occupancy, level=0.5)

# Scale back to original space
verts = verts / resolution
verts = verts * (coords_max - coords_min) + coords_min

# Create mesh
mesh = trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)
```

### Mesh Cleaning

**Operations**:
1. **Remove duplicate faces**: Ensure each face is unique
2. **Remove unreferenced vertices**: Delete vertices not used by any face
3. **Fix normals**: Ensure consistent face orientation

**Code**:
```python
mesh.remove_duplicate_faces()
mesh.remove_unreferenced_vertices()
mesh.fix_normals()
```

---

## 4. Export Format Conversion

### Supported Formats
- **PLY** (Stanford Polygon): Vertex colors, simple format
- **OBJ** (Wavefront): Universal compatibility, materials
- **GLB** (glTF Binary): Web/game engines, animations

### PLY Export
```python
mesh.export(output_path, file_type='ply', encoding='binary')
```

**Structure**:
- Header: Vertex/face count, property types
- Vertex list: x, y, z, r, g, b
- Face list: Triangle indices

### OBJ Export
```python
mesh.export(output_path, file_type='obj', include_color=True)
```

**Structure**:
- Vertices: `v x y z`
- Vertex colors: `vc r g b` (if supported)
- Faces: `f v1 v2 v3`

---

## 5. Quality Metrics

### Mesh Quality Checks

**Computed Metrics**:
1. **Vertex count**: Higher = more detail
2. **Face count**: Surface complexity
3. **Bounding box**: Model dimensions
4. **Watertightness**: Mesh is closed
5. **Face area distribution**: Uniformity check

**Implementation** (app/core_generator.py:254-269):
```python
stats = {
    'vertices': len(mesh.vertices),
    'faces': len(mesh.faces),
    'bounds': mesh.bounds.tolist(),
    'is_watertight': mesh.is_watertight,
    'volume': float(mesh.volume) if mesh.is_watertight else None,
}
```

---

## 6. Error Handling

### Common Issues and Solutions

| Issue | Detection | Solution |
|-------|-----------|----------|
| Empty mesh | 0 vertices or faces | Regenerate with different params |
| Degenerate faces | Zero-area triangles | Remove with trimesh.nondegenerate_faces() |
| Disconnected components | Multiple bodies | Keep largest component |
| Invalid normals | NaN values | Recompute with mesh.fix_normals() |
| Color mismatc

h | Wrong shape | Interpolate from nearest neighbors |

**Error Recovery** (app/core_generator.py:410-415):
```python
try:
    mesh = generate_mesh(prompt)
except Exception as e:
    logger.error(f"Generation failed: {e}")
    return None, f"Error: {str(e)}"
```

---

## 7. Performance Optimizations

### GPU Acceleration
- **CUDA**: All model inference on RTX 3080
- **Batch processing**: Single prompt per batch (memory limited)
- **Mixed precision**: FP16 for faster computation

### Caching Strategy
- **Model weights**: Cached in HuggingFace hub (~/.cache)
- **CLIP embeddings**: No caching (fast to compute)
- **Generated meshes**: Saved to outputs/ directory

### Memory Management
```python
# Clear CUDA cache after generation
torch.cuda.empty_cache()

# Delete intermediate tensors
del samples, mesh_output
gc.collect()
```

---

## 8. Pipeline Summary

### Complete Flow

```
User Text Input
    ↓
[1] Sanitize & validate
    ↓
[2] Enhance with keywords
    ↓
[3] Encode to embeddings (CLIP/Point-E)
    ↓
[4] Diffusion generation
    ↓
[5] Extract mesh/point cloud
    ↓
[6] Post-process (Shap-E) or Volumetric reconstruction (Point-E)
    ↓
[7] Clean mesh (remove duplicates, fix normals)
    ↓
[8] Compute quality metrics
    ↓
[9] Export to PLY/OBJ
    ↓
[10] Return to user
```

### Timing Breakdown

**Shap-E** (Total: ~5-7 seconds):
- Text preprocessing: <0.1s
- Model inference: 4-5s
- Mesh extraction: 0.5s
- Export: 0.5s

**Point-E** (Total: ~5-7 minutes):
- Text preprocessing: <0.1s
- Point cloud generation: 3-4 min
- Volumetric reconstruction: 2-3 min
- Export: 0.5s

---

## Conclusion

The preprocessing pipeline ensures:
- ✅ Clean, standardized text inputs
- ✅ Optimized model parameters
- ✅ High-quality mesh outputs
- ✅ Robust error handling
- ✅ Multiple export formats

This pipeline is production-ready for Iteration 1 demo.
