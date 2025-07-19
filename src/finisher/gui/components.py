"""GUI components for the main window."""

import logging
from typing import Optional, Callable, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QComboBox, QSpinBox, QDoubleSpinBox, QGridLayout,
    QGroupBox
)
from PySide6.QtCore import Qt, Signal, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QDragEnterEvent, QDropEvent

logger = logging.getLogger(__name__)


class StatusBar(QWidget):
    """Status bar component for showing progress and status."""

    def __init__(self, parent: QWidget):
        """Initialize status bar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Add stretch to push progress bar to the right
        layout.addStretch()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)  # Initially hidden
        layout.addWidget(self.progress_bar)

        # Add to parent's status bar if it's a QMainWindow
        if hasattr(parent, 'statusBar') and callable(getattr(parent, 'statusBar')):
            parent.statusBar().addPermanentWidget(self)
        else:
            # If not a QMainWindow, add ourselves to the parent's layout
            if hasattr(parent, 'layout') and parent.layout():
                parent.layout().addWidget(self)

    def update_status(self, status: str, progress: Optional[float] = None) -> None:
        """Update status and progress.

        Args:
            status: Status text
            progress: Progress value (0.0 to 1.0) or None to hide
        """
        self.status_label.setText(status)

        if progress is not None:
            progress_percent = int(progress * 100)
            self.progress_bar.setValue(progress_percent)
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)


class ProgressIndicator(QWidget):
    """Standalone progress indicator component."""

    def __init__(self, parent: QWidget):
        """Initialize progress indicator.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)  # Set initial value to 0
        layout.addWidget(self.progress_bar)

        # Label
        self.label = QLabel("")
        layout.addWidget(self.label)

    def update_progress(self, progress: float, text: str = "") -> None:
        """Update progress indicator.

        Args:
            progress: Progress value (0.0 to 1.0)
            text: Optional text to display
        """
        self.progress_bar.setValue(int(progress * 100))
        self.label.setText(text)

    def show(self) -> None:
        """Show the progress indicator."""
        super().show()

    def hide(self) -> None:
        """Hide the progress indicator."""
        super().hide()


