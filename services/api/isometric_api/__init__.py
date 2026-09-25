"""FastAPI service for upload and job control."""

__version__ = "0.1.0"

from .app import app, create_app

__all__ = ["app", "create_app", "__version__"]
