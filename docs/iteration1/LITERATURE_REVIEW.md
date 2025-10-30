# Literature Review - Text-to-3D Generation for Architecture

## Executive Summary

This literature review examines state-of-the-art text-to-3D generation models, with focus on architectural applications. We analyzed 3 major models (Shap-E, Point-E, GET3D) and identified Shap-E as the optimal solution for house generation.

---

## 1. Shap-E: Direct 3D Shape Generation

### Paper
**"Shap-E: Generating Conditional 3D Implicit Functions"**
- Authors: OpenAI (Heewoo Jun, Alex Nichol)
- Published: 2023
- Repository: https://github.com/openai/shap-e

### Key Contributions
1. **Implicit function learning**: Generates NeRF-like representations
2. **Direct mesh extraction**: Converts to explicit geometry
3. **CLIP conditioning**: Text-to-3D via contrastive embeddings
4. **Fast inference**: ~5 seconds on consumer GPUs

### Architecture
- **Encoder**: Dual encoders (point cloud + NeRF)
- **Diffusion model**: Latent space diffusion (64 steps)
- **Decoder**: MeshDecoder extracts triangular meshes
- **Text conditioning**: CLIP text embeddings

### Performance
- **Quality**: 84,000 average vertices
- **Speed**: 4-6 seconds per model
- **Diversity**: High variation from same prompt
- **Color**: Full RGB vertex colors

### Strengths for Architecture
✅ Direct mesh generation (no conversion needed)
✅ High vertex count = detailed structures
✅ CLIP understands architectural terms well
✅ Fast enough for interactive use

### Limitations
❌ Limited control over specific features (windows, doors)
❌ No explicit floor plan input
❌ Occasional structural inconsistencies

### Our Implementation
- Guidance scale: 15.0 (high fidelity)
- Inference steps: 64 (default)
- Frame size: 64 (spatial resolution)
- Output: PLY/OBJ with vertex colors

---

## 2. Point-E: Point Cloud Diffusion

### Paper
**"Point-E: A System for Generating 3D Point Clouds from Complex Prompts"**
- Authors: OpenAI (Alex Nichol, Heewoo Jun, Prafulla Dhariwal)
- Published: 2022
- Repository: https://github.com/openai/point-e

### Key Contributions
1. **Two-stage generation**: Base model + upsampler
2. **RGB point clouds**: Colored 3D points
3. **Faster than NeRF**: Minutes vs hours
4. **Text conditioning**: Direct text-to-point-cloud

### Architecture
- **Base model**: Generates 1,024 points
- **Upsampler**: Refines to 4,096 points
- **Diffusion**: Point cloud diffusion process
- **Color channels**: R, G, B auxiliary channels

### Performance
- **Quality**: 4,096 colored points
- **Speed**: 3-5 minutes per model
- **Mesh conversion**: Requires post-processing

### Mesh Reconstruction Methods Tested

#### Method 1: Convex Hull (Failed)
- Result: Only 8 vertices
- Quality: Too simple, blob-like
- Verdict: Unusable

#### Method 2: Alpha Shape (Failed)
- Result: 0 vertices (corrupted)
- Quality: Reconstruction failed
- Verdict: Unreliable

#### Method 3: Volumetric Marching Cubes (Success)
- Result: 30,000-67,000 vertices
- Quality: Solid meshes
- Settings: 128³ grid, threshold=0.03
- Verdict: Usable but complex

### Strengths
✅ Different approach (point-based)
✅ Can generate diverse shapes
✅ Colored output

### Limitations for Architecture
❌ Requires complex mesh reconstruction
❌ Lower quality than Shap-E
❌ Much slower (minutes vs seconds)
❌ Point clouds less suitable for CAD import

### Our Implementation
- Guidance scale: 15.0 (maximum)
- Resolution: 128×128×128 voxels
- Marching cubes threshold: 0.03
- Output: PLY/OBJ via volumetric reconstruction

---

## 3. GET3D: Generative 3D Textured Shapes

### Paper
**"GET3D: A Generative Model of High Quality 3D Textured Shapes Learned from Images"**
- Authors: NVIDIA (Jun Gao, Tianchang Shen, Zian Wang, et al.)
- Published: NeurIPS 2022
- Repository: https://github.com/nv-tlabs/GET3D

