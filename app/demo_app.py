"""
Gradio-based demo application for Architext
Interactive web UI for text-to-3D house generation
Beautiful wood and white themed interface
"""

import gradio as gr
import trimesh
import numpy as np
from PIL import Image
import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core_generator import HouseGenerator


# Custom CSS for dark mode with wood accents and brick theme
CUSTOM_CSS = """
/* Main container - Dark background with subtle texture */
.gradio-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%) !important;
    color: #e0e0e0 !important;
}

/* Header styling with wood accent */
.gradio-container h1 {
    color: #d4a574 !important;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    font-weight: 700 !important;
    border-bottom: 3px solid #8b7355;
    padding-bottom: 15px;
    margin-bottom: 20px;
}

.gradio-container h2, .gradio-container h3 {
    color: #c4a77d !important;
    font-weight: 600 !important;
}

/* Button styling - Wood accent with brick secondary */
.gradio-container button.primary {
    background: linear-gradient(135deg, #8b7355 0%, #6b5d4f 100%) !important;
    border: 2px solid #5d4e37 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    padding: 12px 24px !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4) !important;
    transition: all 0.3s ease !important;
}

.gradio-container button.primary:hover {
    background: linear-gradient(135deg, #a0826a 0%, #8b7355 100%) !important;
    box-shadow: 0 6px 8px rgba(0, 0, 0, 0.5) !important;
    transform: translateY(-2px) !important;
}

/* Secondary buttons - Brick theme */
.gradio-container button.secondary {
    background: linear-gradient(135deg, #8b4513 0%, #a0522d 100%) !important;
    border: 2px solid #654321 !important;
    color: #ffffff !important;
}

/* Input boxes - Dark with wood accents */
.gradio-container input,
.gradio-container textarea {
    background-color: #2a2a2a !important;
    border: 2px solid #5d4e37 !important;
    border-radius: 6px !important;
    padding: 10px !important;
    color: #e0e0e0 !important;
}

.gradio-container input:focus,
.gradio-container textarea:focus {
    border-color: #8b7355 !important;
    box-shadow: 0 0 0 3px rgba(139, 115, 85, 0.3) !important;
    background-color: #333333 !important;
}

/* Labels styling */
.gradio-container label {
    color: #d4a574 !important;
    font-weight: 600 !important;
    margin-bottom: 8px !important;
}

/* Radio and dropdown styling */
.gradio-container .wrap {
    background-color: #2a2a2a !important;
    border: 2px solid #5d4e37 !important;
    border-radius: 8px !important;
    padding: 15px !important;
}

/* Info boxes - Dark with brick accent */
.gradio-container .info {
    background-color: #2d2520 !important;
    border-left: 4px solid #a0522d !important;
    padding: 12px !important;
    border-radius: 4px !important;
    color: #e0e0e0 !important;
}

/* Preview image container */
.gradio-container .image-container {
    background-color: #1f1f1f !important;
    border: 3px solid #5d4e37 !important;
    border-radius: 10px !important;
    padding: 10px !important;
    box-shadow: 0 4px 8px rgba(0,0,0,0.6) !important;
}

/* File download section */
.gradio-container .file-preview {
    background-color: #2a2a2a !important;
    border: 2px dashed #8b7355 !important;
    border-radius: 8px !important;
    padding: 15px !important;
}

/* Example cards */
.gradio-container .examples {
    background-color: #2a2a2a !important;
    border: 2px solid #5d4e37 !important;
    border-radius: 10px !important;
    padding: 20px !important;
    margin-top: 20px !important;
}

/* Footer - Wood gradient */
.gradio-container .footer {
    background: linear-gradient(90deg, #5d4e37 0%, #8b7355 100%) !important;
    color: #ffffff !important;
    padding: 20px !important;
    border-radius: 8px !important;
    margin-top: 30px !important;
}

/* Markdown content styling */
.gradio-container .markdown {
    color: #e0e0e0 !important;
    line-height: 1.6 !important;
}

/* Progress bar - Wood tones */
.gradio-container .progress-bar {
    background-color: #8b7355 !important;
}

/* Slider styling */
.gradio-container input[type="range"] {
    accent-color: #8b7355 !important;
}

/* Tab styling */
.gradio-container .tab-nav button {
    color: #c4a77d !important;
    border-bottom: 2px solid transparent !important;
    background-color: #2a2a2a !important;
}

.gradio-container .tab-nav button.selected {
    color: #d4a574 !important;
    border-bottom: 2px solid #8b7355 !important;
    background-color: #333333 !important;
}

/* Card-like containers - Dark mode */
.card {
    background: #2a2a2a !important;
    border-radius: 12px !important;
    padding: 20px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5) !important;
    margin: 10px 0 !important;
    border: 1px solid #5d4e37 !important;
}

/* Accent dividers - Brick color */
hr {
    border: none !important;
    border-top: 2px solid #a0522d !important;
    margin: 20px 0 !important;
}

/* Model dropdown/radio buttons - Brick accent when selected */
.gradio-container input[type="radio"]:checked + label {
    background-color: #8b4513 !important;
    color: white !important;
}

/* Scrollbar styling for dark mode */
::-webkit-scrollbar {
    width: 12px;
    background-color: #1a1a1a;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #8b7355 0%, #5d4e37 100%);
    border-radius: 6px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #a0826a 0%, #8b7355 100%);
}

/* Loading spinner customization - Dark grey-brown theme */
.gradio-container .wrap.pending {
    background-color: #2a2a2a !important;
    border-color: #5d4e37 !important;
}

/* Customize the loading circle/spinner */
.gradio-container .loading {
    border-color: #4a4034 !important;
    border-top-color: #8b7355 !important;
}

/* Animated spinner with wood theme */
@keyframes spin-wood {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.gradio-container .wrap.pending::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 40px;
    height: 40px;
    margin-top: -20px;
    margin-left: -20px;
    border: 4px solid #4a4034;
    border-top: 4px solid #8b7355;
    border-radius: 50%;
    animation: spin-wood 1s linear infinite;
}

/* Hide default Gradio spinner, use our custom one */
.gradio-container .wrap.pending .loader {
    display: none;
}

/* Progress bar remains wood-themed */
.gradio-container .progress-bar-wrap {
    background-color: #2a2a2a !important;
    border: 2px solid #5d4e37 !important;
}

.gradio-container .progress-bar {
    background: linear-gradient(90deg, #8b7355 0%, #6b5d4f 100%) !important;
}

/* Loading text styling */
.gradio-container .loading-text {
    color: #d4a574 !important;
    font-weight: 600 !important;
}
"""


