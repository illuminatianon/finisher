"""Batch input handling for multiple files and directories."""

import logging
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Callable

from .utils import validate_image_format
from ..config.defaults import IMAGE_LIMITS

logger = logging.getLogger(__name__)


class BatchInputHandler:
    """Handles multiple file inputs and batch operations."""

    def __init__(self):
        """Initialize batch input handler."""
        self.supported_formats = IMAGE_LIMITS["supported_formats"]
        self.max_file_size = IMAGE_LIMITS["max_file_size"]

        # Callbacks
        self.on_batch_validated: Optional[Callable[[List[str], str], None]] = None
        self.on_validation_error: Optional[Callable[[str], None]] = None
        self.on_progress: Optional[Callable[[str, int, int], None]] = None

    def handle_multiple_files(
        self, file_paths: List[str], batch_name: Optional[str] = None
    ) -> Tuple[List[str], List[str], str]:
        """Create batch job from multiple files.

        Args:
            file_paths: List of file paths
            batch_name: Optional name for the batch

        Returns:
            Tuple of (valid_files, invalid_files, batch_id)
        """
        logger.info(f"Processing batch of {len(file_paths)} files")

        # Validate all files
        valid_files, invalid_files = self.validate_batch_input(file_paths)

        if not valid_files:
            error_msg = (
                f"No valid image files found in batch of {len(file_paths)} files"
            )
            logger.warning(error_msg)
            if self.on_validation_error:
                self.on_validation_error(error_msg)
            return [], invalid_files, ""

        # Generate batch name if not provided
        if not batch_name:
            batch_name = self._generate_batch_name(valid_files)

        # Generate batch ID
        batch_id = self._generate_batch_id(batch_name)

        logger.info(f"Created batch '{batch_name}' with {len(valid_files)} valid files")

        if invalid_files:
            logger.warning(f"Skipped {len(invalid_files)} invalid files")

        # Notify callback
        if self.on_batch_validated:
            self.on_batch_validated(valid_files, batch_id)

        return valid_files, invalid_files, batch_id

    def handle_directory_drop(
        self,
        directory_path: str,
        recursive: bool = True,
        batch_name: Optional[str] = None,
    ) -> Tuple[List[str], List[str], str]:
        """Process all images in dropped directory.

        Args:
            directory_path: Path to directory
            recursive: Whether to search subdirectories
            batch_name: Optional name for the batch

        Returns:
            Tuple of (valid_files, invalid_files, batch_id)
        """
        logger.info(f"Processing directory: {directory_path} (recursive={recursive})")

        if not os.path.isdir(directory_path):
            error_msg = f"Path is not a directory: {directory_path}"
            logger.error(error_msg)
            if self.on_validation_error:
                self.on_validation_error(error_msg)
            return [], [], ""

        # Find all image files
        image_files = self._find_image_files(directory_path, recursive)

        if not image_files:
            error_msg = f"No image files found in directory: {directory_path}"
            logger.warning(error_msg)
            if self.on_validation_error:
                self.on_validation_error(error_msg)
            return [], [], ""

        # Generate batch name if not provided
        if not batch_name:
            dir_name = os.path.basename(directory_path.rstrip(os.sep))
            batch_name = f"Directory: {dir_name}"

        # Process as batch
        return self.handle_multiple_files(image_files, batch_name)

    def validate_batch_input(
        self, file_paths: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Validate batch input files.

        Args:
            file_paths: List of file paths to validate

        Returns:
            Tuple of (valid_files, invalid_files) with reasons
        """
        valid_files = []
        invalid_files = []

        total_files = len(file_paths)

        for i, file_path in enumerate(file_paths):
            # Report progress
            if self.on_progress:
                self.on_progress(
                    f"Validating {os.path.basename(file_path)}",
                    i + 1,
                    total_files,
                )

            try:
                # Check if file exists
                if not os.path.isfile(file_path):
                    invalid_files.append(f"{file_path}: File not found")
                    continue

                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size > self.max_file_size:
                    size_mb = file_size / (1024 * 1024)
                    max_mb = self.max_file_size / (1024 * 1024)
                    invalid_files.append(
                        f"{file_path}: File too large "
                        f"({size_mb:.1f}MB > {max_mb:.1f}MB)"
                    )
                    continue

                if file_size == 0:
                    invalid_files.append(f"{file_path}: Empty file")
                    continue

                # Check file format
                if not validate_image_format(file_path):
                    invalid_files.append(f"{file_path}: Unsupported image format")
                    continue

                # File is valid
                valid_files.append(file_path)

            except Exception as e:
                invalid_files.append(f"{file_path}: Validation error - {str(e)}")

        logger.info(
            f"Validation complete: {len(valid_files)} valid, {len(invalid_files)} invalid"
        )
        return valid_files, invalid_files

    def _find_image_files(
        self, directory_path: str, recursive: bool = True
    ) -> List[str]:
        """Find all image files in directory.

        Args:
            directory_path: Directory to search
            recursive: Whether to search subdirectories

        Returns:
            List of image file paths
        """
        image_files = []

        try:
            if recursive:
                # Use pathlib for recursive search
                path = Path(directory_path)
                for ext in self.supported_formats:
                    # Search for files with this extension (case insensitive)
                    pattern = f"**/*{ext}"
                    for file_path in path.glob(pattern):
                        if file_path.is_file():
                            image_files.append(str(file_path))

                    # Also search for uppercase extensions
                    pattern = f"**/*{ext.upper()}"
                    for file_path in path.glob(pattern):
                        if file_path.is_file():
                            image_files.append(str(file_path))
            else:
                # Search only in the current directory
                for filename in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, filename)
                    if os.path.isfile(file_path):
                        _, ext = os.path.splitext(filename)
                        if ext.lower() in self.supported_formats:
                            image_files.append(file_path)

            # Remove duplicates and sort
            image_files = sorted(list(set(image_files)))

        except Exception as e:
            logger.error(f"Error finding image files in {directory_path}: {e}")

        return image_files

    def _generate_batch_name(self, file_paths: List[str]) -> str:
        """Generate a descriptive batch name.

        Args:
            file_paths: List of file paths in the batch

        Returns:
            Generated batch name
        """
        if not file_paths:
            return "Empty Batch"

        # If all files are from the same directory, use directory name
        directories = set(os.path.dirname(path) for path in file_paths)
        if len(directories) == 1:
            dir_name = os.path.basename(list(directories)[0])
            if dir_name:
                return f"{dir_name} ({len(file_paths)} files)"

        # Otherwise, use a generic name
        return f"Batch of {len(file_paths)} files"

    def _generate_batch_id(self, batch_name: str) -> str:
        """Generate a unique batch ID.

        Args:
            batch_name: Name of the batch

        Returns:
            Unique batch ID
        """
        from datetime import datetime
        import uuid

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:8]
        return f"batch_{timestamp}_{short_uuid}"

    def get_batch_summary(
        self, valid_files: List[str], invalid_files: List[str]
    ) -> Dict[str, Any]:
        """Get summary information about a batch.

        Args:
            valid_files: List of valid file paths
            invalid_files: List of invalid files with reasons

        Returns:
            Dictionary with batch summary
        """
        total_size = 0
        file_types = {}

        for file_path in valid_files:
            try:
                # Get file size
                size = os.path.getsize(file_path)
                total_size += size

                # Count file types
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()
                file_types[ext] = file_types.get(ext, 0) + 1

            except Exception as e:
                logger.warning(f"Error getting info for {file_path}: {e}")

        return {
            "total_files": len(valid_files) + len(invalid_files),
            "valid_files": len(valid_files),
            "invalid_files": len(invalid_files),
            "total_size_mb": total_size / (1024 * 1024),
            "file_types": file_types,
            "invalid_reasons": invalid_files,
        }
