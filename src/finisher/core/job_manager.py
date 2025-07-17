"""Job management and cancellation system."""

import logging
import threading
import time
from typing import Optional, Callable, List, Dict, Any
from enum import Enum
from datetime import datetime

from ..api import Auto1111Client
from .status_monitor import StatusMonitor, JobStatus
from .upscaling_pipeline import UpscalingPipeline
from ..config.defaults import JOB_CONFIG

logger = logging.getLogger(__name__)


class JobType(Enum):
    """Job type enumeration."""
    UPSCALING = "UPSCALING"
    EXTERNAL = "EXTERNAL"


class JobState(Enum):
    """Job state enumeration."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Job:
    """Represents a processing job."""
    
    def __init__(self, job_id: str, job_type: JobType, description: str):
        """Initialize job.
        
        Args:
            job_id: Unique job identifier
            job_type: Type of job
            description: Job description
        """
        self.job_id = job_id
        self.job_type = job_type
        self.description = description
        self.state = JobState.QUEUED
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.progress = 0.0
        self.cancellable = True


class JobManager:
    """Manages job queue and cancellation."""
    
    def __init__(self, client: Auto1111Client, status_monitor: StatusMonitor, 
                 pipeline: UpscalingPipeline):
        """Initialize job manager.
        
        Args:
            client: Auto1111 API client
            status_monitor: Status monitor
            pipeline: Upscaling pipeline
        """
        self.client = client
        self.status_monitor = status_monitor
        self.pipeline = pipeline
        
        # Job tracking
        self.jobs: Dict[str, Job] = {}
        self.job_queue: List[str] = []
        self.current_job_id: Optional[str] = None
        
        # Callbacks
        self.on_job_started: Optional[Callable[[Job], None]] = None
        self.on_job_progress: Optional[Callable[[Job, float], None]] = None
        self.on_job_completed: Optional[Callable[[Job], None]] = None
        self.on_job_cancelled: Optional[Callable[[Job], None]] = None
        self.on_job_failed: Optional[Callable[[Job, str], None]] = None
        
        # Configuration
        self.cancel_timeout = JOB_CONFIG['cancel_timeout']
        self.interrupt_timeout = JOB_CONFIG['interrupt_timeout']
        
        # Setup pipeline callbacks
        self._setup_pipeline_callbacks()
    
    def _setup_pipeline_callbacks(self) -> None:
        """Set up callbacks from pipeline."""
        self.pipeline.on_progress = self._on_pipeline_progress
        self.pipeline.on_completed = self._on_pipeline_completed
        self.pipeline.on_error = self._on_pipeline_error
        self.pipeline.on_cancelled = self._on_pipeline_cancelled
    
    def queue_upscaling_job(self, image_path: str, config: Any, 
                           description: str = "Image upscaling") -> str:
        """Queue an upscaling job.
        
        Args:
            image_path: Path to image file
            config: Processing configuration
            description: Job description
            
        Returns:
            Job ID
        """
        job_id = self._generate_job_id()
        job = Job(job_id, JobType.UPSCALING, description)
        
        # Store job data
        job.image_path = image_path
        job.config = config
        
        self.jobs[job_id] = job
        self.job_queue.append(job_id)
        
        logger.info(f"Queued upscaling job {job_id}: {description}")
        
        # Try to start job immediately if possible
        self._try_start_next_job()
        
        return job_id
    
    def queue_upscaling_job_from_data(self, image_data: bytes, config: Any,
                                    description: str = "Image upscaling from data") -> str:
        """Queue an upscaling job from image data.
        
        Args:
            image_data: Raw image bytes
            config: Processing configuration
            description: Job description
            
        Returns:
            Job ID
        """
        job_id = self._generate_job_id()
        job = Job(job_id, JobType.UPSCALING, description)
        
        # Store job data
        job.image_data = image_data
        job.config = config
        
        self.jobs[job_id] = job
        self.job_queue.append(job_id)
        
        logger.info(f"Queued upscaling job from data {job_id}: {description}")
        
        # Try to start job immediately if possible
        self._try_start_next_job()
        
        return job_id
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if cancellation initiated, False otherwise
        """
        if job_id not in self.jobs:
            logger.warning(f"Job {job_id} not found")
            return False
        
        job = self.jobs[job_id]
        
        if not job.cancellable:
            logger.warning(f"Job {job_id} is not cancellable")
            return False
        
        if job.state == JobState.QUEUED:
            # Remove from queue
            if job_id in self.job_queue:
                self.job_queue.remove(job_id)
            
            job.state = JobState.CANCELLED
            job.completed_at = datetime.now()
            
            logger.info(f"Cancelled queued job {job_id}")
            
            if self.on_job_cancelled:
                self.on_job_cancelled(job)
            
            return True
        
        elif job.state == JobState.RUNNING:
            # Cancel running job
            job.state = JobState.CANCELLING
            
            logger.info(f"Cancelling running job {job_id}")
            
            # Cancel pipeline processing
            success = self.pipeline.cancel_processing()
            
            if success:
                job.state = JobState.CANCELLED
                job.completed_at = datetime.now()
                self.current_job_id = None
                
                if self.on_job_cancelled:
                    self.on_job_cancelled(job)
            else:
                job.state = JobState.FAILED
                job.error_message = "Failed to cancel job"
                job.completed_at = datetime.now()
                
                if self.on_job_failed:
                    self.on_job_failed(job, "Failed to cancel job")
            
            return success
        
        else:
            logger.warning(f"Cannot cancel job {job_id} in state {job.state}")
            return False
    
    def cancel_current_job(self) -> bool:
        """Cancel the currently running job.
        
        Returns:
            True if cancellation initiated, False otherwise
        """
        if not self.current_job_id:
            logger.warning("No current job to cancel")
            return False
        
        return self.cancel_job(self.current_job_id)
    
    def emergency_interrupt(self) -> bool:
        """Emergency interrupt any running Auto1111 job.
        
        Returns:
            True if interrupt sent successfully, False otherwise
        """
        logger.warning("Emergency interrupt initiated")
        
        try:
            # Send interrupt to Auto1111
            self.client.interrupt()
            
            # Mark current job as cancelled if we have one
            if self.current_job_id and self.current_job_id in self.jobs:
                job = self.jobs[self.current_job_id]
                job.state = JobState.CANCELLED
                job.completed_at = datetime.now()
                job.error_message = "Emergency interrupt"
                
                if self.on_job_cancelled:
                    self.on_job_cancelled(job)
            
            self.current_job_id = None
            
            logger.info("Emergency interrupt completed")
            return True
            
        except Exception as e:
            logger.error(f"Emergency interrupt failed: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job object or None if not found
        """
        return self.jobs.get(job_id)
    
    def get_current_job(self) -> Optional[Job]:
        """Get currently running job.
        
        Returns:
            Current job or None
        """
        if self.current_job_id:
            return self.jobs.get(self.current_job_id)
        return None
    
    def get_queue_status(self) -> List[Job]:
        """Get list of queued jobs.
        
        Returns:
            List of queued jobs
        """
        return [self.jobs[job_id] for job_id in self.job_queue 
                if job_id in self.jobs and self.jobs[job_id].state == JobState.QUEUED]
    
    def clear_completed_jobs(self) -> None:
        """Clear completed and cancelled jobs from memory."""
        completed_states = {JobState.COMPLETED, JobState.CANCELLED, JobState.FAILED}
        
        jobs_to_remove = [
            job_id for job_id, job in self.jobs.items()
            if job.state in completed_states
        ]
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
        
        logger.info(f"Cleared {len(jobs_to_remove)} completed jobs")
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID.
        
        Returns:
            Job ID string
        """
        return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _try_start_next_job(self) -> None:
        """Try to start the next job in queue."""
        if self.current_job_id or not self.job_queue:
            return
        
        if not self.status_monitor.is_idle():
            logger.debug("Auto1111 not idle, waiting to start next job")
            return
        
        # Get next job from queue
        job_id = self.job_queue.pop(0)
        job = self.jobs.get(job_id)
        
        if not job or job.state != JobState.QUEUED:
            logger.warning(f"Invalid job {job_id} in queue")
            return
        
        # Start the job
        self.current_job_id = job_id
        job.state = JobState.RUNNING
        job.started_at = datetime.now()
        
        logger.info(f"Starting job {job_id}: {job.description}")
        
        if self.on_job_started:
            self.on_job_started(job)
        
        # Start pipeline processing
        if hasattr(job, 'image_path'):
            success = self.pipeline.start_upscaling(job.image_path, job.config)
        elif hasattr(job, 'image_data'):
            success = self.pipeline.start_upscaling_from_data(job.image_data, job.config)
        else:
            success = False
            logger.error(f"Job {job_id} has no image data")
        
        if not success:
            job.state = JobState.FAILED
            job.error_message = "Failed to start pipeline"
            job.completed_at = datetime.now()
            self.current_job_id = None
            
            if self.on_job_failed:
                self.on_job_failed(job, "Failed to start pipeline")
    
    def _on_pipeline_progress(self, message: str, progress: float) -> None:
        """Handle pipeline progress updates."""
        if self.current_job_id and self.current_job_id in self.jobs:
            job = self.jobs[self.current_job_id]
            job.progress = progress
            
            if self.on_job_progress:
                self.on_job_progress(job, progress)
    
    def _on_pipeline_completed(self, message: str) -> None:
        """Handle pipeline completion."""
        if self.current_job_id and self.current_job_id in self.jobs:
            job = self.jobs[self.current_job_id]
            job.state = JobState.COMPLETED
            job.progress = 1.0
            job.completed_at = datetime.now()
            
            logger.info(f"Job {self.current_job_id} completed: {message}")
            
            if self.on_job_completed:
                self.on_job_completed(job)
            
            self.current_job_id = None
            
            # Try to start next job
            self._try_start_next_job()
    
    def _on_pipeline_error(self, error_message: str) -> None:
        """Handle pipeline errors."""
        if self.current_job_id and self.current_job_id in self.jobs:
            job = self.jobs[self.current_job_id]
            job.state = JobState.FAILED
            job.error_message = error_message
            job.completed_at = datetime.now()
            
            logger.error(f"Job {self.current_job_id} failed: {error_message}")
            
            if self.on_job_failed:
                self.on_job_failed(job, error_message)
            
            self.current_job_id = None
            
            # Try to start next job
            self._try_start_next_job()
    
    def _on_pipeline_cancelled(self) -> None:
        """Handle pipeline cancellation."""
        if self.current_job_id and self.current_job_id in self.jobs:
            job = self.jobs[self.current_job_id]
            
            if job.state == JobState.CANCELLING:
                job.state = JobState.CANCELLED
                job.completed_at = datetime.now()
                
                logger.info(f"Job {self.current_job_id} cancelled")
                
                if self.on_job_cancelled:
                    self.on_job_cancelled(job)
            
            self.current_job_id = None
            
            # Try to start next job
            self._try_start_next_job()