### Key Contributions
1. **Image-based training**: Learn from 2D image collections
2. **Explicit textured meshes**: Direct mesh + texture generation
3. **High quality**: Detailed geometry and textures
4. **GAN-based**: Adversarial training for realism

### Architecture
- **Generator**: DMTet surface representation
- **Texture network**: UV-mapped texture generation
- **Discriminator**: 2D image discrimination
- **Training**: ShapeNet datasets

### Critical Limitation for Our Project
**GET3D does NOT support text-to-3D**

- ❌ No text encoder (no CLIP integration)
- ❌ Training-based generative model only
- ❌ Generates RANDOM models from learned distribution
- ❌ Cannot specify "house" vs "car"
- ❌ Requires training on thousands of house models
- ❌ Linux only, Python 3.8, outdated PyTorch

### Why GET3D Cannot Be Used
1. **No conditional generation**: Cannot take text prompts
2. **Wrong training data**: Pretrained on cars/chairs, not houses
3. **Platform incompatibility**: Requires Linux, V100/A100 GPUs
4. **No pretrained house models**: Would need weeks of training

### Verdict
**Not applicable** for text-to-3D house generation.

---

## 4. Alternative Approaches Considered

### 4.1 DreamFusion (Google)
**"DreamFusion: Text-to-3D using 2D Diffusion"**

**Approach**: Score distillation sampling from 2D diffusion models

**Pros**:
- Very high quality
- Detailed textures
- Good architectural understanding

**Cons**:
- EXTREMELY slow (1-2 hours per model)
- Requires massive compute
- No official implementation
- Not suitable for interactive demo

**Verdict**: Too slow for our use case

### 4.2 Magic3D (NVIDIA)
**"Magic3D: High-Resolution Text-to-3D Content Creation"**

**Approach**: Coarse-to-fine optimization with NeRF

**Pros**:
- Higher resolution than DreamFusion
- 2x faster than DreamFusion

**Cons**:
- Still very slow (~30-60 minutes)
- Complex two-stage pipeline
- Requires powerful GPUs

**Verdict**: Too slow for demo

### 4.3 Stable Fast 3D (Stability AI)
**"SF3D: Stable Fast 3D Mesh Reconstruction"**

**Approach**: Image-to-3D in 0.5 seconds

**Pros**:
- VERY fast (0.5 seconds)
- High quality textures
- UV-unwrapped meshes

**Cons**:
- Requires IMAGE input, not text
- Would need Stable Diffusion first (text→image)
- Two-stage pipeline adds complexity

**Verdict**: Possible future enhancement (text→image→3D)

---

## 5. Comparative Analysis

### Quantitative Comparison

| Model | Speed | Vertices | Text-to-3D | RTX 3080 | Architecture Quality |
|-------|-------|----------|------------|----------|---------------------|
| **Shap-E** | **5s** | **84,000** | **✅ Yes** | **✅ Yes** | **⭐⭐⭐⭐⭐** |
| **Point-E** | 5min | 67,000* | ✅ Yes | ✅ Yes | ⭐⭐⭐ |
| GET3D | N/A | N/A | ❌ No | ❌ No | N/A |
| DreamFusion | 2hr | High | ✅ Yes | ⚠️ Slow | ⭐⭐⭐⭐⭐ |
| Magic3D | 1hr | High | ✅ Yes | ⚠️ Slow | ⭐⭐⭐⭐⭐ |
| SF3D | 0.5s | High | ❌ Image | ✅ Yes | ⭐⭐⭐⭐ |

*Point-E after volumetric reconstruction

### Qualitative Comparison

**For Architectural Generation:**

1. **Shap-E** (Best Choice)
   - Direct mesh output
   - Fast enough for demos
   - Good architectural understanding
   - Works on consumer hardware

2. **Point-E** (Alternative)
   - Different approach shows variety
   - Requires complex post-processing
   - Slower but still usable

3. **GET3D** (Not Usable)
   - Cannot do text-to-3D
   - Wrong tool for the job

4. **DreamFusion/Magic3D** (Too Slow)
   - Highest quality
   - Not suitable for interactive demos
   - Requires hours per model

---

## 6. Domain-Specific Considerations

### Architectural 3D Generation Challenges

