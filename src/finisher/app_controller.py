"""Main application controller that wires all components together."""

import logging
import threading
from typing import Optional
from PySide6.QtWidgets import QApplication

from .gui import MainWindow
from .api import Auto1111Client, ConfigurationManager
from .core import (
    ImageProcessor, StatusMonitor, UpscalingPipeline, JobManager,
    InputHandler, ErrorHandler, JobStatus, Job
)
from .config import ApplicationSettings
from .api.models import ProcessingConfig

logger = logging.getLogger(__name__)


class ApplicationController:
    """Main application controller."""
    
    def __init__(self):
        """Initialize the application controller."""
        # Load settings
        self.settings = ApplicationSettings()
        
        # Initialize error handler first
        self.error_handler = ErrorHandler()
        
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
        self.job_manager = JobManager(
            self.client, self.status_monitor, self.upscaling_pipeline
        )
        self.input_handler = InputHandler()
        
        # GUI components (initialized later)
        self.main_window: Optional[MainWindow] = None
        
        # Application state
        self.initialized = False
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
            # Cancel any running jobs
            self.job_manager.cancel_current_job()
            
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
        
        # Job manager callbacks
        self.job_manager.on_job_started = self._on_job_started
        self.job_manager.on_job_progress = self._on_job_progress
        self.job_manager.on_job_completed = self._on_job_completed
        self.job_manager.on_job_cancelled = self._on_job_cancelled
        self.job_manager.on_job_failed = self._on_job_failed
        
        # Input handler callbacks
        self.input_handler.on_image_received = self._on_image_received
        self.input_handler.on_error = self._on_input_error
        
        # Error handler callbacks
        self.error_handler.on_error = self._on_error
        self.error_handler.on_critical_error = self._on_critical_error
    
    def _setup_gui_callbacks(self) -> None:
        """Set up GUI callbacks."""
        if not self.main_window:
            return
        
        self.main_window.on_image_dropped = self._on_image_dropped
        self.main_window.on_file_selected = self._on_file_selected
        self.main_window.on_cancel_job = self._on_cancel_job
        self.main_window.on_emergency_stop = self._on_emergency_stop
        self.main_window.on_config_changed = self._on_config_changed
    
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

                    self.main_window.update_configuration_options(
                        upscaler_names, model_names, sampler_names, scheduler_names
                    )

                if self.main_window:
                    self.main_window.update_status("Ready")
                logger.info("Configuration loaded successfully")

            except Exception as e:
                error = self.error_handler.handle_exception(e, "Configuration loading")
                if self.main_window:
                    self.main_window.update_status(f"Configuration error: {error.user_message}")

        thread = threading.Thread(target=load_config, daemon=True)
        thread.start()
    
    def _on_status_changed(self, status: JobStatus, progress: float, 
                          eta: Optional[float], job_info: Optional[str]) -> None:
        """Handle status monitor changes."""
        if not self.main_window:
            return
        
        # Update status bar
        status_text = status.value
        if job_info:
            status_text += f" - {job_info}"
        
        # Show progress for processing states
        show_progress = status in [JobStatus.PROCESSING, JobStatus.EXTERNAL]
        progress_value = progress if show_progress else None
        
        self.main_window.update_status(status_text, progress_value)
        
        # Update cancel button state
        can_cancel = status in [JobStatus.PROCESSING, JobStatus.FINALIZING]
        self.main_window.set_cancel_button_enabled(can_cancel)
    
    def _on_status_error(self, error_message: str) -> None:
        """Handle status monitor errors."""
        logger.warning(f"Status monitor error: {error_message}")
        if self.main_window:
            self.main_window.update_status("Connection error")
    
    def _on_job_started(self, job: Job) -> None:
        """Handle job started."""
        logger.info(f"Job started: {job.description}")
        if self.main_window:
            self.main_window.update_status(f"Processing: {job.description}")
    
    def _on_job_progress(self, job: Job, progress: float) -> None:
        """Handle job progress updates."""
        if self.main_window:
            self.main_window.update_status(f"Processing: {job.description}", progress)
    
    def _on_job_completed(self, job: Job) -> None:
        """Handle job completion."""
        logger.info(f"Job completed: {job.description}")
        if self.main_window:
            self.main_window.update_status("Processing completed")
            self.main_window.show_success_message("Image upscaling completed successfully!")
            self.main_window.reset_ui_state()
    
    def _on_job_cancelled(self, job: Job) -> None:
        """Handle job cancellation."""
        logger.info(f"Job cancelled: {job.description}")
        if self.main_window:
            self.main_window.update_status("Processing cancelled")
    
    def _on_job_failed(self, job: Job, error_message: str) -> None:
        """Handle job failure."""
        logger.error(f"Job failed: {job.description} - {error_message}")
        if self.main_window:
            self.main_window.update_status("Processing failed")
            self.main_window.show_error_message(f"Processing failed: {error_message}")
            self.main_window.reset_ui_state()
    
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
                self.main_window.show_error_message(error.user_message)
    
    def _on_input_error(self, error_message: str) -> None:
        """Handle input handler errors."""
        logger.warning(f"Input error: {error_message}")
        if self.main_window:
            self.main_window.drop_area.set_status(error_message, "red")
    
    def _on_image_dropped(self, file_path: str) -> None:
        """Handle image dropped on GUI."""
        self.input_handler.handle_file_drop(file_path)
    
    def _on_file_selected(self, file_path: str) -> None:
        """Handle file selected from browser."""
        self.input_handler.handle_file_drop(file_path)
    
    def _on_cancel_job(self) -> None:
        """Handle cancel job request."""
        self.job_manager.cancel_current_job()
    
    def _on_emergency_stop(self) -> None:
        """Handle emergency stop request."""
        self.job_manager.emergency_interrupt()
    
    def _on_config_changed(self, config: dict) -> None:
        """Handle configuration changes."""
        # Update processing configuration in settings
        processing_config = self.settings.get_processing_config()
        processing_config.update(config)
        self.settings.set_processing_config(processing_config)
        
        logger.debug(f"Configuration updated: {config}")
    
    def _on_error(self, error) -> None:
        """Handle general errors."""
        logger.error(f"Application error: {error}")
    
    def _on_critical_error(self, error) -> None:
        """Handle critical errors."""
        logger.critical(f"Critical error: {error}")
        # Could trigger application shutdown or recovery
    
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