class ImageDropArea(QWidget):
    """Drag and drop area for images."""

    # Define signals for callbacks
    image_dropped = Signal(str)
    file_selected = Signal()

    def __init__(self, parent: QWidget):
        """Initialize image drop area.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.on_image_dropped: Optional[Callable[[str], None]] = None
        self.on_file_selected: Optional[Callable[[str], None]] = None
        self.on_image_data_dropped: Optional[Callable[[bytes, str], None]] = None

        self._setup_ui()
        self._setup_drag_drop()

    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Create layout for the parent group box
        parent_widget = self.parent()
        if isinstance(parent_widget, QGroupBox):
            parent_layout = QVBoxLayout(parent_widget)
            parent_layout.addWidget(self)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Instructions label
        self.instructions = QLabel("Drop image files here\nor click to browse")
        self.instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.instructions.setStyleSheet("""
            QLabel {
                background-color: lightgray;
                color: darkgray;
                font-size: 12pt;
                border: 2px solid gray;
                border-style: inset;
                padding: 20px;
            }
        """)
        self.instructions.setMinimumHeight(150)
        layout.addWidget(self.instructions)

        # Make the widget clickable
        self.instructions.mousePressEvent = self._on_click
    
    def _setup_drag_drop(self) -> None:
        """Set up drag and drop functionality."""
        # Enable drag and drop
        self.setAcceptDrops(True)
        logger.info("Drag and drop enabled")

    def _on_click(self, event) -> None:
        """Handle click event to browse files."""
        # Trigger file browser through callback
        if self.on_file_selected:
            self.on_file_selected("")  # Empty string to trigger file browser
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        # Accept both file URLs and raw image data (e.g., from browsers)
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
            self.instructions.setStyleSheet("""
                QLabel {
                    background-color: lightblue;
                    color: darkblue;
                    font-size: 12pt;
                    border: 2px solid blue;
                    border-style: inset;
                    padding: 20px;
                }
            """)
            self.instructions.setText("Drop image here")

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave event."""
        self.instructions.setStyleSheet("""
            QLabel {
                background-color: lightgray;
                color: darkgray;
                font-size: 12pt;
                border: 2px solid gray;
                border-style: inset;
                padding: 20px;
            }
        """)
        self.instructions.setText("Drop image files here\nor click to browse")

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle file drop event."""
        try:
            mime_data = event.mimeData()

            # First try to handle URLs (both local files and HTTP URLs)
            if mime_data.hasUrls():
                urls = mime_data.urls()

                # Process first valid URL
                for url in urls:
                    url_string = url.toString()
                    file_path = url.toLocalFile()

                    # Handle local file paths
                    if file_path and self._is_image_file(file_path) and self.on_image_dropped:
                        self.on_image_dropped(file_path)
                        event.acceptProposedAction()
                        self.dragLeaveEvent(None)
                        return

                    # Handle HTTP URLs (e.g., from browser)
                    elif url_string.startswith(('http://', 'https://')) and self.on_image_data_dropped:
                        try:
                            import requests
                            response = requests.get(url_string, timeout=10)
                            response.raise_for_status()

                            # Check if it's an image by content type
                            content_type = response.headers.get('content-type', '').lower()
                            if content_type.startswith('image/'):
                                self.on_image_data_dropped(response.content, f"http_url:{url_string}")
                                event.acceptProposedAction()
                                self.dragLeaveEvent(None)
                                return
                        except Exception as e:
                            logger.error(f"Failed to download image from URL {url_string}: {e}")
                            continue

            # If no valid file URLs, try to handle raw image data (browser drag-drop)
            if mime_data.hasImage() and self.on_image_data_dropped:
                from PySide6.QtGui import QPixmap

                # Get the image from mime data
                pixmap = mime_data.imageData()
                if isinstance(pixmap, QPixmap) and not pixmap.isNull():
                    # Convert QPixmap to bytes
                    byte_array = QByteArray()
                    buffer = QBuffer(byte_array)
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    pixmap.save(buffer, "PNG")
                    buffer.close()

                    image_bytes = byte_array.data()
                    self.on_image_data_dropped(image_bytes, "browser_drag")
                    event.acceptProposedAction()
                    self.dragLeaveEvent(None)
                    return

            # If we get here, nothing was handled
            formats = mime_data.formats()
            text_content = mime_data.text() if mime_data.hasText() else "no text"
            logger.warning(f"Dropped content could not be processed as image. Formats: {formats}, Text: {text_content}")

        except Exception as e:
            logger.error(f"Error handling drop event: {e}")

        # Reset appearance
        self.dragLeaveEvent(None)
    
    def _is_image_file(self, file_path: str) -> bool:
        """Check if file is an image.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is an image
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}
        return any(file_path.lower().endswith(ext) for ext in image_extensions)
    
    def set_status(self, text: str, color: str = "darkgray") -> None:
        """Set status text in the drop area.

        Args:
            text: Status text
            color: Text color
        """
        self.instructions.setText(text)
        # Update stylesheet with new color
        self.instructions.setStyleSheet(f"""
            QLabel {{
                background-color: lightgray;
                color: {color};
                font-size: 12pt;
                border: 2px solid gray;
                border-style: inset;
                padding: 20px;
            }}
        """)