1. **Structural Coherence**: Buildings need logical structure
   - **Shap-E**: Good understanding of basic structure
   - **Point-E**: Struggles with complex geometry

2. **Geometric Precision**: Straight lines, right angles
   - **Shap-E**: Reasonable geometric accuracy
   - **Point-E**: Blob-like, needs high guidance

3. **Detail Level**: Windows, doors, roofs
   - **Shap-E**: Can generate recognizable features
   - **Point-E**: Only basic shapes even with optimization

4. **CAD Integration**: Import into Blender/Revit
   - **Shap-E**: Clean meshes, direct PLY/OBJ export
   - **Point-E**: Requires mesh reconstruction

---

## 7. Our Selection Rationale

### Why We Chose Shap-E as Primary Model

**Technical Reasons**:
1. ✅ Direct mesh generation (no conversion needed)
2. ✅ Fast inference (5s vs 5min for Point-E)
3. ✅ High vertex count (84k vertices)
4. ✅ Robust CLIP conditioning
5. ✅ Production-ready code
6. ✅ Works on RTX 3080

**Practical Reasons**:
1. ✅ Suitable for live demo
2. ✅ Easy to integrate into web app
3. ✅ Reliable outputs
4. ✅ Good documentation
5. ✅ Active community

**Quality Reasons**:
1. ✅ Best balance of speed/quality
2. ✅ Recognizable architectural features
3. ✅ Vertex colors for visualization
4. ✅ Clean topology

### Why We Tested Point-E

**Reasons**:
1. Alternative approach (point-based)
2. Research comparison
3. Different quality trade-offs
4. Learning experience

**Conclusion**: Point-E is interesting but Shap-E is superior for our use case

---

## 8. Future Work

### Potential Improvements

1. **Fine-tuning on Architectural Data**
   - Train on house-specific datasets
   - Improve architectural vocabulary
   - Better structural coherence

2. **Hybrid Approaches**
   - Combine Shap-E with floor plan input
   - Add ControlNet for structure guidance
   - Multi-stage refinement

3. **Text-to-Image-to-3D Pipeline**
   - Stable Diffusion for house image
   - SF3D for 3D reconstruction
   - Higher quality textures

4. **Interactive Editing**
   - Modify generated models
   - Add/remove features
   - Style transfer

---

## 9. Conclusion

### Summary

After extensive literature review and baseline testing:

- **Shap-E**: Selected as primary model (fast, high quality, reliable)
- **Point-E**: Tested as alternative (slower, requires reconstruction)
- **GET3D**: Rejected (no text-to-3D capability)
- **DreamFusion/Magic3D**: Rejected (too slow for demo)

### Iteration 1 Deliverable

We have successfully:
- ✅ Reviewed state-of-the-art text-to-3D models
- ✅ Tested multiple approaches (Shap-E, Point-E)
- ✅ Identified optimal solution (Shap-E)
- ✅ Implemented production-ready system
- ✅ Documented technical rationale

**Primary Model**: Shap-E with dark-themed web interface
**Status**: Production-ready for demo

---

## References

1. Jun, H., & Nichol, A. (2023). Shap-E: Generating Conditional 3D Implicit Functions. OpenAI.

2. Nichol, A., Jun, H., Dhariwal, P., Dhariwal, P., & Chen, M. (2022). Point-E: A System for Generating 3D Point Clouds from Complex Prompts. OpenAI.

3. Gao, J., Shen, T., Wang, Z., Chen, W., Yin, K., Li, D., ... & Fidler, S. (2022). GET3D: A Generative Model of High Quality 3D Textured Shapes Learned from Images. NeurIPS.

4. Poole, B., Jain, A., Barron, J. T., & Mildenhall, B. (2022). DreamFusion: Text-to-3D using 2D Diffusion. Google Research.

5. Lin, C. H., Gao, J., Tang, L., Takikawa, T., Zeng, X., Huang, X., ... & Fidler, S. (2023). Magic3D: High-Resolution Text-to-3D Content Creation. NVIDIA.

6. Boss, M., Huang, Z., Vasishta, A., & Jampani, V. (2024). SF3D: Stable Fast 3D Mesh Reconstruction with UV-unwrapping and Illumination Disentanglement. Stability AI.
