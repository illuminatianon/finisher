"""Two-pass upscaling pipeline implementation."""

import logging
import threading
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from ..api import Auto1111Client
from ..api.models import ProcessingConfig
from .processor import ImageProcessor
from .status_monitor import StatusMonitor, JobStatus
from ..config.defaults import JOB_CONFIG

logger = logging.getLogger(__name__)


class UpscalingPipeline:
    """Manages the two-pass upscaling workflow."""
    
    def __init__(self, client: Auto1111Client, processor: ImageProcessor, 
                 status_monitor: StatusMonitor):
        """Initialize upscaling pipeline.
        
        Args:
            client: Auto1111 API client
            processor: Image processor
            status_monitor: Status monitor
        """
        self.client = client
        self.processor = processor
        self.status_monitor = status_monitor
        
        # Pipeline state
        self.is_processing = False
        self.current_job_id: Optional[str] = None
        self.processing_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.on_progress: Optional[Callable[[str, float], None]] = None
        self.on_completed: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_cancelled: Optional[Callable[[], None]] = None
        
        # Configuration
        self.cancel_timeout = JOB_CONFIG['cancel_timeout']
        self.interrupt_timeout = JOB_CONFIG['interrupt_timeout']
    
    def start_upscaling(self, image_path: str, config: ProcessingConfig) -> bool:
        """Start the upscaling process.
        
        Args:
            image_path: Path to input image
            config: Processing configuration
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_processing:
            logger.warning("Pipeline already processing")
            return False
        
        # Check if Auto1111 is available
        if not self.status_monitor.is_idle():
            logger.warning("Auto1111 is not idle, cannot start processing")
            return False
        
        # Start processing in background thread
        self.is_processing = True
        self.current_job_id = self._generate_job_id()
        
        self.processing_thread = threading.Thread(
            target=self._process_image,
            args=(image_path, config),
            daemon=True
        )
        self.processing_thread.start()
        
        logger.info(f"Started upscaling pipeline for {image_path}")
        return True
    
    def start_upscaling_from_data(self, image_data: bytes, config: ProcessingConfig) -> bool:
        """Start upscaling from raw image data.
        
        Args:
            image_data: Raw image bytes
            config: Processing configuration
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_processing:
            logger.warning("Pipeline already processing")
            return False
        
        if not self.status_monitor.is_idle():
            logger.warning("Auto1111 is not idle, cannot start processing")
            return False
        
        self.is_processing = True
        self.current_job_id = self._generate_job_id()
        
        self.processing_thread = threading.Thread(
            target=self._process_image_data,
            args=(image_data, config),
            daemon=True
        )
        self.processing_thread.start()
        
        logger.info("Started upscaling pipeline from image data")
        return True
    
    def cancel_processing(self) -> bool:
        """Cancel current processing.
        
        Returns:
            True if cancellation initiated, False otherwise
        """
        if not self.is_processing:
            logger.warning("No processing to cancel")
            return False
        
        logger.info("Cancelling upscaling pipeline")
        
        try:
            # Interrupt Auto1111 job
            self.client.interrupt()
            
            # Wait for processing thread to finish
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=self.cancel_timeout)
            
            self._cleanup_processing()
            
            if self.on_cancelled:
                self.on_cancelled()
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling processing: {e}")
            return False
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID.
        
        Returns:
            Job ID string
        """
        return datetime.now().strftime("%Y%m%d%H%M%S")
    
    def _process_image(self, image_path: str, config: ProcessingConfig) -> None:
        """Process image through two-pass pipeline.
        
        Args:
            image_path: Path to input image
            config: Processing configuration
        """
        try:
            self._notify_progress("Preparing image...", 0.0)
            
            # Prepare image for processing
            base64_image, prompt, negative_prompt = self.processor.prepare_image_for_processing(image_path)
            
            # Execute two-pass pipeline
            self._execute_pipeline(base64_image, prompt, negative_prompt, config)
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            self._handle_error(f"Failed to process image: {e}")
        finally:
            self._cleanup_processing()
    
    def _process_image_data(self, image_data: bytes, config: ProcessingConfig) -> None:
        """Process image data through two-pass pipeline.
        
        Args:
            image_data: Raw image bytes
            config: Processing configuration
        """
        try:
            self._notify_progress("Preparing image data...", 0.0)
            
            # Prepare image data for processing
            base64_image, prompt, negative_prompt = self.processor.prepare_image_data_for_processing(image_data)
            
            # Execute two-pass pipeline
            self._execute_pipeline(base64_image, prompt, negative_prompt, config)
            
        except Exception as e:
            logger.error(f"Error processing image data: {e}")
            self._handle_error(f"Failed to process image data: {e}")
        finally:
            self._cleanup_processing()
    
    def _execute_pipeline(self, base64_image: str, prompt: str, 
                         negative_prompt: str, config: ProcessingConfig) -> None:
        """Execute the two-pass upscaling pipeline.
        
        Args:
            base64_image: Base64 encoded input image
            prompt: Generation prompt
            negative_prompt: Negative prompt
            config: Processing configuration
        """
        # Register job with status monitor
        job_timestamp = self._generate_job_id()
        self.status_monitor.register_our_job(job_timestamp)
        
        try:
            # First pass: img2img with SD upscale
            self._notify_progress("Starting first pass (img2img)...", 0.1)
            
            first_pass_payload = config.to_img2img_payload(
                init_images=[base64_image],
                prompt=prompt,
                negative_prompt=negative_prompt
            )
            
            logger.info("Executing first pass (img2img)")
            first_pass_result = self.client.img2img(first_pass_payload)
            
            # Extract result from first pass
            if not first_pass_result.get('images'):
                raise ValueError("No images returned from first pass")
            
            first_pass_image = first_pass_result['images'][0]
            
            # Transition to second pass
            self.status_monitor.start_second_pass()
            self._notify_progress("Starting second pass (extra-single-image)...", 0.8)
            
            # Second pass: extra-single-image for final enhancement
            second_pass_payload = config.to_extra_single_image_payload(
                image=first_pass_image,
                upscaling_resize=1.5  # Additional scaling for second pass
            )
            
            logger.info("Executing second pass (extra-single-image)")
            second_pass_result = self.client.extra_single_image(second_pass_payload)
            
            # Processing completed successfully
            self._notify_progress("Processing completed", 1.0)
            
            # Auto1111 saves the final result automatically
            # We just need to notify completion
            if self.on_completed:
                self.on_completed("Processing completed successfully")
            
            logger.info("Upscaling pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline execution error: {e}")
            self._handle_error(f"Pipeline execution failed: {e}")
    
    def _notify_progress(self, message: str, progress: float) -> None:
        """Notify progress callback.
        
        Args:
            message: Progress message
            progress: Progress value (0.0 to 1.0)
        """
        logger.debug(f"Progress: {message} ({progress:.1%})")
        
        if self.on_progress:
            try:
                self.on_progress(message, progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _handle_error(self, error_message: str) -> None:
        """Handle pipeline errors.
        
        Args:
            error_message: Error message
        """
        logger.error(f"Pipeline error: {error_message}")
        
        if self.on_error:
            try:
                self.on_error(error_message)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def _cleanup_processing(self) -> None:
        """Clean up processing state."""
        self.is_processing = False
        self.current_job_id = None
        self.processing_thread = None
        self.status_monitor.clear_job_ownership()
        
        logger.debug("Pipeline processing state cleaned up")
    
    def is_busy(self) -> bool:
        """Check if pipeline is currently processing.
        
        Returns:
            True if processing, False otherwise
        """
        return self.is_processing
    
    def get_current_job_id(self) -> Optional[str]:
        """Get current job ID.
        
        Returns:
            Current job ID or None if not processing
        """
        return self.current_job_id
