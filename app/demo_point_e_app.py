"""
Point-E Demo Web App
Standalone demo for testing Point-E model
"""
import gradio as gr
import torch
import numpy as np
from point_e.diffusion.configs import DIFFUSION_CONFIGS, diffusion_from_config
from point_e.diffusion.sampler import PointCloudSampler
from point_e.models.configs import MODEL_CONFIGS, model_from_config
import trimesh
import io
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Initialize device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Load Point-E models
print("Loading Point-E models...")
base_model = model_from_config(MODEL_CONFIGS['base40M-textvec'], device)
base_model.eval()
base_diffusion = diffusion_from_config(DIFFUSION_CONFIGS['base40M-textvec'])

upsampler_model = model_from_config(MODEL_CONFIGS['upsample'], device)
upsampler_model.eval()
upsampler_diffusion = diffusion_from_config(DIFFUSION_CONFIGS['upsample'])

sampler = PointCloudSampler(
    device=device,
    models=[base_model, upsampler_model],
    diffusions=[base_diffusion, upsampler_diffusion],
    num_points=[1024, 4096 - 1024],
    aux_channels=['R', 'G', 'B'],
    guidance_scale=[7.0, 7.0],  # High guidance for quality
)
print("Models loaded successfully!")

def generate_house(prompt, guidance_scale=7.0):
    """Generate 3D house from text prompt"""
    try:
        # Update guidance
        sampler.guidance_scale = [guidance_scale, guidance_scale]

        # Generate point cloud
        samples = None
        for x in sampler.sample_batch_progressive(batch_size=1, model_kwargs=dict(texts=[prompt])):
            samples = x

        # Extract point cloud
        pc = sampler.output_to_point_clouds(samples)[0]
        coords = pc.coords
        colors = np.stack([pc.channels['R'], pc.channels['G'], pc.channels['B']], axis=-1)

        # Create mesh using subdivided convex hull (most reliable method)
        mesh = trimesh.convex.convex_hull(coords)

        # Subdivide for better detail
        mesh = mesh.subdivide()
        mesh = mesh.subdivide()  # Subdivide twice

        # Map colors from point cloud to mesh vertices
        from scipy.spatial import cKDTree
        tree = cKDTree(coords)
        _, indices = tree.query(mesh.vertices, k=5)
        neighbor_colors = colors[indices]
        vertex_colors = neighbor_colors.mean(axis=1)
        mesh.visual.vertex_colors = (vertex_colors * 255).astype(np.uint8)

        # Save files
        timestamp = str(int(np.random.rand() * 1000000))

        # Save mesh as PLY
        mesh_path = f"D:/Work/Uni/FYP/architext/outputs/point_e_web_{timestamp}.ply"
        mesh.export(mesh_path)

        # Save mesh as OBJ
        obj_path = f"D:/Work/Uni/FYP/architext/outputs/point_e_web_{timestamp}.obj"
        mesh.export(obj_path)

        # Create 3D preview image
        preview_img = render_3d_preview(mesh)

        # Stats
        stats = f"""
### Generation Statistics

- **Model**: Point-E (OpenAI)
- **Points Generated**: {len(coords):,}
- **Mesh Vertices**: {len(mesh.vertices):,}
- **Mesh Faces**: {len(mesh.faces):,}
- **Guidance Scale**: {guidance_scale}
- **Has Colors**: Yes
"""

        return preview_img, mesh_path, obj_path, stats, "[SUCCESS] House generated!"

    except Exception as e:
        import traceback
        error_msg = f"[ERROR] Generation failed: {str(e)}\n{traceback.format_exc()}"
        return None, None, None, error_msg, error_msg


