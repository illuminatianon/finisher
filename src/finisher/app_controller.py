"""Main application controller that wires all components together."""

import logging
import os
import threading
from typing import Optional, List
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject, Signal

from .gui import MainWindow
from .api import Auto1111Client, ConfigurationManager
from .core import (
    ImageProcessor, StatusMonitor, UpscalingPipeline, JobManager,
    EnhancedQueueManager, BatchInputHandler, QueuedJob, QueueEventData,
    InputHandler, ErrorHandler, JobStatus, Job
)
from .config import ApplicationSettings
from .api.models import ProcessingConfig

logger = logging.getLogger(__name__)


class StatusUpdateSignals(QObject):
    """Signal emitter for thread-safe GUI updates."""
    status_changed = Signal(object, float, object, object)  # status, progress, eta, job_info


class ApplicationController:
    """Main application controller."""
    
    def __init__(self):
        """Initialize the application controller."""
        # Load settings
        self.settings = ApplicationSettings()

        # Initialize error handler first
        self.error_handler = ErrorHandler()

        # Initialize signal emitter for thread-safe GUI updates
        self.status_signals = StatusUpdateSignals()
        
        # Initialize API components
        api_config = self.settings.get_api_config()
        self.client = Auto1111Client(
            base_url=api_config['base_url'],
            timeout=api_config['timeout']
        )
        self.config_manager = ConfigurationManager(self.client)
        
        # Initialize core components
        self.image_processor = ImageProcessor()
        self.status_monitor = StatusMonitor(self.client)
        self.upscaling_pipeline = UpscalingPipeline(
            self.client, self.image_processor, self.status_monitor
        )
        # Use enhanced queue manager instead of basic job manager
        self.queue_manager = EnhancedQueueManager(
            self.client, self.status_monitor, self.upscaling_pipeline, self.settings
        )
        # Keep legacy job_manager reference for backward compatibility
        self.job_manager = self.queue_manager

        self.input_handler = InputHandler()
        self.batch_input_handler = BatchInputHandler()

        # GUI components (initialized later)
        self.main_window: Optional[MainWindow] = None

        # Application state
        self.initialized = False
        self._pending_saved_config: Optional[dict] = None
        self._config_loaded = False
        self.shutting_down = False
        
        self._setup_callbacks()
    
    def initialize(self) -> bool:
        """Initialize the application.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing application")

            # Create main window
            self.main_window = MainWindow()
            # Note: PySide6 doesn't need root reference for error handler

            # Setup GUI callbacks
            self._setup_gui_callbacks()

            # Setup input handler
            self._setup_input_handler()

            # Load Auto1111 configuration in background
            self._load_configuration_async()

            # Start status monitoring
            self.status_monitor.start_monitoring()

            # Start configuration check timer on main thread
            self._start_config_check_timer()

            self.initialized = True
            logger.info("Application initialized successfully")
            return True

        except Exception as e:
            error = self.error_handler.handle_exception(e, "Application initialization")
            logger.critical(f"Failed to initialize application: {error}")
            return False
    
    def run(self) -> None:
        """Run the application."""
        if not self.initialized:
            if not self.initialize():
                return

        try:
            logger.info("Starting application")
            self.main_window.run()

            # Start the Qt event loop
            app = QApplication.instance()
            if app:
                app.exec()

        except Exception as e:
            self.error_handler.handle_exception(e, "Application runtime")
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Shutdown the application."""
        if self.shutting_down:
            return
        
        self.shutting_down = True
        logger.info("Shutting down application")
        
        try:
            # Shutdown enhanced queue manager
            self.queue_manager.shutdown()

            # Stop monitoring
            self.status_monitor.stop_monitoring()
            
            # Save settings
            self.settings.save_settings()
            
            # Cleanup temporary files
            from .core.utils import cleanup_temp_files
            cleanup_temp_files()
            
            logger.info("Application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def _setup_callbacks(self) -> None:
        """Set up callbacks between components."""
        # Status monitor callbacks
        self.status_monitor.on_status_changed = self._on_status_changed
        self.status_monitor.on_error = self._on_status_error
        
        # Enhanced queue manager callbacks
        self.queue_manager.on_queue_event = self._on_queue_event
        # Legacy callbacks for backward compatibility
        self.queue_manager.on_job_started = self._on_job_started
        self.queue_manager.on_job_progress = self._on_job_progress
        self.queue_manager.on_job_completed = self._on_job_completed
        self.queue_manager.on_job_cancelled = self._on_job_cancelled
        self.queue_manager.on_job_failed = self._on_job_failed
        
        # Input handler callbacks
        self.input_handler.on_image_received = self._on_image_received
        self.input_handler.on_error = self._on_input_error

        # Batch input handler callbacks
        self.batch_input_handler.on_batch_validated = self._on_batch_validated
        self.batch_input_handler.on_validation_error = self._on_validation_error
        self.batch_input_handler.on_progress = self._on_batch_progress
        
        # Error handler callbacks
        self.error_handler.on_error = self._on_error
        self.error_handler.on_critical_error = self._on_critical_error
    
    def _setup_gui_callbacks(self) -> None:
        """Set up GUI callbacks."""
        if not self.main_window:
            return

        self.main_window.on_image_dropped = self._on_image_dropped
        self.main_window.on_file_selected = self._on_file_selected
        self.main_window.on_image_data_dropped = self._on_image_data_dropped
        self.main_window.on_cancel_job = self._on_cancel_job
        self.main_window.on_emergency_stop = self._on_emergency_stop
        self.main_window.on_config_changed = self._on_config_changed
        # New batch callbacks
        self.main_window.on_multiple_files_dropped = self._on_multiple_files_dropped
        self.main_window.on_directory_dropped = self._on_directory_dropped

        # Connect status update signal for thread-safe GUI updates
        self.status_signals.status_changed.connect(self._handle_status_update_signal)

        # Set up queue manager with GUI
        self.main_window.set_queue_manager(self.queue_manager)
    
    def _setup_input_handler(self) -> None:
        """Set up input handler with GUI."""
        if not self.main_window:
            return

        # Note: PySide6 drag-and-drop is handled natively by the ImageDropArea widget
        # No additional setup needed for drag-and-drop

        # Setup clipboard monitoring if needed
        # Note: PySide6 clipboard handling is different from tkinter
        # This can be implemented later if needed
        pass
    
    def _load_configuration_async(self) -> None:
        """Load Auto1111 configuration in background thread."""
        def load_config():
            try:
                if self.main_window:
                    self.main_window.update_status("Loading Auto1111 configuration...")

                # Load all configuration options
                self.config_manager.load_all_options()

                # Update GUI with options
                if self.main_window:
                    upscaler_names = [u.name for u in self.config_manager.upscalers]
                    model_names = [m.model_name for m in self.config_manager.models]
                    sampler_names = [s.name for s in self.config_manager.samplers]
                    scheduler_names = [s.name for s in self.config_manager.schedulers]

                    # Update options first
                    self.main_window.update_configuration_options(
                        upscaler_names, model_names, sampler_names, scheduler_names
                    )

                    # Store the configuration data for main thread to apply
                    saved_config = self.settings.get_processing_config()

                    # Store config for later application on main thread
                    self._pending_saved_config = saved_config

                # Mark configuration as loaded
                self._config_loaded = True
                logger.info("Configuration loaded successfully")

            except Exception as e:
                error = self.error_handler.handle_exception(e, "Configuration loading")
                if self.main_window:
                    QTimer.singleShot(0, lambda: self.main_window.update_status(f"Configuration error: {error.user_message}"))

        thread = threading.Thread(target=load_config, daemon=True)
        thread.start()

    def _start_config_check_timer(self) -> None:
        """Start a timer to check for configuration loading completion."""
        def check_config():
            if self._config_loaded and self._pending_saved_config and self.main_window:
                self.main_window.set_configuration(self._pending_saved_config)
                self.main_window.update_status("Ready")
                self._pending_saved_config = None
                self._config_loaded = False
            else:
                # Check again in 100ms
                QTimer.singleShot(100, check_config)

        # Start checking
        QTimer.singleShot(100, check_config)

    def _apply_pending_config(self) -> None:
        """Apply pending saved configuration to GUI on main thread."""
        if self.main_window and self._pending_saved_config:
            logger.info(f"Applying pending configuration to GUI: {self._pending_saved_config}")
            self.main_window.set_configuration(self._pending_saved_config)
            logger.info("Applied saved configuration to GUI")
            self._pending_saved_config = None  # Clear after applying

    def _apply_config_on_main_thread(self, config: dict) -> None:
        """Apply saved configuration to GUI on main thread."""
        if self.main_window:
            logger.info(f"Applying configuration to GUI: {config}")
            self.main_window.set_configuration(config)
            logger.info("Applied saved configuration to GUI")

    def _on_status_changed(self, status: JobStatus, progress: float,
                          eta: Optional[float], job_info: Optional[str]) -> None:
        """Handle status monitor changes."""
        if not self.main_window:
            return

        # Emit signal for thread-safe GUI update
        self.status_signals.status_changed.emit(status, progress, eta, job_info)

    def _handle_status_update_signal(self, status: JobStatus, progress: float,
                                   eta: Optional[float], job_info: Optional[str]) -> None:
        """Handle status update signal on main thread."""
        if not self.main_window:
            return

        # Update status bar
        status_text = status.value
        if job_info:
            status_text += f" - {job_info}"

        # Show progress for processing states (including finalizing)
        show_progress = status in [JobStatus.PROCESSING, JobStatus.FINALIZING, JobStatus.EXTERNAL]
        progress_value = progress if show_progress else None

        self.main_window.update_status(status_text, progress_value)

        # Update cancel button state
        can_cancel = status in [JobStatus.PROCESSING, JobStatus.FINALIZING]
        self.main_window.set_cancel_button_enabled(can_cancel)
    
    def _on_status_error(self, error_message: str) -> None:
        """Handle status monitor errors."""
        logger.warning(f"Status monitor error: {error_message}")
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.update_status("Connection error"))
    
    def _on_job_started(self, job: Job) -> None:
        """Handle job started."""
        logger.info(f"Job started: {job.description}")
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.update_status(f"Processing: {job.description}"))
    
    def _on_job_progress(self, job: Job, progress: float) -> None:
        """Handle job progress updates."""
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.update_status(f"Processing: {job.description}", progress))
    
    def _on_job_completed(self, job: Job) -> None:
        """Handle job completion."""
        logger.info(f"Job completed: {job.description}")
        if self.main_window:
            def update_completion():
                self.main_window.update_status("Processing completed")
                self.main_window.show_success_message("Image upscaling completed successfully!")
                self.main_window.reset_ui_state()
            QTimer.singleShot(0, update_completion)
    
    def _on_job_cancelled(self, job: Job) -> None:
        """Handle job cancellation."""
        logger.info(f"Job cancelled: {job.description}")
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.update_status("Processing cancelled"))
    
    def _on_job_failed(self, job: Job, error_message: str) -> None:
        """Handle job failure."""
        logger.error(f"Job failed: {job.description} - {error_message}")
        if self.main_window:
            def update_failure():
                self.main_window.update_status("Processing failed")
                self.main_window.show_error_message(f"Processing failed: {error_message}")
                self.main_window.reset_ui_state()
            QTimer.singleShot(0, update_failure)
    
    def _on_image_received(self, source: str, path_or_data: str) -> None:
        """Handle image received from input handler."""
        try:
            # Show processing feedback
            if self.main_window:
                self.main_window.show_processing_feedback(f"Processing image from {source}")

            # Get current configuration
            config = self._get_current_processing_config()

            # Queue the upscaling job
            if source == "file_drop" or source == "clipboard":
                job_id = self.job_manager.queue_upscaling_job(
                    path_or_data, config, f"Upscaling from {source}"
                )
            else:
                # Handle as image data
                with open(path_or_data, 'rb') as f:
                    image_data = f.read()
                job_id = self.job_manager.queue_upscaling_job_from_data(
                    image_data, config, f"Upscaling from {source}"
                )

            logger.info(f"Queued upscaling job {job_id} from {source}")

        except Exception as e:
            error = self.error_handler.handle_exception(e, f"Processing image from {source}")
            if self.main_window:
                QTimer.singleShot(0, lambda: self.main_window.show_error_message(error.user_message))
    
    def _on_input_error(self, error_message: str) -> None:
        """Handle input handler errors."""
        logger.warning(f"Input error: {error_message}")
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.drop_area.set_status(error_message, "red"))
    
    def _on_image_dropped(self, file_path: str) -> None:
        """Handle image dropped on GUI."""
        self.input_handler.handle_file_drop(file_path)

    def _on_file_selected(self, file_path: str) -> None:
        """Handle file selected from browser."""
        self.input_handler.handle_file_drop(file_path)

    def _on_multiple_files_dropped(self, file_paths: List[str]) -> None:
        """Handle multiple files dropped or selected."""
        self.handle_multiple_files(file_paths)

    def _on_directory_dropped(self, directory_path: str) -> None:
        """Handle directory dropped."""
        self.handle_directory_drop(directory_path)

    def _on_image_data_dropped(self, image_data: bytes, source: str) -> None:
        """Handle raw image data dropped on GUI."""
        self.input_handler.handle_image_data(image_data, source)
    
    def _on_cancel_job(self) -> None:
        """Handle cancel job request."""
        # For enhanced queue manager, we need to cancel the current active job
        active_jobs = list(self.queue_manager.active_jobs.keys())
        if active_jobs:
            self.queue_manager.cancel_job(active_jobs[0])

    def _on_emergency_stop(self) -> None:
        """Handle emergency stop request."""
        # Cancel all active jobs and pause the queue
        active_jobs = list(self.queue_manager.active_jobs.keys())
        for job_id in active_jobs:
            self.queue_manager.cancel_job(job_id)
        self.queue_manager.pause_queue()
    
    def _on_config_changed(self, config: dict) -> None:
        """Handle configuration changes."""
        # Update processing configuration in settings
        processing_config = self.settings.get_processing_config()
        processing_config.update(config)
        self.settings.set_processing_config(processing_config)

        # Save settings to disk
        self.settings.save_settings()

        logger.debug(f"Configuration updated and saved: {config}")
    
    def _on_error(self, error) -> None:
        """Handle general errors."""
        logger.error(f"Application error: {error}")
    
    def _on_critical_error(self, error) -> None:
        """Handle critical errors."""
        logger.critical(f"Critical error: {error}")
        # Could trigger application shutdown or recovery

    def _on_queue_event(self, event_data: QueueEventData) -> None:
        """Handle queue events from enhanced queue manager.

        Args:
            event_data: Queue event data
        """
        logger.debug(f"Queue event: {event_data.event_type.value}")

        # Update GUI based on event type
        if self.main_window:
            # For now, just update the status - later we'll add queue panel
            if event_data.job:
                job = event_data.job
                if event_data.event_type.value == "JOB_ADDED":
                    QTimer.singleShot(0, lambda: self.main_window.update_status(
                        f"Job queued: {job.get_display_name()}"
                    ))
                elif event_data.event_type.value == "JOB_STARTED":
                    QTimer.singleShot(0, lambda: self.main_window.update_status(
                        f"Processing: {job.get_display_name()}"
                    ))
                elif event_data.event_type.value == "JOB_COMPLETED":
                    QTimer.singleShot(0, lambda: self.main_window.update_status(
                        f"Completed: {job.get_display_name()}"
                    ))
                elif event_data.event_type.value == "JOB_FAILED":
                    QTimer.singleShot(0, lambda: self.main_window.update_status(
                        f"Failed: {job.get_display_name()}"
                    ))
                elif event_data.event_type.value == "JOB_CANCELLED":
                    QTimer.singleShot(0, lambda: self.main_window.update_status(
                        f"Cancelled: {job.get_display_name()}"
                    ))

        # Also notify the main window's queue components
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.handle_queue_event(event_data))

    def _on_batch_validated(self, valid_files: List[str], batch_id: str) -> None:
        """Handle batch validation completion.

        Args:
            valid_files: List of valid file paths
            batch_id: Generated batch ID
        """
        try:
            logger.info(f"Batch validated: {len(valid_files)} files, batch_id: {batch_id}")

            # Get current configuration
            config = self._get_current_processing_config()

            # Create job specifications for the batch
            job_specs = []
            for file_path in valid_files:
                job_specs.append({
                    'source_path': file_path,
                    'config': config,
                    'description': f"Upscaling {os.path.basename(file_path)}"
                })

            # Queue the batch
            batch_name = f"Batch of {len(valid_files)} files"
            actual_batch_id, job_ids = self.queue_manager.queue_batch_jobs(job_specs, batch_name)

            # Update GUI
            if self.main_window:
                QTimer.singleShot(0, lambda: self.main_window.update_status(
                    f"Queued batch: {len(job_ids)} jobs"
                ))

            logger.info(f"Queued batch {actual_batch_id} with {len(job_ids)} jobs")

        except Exception as e:
            error = self.error_handler.handle_exception(e, "Processing batch")
            if self.main_window:
                QTimer.singleShot(0, lambda: self.main_window.show_error_message(error.user_message))

    def _on_validation_error(self, error_message: str) -> None:
        """Handle batch validation errors.

        Args:
            error_message: Error message
        """
        logger.warning(f"Batch validation error: {error_message}")
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.show_error_message(error_message))

    def _on_batch_progress(self, message: str, current: int, total: int) -> None:
        """Handle batch processing progress.

        Args:
            message: Progress message
            current: Current item number
            total: Total items
        """
        logger.debug(f"Batch progress: {message} ({current}/{total})")
        if self.main_window:
            QTimer.singleShot(0, lambda: self.main_window.update_status(
                f"{message} ({current}/{total})"
            ))

    def handle_multiple_files(self, file_paths: List[str]) -> None:
        """Handle multiple files dropped or selected.

        Args:
            file_paths: List of file paths
        """
        if len(file_paths) == 1:
            # Single file - use existing handler
            self.input_handler.handle_file_drop(file_paths[0])
        else:
            # Multiple files - use batch handler
            self.batch_input_handler.handle_multiple_files(file_paths)

    def handle_directory_drop(self, directory_path: str) -> None:
        """Handle directory dropped on GUI.

        Args:
            directory_path: Path to dropped directory
        """
        self.batch_input_handler.handle_directory_drop(directory_path)
    
    def _get_current_processing_config(self) -> ProcessingConfig:
        """Get current processing configuration.
        
        Returns:
            ProcessingConfig instance
        """
        # Get configuration from GUI
        if self.main_window:
            gui_config = self.main_window.get_configuration()
        else:
            gui_config = {}
        
        # Get base configuration from settings
        base_config = self.settings.get_processing_config()
        
        # Merge configurations
        merged_config = base_config.copy()
        merged_config.update(gui_config)
        
        # Create ProcessingConfig object with proper type conversion
        return ProcessingConfig(
            upscaler=merged_config.get('upscaler', 'Lanczos'),
            scale_factor=float(merged_config.get('scale_factor', 2.5)),
            denoising_strength=float(merged_config.get('denoising_strength', 0.15)),
            tile_overlap=int(merged_config.get('tile_overlap', 64)),
            steps=int(merged_config.get('steps', 25)),
            sampler_name=merged_config.get('sampler_name', 'Euler a'),
            cfg_scale=int(merged_config.get('cfg_scale', 10)),
            scheduler=merged_config.get('scheduler', 'Automatic')
        )