class ArchitextDemo:
    """
    Gradio demo application for Architext FYP
    Provides interactive UI for text-to-3D house generation
    Beautiful wood and white themed interface
    """

    def __init__(self, default_model: str = "shap-e"):
        """
        Initialize the demo application

        Args:
            default_model: Default model to use ("shap-e" or "point-e")
        """
        self.current_model = default_model
        self.generator = None
        self.current_mesh = None
        self.current_spec = None
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "demo")
        os.makedirs(self.output_dir, exist_ok=True)

        print(f"ArchitextDemo initialized with {default_model}")

    def load_generator(self, model_name: str):
        """Load or switch generator model"""
        if self.generator is None or self.current_model != model_name:
            print(f"Loading {model_name} model...")
            self.generator = HouseGenerator(model_name=model_name)
            self.current_model = model_name
            return f"[SUCCESS] {model_name} loaded successfully!"
        return f"[SUCCESS] {model_name} already loaded"

    def generate_from_text(
        self,
        text_prompt: str,
        model_choice: str,
        quality: str,
        guidance_scale: float,
        progress=gr.Progress()
    ):
        """
        Main generation function for Gradio interface

        Args:
            text_prompt: User's text description
            model_choice: Which model to use
            quality: Quality setting (low/medium/high)
            guidance_scale: Guidance scale for generation
            progress: Gradio progress tracker

        Returns:
            Tuple of (3D model file, preview image, info text, metadata file)
        """
        if not text_prompt or text_prompt.strip() == "":
            return None, None, "[ERROR] Please enter a house description", None

        try:
            # Progress tracking
            progress(0.1, desc="Loading model...")

            # Load model
            model_name = model_choice.lower().replace(" ", "-")
            status = self.load_generator(model_name)
            print(status)

            # Set quality parameters
            quality_settings = {
                "Low (Fast)": {"num_steps": 32, "frame_size": 128},
                "Medium": {"num_steps": 64, "frame_size": 256},
                "High (Slow)": {"num_steps": 128, "frame_size": 256}
            }
            settings = quality_settings[quality]

            progress(0.2, desc="Starting generation...")

            # Generate house
            mesh, spec = self.generator.generate_house(
                text_prompt,
                num_steps=settings["num_steps"],
                guidance_scale=guidance_scale,
                frame_size=settings["frame_size"]
            )

            self.current_mesh = mesh
            self.current_spec = spec

            progress(0.7, desc="Rendering preview...")

            # Create preview image
            preview = self.render_preview(mesh)

            progress(0.8, desc="Generating info...")

            # Generate info text
            info = self.generate_info(spec, mesh)

            progress(0.9, desc="Exporting files...")

            # Export files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"house_{timestamp}"

            # Export mesh as OBJ (primary format for 3D software)
            obj_path = self.generator.export_mesh(
                mesh, base_name, format="obj", output_dir=self.output_dir
            )

            # Also export as PLY (alternative format)
            ply_path = self.generator.export_mesh(
                mesh, base_name, format="ply", output_dir=self.output_dir
            )

            # Export metadata
            metadata_path = self.generator.export_metadata(
                spec, base_name, output_dir=self.output_dir
            )

            progress(1.0, desc="Complete!")

            return obj_path, preview, info, metadata_path

        except Exception as e:
            error_msg = f"[ERROR] Error: {str(e)}\n\nPlease check:\n1. Model is installed correctly\n2. Prompt is valid\n3. Enough memory available"
            print(f"Generation error: {e}")
            import traceback
            traceback.print_exc()
            return None, None, error_msg, None

    def render_preview(self, mesh: trimesh.Trimesh) -> Image.Image:
        """
        Render mesh to image for preview using matplotlib

        Args:
            mesh: Mesh to render

        Returns:
            PIL Image
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection

            # Create figure
            fig = plt.figure(figsize=(10, 8), facecolor='#2d2d2d')
            ax = fig.add_subplot(111, projection='3d', facecolor='#2d2d2d')

            # Get vertices and faces
            vertices = mesh.vertices
            faces = mesh.faces

            # Create mesh collection with vertex colors if available
            if hasattr(mesh.visual, 'vertex_colors') and mesh.visual.vertex_colors is not None:
                colors = mesh.visual.vertex_colors[:, :3] / 255.0  # RGB only, normalize
                mesh_collection = Poly3DCollection(vertices[faces], facecolors=colors[faces].mean(axis=1), edgecolor='#5d4e37', linewidth=0.1, alpha=0.9)
            else:
                mesh_collection = Poly3DCollection(vertices[faces], facecolors='#c4a77d', edgecolor='#5d4e37', linewidth=0.1, alpha=0.9)

            ax.add_collection3d(mesh_collection)

            # Set axis limits
            bounds = mesh.bounds
            ax.set_xlim(bounds[0, 0], bounds[1, 0])
            ax.set_ylim(bounds[0, 1], bounds[1, 1])
            ax.set_zlim(bounds[0, 2], bounds[1, 2])

            # Set viewing angle
            ax.view_init(elev=30, azim=45)

            # Style the plot
            ax.set_xlabel('X', color='#d4a574')
            ax.set_ylabel('Y', color='#d4a574')
            ax.set_zlabel('Z', color='#d4a574')
            ax.tick_params(colors='#d4a574')
            ax.grid(True, color='#5d4e37', alpha=0.3)

            # Title
            ax.set_title('3D House Model Preview', color='#d4a574', fontsize=14, pad=20)

            # Save to buffer
            buf = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buf, format='png', dpi=100, facecolor='#2d2d2d', edgecolor='none')
            buf.seek(0)
            image = Image.open(buf)
            plt.close(fig)

            return image

        except Exception as e:
            print(f"Error rendering preview: {e}")
            import traceback
            traceback.print_exc()
            # Return a placeholder image with dark theme and text
            placeholder = Image.new('RGB', (800, 600), color=(45, 45, 45))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(placeholder)
            draw.text((400, 300), "3D Model Generated\n(Preview rendering unavailable)\nDownload .obj file to view", fill=(212, 165, 116), anchor="mm")
            return placeholder

    def generate_info(self, spec: Dict, mesh: trimesh.Trimesh) -> str:
        """
        Generate information text about the created model

        Args:
            spec: Specifications dictionary
            mesh: Generated mesh

        Returns:
            Formatted info string
        """
        stats = self.generator.get_mesh_stats(mesh)

        info = f"""
## Generated House Specifications

**Input Prompt:** {spec['original_prompt']}

### Detected Features
- **Floors:** {spec['floors']}
- **Style:** {spec['style'].title()}
- **Estimated Rooms:** {spec['rooms']}
- **Features:** {', '.join(spec['features']) if spec['features'] else 'None specified'}

### 3D Mesh Information
- **Vertices:** {stats['vertices']:,}
- **Faces:** {stats['faces']:,}
- **Edges:** {stats['edges']:,}
- **Surface Area:** {stats['area']:.2f} m²
- **Watertight:** {'Yes' if stats['is_watertight'] else 'No'}

### Bounding Box (Real-world Scale)
- **Width (X):** {stats['bounds']['size'][0]:.2f} m
- **Depth (Y):** {stats['bounds']['size'][1]:.2f} m
- **Height (Z):** {stats['bounds']['size'][2]:.2f} m

### Generation Settings
- **Model:** {spec['generation']['model'].upper()}
- **Inference Steps:** {spec['generation']['num_steps']}
- **Guidance Scale:** {spec['generation']['guidance_scale']}
- **Resolution:** {spec['generation']['frame_size']}px

### Export Formats
- **OBJ** - For Blender, Maya, 3DS Max, Revit
- **PLY** - For MeshLab, CloudCompare
- **JSON** - Metadata and specifications

---
*Generated at {spec['timestamp']}*
"""
        return info

    def create_interface(self):
        """Create and configure Gradio interface with beautiful wood theme"""

        # Custom theme with wood and white colors
        theme = gr.themes.Soft(
            primary_hue="orange",
            secondary_hue="stone",
            neutral_hue="stone",
            font=("Segoe UI", "Arial", "sans-serif")
        ).set(
            body_background_fill="linear-gradient(135deg, #f5f5f0 0%, #e8e8dc 100%)",
            button_primary_background_fill="linear-gradient(135deg, #8b7355 0%, #6b5d4f 100%)",
            button_primary_background_fill_hover="linear-gradient(135deg, #6b5d4f 0%, #5d4e37 100%)",
            button_primary_border_color="#5d4e37",
            button_primary_text_color="white",
            input_background_fill="white",
            input_border_color="#c4b5a0",
        )

        with gr.Blocks(
            title="Architext - AI House Generator",
            theme=theme,
            css=CUSTOM_CSS
        ) as demo:

            # Header
            gr.Markdown("""
            # Architext: AI Text-to-House Generation
            ### *Transform Your Words Into 3D Architecture*

            **FYP Iteration 1 Demo** | Team: Umer Abdullah, Jalal Sherazi, Arfeen Awan

            Welcome to Architext - where imagination meets innovation. Describe your dream house in natural language,
            and watch as AI brings it to life in stunning 3D.
            """)

            gr.Markdown("---")

            with gr.Row(equal_height=True):
                # Left column - Input Panel
                with gr.Column(scale=1):
                    gr.Markdown("### Design Your House")

                    with gr.Group():
                        text_input = gr.Textbox(
                            label="House Description",
                            placeholder="e.g., 'A modern two-story house with large windows and a garage'\n\nBe creative! Describe the style, features, and character you envision...",
                            lines=5,
                            info="Tip: Be specific about architectural style and key features"
                        )

                    with gr.Group():
                        gr.Markdown("#### Generation Settings")

                        model_choice = gr.Radio(
                            choices=["Shap-E", "Point-E"],
                            value="Shap-E",
                            label="AI Model",
                            info="Shap-E recommended for higher quality meshes"
                        )

                        quality = gr.Radio(
                            choices=["Low (Fast)", "Medium", "High (Slow)"],
                            value="Medium",
                            label="Generation Quality",
                            info="Medium balances quality and speed"
                        )

                        guidance_scale = gr.Slider(
                            minimum=7.0,
                            maximum=20.0,
                            value=15.0,
                            step=0.5,
                            label="Guidance Scale",
                            info="Higher values follow prompt more literally"
                        )

                    generate_btn = gr.Button(
                        "Generate My House",
                        variant="primary",
                        size="lg",
                        elem_classes=["generate-button"]
                    )

                    with gr.Accordion("Pro Tips", open=False):
                        gr.Markdown("""
                        **For Best Results:**
                        - Specify architectural style (modern, traditional, contemporary)
                        - Mention number of floors
                        - Include key features (windows, garage, balcony)
                        - Add aesthetic details (minimalist, Victorian, rustic)
                        - Start with Medium quality for testing

                        **Example Prompts:**
                        - "A sleek modern house with flat roof and floor-to-ceiling windows"
                        - "Traditional two-story suburban home with white picket fence"
                        - "Cozy cottage with stone chimney and wooden porch"
                        """)

                # Right column - Output Panel
                with gr.Column(scale=1):
                    gr.Markdown("### Your Generated House")

                    with gr.Group():
                        preview_image = gr.Image(
                            label="3D Preview",
                            type="pil",
                            show_label=True,
                            elem_classes=["preview-image"]
                        )

                    with gr.Group():
                        gr.Markdown("#### Download Files")

                        model_output = gr.File(
                            label="3D Model (OBJ format)",
                            file_types=[".obj"],
                            file_count="single"
                        )

                        metadata_output = gr.File(
                            label="Metadata (JSON)",
                            file_types=[".json"],
                            file_count="single"
                        )

            # Info section
            gr.Markdown("---")
            with gr.Group():
                info_output = gr.Markdown(
                    label="Model Information",
                    value="*Generate a house to see detailed specifications here*",
                    elem_classes=["info-box"]
                )

            # Examples section
            gr.Markdown("---")
            gr.Markdown("### Example Prompts - Click to Try")

            with gr.Group(elem_classes=["examples"]):
                gr.Examples(
                    examples=[
                        ["A modern minimalist house with flat roof and large glass windows", "Shap-E", "Medium", 15.0],
                        ["Traditional two-story suburban home with garage and chimney", "Shap-E", "Medium", 15.0],
                        ["Small cottage with pitched roof and front porch", "Shap-E", "Medium", 15.0],
                        ["Contemporary house with balcony and modern architecture", "Shap-E", "Medium", 15.0],
                        ["Victorian style house with ornate details and turret", "Shap-E", "Medium", 16.0],
                        ["Ranch style single-story house with wide layout", "Shap-E", "Low (Fast)", 12.0],
                        ["Mediterranean villa with terrace and arches", "Shap-E", "Medium", 15.0],
                        ["Craftsman style house with exposed beams and stone base", "Shap-E", "Medium", 15.0],
                    ],
                    inputs=[text_input, model_choice, quality, guidance_scale],
                    label="Try These Prompts"
                )

            # Footer
            gr.Markdown("---")
            gr.Markdown("""
            <div style='background: linear-gradient(90deg, #8b7355 0%, #6b5d4f 100%);
                        padding: 25px; border-radius: 10px; color: white;'>

            ### About Architext

            **Architext** is an AI-powered text-to-3D house generation system developed as part of our Final Year Project.
            It uses state-of-the-art diffusion models to transform natural language descriptions into detailed 3D architectural models.

            **Project Goals:**
            - Enable rapid architectural prototyping through natural language
            - Integrate with BIM software (Revit) for professional workflows
            - Democratize 3D architectural visualization

            **Current Status:** Iteration 1 - Proof of Concept with Pre-trained Models

            **Next Steps:**
            1. Import OBJ file into Blender, Revit, or your preferred 3D software
            2. Refine and customize the generated model
            3. Add textures, materials, and fine details
            4. Use for visualization, presentations, or further development

            **Note:** This iteration uses pre-trained general models. Future iterations will include:
            - Custom training on architectural datasets
            - Direct Revit plugin integration
            - Structural analysis and feasibility checking
            - Advanced customization controls

            ---

            **Team:** Umer Abdullah (22i-1349), Jalal Sherazi (22i-8755), Arfeen Awan (22i-2645)
            **Institution:** IBA Karachi | **Year:** 2024-2025

            </div>
            """)

            # Connect the generate button
            generate_btn.click(
                fn=self.generate_from_text,
                inputs=[text_input, model_choice, quality, guidance_scale],
                outputs=[model_output, preview_image, info_output, metadata_output]
            )

        return demo

    def launch(self, share: bool = True, server_port: int = 7860, server_name: str = "0.0.0.0"):
        """
        Launch the Gradio interface

        Args:
            share: Create public link (default: True for demo)
            server_port: Port to run on (default: 7860)
            server_name: Server name (default: 0.0.0.0 for all interfaces)
        """
        demo = self.create_interface()

        print("\n" + "="*70)
        print("ARCHITEXT - AI HOUSE GENERATOR")
        print("="*70)
        print(f"Launching beautiful wood-themed interface...")
        print(f"Server: http://localhost:{server_port}")
        print(f"Port: {server_port}")
        if share:
            print("Public URL will be generated for sharing")
        print("\nThe interface features:")
        print("   - Beautiful wood and white theme")
        print("   - Professional architectural design")
        print("   - Easy-to-use controls")
        print("   - Multiple example prompts")
        print("\nPress Ctrl+C to stop the server")
        print("="*70 + "\n")

        demo.launch(
            share=share,
            server_port=server_port,
            server_name=server_name,
            show_error=True,
            favicon_path=None,  # Could add custom favicon
            show_api=False
        )


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Architext Demo - AI Text-to-3D House Generator"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="shap-e",
        choices=["shap-e", "point-e"],
        help="Default model to use (default: shap-e)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run server on (default: 7860)"
    )
    parser.add_argument(
        "--no-share",
        action="store_true",
        help="Don't create public share link"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )

    args = parser.parse_args()

    # Create and launch app
    app = ArchitextDemo(default_model=args.model)
    app.launch(
        share=not args.no_share,
        server_port=args.port,
        server_name=args.host
    )


if __name__ == "__main__":
    main()