def render_3d_preview(mesh):
    """Render 3D preview of mesh"""
    try:
        fig = plt.figure(figsize=(10, 8), facecolor='#2d2d2d')
        ax = fig.add_subplot(111, projection='3d', facecolor='#2d2d2d')

        # Get mesh data
        vertices = mesh.vertices
        faces = mesh.faces

        # Create mesh collection
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
            colors = mesh.visual.vertex_colors[:, :3] / 255.0
            face_colors = colors[faces].mean(axis=1)
        else:
            face_colors = '#c4a77d'

        mesh_collection = Poly3DCollection(
            vertices[faces],
            facecolors=face_colors,
            edgecolor='#5d4e37',
            linewidth=0.1,
            alpha=0.9
        )

        ax.add_collection3d(mesh_collection)

        # Set bounds
        bounds = mesh.bounds
        ax.set_xlim(bounds[0, 0], bounds[1, 0])
        ax.set_ylim(bounds[0, 1], bounds[1, 1])
        ax.set_zlim(bounds[0, 2], bounds[1, 2])

        # Set view angle
        ax.view_init(elev=30, azim=45)

        # Style axes
        ax.set_xlabel('X', color='#e0e0e0')
        ax.set_ylabel('Y', color='#e0e0e0')
        ax.set_zlabel('Z', color='#e0e0e0')
        ax.tick_params(colors='#e0e0e0')
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False

        # Save to buffer
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, facecolor='#2d2d2d')
        buf.seek(0)
        image = Image.open(buf)
        plt.close(fig)

        return image

    except Exception as e:
        print(f"Preview rendering failed: {e}")
        # Return placeholder
        placeholder = Image.new('RGB', (800, 600), color=(45, 45, 45))
        return placeholder


# Custom CSS
CUSTOM_CSS = """
.gradio-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%) !important;
    color: #e0e0e0 !important;
}

.gr-button-primary {
    background: linear-gradient(135deg, #8b7355 0%, #6b5d4f 100%) !important;
    border: 2px solid #5d4e37 !important;
    color: #ffffff !important;
}

.gr-button-secondary {
    background: linear-gradient(135deg, #a0522d 0%, #8b4513 100%) !important;
    border: 2px solid #6b3410 !important;
    color: #ffffff !important;
}

h1, h2, h3 {
    color: #d4a574 !important;
}
"""

# Create Gradio interface
with gr.Blocks(css=CUSTOM_CSS, title="Point-E Demo - Architext") as demo:
    gr.Markdown("""
    # Point-E 3D House Generator
    ### OpenAI's Point-E Model - Text to 3D Point Cloud
    Generate 3D house models from text descriptions using Point-E
    """)

    with gr.Row():
        with gr.Column(scale=1):
            prompt_input = gr.Textbox(
                label="House Description",
                placeholder="a detailed modern two-story house with windows and door",
                value="a modern two-story house with windows, door, and sloped roof",
                lines=3
            )

            guidance_slider = gr.Slider(
                minimum=1.0,
                maximum=15.0,
                value=7.0,
                step=0.5,
                label="Guidance Scale (higher = more detailed)",
            )

            generate_btn = gr.Button("Generate My House", variant="primary", size="lg")

            status_output = gr.Textbox(label="Status", lines=2)

        with gr.Column(scale=1):
            preview_output = gr.Image(label="3D Preview", type="pil")

    with gr.Row():
        stats_output = gr.Markdown("### Awaiting generation...")

    with gr.Row():
        ply_output = gr.File(label="Download PLY")
        obj_output = gr.File(label="Download OBJ")

    gr.Markdown("""
    ### How to Use Point-E Output:
    1. **PLY File**: Open in Blender (File → Import → Stanford), MeshLab, or Windows 3D Viewer
    2. **OBJ File**: Universal format for Blender, Revit, 3ds Max, etc.
    3. **Guidance Scale**: Higher values (7-15) give more structure, lower values (1-5) more creative

    ### Model Info:
    - **Point-E**: Generates 4,096 colored points then converts to mesh
    - **Generation Time**: 3-5 minutes per model
    - **Quality**: Good for prototyping, uses subdivided convex hull
    """)

    # Event handler
    generate_btn.click(
        fn=generate_house,
        inputs=[prompt_input, guidance_slider],
        outputs=[preview_output, ply_output, obj_output, stats_output, status_output]
    )

# Launch app
if __name__ == "__main__":
    print("\n" + "="*60)
    print("POINT-E DEMO APP STARTING")
    print("="*60)
    print(f"Device: {device}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print("="*60 + "\n")

    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,
        share=False,
        show_error=True
    )
