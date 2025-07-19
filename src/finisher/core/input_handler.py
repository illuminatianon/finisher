"""Enhanced input handling for multiple image sources."""

import logging
import io
from typing import Optional, Callable, Union, Tuple
from PIL import Image, ImageGrab
import base64
import tempfile
import os

from .utils import validate_image_format, get_supported_formats

logger = logging.getLogger(__name__)


class InputHandler:
    """Handles multiple types of image input sources."""
    
    def __init__(self):
        """Initialize input handler."""
        self.on_image_received: Optional[Callable[[str, str], None]] = None  # (source, path_or_data)
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Supported formats
        self.supported_formats = get_supported_formats()
    
    def handle_file_drop(self, file_path: str) -> bool:
        """Handle dropped file.
        
        Args:
            file_path: Path to dropped file
            
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Validate file
            if not os.path.isfile(file_path):
                self._handle_error(f"File not found: {file_path}")
                return False
            
            if not validate_image_format(file_path):
                self._handle_error(f"Unsupported image format: {file_path}")
                return False
            
            logger.info(f"Handling dropped file: {file_path}")
            
            if self.on_image_received:
                self.on_image_received("file_drop", file_path)
            
            return True
            
        except Exception as e:
            self._handle_error(f"Error handling dropped file: {e}")
            return False
    
    def handle_clipboard_paste(self) -> bool:
        """Handle clipboard paste.
        
        Returns:
            True if image found and handled, False otherwise
        """
        try:
            # Try to get image from clipboard
            image = ImageGrab.grabclipboard()
            
            if image is None:
                self._handle_error("No image found in clipboard")
                return False
            
            if not isinstance(image, Image.Image):
                self._handle_error("Clipboard content is not an image")
                return False
            
            logger.info("Handling clipboard image")
            
            # Save to temporary file
            temp_path = self._save_temp_image(image, "clipboard")
            
            if temp_path and self.on_image_received:
                self.on_image_received("clipboard", temp_path)
            
            return True
            
        except Exception as e:
            self._handle_error(f"Error handling clipboard paste: {e}")
            return False
    
    def handle_image_data(self, image_data: bytes, source: str = "data") -> bool:
        """Handle raw image data.
        
        Args:
            image_data: Raw image bytes
            source: Source description
            
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Validate image data
            image = Image.open(io.BytesIO(image_data))
            image.verify()
            
            # Reopen for processing (verify() closes the image)
            image = Image.open(io.BytesIO(image_data))
            
            logger.info(f"Handling image data from {source}")
            
            # Save to temporary file
            temp_path = self._save_temp_image(image, source)
            
            if temp_path and self.on_image_received:
                self.on_image_received(source, temp_path)
            
            return True
            
        except Exception as e:
            self._handle_error(f"Error handling image data: {e}")
            return False
    
    def handle_base64_image(self, base64_data: str, source: str = "base64") -> bool:
        """Handle base64 encoded image.
        
        Args:
            base64_data: Base64 encoded image string
            source: Source description
            
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            # Remove data URL prefix if present
            if base64_data.startswith('data:image/'):
                base64_data = base64_data.split(',', 1)[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_data)
            
            return self.handle_image_data(image_data, source)
            
        except Exception as e:
            self._handle_error(f"Error handling base64 image: {e}")
            return False
    
    def handle_url_drop(self, url: str) -> bool:
        """Handle dropped URL (for future implementation).
        
        Args:
            url: Image URL
            
        Returns:
            True if handled successfully, False otherwise
        """
        # TODO: Implement URL image downloading
        self._handle_error("URL image handling not yet implemented")
        return False
    
    def _save_temp_image(self, image: Image.Image, source: str) -> Optional[str]:
        """Save image to temporary file.
        
        Args:
            image: PIL Image object
            source: Source description for filename
            
        Returns:
            Path to temporary file or None if failed
        """
        try:
            # Create temporary file in docs/temp directory
            from .utils import get_docs_temp_dir
            import re

            suffix = ".png"  # Always save as PNG for consistency
            # Sanitize source name for use in filename (remove invalid characters)
            safe_source = re.sub(r'[<>:"/\\|?*]', '_', source)
            prefix = f"finisher_{safe_source}_"
            docs_temp_dir = get_docs_temp_dir()

            temp_fd, temp_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=prefix,
                dir=docs_temp_dir
            )
            os.close(temp_fd)  # Close file descriptor
            
            # Convert to RGB if necessary (for PNG compatibility)
            if image.mode in ('RGBA', 'LA'):
                # Keep transparency for RGBA/LA
                image.save(temp_path, "PNG")
            else:
                # Convert other modes to RGB
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(temp_path, "PNG")
            
            logger.debug(f"Saved temporary image: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to save temporary image: {e}")
            return None
    
    def _handle_error(self, error_message: str) -> None:
        """Handle input errors.
        
        Args:
            error_message: Error message
        """
        logger.warning(f"Input handler error: {error_message}")
        
        if self.on_error:
            try:
                self.on_error(error_message)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def get_supported_formats_string(self) -> str:
        """Get supported formats as a user-friendly string.
        
        Returns:
            Formatted string of supported formats
        """
        formats = [fmt.upper().lstrip('.') for fmt in self.supported_formats]
        return ", ".join(formats)
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if supported, False otherwise
        """
        return validate_image_format(file_path)


