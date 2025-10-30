"""
Shap-E model implementation for Architext
OpenAI's Shap-E model for text-to-3D generation
"""

import torch
import trimesh
import numpy as np
from typing import Dict, Any
from .base_model import Base3DModel, ModelCapabilities, ModelMetadata


class ShapEModel(Base3DModel):
    """
    Shap-E model wrapper for Architext

    Shap-E is OpenAI's text-conditional 3D generation model that
    produces high-quality meshes with implicit neural representations
    """

    def __init__(self, device: str = "cuda", cache_dir: str = None):
        super().__init__(device, cache_dir)
        self.model_name = "shap-e"

    def load_model(self) -> None:
        """Load Shap-E model from HuggingFace"""
        try:
            from diffusers import ShapEPipeline

            print(f"[Shap-E] Loading model on {self.device}...")

            dtype = torch.float16 if self.device == "cuda" else torch.float32

            self.pipeline = ShapEPipeline.from_pretrained(
                "openai/shap-e",
                torch_dtype=dtype,
                cache_dir=self.cache_dir
            )

            self.pipeline = self.pipeline.to(self.device)
            self.model_loaded = True

            print(f"[Shap-E] Model loaded successfully!")

        except Exception as e:
            print(f"[Shap-E] Error loading model: {e}")
            raise

    def generate(
        self,
        prompt: str,
        num_steps: int = 64,
        guidance_scale: float = 15.0,
        frame_size: int = 256,
        **kwargs
    ) -> trimesh.Trimesh:
        """
        Generate 3D mesh from text prompt using Shap-E

        Args:
            prompt: Text description
            num_steps: Number of inference steps (32-128)
            guidance_scale: Guidance scale (7-20)
            frame_size: Resolution (64, 128, 256)
            **kwargs: Additional parameters

        Returns:
            Generated trimesh object
        """
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Validate and preprocess prompt
        if not self.validate_prompt(prompt):
            raise ValueError("Invalid prompt")

        prompt = self.preprocess_prompt(prompt)

        print(f"[Shap-E] Generating from prompt: '{prompt}'")
        print(f"[Shap-E] Parameters: steps={num_steps}, guidance={guidance_scale}, size={frame_size}")

        try:
            # Generate with Shap-E
            output = self.pipeline(
                prompt,
                num_inference_steps=num_steps,
                guidance_scale=guidance_scale,
                frame_size=frame_size,
                output_type="mesh"
            )

            # Extract mesh from Shap-E output
            mesh_output = output.images[0]

            # Convert tensors to numpy arrays
            vertices = mesh_output.verts.cpu().numpy()
            faces = mesh_output.faces.cpu().numpy()

            # Get vertex colors if available
            vertex_colors = None
            if hasattr(mesh_output, 'vertex_channels') and mesh_output.vertex_channels:
                r = mesh_output.vertex_channels['R'].cpu().numpy()
                g = mesh_output.vertex_channels['G'].cpu().numpy()
                b = mesh_output.vertex_channels['B'].cpu().numpy()

                # Stack RGB and add alpha channel (fully opaque)
                vertex_colors = np.stack([r, g, b, np.ones_like(r)], axis=1)
                # Scale to 0-255 range
                vertex_colors = (vertex_colors * 255).astype(np.uint8)

            # Create trimesh object
            mesh = trimesh.Trimesh(
                vertices=vertices,
                faces=faces,
                vertex_colors=vertex_colors
            )

            print(f"[Shap-E] Generated mesh: {len(vertices)} vertices, {len(faces)} faces")

            # Post-process mesh
            mesh = self.postprocess_mesh(mesh, scale_to_meters=True, target_height=3.0)

            return mesh

        except Exception as e:
            print(f"[Shap-E] Error during generation: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """Get Shap-E model information"""
        metadata = get_shap_e_metadata()
        return metadata.to_dict()


def get_shap_e_metadata() -> ModelMetadata:
    """Get Shap-E model metadata"""
    return ModelMetadata(
        name="shap-e",
        display_name="Shap-E",
        version="1.0",
        source="OpenAI",
        description="Text-to-3D generation using implicit neural representations. Produces high-quality meshes with good geometric detail.",
        capabilities=[
            ModelCapabilities.TEXT_TO_3D,
            ModelCapabilities.MESH_OUTPUT,
            ModelCapabilities.TEXTURE_SUPPORT,
            ModelCapabilities.HIGH_DETAIL
        ],
        requirements={
            "gpu_memory": "4GB+ recommended",
            "dependencies": ["diffusers", "torch", "trimesh"],
            "platforms": ["Windows", "Linux", "macOS"]
        },
        limitations=[
            "General-purpose model, not specifically trained on architecture",
            "Quality depends on prompt clarity",
            "May take 1-2 minutes for high-quality generation"
        ]
    )


# Auto-register when imported
def _register():
    """Auto-register Shap-E model"""
    from .model_registry import register_model
    register_model(ShapEModel, get_shap_e_metadata())


_register()
