"""
Logging configuration for Architext
Provides structured logging with file rotation and console output
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

# Try to import config, fallback to defaults if not available
try:
    from config import get_config
    config = get_config()
except ImportError:
    # Fallback configuration
    class FallbackConfig:
        LOG_LEVEL = "INFO"
        LOG_FILE = Path("logs") / "architext.log"
        LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
        LOG_BACKUP_COUNT = 5
        LOGS_DIR = Path("logs")

    config = FallbackConfig()
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(
    name: str = "architext",
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Set up a logger with console and file handlers

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)

    Returns:
        Configured logger instance
    """

    # Get or create logger
    logger = logging.getLogger(name)

    # Set level
    log_level = level or config.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler (simplified output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed output with rotation)
    try:
        file_path = log_file or config.LOG_FILE
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    except Exception as e:
        logger.warning(f"Could not create file handler: {e}")

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "architext") -> logging.Logger:
    """
    Get a logger instance (creates if doesn't exist)

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # Set up logger if it doesn't have handlers
    if not logger.handlers:
        return setup_logger(name)

    return logger


class LoggerMixin:
    """
    Mixin class to add logging capability to any class

    Usage:
        class MyClass(LoggerMixin):
            def my_method(self):
                self.logger.info("Doing something")
    """

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def log_function_call(func):
    """
    Decorator to log function calls with arguments and results

    Usage:
        @log_function_call
        def my_function(arg1, arg2):
            return result
    """
    logger = get_logger(func.__module__)

    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args[:2]}, kwargs={list(kwargs.keys())}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}", exc_info=True)
            raise

    return wrapper


def log_generation_metrics(
    prompt: str,
    model_name: str,
    generation_time: float,
    success: bool,
    error: Optional[str] = None
):
    """
    Log generation metrics in a structured format

    Args:
        prompt: Input prompt
        model_name: Model used
        generation_time: Time taken in seconds
        success: Whether generation succeeded
        error: Error message if failed
    """
    logger = get_logger("architext.metrics")

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "prompt_length": len(prompt),
        "model": model_name,
        "duration_seconds": round(generation_time, 2),
        "success": success
    }

    if error:
        metrics["error"] = str(error)

    if success:
        logger.info(f"Generation successful: {metrics}")
    else:
        logger.error(f"Generation failed: {metrics}")


# Create default logger instance
default_logger = setup_logger()


if __name__ == "__main__":
    # Test logging
    logger = get_logger("test")

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test metrics logging
    log_generation_metrics(
        prompt="a modern house",
        model_name="shap-e",
        generation_time=45.2,
        success=True
    )

    print(f"Logs written to: {config.LOG_FILE}")
