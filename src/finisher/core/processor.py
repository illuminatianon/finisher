"""Image processing pipeline for upscaling workflow."""

import logging
from typing import Tuple
from PIL import Image
import io
from .metadata import MetadataExtractor
from .utils import (
    encode_image_to_base64,
    decode_base64_to_image,
    validate_image_format,
)

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image processing for the upscaling pipeline."""

    def __init__(self):
        """Initialize the image processor."""
        self.metadata_extractor = MetadataExtractor()

    def prepare_image_for_processing(
        self, image_path: str
    ) -> Tuple[str, str, str, int, int]:
        """Prepare an image file for API processing.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (base64_image, prompt, negative_prompt, width, height)

        Raises:
            ValueError: If image format is invalid
            IOError: If image cannot be loaded
        """
        logger.info(f"Preparing image for processing: {image_path}")

        # Validate image format
        if not validate_image_format(image_path):
            raise ValueError(f"Unsupported image format: {image_path}")

        # Load and convert image
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Extract metadata before conversion
                prompt, negative_prompt = self.metadata_extractor.extract_prompts(img)

                # Encode to base64
                base64_image = encode_image_to_base64(img)

                width, height = img.size
                logger.info(f"Image prepared successfully. Size: {width}x{height}")
                return base64_image, prompt, negative_prompt, width, height

        except Exception as e:
            logger.error(f"Failed to prepare image: {e}")
            raise IOError(f"Cannot load image: {e}")

    def prepare_image_data_for_processing(
        self, image_data: bytes
    ) -> Tuple[str, str, str, int, int]:
        """Prepare raw image data for API processing.

        Args:
            image_data: Raw image bytes

        Returns:
            Tuple of (base64_image, prompt, negative_prompt, width, height)

        Raises:
            ValueError: If image data is invalid
            IOError: If image cannot be processed
        """
        logger.info("Preparing image data for processing")

        try:
            # Load image from bytes
            img = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Extract metadata
            prompt, negative_prompt = self.metadata_extractor.extract_prompts(img)

            # Encode to base64
            base64_image = encode_image_to_base64(img)

            width, height = img.size
            logger.info(f"Image data prepared successfully. Size: {width}x{height}")
            return base64_image, prompt, negative_prompt, width, height

        except Exception as e:
            logger.error(f"Failed to prepare image data: {e}")
            raise IOError(f"Cannot process image data: {e}")

    def process_base64_result(self, base64_result: str) -> Image.Image:
        """Process base64 result from API into PIL Image.

        Args:
            base64_result: Base64 encoded image from API

        Returns:
            PIL Image object

        Raises:
            ValueError: If base64 data is invalid
        """
        logger.info("Processing base64 result from API")

        try:
            image = decode_base64_to_image(base64_result)
            logger.info(f"Base64 result processed successfully. Size: {image.size}")
            return image

        except Exception as e:
            logger.error(f"Failed to process base64 result: {e}")
            raise ValueError(f"Invalid base64 image data: {e}")

    def validate_image_dimensions(
        self, image: Image.Image, max_width: int = 4096, max_height: int = 4096
    ) -> bool:
        """Validate image dimensions are within acceptable limits.

        Args:
            image: PIL Image to validate
            max_width: Maximum allowed width
            max_height: Maximum allowed height

        Returns:
            True if dimensions are valid, False otherwise
        """
        width, height = image.size

        if width > max_width or height > max_height:
            logger.warning(
                f"Image dimensions {width}x{height} exceed limits "
                f"{max_width}x{max_height}"
            )
            return False

        if width < 64 or height < 64:
            logger.warning(
                f"Image dimensions {width}x{height} too small (minimum 64x64)"
            )
            return False

        return True

    def resize_image_if_needed(
        self, image: Image.Image, max_dimension: int = 2048
    ) -> Image.Image:
        """Resize image if it exceeds maximum dimension while preserving aspect ratio.

        Args:
            image: PIL Image to potentially resize
            max_dimension: Maximum allowed dimension (width or height)

        Returns:
            Resized image or original if no resize needed
        """
        width, height = image.size

        if width <= max_dimension and height <= max_dimension:
            return image

        # Calculate new dimensions preserving aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int((height * max_dimension) / width)
        else:
            new_height = max_dimension
            new_width = int((width * max_dimension) / height)

        logger.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")

        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized
