"""Enhanced input handling for multiple image sources."""

import logging
import io
import tkinter as tk
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
            # Create temporary file
            suffix = ".png"  # Always save as PNG for consistency
            prefix = f"finisher_{source}_"
            
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
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
    """Monitors clipboard for image changes."""
    
    def __init__(self, root: tk.Tk, input_handler: InputHandler):
        """Initialize clipboard monitor.
        
        Args:
            root: Tkinter root window
            input_handler: Input handler instance
        """
        self.root = root
        self.input_handler = input_handler
        self.monitoring = False
        self.last_clipboard_content = None
        
    def start_monitoring(self, interval: int = 1000) -> None:
        """Start monitoring clipboard.
        
        Args:
            interval: Check interval in milliseconds
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self._check_clipboard()
        
        # Schedule next check
        self.root.after(interval, lambda: self._schedule_check(interval))
        
        logger.info("Clipboard monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring clipboard."""
        self.monitoring = False
        logger.info("Clipboard monitoring stopped")
    
    def _schedule_check(self, interval: int) -> None:
        """Schedule next clipboard check.
        
        Args:
            interval: Check interval in milliseconds
        """
        if self.monitoring:
            self._check_clipboard()
            self.root.after(interval, lambda: self._schedule_check(interval))
    
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
    """Enhanced drag and drop handler."""
    
    def __init__(self, widget: tk.Widget, input_handler: InputHandler):
        """Initialize drag drop handler.
        
        Args:
            widget: Widget to enable drag and drop on
            input_handler: Input handler instance
        """
        self.widget = widget
        self.input_handler = input_handler
        
        self._setup_drag_drop()
    
    def _setup_drag_drop(self) -> None:
        """Set up drag and drop functionality."""
        try:
            # Try to import tkinterdnd2
            from tkinterdnd2 import DND_FILES, TkinterDnD

            # Enable drag and drop
            self.widget.drop_target_register(DND_FILES)
            self.widget.dnd_bind('<<Drop>>', self._on_drop)
            self.widget.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.widget.dnd_bind('<<DragLeave>>', self._on_drag_leave)

            logger.info("Enhanced drag and drop enabled")

        except (ImportError, Exception) as e:
            logger.warning(f"Enhanced drag and drop not available ({e}), using basic drag and drop")
            self._setup_basic_drag_drop()
    
    def _setup_basic_drag_drop(self) -> None:
        """Set up basic drag and drop using tkinter events."""
        # Basic implementation using tkinter events
        # This is limited but provides some functionality
        self.widget.bind('<Button-1>', self._on_click)
    
    def _on_drop(self, event) -> None:
        """Handle drop event.
        
        Args:
            event: Drop event
        """
        try:
            # Get dropped files
            files = event.data.split()
            
            # Process first valid image file
            for file_path in files:
                # Remove curly braces if present
                file_path = file_path.strip('{}')
                
                if self.input_handler.is_supported_format(file_path):
                    self.input_handler.handle_file_drop(file_path)
                    break
            
        except Exception as e:
            logger.error(f"Error handling drop event: {e}")
    
    def _on_drag_enter(self, event) -> None:
        """Handle drag enter event."""
        # Visual feedback for drag enter
        self.widget.config(bg="lightblue")
    
    def _on_drag_leave(self, event) -> None:
        """Handle drag leave event."""
        # Reset visual feedback
        self.widget.config(bg="lightgray")
    
    def _on_click(self, event) -> None:
        """Handle click event for basic implementation."""
        # This could trigger file browser as fallback
        pass
