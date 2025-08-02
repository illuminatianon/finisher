"""Main application window implementation."""

import logging
import tempfile
import os
from typing import Optional, Callable, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QMenuBar, QStatusBar, QMessageBox, QFileDialog,
    QApplication, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from .components import StatusBar, ImageDropArea, ConfigurationPanel
from .queue_panel import QueuePanel
from .enhanced_status import EnhancedStatusBar

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for Finisher."""

    def __init__(self, title: str = "Finisher - AI Image Upscaling Tool"):
        """Initialize the main window.

        Args:
            title: Window title
        """
        super().__init__()
        self.setWindowTitle(title)
        self.resize(800, 600)
        self.setMinimumSize(600, 400)

        # Callbacks for external functionality
        self.on_image_dropped: Optional[Callable[[str], None]] = None
        self.on_file_selected: Optional[Callable[[str], None]] = None
        self.on_image_data_dropped: Optional[Callable[[bytes, str], None]] = None
        self.on_cancel_job: Optional[Callable[[], None]] = None
        self.on_emergency_stop: Optional[Callable[[], None]] = None
        self.on_config_changed: Optional[Callable[[dict], None]] = None
        # New batch callbacks
        self.on_multiple_files_dropped: Optional[Callable[[List[str]], None]] = None
        self.on_directory_dropped: Optional[Callable[[str], None]] = None

        self._setup_ui()
        self._setup_menu()
        self._setup_bindings()

        logger.info("Main window initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top section - Configuration panel
        config_group = QGroupBox("Configuration")
        main_layout.addWidget(config_group)

        self.config_panel = ConfigurationPanel(config_group)
        self.config_panel.on_config_changed = self._on_config_changed

        # Main content area with splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(content_splitter, 1)

        # Left side - Image input and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Image drop area
        drop_group = QGroupBox("Image Input")
        left_layout.addWidget(drop_group, 1)

        self.drop_area = ImageDropArea(drop_group)
        self.drop_area.on_image_dropped = self._on_image_dropped
        self.drop_area.on_file_selected = self._on_file_selected
        self.drop_area.on_image_data_dropped = self._on_image_data_dropped
        # New batch callbacks
        self.drop_area.on_multiple_files_dropped = self._on_multiple_files_dropped
        self.drop_area.on_directory_dropped = self._on_directory_dropped

        # Control buttons
        button_layout = QHBoxLayout()
        left_layout.addLayout(button_layout)

        # File browser button
        self.browse_button = QPushButton("Browse Files...")
        self.browse_button.clicked.connect(self._browse_files)
        button_layout.addWidget(self.browse_button)

        # Cancel job button
        self.cancel_button = QPushButton("Cancel Job")
        self.cancel_button.clicked.connect(self._cancel_job)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)

        # Add stretch to push emergency button to the right
        button_layout.addStretch()

        # Emergency stop button
        self.emergency_button = QPushButton("Emergency Stop")
        self.emergency_button.clicked.connect(self._emergency_stop)
        self.emergency_button.setStyleSheet("QPushButton { color: red; font-weight: bold; }")
        button_layout.addWidget(self.emergency_button)

        content_splitter.addWidget(left_widget)

        # Right side - Queue panel
        self.queue_panel = QueuePanel()
        content_splitter.addWidget(self.queue_panel)

        # Set splitter proportions (2:1 ratio)
        content_splitter.setSizes([400, 200])

        # Enhanced status bar
        self.enhanced_status_bar = EnhancedStatusBar()
        self.statusBar().addPermanentWidget(self.enhanced_status_bar)

        # Keep legacy status bar reference for backward compatibility
        self.status_bar = self.enhanced_status_bar

        # Add tooltips
        self._setup_tooltips()

    def _setup_tooltips(self) -> None:
        """Set up tooltips for UI elements."""
        # Add tooltips to buttons
        self.browse_button.setToolTip("Browse for image files (Ctrl+O)")
        self.cancel_button.setToolTip("Cancel current processing job (Esc)")
        self.emergency_button.setToolTip("Emergency stop - interrupts any Auto1111 job")

        # Add tooltip to drop area
        self.drop_area.setToolTip("Drop image files here or paste from clipboard (Ctrl+V)")

    def _setup_menu(self) -> None:
        """Set up the application menu."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Image...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._browse_files)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        paste_action = QAction("&Paste Image", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._paste_image)
        edit_menu.addAction(paste_action)

        # Queue menu
        queue_menu = menubar.addMenu("&Queue")

        pause_action = QAction("&Pause Queue", self)
        pause_action.setShortcut("Ctrl+P")
        pause_action.triggered.connect(self._toggle_queue_processing)
        queue_menu.addAction(pause_action)

        clear_action = QAction("&Clear Completed", self)
        clear_action.setShortcut("Ctrl+Shift+C")
        clear_action.triggered.connect(self._clear_completed_jobs)
        queue_menu.addAction(clear_action)

        queue_menu.addSeparator()

        cancel_all_action = QAction("Cancel &All Jobs", self)
        cancel_all_action.setShortcut("Ctrl+Shift+X")
        cancel_all_action.triggered.connect(self._cancel_all_jobs)
        queue_menu.addAction(cancel_all_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_bindings(self) -> None:
        """Set up keyboard bindings."""
        # Keyboard shortcuts are handled by the menu actions
        # Additional shortcuts can be added here if needed
        pass
    
    def _browse_files(self) -> None:
        """Open file browser dialog."""
        file_filter = (
            "Image files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp);;"
            "PNG files (*.png);;"
            "JPEG files (*.jpg *.jpeg);;"
            "All files (*.*)"
        )

        # Use getOpenFileNames for multiple file selection
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image File(s)",
            "",
            file_filter
        )

        if filenames:
            if len(filenames) == 1:
                # Single file - use existing callback
                if self.on_file_selected:
                    self.on_file_selected(filenames[0])
            else:
                # Multiple files - use new callback
                if self.on_multiple_files_dropped:
                    self.on_multiple_files_dropped(filenames)
    
    def _paste_image(self) -> None:
        """Handle paste image from clipboard."""
        try:
            from PIL import ImageGrab
            image = ImageGrab.grabclipboard()

            if image is None:
                QMessageBox.warning(self, "Clipboard", "No image found in clipboard")
                return

            if not hasattr(image, 'save'):
                QMessageBox.warning(self, "Clipboard", "Clipboard content is not an image")
                return

            # Create temporary file in docs/temp directory and trigger processing
            from finisher.core.utils import get_docs_temp_dir

            docs_temp_dir = get_docs_temp_dir()
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.png',
                prefix='finisher_clipboard_',
                dir=docs_temp_dir
            )
            os.close(temp_fd)

            image.save(temp_path, 'PNG')

            if self.on_file_selected:
                self.on_file_selected(temp_path)

            # Schedule cleanup
            QTimer.singleShot(5000, lambda: self._cleanup_temp_file(temp_path))

        except ImportError:
            QMessageBox.critical(self, "Error", "PIL library not available for clipboard operations")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to paste image: {e}")

    def _cleanup_temp_file(self, file_path: str) -> None:
        """Clean up temporary file."""
        try:
            import os
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass  # Ignore cleanup errors
    
    def _on_image_dropped(self, file_path: str) -> None:
        """Handle image dropped event."""
        if self.on_image_dropped:
            self.on_image_dropped(file_path)

    def _on_file_selected(self, file_path: str) -> None:
        """Handle file selected event."""
        if self.on_file_selected:
            self.on_file_selected(file_path)

    def _on_image_data_dropped(self, image_data: bytes, source: str) -> None:
        """Handle raw image data dropped event."""
        if self.on_image_data_dropped:
            self.on_image_data_dropped(image_data, source)
    
    def _on_config_changed(self, config: dict) -> None:
        """Handle configuration changed event."""
        if self.on_config_changed:
            self.on_config_changed(config)

    def _on_multiple_files_dropped(self, file_paths: List[str]) -> None:
        """Handle multiple files dropped event."""
        if self.on_multiple_files_dropped:
            self.on_multiple_files_dropped(file_paths)

    def _on_directory_dropped(self, directory_path: str) -> None:
        """Handle directory dropped event."""
        if self.on_directory_dropped:
            self.on_directory_dropped(directory_path)

    def set_queue_manager(self, queue_manager) -> None:
        """Set the queue manager for the queue panel and status bar.

        Args:
            queue_manager: EnhancedQueueManager instance
        """
        self.queue_panel.set_queue_manager(queue_manager)
        self.enhanced_status_bar.set_queue_manager(queue_manager)

    def handle_queue_event(self, event_data) -> None:
        """Handle queue events.

        Args:
            event_data: QueueEventData instance
        """
        self.queue_panel.handle_queue_event(event_data)
        self.enhanced_status_bar.handle_queue_event(event_data)

    def _toggle_queue_processing(self) -> None:
        """Toggle queue processing (pause/resume)."""
        if hasattr(self, 'queue_panel') and self.queue_panel.queue_manager:
            self.queue_panel._toggle_queue_processing()

    def _clear_completed_jobs(self) -> None:
        """Clear completed jobs from queue."""
        if hasattr(self, 'queue_panel') and self.queue_panel.queue_manager:
            self.queue_panel._clear_completed()

    def _cancel_all_jobs(self) -> None:
        """Cancel all jobs in queue."""
        if hasattr(self, 'queue_panel') and self.queue_panel.queue_manager:
            reply = QMessageBox.question(
                self, "Cancel All Jobs",
                "Are you sure you want to cancel all jobs in the queue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                queue_manager = self.queue_panel.queue_manager

                # Cancel all queued jobs
                for job in list(queue_manager.job_queue):
                    queue_manager.cancel_job(job.id)

                # Cancel all active jobs
                for job_id in list(queue_manager.active_jobs.keys()):
                    queue_manager.cancel_job(job_id)
    
    def _cancel_job(self) -> None:
        """Handle cancel job button."""
        if self.on_cancel_job:
            self.on_cancel_job()
    
    def _emergency_stop(self) -> None:
        """Handle emergency stop button."""
        result = QMessageBox.question(
            self,
            "Emergency Stop",
            "This will interrupt any running Auto1111 job. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes and self.on_emergency_stop:
            self.on_emergency_stop()

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Finisher",
            "Finisher - AI Image Upscaling Tool\n\n"
            "Version: 0.0.0\n"
            "Author: illuminatianon\n\n"
            "Uses Automatic1111 API for AI-powered image upscaling."
        )
    
    def update_status(self, status: str, progress: Optional[float] = None) -> None:
        """Update status bar.
        
        Args:
            status: Status text
            progress: Progress value (0.0 to 1.0) or None to hide
        """
        self.status_bar.update_status(status, progress)
    
    def set_cancel_button_enabled(self, enabled: bool) -> None:
        """Enable or disable cancel button.

        Args:
            enabled: True to enable, False to disable
        """
        self.cancel_button.setEnabled(enabled)
    
    def update_configuration_options(self, upscalers: list, models: list, 
                                   samplers: list, schedulers: list) -> None:
        """Update configuration panel options.
        
        Args:
            upscalers: List of available upscalers
            models: List of available models
            samplers: List of available samplers
            schedulers: List of available schedulers
        """
        self.config_panel.update_options(upscalers, models, samplers, schedulers)
    
    def get_configuration(self) -> dict:
        """Get current configuration from panel.

        Returns:
            Configuration dictionary
        """
        return self.config_panel.get_configuration()

    def set_configuration(self, config: dict) -> None:
        """Set configuration values in panel.

        Args:
            config: Configuration dictionary
        """
        self.config_panel.set_configuration(config)
    
    def run(self) -> None:
        """Start the GUI event loop."""
        logger.info("Starting GUI event loop")
        self.show()

    def show_success_message(self, message: str) -> None:
        """Show success message to user.

        Args:
            message: Success message to display
        """
        QMessageBox.information(self, "Success", message)

        # Also update drop area with success feedback
        self.drop_area.set_status("✓ " + message, "green")

        # Reset status after a few seconds
        QTimer.singleShot(3000, lambda: self.drop_area.set_status(
            "Drop image files here\nor click to browse", "darkgray"
        ))

    def show_error_message(self, message: str) -> None:
        """Show error message to user.

        Args:
            message: Error message to display
        """
        QMessageBox.critical(self, "Error", message)

        # Also update drop area with error feedback
        self.drop_area.set_status("✗ " + message, "red")

        # Reset status after a few seconds
        QTimer.singleShot(5000, lambda: self.drop_area.set_status(
            "Drop image files here\nor click to browse", "darkgray"
        ))

    def show_processing_feedback(self, message: str) -> None:
        """Show processing feedback to user.

        Args:
            message: Processing message to display
        """
        self.drop_area.set_status("⏳ " + message, "blue")

    def reset_ui_state(self) -> None:
        """Reset UI to initial state."""
        self.set_cancel_button_enabled(False)
        self.update_status("Ready")
        self.drop_area.set_status(
            "Drop image files here\nor click to browse", "darkgray"
        )

    def destroy(self) -> None:
        """Destroy the window."""
        self.close()
