"""Core utilities for image processing and file handling."""

import base64
import io
import tempfile
import os
import logging
from typing import List, Optional
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)

# Global list to track temporary files for cleanup
_temp_files: List[str] = []


def encode_image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Encode PIL Image to base64 string.
    
    Args:
        image: PIL Image object
        format: Image format for encoding (PNG, JPEG)
        
    Returns:
        Base64 encoded image string
        
    Raises:
        ValueError: If encoding fails
    """
    try:
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        
        image_bytes = buffer.getvalue()
        base64_string = base64.b64encode(image_bytes).decode('utf-8')
        
        logger.debug(f"Encoded image to base64: {len(base64_string)} characters")
        return base64_string
        
    except Exception as e:
        logger.error(f"Failed to encode image to base64: {e}")
        raise ValueError(f"Cannot encode image: {e}")


def decode_base64_to_image(base64_string: str) -> Image.Image:
    """Decode base64 string to PIL Image.
    
    Args:
        base64_string: Base64 encoded image string
        
    Returns:
        PIL Image object
        
    Raises:
        ValueError: If decoding fails
    """
    try:
        # Remove data URL prefix if present
        if base64_string.startswith('data:image/'):
            base64_string = base64_string.split(',', 1)[1]
        
        image_bytes = base64.b64decode(base64_string)
        buffer = io.BytesIO(image_bytes)
        image = Image.open(buffer)
        
        logger.debug(f"Decoded base64 to image: {image.size}")
        return image
        
    except Exception as e:
        logger.error(f"Failed to decode base64 to image: {e}")
        raise ValueError(f"Cannot decode base64 image: {e}")


def validate_image_format(file_path: str) -> bool:
    """Validate if file is a supported image format.
    
    Args:
        file_path: Path to image file
        
    Returns:
        True if format is supported, False otherwise
    """
    supported_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
    
    try:
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension not in supported_extensions:
            logger.warning(f"Unsupported file extension: {extension}")
            return False
        
        # Try to open the image to verify it's valid
        with Image.open(file_path) as img:
            img.verify()
        
        logger.debug(f"Validated image format: {file_path}")
        return True
        
    except Exception as e:
        logger.warning(f"Invalid image file {file_path}: {e}")
        return False


def create_temp_file(image: Image.Image, suffix: str = ".png") -> str:
    """Create a temporary file for an image.
    
    Args:
        image: PIL Image object
        suffix: File suffix/extension
        
    Returns:
        Path to temporary file
        
    Raises:
        IOError: If file creation fails
    """
    try:
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="finisher_")
        os.close(temp_fd)  # Close file descriptor, we'll use the path
        
        # Save image to temporary file
        image.save(temp_path)
        
        # Track for cleanup
        _temp_files.append(temp_path)
        
        logger.debug(f"Created temporary file: {temp_path}")
        return temp_path
        
    except Exception as e:
        logger.error(f"Failed to create temporary file: {e}")
        raise IOError(f"Cannot create temporary file: {e}")


def cleanup_temp_files() -> None:
    """Clean up all tracked temporary files."""
    global _temp_files
    
    cleaned_count = 0
    for temp_file in _temp_files:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                cleaned_count += 1
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")
    
    logger.info(f"Cleaned up {cleaned_count} temporary files")
    _temp_files.clear()


def get_image_info(file_path: str) -> dict:
    """Get basic information about an image file.
    
    Args:
        file_path: Path to image file
        
    Returns:
        Dictionary with image information
        
    Raises:
        IOError: If image cannot be read
    """
    try:
        with Image.open(file_path) as img:
            info = {
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
            }
        
        # Add file size
        file_size = os.path.getsize(file_path)
        info["file_size"] = file_size
        
        logger.debug(f"Got image info for {file_path}: {info}")
        return info
        
    except Exception as e:
        logger.error(f"Failed to get image info for {file_path}: {e}")
        raise IOError(f"Cannot read image info: {e}")


def convert_image_format(image: Image.Image, target_format: str = "RGB") -> Image.Image:
    """Convert image to target format.
    
    Args:
        image: PIL Image object
        target_format: Target color format (RGB, RGBA, L, etc.)
        
    Returns:
        Converted image
    """
    if image.mode == target_format:
        return image
    
    try:
        converted = image.convert(target_format)
        logger.debug(f"Converted image from {image.mode} to {target_format}")
        return converted
        
    except Exception as e:
        logger.error(f"Failed to convert image format: {e}")
        raise ValueError(f"Cannot convert image format: {e}")


def is_image_file(file_path: str) -> bool:
    """Check if file path points to an image file.
    
    Args:
        file_path: Path to check
        
    Returns:
        True if file is an image, False otherwise
    """
    if not os.path.isfile(file_path):
        return False
    
    return validate_image_format(file_path)


def get_supported_formats() -> List[str]:
    """Get list of supported image formats.
    
    Returns:
        List of supported file extensions
    """
    return ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp']
