"""
Configuration management for Architext
Handles environment variables, settings, and deployment configuration
"""

import os
from pathlib import Path
from typing import Optional
import json


class Config:
    """
    Centralized configuration management
    Supports multiple environments: development, staging, production
    """

    def __init__(self, env: Optional[str] = None):
        """
        Initialize configuration

        Args:
            env: Environment name (development, staging, production)
                 If None, reads from ARCHITEXT_ENV environment variable
        """
        self.env = env or os.getenv("ARCHITEXT_ENV", "development")
        self.base_dir = Path(__file__).parent.absolute()

        # Load environment-specific settings
        self._load_settings()

    def _load_settings(self):
        """Load environment-specific settings"""

        # Base paths
        self.PROJECT_ROOT = self.base_dir
        self.APP_DIR = self.base_dir / "app"
        self.OUTPUT_DIR = self.base_dir / "outputs"
        self.MODELS_CACHE_DIR = self.base_dir / "models"
        self.DATA_DIR = self.base_dir / "data"
        self.LOGS_DIR = self.base_dir / "logs"

        # Create directories if they don't exist
        for dir_path in [self.OUTPUT_DIR, self.MODELS_CACHE_DIR,
                        self.DATA_DIR, self.LOGS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Server settings
        self.SERVER_HOST = os.getenv("ARCHITEXT_HOST", "0.0.0.0")
        self.SERVER_PORT = int(os.getenv("ARCHITEXT_PORT", "7860"))
        self.DEBUG = os.getenv("ARCHITEXT_DEBUG", "false").lower() == "true"

        # Model settings
        self.DEFAULT_MODEL = os.getenv("ARCHITEXT_MODEL", "shap-e")
        self.MODEL_CACHE_DIR = os.getenv("ARCHITEXT_MODEL_CACHE",
                                        str(self.MODELS_CACHE_DIR))

        # Generation settings
        self.DEFAULT_QUALITY = os.getenv("ARCHITEXT_QUALITY", "medium")
        self.DEFAULT_GUIDANCE_SCALE = float(os.getenv(
            "ARCHITEXT_GUIDANCE_SCALE", "15.0"))
        self.MAX_INFERENCE_STEPS = int(os.getenv(
            "ARCHITEXT_MAX_STEPS", "128"))

        # Gradio settings
        self.GRADIO_SHARE = os.getenv(
            "ARCHITEXT_SHARE", "true").lower() == "true"
        self.GRADIO_AUTH = self._parse_auth()
        self.GRADIO_THEME = os.getenv("ARCHITEXT_THEME", "architext_wood")

        # Performance settings
        self.USE_GPU = os.getenv(
            "ARCHITEXT_USE_GPU", "true").lower() == "true"
        self.MAX_BATCH_SIZE = int(os.getenv("ARCHITEXT_MAX_BATCH", "1"))
        self.MEMORY_LIMIT_GB = int(os.getenv("ARCHITEXT_MEMORY_LIMIT", "8"))

        # Logging settings
        self.LOG_LEVEL = os.getenv("ARCHITEXT_LOG_LEVEL", "INFO")
        self.LOG_FILE = self.LOGS_DIR / f"architext_{self.env}.log"
        self.LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.LOG_MAX_BYTES = int(os.getenv("ARCHITEXT_LOG_MAX_BYTES",
                                           str(10 * 1024 * 1024)))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv("ARCHITEXT_LOG_BACKUPS", "5"))

        # Security settings
        self.ENABLE_CORS = os.getenv(
            "ARCHITEXT_ENABLE_CORS", "false").lower() == "true"
        self.ALLOWED_ORIGINS = self._parse_list(
            os.getenv("ARCHITEXT_ALLOWED_ORIGINS", ""))
        self.MAX_FILE_SIZE_MB = int(os.getenv(
            "ARCHITEXT_MAX_FILE_SIZE", "50"))

        # Feature flags
        self.ENABLE_ANALYTICS = os.getenv(
            "ARCHITEXT_ANALYTICS", "false").lower() == "true"
        self.ENABLE_RATE_LIMITING = os.getenv(
            "ARCHITEXT_RATE_LIMIT", "false").lower() == "true"
        self.RATE_LIMIT_PER_MINUTE = int(os.getenv(
            "ARCHITEXT_RATE_LIMIT_RPM", "10"))

        # Environment-specific overrides
        self._apply_env_overrides()

    def _apply_env_overrides(self):
        """Apply environment-specific configuration overrides"""

        if self.env == "production":
            self.DEBUG = False
            self.LOG_LEVEL = "WARNING"
            self.ENABLE_RATE_LIMITING = True
            self.GRADIO_SHARE = False  # Use reverse proxy in production

        elif self.env == "staging":
            self.DEBUG = False
            self.LOG_LEVEL = "INFO"
            self.ENABLE_RATE_LIMITING = True

        elif self.env == "development":
            self.DEBUG = True
            self.LOG_LEVEL = "DEBUG"
            self.GRADIO_SHARE = True
            self.ENABLE_RATE_LIMITING = False

    def _parse_auth(self):
        """Parse authentication credentials from environment"""
        auth_str = os.getenv("ARCHITEXT_AUTH", "")
        if not auth_str:
            return None

        # Format: "username:password" or "user1:pass1,user2:pass2"
        try:
            auth_pairs = []
            for pair in auth_str.split(","):
                username, password = pair.split(":")
                auth_pairs.append((username.strip(), password.strip()))
            return auth_pairs
        except Exception:
            return None

    def _parse_list(self, value: str):
        """Parse comma-separated list from environment variable"""
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def get_model_settings(self, model_name: Optional[str] = None):
        """
        Get model-specific settings

        Args:
            model_name: Model name (defaults to DEFAULT_MODEL)

        Returns:
            Dictionary of model settings
        """
        model_name = model_name or self.DEFAULT_MODEL

        # Quality presets
        quality_presets = {
            "low": {"num_steps": 32, "frame_size": 128},
            "medium": {"num_steps": 64, "frame_size": 256},
            "high": {"num_steps": 128, "frame_size": 256}
        }

        return {
            "model_name": model_name,
            "cache_dir": self.MODEL_CACHE_DIR,
            "use_gpu": self.USE_GPU,
            "quality_presets": quality_presets,
            "default_quality": self.DEFAULT_QUALITY,
            "guidance_scale": self.DEFAULT_GUIDANCE_SCALE,
            "max_steps": self.MAX_INFERENCE_STEPS
        }

    def to_dict(self):
        """Convert configuration to dictionary (for logging/debugging)"""
        return {
            "environment": self.env,
            "server": {
                "host": self.SERVER_HOST,
                "port": self.SERVER_PORT,
                "debug": self.DEBUG
            },
            "model": {
                "default": self.DEFAULT_MODEL,
                "cache_dir": str(self.MODEL_CACHE_DIR),
                "use_gpu": self.USE_GPU
            },
            "paths": {
                "project_root": str(self.PROJECT_ROOT),
                "output_dir": str(self.OUTPUT_DIR),
                "logs_dir": str(self.LOGS_DIR)
            },
            "logging": {
                "level": self.LOG_LEVEL,
                "file": str(self.LOG_FILE)
            },
            "features": {
                "analytics": self.ENABLE_ANALYTICS,
                "rate_limiting": self.ENABLE_RATE_LIMITING,
                "cors": self.ENABLE_CORS
            }
        }

    def __repr__(self):
        """String representation of configuration"""
        return f"<Config env={self.env}>"


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance"""
    return config


def reload_config(env: Optional[str] = None):
    """Reload configuration (useful for testing)"""
    global config
    config = Config(env=env)
    return config
