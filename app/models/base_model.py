"""
Base model interface for all 3D generation models in Architext
Provides a consistent API for different model implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import trimesh
import numpy as np


class Base3DModel(ABC):
    """
    Abstract base class for all 3D generation models

    All model implementations must inherit from this class and implement
    the required methods to ensure consistency across different models.
    """

    def __init__(self, device: str = "cuda", cache_dir: Optional[str] = None):
        """
        Initialize the base model

        Args:
            device: Device to run model on ("cuda" or "cpu")
            cache_dir: Directory to cache model weights
        """
        self.device = device
        self.cache_dir = cache_dir
        self.pipeline = None
        self.model_loaded = False

    @abstractmethod
    def load_model(self) -> None:
        """
        Load the model and prepare it for inference
        Must be implemented by each model
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        num_steps: int = 64,
        guidance_scale: float = 15.0,
        **kwargs
    ) -> trimesh.Trimesh:
        """
        Generate 3D mesh from text prompt

        Args:
            prompt: Text description
            num_steps: Number of inference steps
            guidance_scale: How closely to follow the prompt
            **kwargs: Additional model-specific parameters

        Returns:
            Generated trimesh object
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about this model

        Returns:
            Dictionary with model metadata (name, version, source, etc.)
        """
        pass

    def validate_prompt(self, prompt: str) -> bool:
        """
        Validate if prompt is appropriate for this model

        Args:
            prompt: Text prompt to validate

        Returns:
            True if valid, False otherwise
        """
        if not prompt or len(prompt.strip()) == 0:
            return False
        return True

    def preprocess_prompt(self, prompt: str) -> str:
        """
        Preprocess prompt before generation (can be overridden)

        Args:
            prompt: Original prompt

        Returns:
            Preprocessed prompt
        """
        # Ensure "house" or "building" is mentioned for architectural focus
        prompt_lower = prompt.lower()
        if "house" not in prompt_lower and "building" not in prompt_lower:
            prompt += " house"
        return prompt

    def postprocess_mesh(
        self,
        mesh: trimesh.Trimesh,
        scale_to_meters: bool = True,
        target_height: float = 3.0
    ) -> trimesh.Trimesh:
        """
        Post-process generated mesh (can be overridden)

        Args:
            mesh: Raw generated mesh
            scale_to_meters: Whether to scale to real-world dimensions
            target_height: Target height per floor in meters

        Returns:
            Processed mesh
        """
        # Remove degenerate faces
        mesh.remove_degenerate_faces()

        # Fix normals
        mesh.fix_normals()

        # Merge duplicate vertices
        mesh.merge_vertices()

        if scale_to_meters:
            # Scale to reasonable house dimensions
            bounds = mesh.bounds
            current_size = bounds[1] - bounds[0]

            # Target size: 10m x 10m x target_height
            target_size = np.array([10.0, 10.0, target_height])
            scale_factor = np.min(target_size / (current_size + 1e-6))
            mesh.apply_scale(scale_factor)

        # Center at origin
        mesh.vertices -= mesh.centroid

        return mesh

    def get_generation_stats(self, mesh: trimesh.Trimesh) -> Dict[str, Any]:
        """
        Get statistics about the generated mesh

        Args:
            mesh: Generated mesh

        Returns:
            Dictionary with mesh statistics
        """
        bounds = mesh.bounds
        size = bounds[1] - bounds[0]

        return {
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "edges": int(len(mesh.edges)) if hasattr(mesh, 'edges') else 0,
            "is_watertight": bool(mesh.is_watertight),
            "is_winding_consistent": bool(mesh.is_winding_consistent),
            "bounds": {
                "min": bounds[0].tolist(),
                "max": bounds[1].tolist(),
                "size": size.tolist()
            },
            "volume": float(mesh.volume) if mesh.is_watertight else None,
            "area": float(mesh.area)
        }

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model_loaded

    def unload_model(self) -> None:
        """
        Unload model from memory (optional, can be overridden)
        Useful for freeing GPU memory when switching models
        """
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
        self.model_loaded = False

        # Force garbage collection
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class ModelCapabilities:
    """
    Enum-like class defining model capabilities
    Used to indicate what features each model supports
    """
    TEXT_TO_3D = "text_to_3d"
    IMAGE_TO_3D = "image_to_3d"
    POINT_CLOUD = "point_cloud"
    MESH_OUTPUT = "mesh_output"
    TEXTURE_SUPPORT = "texture_support"
    HIGH_DETAIL = "high_detail"
    FAST_GENERATION = "fast_generation"
    ARCHITECTURAL_OPTIMIZED = "architectural_optimized"


class ModelMetadata:
    """
    Metadata container for model information
    """
    def __init__(
        self,
        name: str,
        display_name: str,
        version: str,
        source: str,
        description: str,
        capabilities: list,
        requirements: Dict[str, Any] = None,
        limitations: list = None
    ):
        self.name = name
        self.display_name = display_name
        self.version = version
        self.source = source
        self.description = description
        self.capabilities = capabilities
        self.requirements = requirements or {}
        self.limitations = limitations or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "source": self.source,
            "description": self.description,
            "capabilities": self.capabilities,
            "requirements": self.requirements,
            "limitations": self.limitations
        }
