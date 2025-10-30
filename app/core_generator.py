"""
Core house generation module for Architext
Handles text-to-3D generation using various pretrained models
"""

import torch
import trimesh
import numpy as np
from typing import Optional, Dict, Any, Tuple
import json
from datetime import datetime
import os
from pathlib import Path


class HouseGenerator:
    """
    Main class for generating 3D house models from text prompts
    Supports multiple models: Shap-E, Point-E, etc.
    """

    SUPPORTED_MODELS = ["shap-e", "point-e"]

    def __init__(self, model_name: str = "shap-e", cache_dir: Optional[str] = None):
        """
        Initialize the house generator

        Args:
            model_name: Name of the model to use ("shap-e" or "point-e")
            cache_dir: Directory to cache models (default: ./models)
        """
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model_name} not supported. Choose from {self.SUPPORTED_MODELS}")

        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        self.pipeline = None

        print(f"Initializing HouseGenerator with {model_name} on {self.device}")
        self.load_model()

    def load_model(self):
        """Load the selected pre-trained model"""
        from diffusers import ShapEPipeline, DiffusionPipeline

        print(f"Loading {self.model_name} model...")

        try:
            dtype = torch.float16 if self.device == "cuda" else torch.float32

            if self.model_name == "shap-e":
                self.pipeline = ShapEPipeline.from_pretrained(
                    "openai/shap-e",
                    torch_dtype=dtype
                    # Use default HuggingFace cache to reuse already downloaded model
                )
            elif self.model_name == "point-e":
                self.pipeline = DiffusionPipeline.from_pretrained(
                    "openai/point-e-base",
                    torch_dtype=dtype,
                    cache_dir=self.cache_dir
                )

            self.pipeline = self.pipeline.to(self.device)
            print(f"[SUCCESS] {self.model_name} loaded successfully!")

        except Exception as e:
            print(f"[ERROR] Error loading model: {e}")
            raise

    def parse_house_requirements(self, text_input: str) -> Dict[str, Any]:
        """
        Extract house specifications from text using keyword matching

        Args:
            text_input: User's text description

        Returns:
            Dictionary with extracted specifications
        """
        text_lower = text_input.lower()

        # Extract number of floors
        floors = 1
        if any(word in text_lower for word in ["two story", "two-story", "2 story", "two floor", "2 floor"]):
            floors = 2
        elif any(word in text_lower for word in ["three story", "3 story", "three floor"]):
            floors = 3

        # Extract style
        style = "traditional"
        if "modern" in text_lower or "contemporary" in text_lower:
            style = "modern"
        elif "cottage" in text_lower or "cabin" in text_lower:
            style = "cottage"
        elif "victorian" in text_lower:
            style = "victorian"
        elif "minimalist" in text_lower:
            style = "minimalist"

        # Extract features
        features = []
        feature_keywords = {
            "garage": ["garage", "car port"],
            "chimney": ["chimney", "fireplace"],
            "balcony": ["balcony", "terrace"],
            "windows": ["window", "glass"],
            "porch": ["porch", "veranda"],
            "roof": ["roof", "pitched roof", "flat roof"]
        }

        for feature, keywords in feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.append(feature)

        # Estimate rooms (rough heuristic)
        rooms = 3  # default
        if floors >= 2:
            rooms = 4
        if "large" in text_lower or "big" in text_lower:
            rooms += 1
        if "small" in text_lower or "compact" in text_lower:
            rooms = 2

        spec = {
            "floors": floors,
            "style": style,
            "features": features,
            "rooms": rooms,
            "original_prompt": text_input,
            "timestamp": datetime.now().isoformat()
        }

        return spec

    def enhance_prompt(self, base_prompt: str) -> str:
        """
        Enhance the user prompt with architectural keywords for better generation

        Args:
            base_prompt: Original user prompt

        Returns:
            Enhanced prompt string
        """
        # Ensure "house" is mentioned
        if "house" not in base_prompt.lower() and "building" not in base_prompt.lower():
            base_prompt += " house"

        # Add architectural context
        enhancements = [
            "architectural 3D model",
            "residential building",
            "detailed structure"
        ]

        enhanced = f"{base_prompt}, {', '.join(enhancements)}"
        return enhanced

    def generate_house(
        self,
        text_prompt: str,
        num_steps: int = 64,
        guidance_scale: float = 15.0,
        frame_size: int = 256
    ) -> Tuple[trimesh.Trimesh, Dict[str, Any]]:
        """
        Generate 3D house mesh from text prompt

        Args:
            text_prompt: Text description of the house
            num_steps: Number of inference steps (more = better quality, slower)
            guidance_scale: How closely to follow the prompt (7-20 typical)
            frame_size: Resolution of generated model (64, 128, 256)

        Returns:
            Tuple of (mesh, specifications_dict)
        """
        if self.pipeline is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        print(f"\nGenerating house from prompt: '{text_prompt}'")

        # Parse requirements
        spec = self.parse_house_requirements(text_prompt)
        print(f"Detected specs: {spec['floors']} floors, {spec['style']} style, features: {spec['features']}")

        # Enhance prompt
        enhanced_prompt = self.enhance_prompt(text_prompt)
        print(f"Enhanced prompt: '{enhanced_prompt}'")

        # Generate based on model type
        print(f"Running {self.model_name} inference with {num_steps} steps...")

        try:
            if self.model_name == "shap-e":
                output = self.pipeline(
                    enhanced_prompt,
                    num_inference_steps=num_steps,
                    guidance_scale=guidance_scale,
                    frame_size=frame_size,
                    output_type="mesh"
                )

                # Extract mesh from Shap-E output
                # The output.images contains MeshDecoderOutput objects with verts and faces
                mesh_output = output.images[0]

                # Convert tensors to numpy and create trimesh object
                vertices = mesh_output.verts.cpu().numpy()
                faces = mesh_output.faces.cpu().numpy()

                # Get vertex colors if available (RGB channels)
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
                mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_colors=vertex_colors)

            elif self.model_name == "point-e":
                output = self.pipeline(
                    enhanced_prompt,
                    num_inference_steps=num_steps,
                )
                # Convert point cloud to mesh
                point_cloud = output.point_clouds[0] if hasattr(output, 'point_clouds') else output[0]
                points = np.array(point_cloud)
                mesh = trimesh.convex.convex_hull(points)

            print(f"[SUCCESS] Generation complete!")

            # Post-process mesh
            mesh = self.post_process_mesh(mesh, spec)

            # Add generation info to spec
            spec["generation"] = {
                "model": self.model_name,
                "num_steps": num_steps,
                "guidance_scale": guidance_scale,
                "frame_size": frame_size,
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces)
            }

            return mesh, spec

        except Exception as e:
            print(f"[ERROR] Error during generation: {e}")
            raise

    def post_process_mesh(self, mesh: trimesh.Trimesh, spec: Dict) -> trimesh.Trimesh:
        """
        Clean and scale the mesh appropriately

        Args:
            mesh: Raw generated mesh
            spec: House specifications

        Returns:
            Processed mesh
        """
        # Remove degenerate faces
        mesh.remove_degenerate_faces()

        # Fix normals
        mesh.fix_normals()

        # Merge duplicate vertices
        mesh.merge_vertices()

        # Scale to reasonable house dimensions
        # Typical house: 10m x 10m x 3m per floor
        bounds = mesh.bounds
        current_size = bounds[1] - bounds[0]

        # Target size based on floors
        height = 3.0 * spec.get("floors", 1)  # 3m per floor
        target_size = np.array([10.0, 10.0, height])  # meters

        # Scale uniformly to fit within target bounds
        scale_factor = np.min(target_size / (current_size + 1e-6))
        mesh.apply_scale(scale_factor)

        # Center at origin
        mesh.vertices -= mesh.centroid

        # Ensure proper orientation (Y-up for most 3D software)
        # Apply 90-degree rotation if needed
        if np.abs(mesh.bounds[1][2] - mesh.bounds[0][2]) < 0.1:  # If very flat in Z
            mesh.apply_transform(trimesh.transformations.rotation_matrix(
                np.pi / 2, [1, 0, 0]
            ))

        print(f"Mesh post-processed: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

        return mesh

    def export_mesh(
        self,
        mesh: trimesh.Trimesh,
        filename: str,
        format: str = "obj",
        output_dir: Optional[str] = None
    ) -> str:
        """
        Export mesh to file

        Args:
            mesh: Mesh to export
            filename: Base filename (without extension)
            format: File format ("obj", "ply", "stl", "gltf")
            output_dir: Output directory (default: ./outputs)

        Returns:
            Path to exported file
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{filename}.{format}")
        mesh.export(output_path)

        print(f"Exported to: {output_path}")
        return output_path

    def export_metadata(
        self,
        spec: Dict[str, Any],
        filename: str,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Export generation metadata as JSON

        Args:
            spec: Specifications dictionary
            filename: Base filename (without extension)
            output_dir: Output directory (default: ./outputs)

        Returns:
            Path to exported JSON file
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")

        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{filename}.json")

        with open(output_path, 'w') as f:
            json.dump(spec, f, indent=2)

        print(f"Metadata exported to: {output_path}")
        return output_path

    def get_mesh_stats(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """Get statistics about a mesh"""
        bounds = mesh.bounds
        size = bounds[1] - bounds[0]

        return {
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "edges": len(mesh.edges),
            "is_watertight": mesh.is_watertight,
            "is_winding_consistent": mesh.is_winding_consistent,
            "bounds": {
                "min": bounds[0].tolist(),
                "max": bounds[1].tolist(),
                "size": size.tolist()
            },
            "volume": float(mesh.volume) if mesh.is_watertight else None,
            "area": float(mesh.area)
        }


# Convenience function for quick generation
def generate_quick(prompt: str, model: str = "shap-e", quality: str = "medium") -> Tuple[trimesh.Trimesh, Dict]:
    """
    Quick generation function for simple use cases

    Args:
        prompt: Text description
        model: Model to use
        quality: "low", "medium", or "high"

    Returns:
        Tuple of (mesh, spec)
    """
    quality_settings = {
        "low": {"num_steps": 32, "frame_size": 128},
        "medium": {"num_steps": 64, "frame_size": 256},
        "high": {"num_steps": 128, "frame_size": 256}
    }

    settings = quality_settings.get(quality, quality_settings["medium"])

    generator = HouseGenerator(model_name=model)
    mesh, spec = generator.generate_house(prompt, **settings)

    return mesh, spec


if __name__ == "__main__":
    # Test the generator
    print("Testing HouseGenerator...")

    generator = HouseGenerator(model_name="shap-e")

    test_prompt = "a modern two-story house with large windows"
    mesh, spec = generator.generate_house(test_prompt, num_steps=64)

    # Export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generator.export_mesh(mesh, f"test_house_{timestamp}", format="obj")
    generator.export_metadata(spec, f"test_house_{timestamp}")

    stats = generator.get_mesh_stats(mesh)
    print(f"\nMesh stats: {json.dumps(stats, indent=2)}")

    print("\n[SUCCESS] Test complete!")