class ConfigurationPanel(QWidget):
    """Configuration panel for processing settings."""

    def __init__(self, parent: QWidget):
        """Initialize configuration panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.on_config_changed: Optional[Callable[[dict], None]] = None

        self._setup_ui()
        self._setup_bindings()
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        # Create layout for the parent group box
        parent_widget = self.parent()
        if isinstance(parent_widget, QGroupBox):
            parent_layout = QVBoxLayout(parent_widget)
            parent_layout.addWidget(self)

        # Create grid layout
        layout = QGridLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        row = 0

        # Upscaler selection
        layout.addWidget(QLabel("Upscaler:"), row, 0)
        self.upscaler_combo = QComboBox()
        layout.addWidget(self.upscaler_combo, row, 1)

        # Scale factor
        layout.addWidget(QLabel("Scale Factor:"), row, 2)
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(1.0, 4.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(2.5)
        self.scale_spin.setDecimals(1)
        layout.addWidget(self.scale_spin, row, 3)

        row += 1

        # Denoising strength
        layout.addWidget(QLabel("Denoising:"), row, 0)
        self.denoising_spin = QDoubleSpinBox()
        self.denoising_spin.setRange(0.0, 1.0)
        self.denoising_spin.setSingleStep(0.05)
        self.denoising_spin.setValue(0.15)
        self.denoising_spin.setDecimals(2)
        layout.addWidget(self.denoising_spin, row, 1)

        # Tile overlap
        layout.addWidget(QLabel("Tile Overlap:"), row, 2)
        self.tile_spin = QSpinBox()
        self.tile_spin.setRange(0, 256)
        self.tile_spin.setSingleStep(8)
        self.tile_spin.setValue(64)
        layout.addWidget(self.tile_spin, row, 3)

        # Configure column stretch
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
    
    def _setup_bindings(self) -> None:
        """Set up variable change bindings."""
        self.upscaler_combo.currentTextChanged.connect(self._on_config_change)
        self.scale_spin.valueChanged.connect(self._on_config_change)
        self.denoising_spin.valueChanged.connect(self._on_config_change)
        self.tile_spin.valueChanged.connect(self._on_config_change)

    def _on_config_change(self) -> None:
        """Handle configuration change."""
        if self.on_config_changed:
            config = self.get_configuration()
            self.on_config_changed(config)

    def update_options(self, upscalers: List[str], models: List[str],
                      samplers: List[str], schedulers: List[str]) -> None:
        """Update available options.

        Args:
            upscalers: List of upscaler names
            models: List of model names
            samplers: List of sampler names
            schedulers: List of scheduler names
        """
        # Temporarily disconnect signals to prevent triggering config changes
        self.upscaler_combo.currentTextChanged.disconnect()

        try:
            # Update upscaler options
            self.upscaler_combo.clear()
            self.upscaler_combo.addItems(upscalers)
            if upscalers and self.upscaler_combo.currentText() == "":
                self.upscaler_combo.setCurrentText(upscalers[0])
        finally:
            # Reconnect signals
            self.upscaler_combo.currentTextChanged.connect(self._on_config_change)

    def get_configuration(self) -> dict:
        """Get current configuration.

        Returns:
            Configuration dictionary
        """
        return {
            "upscaler": self.upscaler_combo.currentText(),
            "scale_factor": self.scale_spin.value(),
            "denoising_strength": self.denoising_spin.value(),
            "tile_overlap": self.tile_spin.value()
        }

    def set_configuration(self, config: dict) -> None:
        """Set configuration values.

        Args:
            config: Configuration dictionary
        """
        # Temporarily disconnect signals to prevent triggering config changes
        self.upscaler_combo.currentTextChanged.disconnect()
        self.scale_spin.valueChanged.disconnect()
        self.denoising_spin.valueChanged.disconnect()
        self.tile_spin.valueChanged.disconnect()

        try:
            if "upscaler" in config:
                self.upscaler_combo.setCurrentText(config["upscaler"])
            if "scale_factor" in config:
                self.scale_spin.setValue(config["scale_factor"])
            if "denoising_strength" in config:
                self.denoising_spin.setValue(config["denoising_strength"])
            if "tile_overlap" in config:
                self.tile_spin.setValue(config["tile_overlap"])
        finally:
            # Reconnect signals
            self.upscaler_combo.currentTextChanged.connect(self._on_config_change)
            self.scale_spin.valueChanged.connect(self._on_config_change)
            self.denoising_spin.valueChanged.connect(self._on_config_change)
            self.tile_spin.valueChanged.connect(self._on_config_change)
