"""Finisher - AI Image Upscaling Tool using Automatic1111 API."""

__version__ = "0.0.0"
__author__ = "illuminatianon"
__email__ = "me@illuminati.com"
__description__ = "AI Image Upscaling Tool using Automatic1111 API"

# Package imports for convenience
from .app_controller import ApplicationController
from .api import Auto1111Client, ConfigurationManager
from .core import ImageProcessor, MetadataExtractor
from .gui import MainWindow

__all__ = [
    "ApplicationController",
    "Auto1111Client",
    "ConfigurationManager",
    "ImageProcessor",
    "MetadataExtractor",
    "MainWindow",
]