class ClipboardMonitor:
    """Monitors clipboard for image changes using PySide6."""

    def __init__(self, input_handler: InputHandler):
        """Initialize clipboard monitor.

        Args:
            input_handler: Input handler instance
        """
        self.input_handler = input_handler
        self.monitoring = False
        self.last_clipboard_content = None
        self.timer = None

        # Import PySide6 components
        try:
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication
            self.QTimer = QTimer
            self.QApplication = QApplication
        except ImportError:
            logger.warning("PySide6 not available for clipboard monitoring")
            self.QTimer = None
            self.QApplication = None

    def start_monitoring(self, interval: int = 1000) -> None:
        """Start monitoring clipboard.

        Args:
            interval: Check interval in milliseconds
        """
        if self.monitoring or not self.QTimer:
            return

        self.monitoring = True

        # Create timer for periodic checks
        self.timer = self.QTimer()
        self.timer.timeout.connect(self._check_clipboard)
        self.timer.start(interval)

        logger.info("Clipboard monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring clipboard."""
        self.monitoring = False
        if self.timer:
            self.timer.stop()
            self.timer = None
        logger.info("Clipboard monitoring stopped")

    def _check_clipboard(self) -> None:
        """Check clipboard for changes."""
        try:
            # Get current clipboard content
            current_content = ImageGrab.grabclipboard()

            # Check if content changed and is an image
            if (current_content is not None and
                isinstance(current_content, Image.Image) and
                current_content != self.last_clipboard_content):

                logger.debug("New image detected in clipboard")
                self.last_clipboard_content = current_content

                # Handle the new image
                self.input_handler.handle_clipboard_paste()

        except Exception as e:
            logger.debug(f"Clipboard check error: {e}")


class DragDropHandler:
    """Deprecated: Drag and drop handler for tkinter (no longer used with PySide6)."""

    def __init__(self, widget, input_handler: InputHandler):
        """Initialize drag drop handler.

        Args:
            widget: Widget to enable drag and drop on (deprecated)
            input_handler: Input handler instance
        """
        logger.warning("DragDropHandler is deprecated. PySide6 uses native drag-and-drop in ImageDropArea.")
        self.widget = widget
        self.input_handler = input_handler

    def _setup_drag_drop(self) -> None:
        """Deprecated: Set up drag and drop functionality."""
        logger.warning("DragDropHandler._setup_drag_drop is deprecated.")
        pass

    def _setup_basic_drag_drop(self) -> None:
        """Deprecated: Set up basic drag and drop."""
        logger.warning("DragDropHandler._setup_basic_drag_drop is deprecated.")
        pass

    def _on_drop(self, event) -> None:
        """Deprecated: Handle drop event."""
        logger.warning("DragDropHandler._on_drop is deprecated.")
        pass

    def _on_drag_enter(self, event) -> None:
        """Deprecated: Handle drag enter event."""
        logger.warning("DragDropHandler._on_drag_enter is deprecated.")
        pass

    def _on_drag_leave(self, event) -> None:
        """Deprecated: Handle drag leave event."""
        logger.warning("DragDropHandler._on_drag_leave is deprecated.")
        pass

    def _on_click(self, event) -> None:
        """Deprecated: Handle click event."""
        logger.warning("DragDropHandler._on_click is deprecated.")
        pass
