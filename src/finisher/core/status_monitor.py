"""Status monitoring system for Auto1111 progress tracking."""

import threading
import time
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from ..api import Auto1111Client
from ..api.models import ProgressInfo, ProgressState
from ..config.defaults import POLLING_CONFIG, JOB_CONFIG

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status enumeration."""
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    FINALIZING = "FINALIZING"
    EXTERNAL = "EXTERNAL"
    CANCELLING = "CANCELLING"
    ERROR = "ERROR"


class StatusMonitor:
    """Monitors Auto1111 status and tracks job progress."""
    
    def __init__(self, client: Auto1111Client):
        """Initialize status monitor.
        
        Args:
            client: Auto1111 API client
        """
        self.client = client
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Status tracking
        self.current_status = JobStatus.IDLE
        self.current_progress = 0.0
        self.current_eta: Optional[float] = None
        self.current_job_info: Optional[str] = None
        
        # Job ownership tracking
        self.our_job_timestamps: set = set()
        self.current_job_timestamp: Optional[str] = None
        self.current_pass = 0  # 0=idle, 1=first pass, 2=second pass
        
        # Callbacks
        self.on_status_changed: Optional[Callable[[JobStatus, float, Optional[float], Optional[str]], None]] = None
        self.on_job_completed: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Configuration
        self.poll_interval = POLLING_CONFIG['progress_interval']
        self.idle_interval = POLLING_CONFIG['idle_interval']
        self.error_interval = POLLING_CONFIG['error_interval']
        self.timestamp_tolerance = JOB_CONFIG['timestamp_tolerance']
        
        # Error handling
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.last_error_time: Optional[datetime] = None
    
    def start_monitoring(self) -> None:
        """Start the status monitoring thread."""
        if self.running:
            logger.warning("Status monitor already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        logger.info("Status monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the status monitoring thread."""
        if not self.running:
            return
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        logger.info("Status monitoring stopped")
    
    def register_our_job(self, timestamp: Optional[str] = None) -> None:
        """Register a job as ours for ownership tracking.
        
        Args:
            timestamp: Job timestamp, or None to use current time
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        self.our_job_timestamps.add(timestamp)
        self.current_job_timestamp = timestamp
        self.current_pass = 1  # Starting first pass
        
        logger.info(f"Registered our job with timestamp: {timestamp}")
    
    def start_second_pass(self) -> None:
        """Mark transition to second pass."""
        self.current_pass = 2
        logger.info("Transitioned to second pass")
    
    def clear_job_ownership(self) -> None:
        """Clear current job ownership."""
        self.current_job_timestamp = None
        self.current_pass = 0
        logger.info("Cleared job ownership")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_status()
                self.consecutive_errors = 0
                
                # Determine sleep interval based on current status
                if self.current_status == JobStatus.IDLE:
                    sleep_time = self.idle_interval
                elif self.current_status == JobStatus.ERROR:
                    sleep_time = self.error_interval
                else:
                    sleep_time = self.poll_interval
                
                time.sleep(sleep_time)
                
            except Exception as e:
                self._handle_error(f"Status monitoring error: {e}")
                time.sleep(self.error_interval)
    
    def _check_status(self) -> None:
        """Check current Auto1111 status."""
        try:
            # Get progress information
            progress_data = self.client.get_progress()
            progress_info = self._parse_progress_data(progress_data)
            
            # Determine job status
            new_status = self._determine_job_status(progress_info)
            
            # Update status if changed
            if (new_status != self.current_status or 
                abs(progress_info.progress - self.current_progress) > 0.01):
                
                self._update_status(
                    new_status,
                    progress_info.progress,
                    progress_info.eta_relative,
                    progress_info.state.job if progress_info.state else None
                )
            
            # Check for job completion
            if (self.current_status in [JobStatus.PROCESSING, JobStatus.FINALIZING] and 
                new_status == JobStatus.IDLE and 
                self.current_job_timestamp):
                
                self._handle_job_completion()
            
        except Exception as e:
            self._handle_error(f"Failed to check status: {e}")
    
    def _parse_progress_data(self, data: Dict[str, Any]) -> ProgressInfo:
        """Parse raw progress data into ProgressInfo object.
        
        Args:
            data: Raw progress data from API
            
        Returns:
            Parsed progress information
        """
        state_data = data.get('state', {})
        state = ProgressState(
            skipped=state_data.get('skipped', False),
            interrupted=state_data.get('interrupted', False),
            stopping_generation=state_data.get('stopping_generation', False),
            job=state_data.get('job'),
            job_count=state_data.get('job_count', 0),
            job_timestamp=state_data.get('job_timestamp'),
            job_no=state_data.get('job_no', 0),
            sampling_step=state_data.get('sampling_step', 0),
            sampling_steps=state_data.get('sampling_steps', 0)
        )
        
        return ProgressInfo(
            progress=data.get('progress', 0.0),
            eta_relative=data.get('eta_relative'),
            state=state,
            current_image=data.get('current_image'),
            textinfo=data.get('textinfo')
        )
    
    def _determine_job_status(self, progress_info: ProgressInfo) -> JobStatus:
        """Determine job status from progress information.
        
        Args:
            progress_info: Progress information
            
        Returns:
            Current job status
        """
        # Check for error conditions
        if progress_info.state and progress_info.state.interrupted:
            return JobStatus.ERROR
        
        # Check if idle
        if progress_info.progress == 0.0:
            return JobStatus.IDLE
        
        # Check if it's our job
        if self._is_our_job(progress_info.state.job_timestamp if progress_info.state else None):
            # Determine which pass we're in
            if self.current_pass == 1:
                return JobStatus.PROCESSING
            elif self.current_pass == 2:
                return JobStatus.FINALIZING
            else:
                return JobStatus.PROCESSING  # Default to processing
        else:
            # External job
            return JobStatus.EXTERNAL
    
    def _is_our_job(self, job_timestamp: Optional[str]) -> bool:
        """Check if a job timestamp belongs to us.
        
        Args:
            job_timestamp: Job timestamp to check
            
        Returns:
            True if it's our job, False otherwise
        """
        if not job_timestamp or not self.our_job_timestamps:
            return False
        
        # Check exact match first
        if job_timestamp in self.our_job_timestamps:
            return True
        
        # Check with tolerance for timing differences
        try:
            job_time = datetime.strptime(job_timestamp, "%Y%m%d%H%M%S")
            
            for our_timestamp in self.our_job_timestamps:
                our_time = datetime.strptime(our_timestamp, "%Y%m%d%H%M%S")
                time_diff = abs((job_time - our_time).total_seconds())
                
                if time_diff <= self.timestamp_tolerance:
                    return True
        
        except ValueError:
            logger.warning(f"Invalid timestamp format: {job_timestamp}")
        
        return False
    
    def _update_status(self, status: JobStatus, progress: float, 
                      eta: Optional[float], job_info: Optional[str]) -> None:
        """Update current status and notify callbacks.
        
        Args:
            status: New job status
            progress: Progress value (0.0 to 1.0)
            eta: Estimated time remaining in seconds
            job_info: Job information string
        """
        old_status = self.current_status
        
        self.current_status = status
        self.current_progress = progress
        self.current_eta = eta
        self.current_job_info = job_info
        
        logger.debug(f"Status updated: {old_status} -> {status}, "
                    f"progress: {progress:.2f}, eta: {eta}")
        
        # Notify callback
        if self.on_status_changed:
            try:
                self.on_status_changed(status, progress, eta, job_info)
            except Exception as e:
                logger.error(f"Error in status changed callback: {e}")
    
    def _handle_job_completion(self) -> None:
        """Handle job completion."""
        logger.info("Job completed")
        
        self.clear_job_ownership()
        
        # Notify callback
        if self.on_job_completed:
            try:
                self.on_job_completed()
            except Exception as e:
                logger.error(f"Error in job completed callback: {e}")
    
    def _handle_error(self, error_message: str) -> None:
        """Handle monitoring errors.
        
        Args:
            error_message: Error message
        """
        self.consecutive_errors += 1
        self.last_error_time = datetime.now()
        
        logger.error(f"Status monitor error ({self.consecutive_errors}): {error_message}")
        
        # Update status to error if too many consecutive errors
        if self.consecutive_errors >= self.max_consecutive_errors:
            self._update_status(JobStatus.ERROR, 0.0, None, "Connection error")
        
        # Notify error callback
        if self.on_error:
            try:
                self.on_error(error_message)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def get_current_status(self) -> tuple:
        """Get current status information.
        
        Returns:
            Tuple of (status, progress, eta, job_info)
        """
        return (self.current_status, self.current_progress, 
                self.current_eta, self.current_job_info)
    
    def is_idle(self) -> bool:
        """Check if Auto1111 is idle.
        
        Returns:
            True if idle, False otherwise
        """
        return self.current_status == JobStatus.IDLE
    
    def is_processing_our_job(self) -> bool:
        """Check if we're currently processing our job.
        
        Returns:
            True if processing our job, False otherwise
        """
        return self.current_status in [JobStatus.PROCESSING, JobStatus.FINALIZING]
