"""
Model Registry for managing multiple 3D generation models
Provides dynamic model loading and switching
"""

from typing import Dict, Type, Optional, List
from .base_model import Base3DModel, ModelMetadata
import importlib


class ModelRegistry:
    """
    Central registry for all available 3D generation models
    Handles model discovery, loading, and switching
    """

    def __init__(self):
        self._models: Dict[str, Type[Base3DModel]] = {}
        self._metadata: Dict[str, ModelMetadata] = {}
        self._loaded_instances: Dict[str, Base3DModel] = {}

    def register_model(
        self,
        model_class: Type[Base3DModel],
        metadata: ModelMetadata
    ) -> None:
        """
        Register a new model class

        Args:
            model_class: The model class (must inherit from Base3DModel)
            metadata: Model metadata
        """
        if not issubclass(model_class, Base3DModel):
            raise TypeError(f"Model class must inherit from Base3DModel")

        model_name = metadata.name
        self._models[model_name] = model_class
        self._metadata[model_name] = metadata

        print(f"[Registry] Registered model: {metadata.display_name} ({model_name})")

    def get_model(
        self,
        model_name: str,
        device: str = "cuda",
        cache_dir: Optional[str] = None,
        load_immediately: bool = True
    ) -> Base3DModel:
        """
        Get or create a model instance

        Args:
            model_name: Name of the model
            device: Device to run on
            cache_dir: Cache directory for model weights
            load_immediately: Whether to load model weights immediately

        Returns:
            Model instance

        Raises:
            ValueError: If model not found
        """
        if model_name not in self._models:
            available = ", ".join(self._models.keys())
            raise ValueError(
                f"Model '{model_name}' not found. Available models: {available}"
            )

        # Check if already loaded
        if model_name in self._loaded_instances:
            instance = self._loaded_instances[model_name]
            # Verify device matches
            if instance.device == device:
                return instance
            else:
                # Need to reload on different device
                print(f"[Registry] Reloading {model_name} on {device}")
                instance.unload_model()
                del self._loaded_instances[model_name]

        # Create new instance
        model_class = self._models[model_name]
        instance = model_class(device=device, cache_dir=cache_dir)

        if load_immediately:
            instance.load_model()

        self._loaded_instances[model_name] = instance
        return instance

    def unload_model(self, model_name: str) -> None:
        """
        Unload a model from memory

        Args:
            model_name: Name of model to unload
        """
        if model_name in self._loaded_instances:
            self._loaded_instances[model_name].unload_model()
            del self._loaded_instances[model_name]
            print(f"[Registry] Unloaded model: {model_name}")

    def unload_all(self) -> None:
        """Unload all models from memory"""
        for model_name in list(self._loaded_instances.keys()):
            self.unload_model(model_name)

    def get_metadata(self, model_name: str) -> ModelMetadata:
        """
        Get metadata for a model

        Args:
            model_name: Name of the model

        Returns:
            Model metadata

        Raises:
            ValueError: If model not found
        """
        if model_name not in self._metadata:
            raise ValueError(f"Model '{model_name}' not found")
        return self._metadata[model_name]

    def list_models(self) -> List[str]:
        """
        List all registered model names

        Returns:
            List of model names
        """
        return list(self._models.keys())

    def list_metadata(self) -> List[ModelMetadata]:
        """
        List metadata for all registered models

        Returns:
            List of ModelMetadata objects
        """
        return list(self._metadata.values())

    def is_model_loaded(self, model_name: str) -> bool:
        """
        Check if a model is currently loaded

        Args:
            model_name: Name of the model

        Returns:
            True if loaded, False otherwise
        """
        return (
            model_name in self._loaded_instances
            and self._loaded_instances[model_name].is_loaded()
        )

    def get_models_by_capability(self, capability: str) -> List[str]:
        """
        Get models that have a specific capability

        Args:
            capability: Capability to filter by (from ModelCapabilities)

        Returns:
            List of model names with that capability
        """
        return [
            name
            for name, metadata in self._metadata.items()
            if capability in metadata.capabilities
        ]


# Global singleton instance
_global_registry = ModelRegistry()


def get_global_registry() -> ModelRegistry:
    """Get the global model registry singleton"""
    return _global_registry


def register_model(model_class: Type[Base3DModel], metadata: ModelMetadata) -> None:
    """
    Convenience function to register a model to the global registry

    Args:
        model_class: The model class
        metadata: Model metadata
    """
    _global_registry.register_model(model_class, metadata)
