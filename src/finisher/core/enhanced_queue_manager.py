"""Enhanced queue management system with batch support and persistence."""

import json
import logging
import threading
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any, Tuple
from pathlib import Path

from ..api import Auto1111Client
from ..api.models import ProcessingConfig
from .status_monitor import StatusMonitor
from .upscaling_pipeline import UpscalingPipeline
from .queue_models import (
    QueuedJob,
    BatchInfo,
    QueueEvent,
    QueueEventData,
    JobType,
    JobState,
)
from ..config.defaults import JOB_CONFIG

logger = logging.getLogger(__name__)


class EnhancedQueueManager:
    """Advanced queue management with batch support and persistence."""

    def __init__(
        self,
        client: Auto1111Client,
        status_monitor: StatusMonitor,
        pipeline: UpscalingPipeline,
        settings=None,
    ):
        """Initialize enhanced queue manager.

        Args:
            client: Auto1111 API client
            status_monitor: Status monitor
            pipeline: Upscaling pipeline
            settings: Application settings (optional)
        """
        self.client = client
        self.status_monitor = status_monitor
        self.pipeline = pipeline
        self.settings = settings

        # Queue state
        self.job_queue: List[QueuedJob] = []
        self.active_jobs: Dict[str, QueuedJob] = {}
        self.completed_jobs: List[QueuedJob] = []
        self.batches: Dict[str, BatchInfo] = {}

        # Queue configuration
        self.max_concurrent_jobs: int = 1  # Auto1111 typically handles one at a time
        self.max_queue_size: int = 50
        self.auto_process: bool = True
        self.queue_persistence: bool = True

        # Set persistence file in config directory
        config_dir = Path.home() / ".finisher"
        config_dir.mkdir(exist_ok=True)
        self.persistence_file: str = str(config_dir / "queue_state.json")

        # Threading
        self._lock = threading.RLock()
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_processing = threading.Event()

        # Callbacks for GUI updates
        self.on_queue_event: Optional[Callable[[QueueEventData], None]] = None

        # Legacy callbacks for backward compatibility
        self.on_job_started: Optional[Callable[[QueuedJob], None]] = None
        self.on_job_progress: Optional[Callable[[QueuedJob, float], None]] = None
        self.on_job_completed: Optional[Callable[[QueuedJob], None]] = None
        self.on_job_cancelled: Optional[Callable[[QueuedJob], None]] = None
        self.on_job_failed: Optional[Callable[[QueuedJob, str], None]] = None

        # Configuration
        self.cancel_timeout = JOB_CONFIG["cancel_timeout"]
        self.interrupt_timeout = JOB_CONFIG["interrupt_timeout"]

        # Setup pipeline callbacks
        self._setup_pipeline_callbacks()

        # Load persisted queue if enabled
        if self.queue_persistence:
            self._load_queue_state()

        # Start processing thread
        self._start_processing_thread()

    def _setup_pipeline_callbacks(self) -> None:
        """Set up callbacks from pipeline."""
        self.pipeline.on_progress = self._on_pipeline_progress
        self.pipeline.on_completed = self._on_pipeline_completed
        self.pipeline.on_error = self._on_pipeline_error
        self.pipeline.on_cancelled = self._on_pipeline_cancelled

    def _start_processing_thread(self) -> None:
        """Start the background processing thread."""
        if self._processing_thread and self._processing_thread.is_alive():
            return

        self._stop_processing.clear()
        self._processing_thread = threading.Thread(
            target=self._processing_loop, daemon=True, name="QueueProcessor"
        )
        self._processing_thread.start()
        logger.info("Queue processing thread started")

    def _processing_loop(self) -> None:
        """Main processing loop for the queue."""
        while not self._stop_processing.is_set():
            try:
                if self.auto_process:
                    self._try_start_next_job()

                # Sleep for a short interval
                self._stop_processing.wait(1.0)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                self._stop_processing.wait(5.0)  # Wait longer on error

    def shutdown(self) -> None:
        """Shutdown the queue manager."""
        logger.info("Shutting down enhanced queue manager")

        # Stop processing
        self._stop_processing.set()
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=5.0)

        # Cancel active jobs
        with self._lock:
            for job in list(self.active_jobs.values()):
                self.cancel_job(job.id)

        # Save queue state
        if self.queue_persistence:
            self._save_queue_state()

    def queue_single_job(
        self,
        source_path: Optional[str] = None,
        source_data: Optional[bytes] = None,
        config: Optional[ProcessingConfig] = None,
        description: str = "Image upscaling",
        priority: int = 0,
    ) -> str:
        """Queue a single upscaling job.

        Args:
            source_path: Path to image file
            source_data: Raw image bytes
            config: Processing configuration
            description: Job description
            priority: Job priority (higher = more important)

        Returns:
            Job ID
        """
        with self._lock:
            if len(self.job_queue) >= self.max_queue_size:
                raise RuntimeError(f"Queue is full (max {self.max_queue_size} jobs)")

            # Create job
            job = QueuedJob(
                id="",  # Will be generated in __post_init__
                type=JobType.UPSCALING,
                state=JobState.QUEUED,
                description=description,
                created_at=datetime.now(),
                source_path=source_path,
                source_data=source_data,
                config=config,
                priority=priority,
            )

            # Add to queue in priority order
            self._insert_job_by_priority(job)
            self._update_queue_positions()

            logger.info(f"Queued job {job.id}: {description}")

            # Emit event
            self._emit_queue_event(QueueEvent.JOB_ADDED, job=job)

            # Save state
            if self.queue_persistence:
                self._save_queue_state()

            return job.id

    def queue_batch_jobs(
        self, job_specs: List[Dict[str, Any]], batch_name: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """Queue multiple jobs as a batch.

        Args:
            job_specs: List of job specifications, each containing:
                      - source_path or source_data
                      - config (optional)
                      - description (optional)
                      - priority (optional)
            batch_name: Name for the batch (optional)

        Returns:
            Tuple of (batch_id, list of job_ids)
        """
        with self._lock:
            if len(self.job_queue) + len(job_specs) > self.max_queue_size:
                raise RuntimeError("Batch would exceed queue size limit")

            # Create batch
            batch = BatchInfo(
                id="",  # Will be generated in __post_init__
                name=batch_name or f"Batch of {len(job_specs)} jobs",
                created_at=datetime.now(),
                total_jobs=len(job_specs),
            )

            job_ids = []

            # Create jobs for batch
            for i, spec in enumerate(job_specs):
                job = QueuedJob(
                    id="",  # Will be generated in __post_init__
                    type=JobType.UPSCALING,
                    state=JobState.QUEUED,
                    description=spec.get("description", f"Batch job {i+1}"),
                    created_at=datetime.now(),
                    source_path=spec.get("source_path"),
                    source_data=spec.get("source_data"),
                    config=spec.get("config"),
                    priority=spec.get("priority", 0),
                    batch_id=batch.id,
                )

                self._insert_job_by_priority(job)
                batch.job_ids.append(job.id)
                job_ids.append(job.id)

            # Store batch
            self.batches[batch.id] = batch
            self._update_queue_positions()

            logger.info(f"Queued batch {batch.id} with {len(job_ids)} jobs")

            # Emit events
            self._emit_queue_event(QueueEvent.BATCH_CREATED, batch=batch)
            for job in self.job_queue:
                if job.id in job_ids:
                    self._emit_queue_event(QueueEvent.JOB_ADDED, job=job)

            # Save state
            if self.queue_persistence:
                self._save_queue_state()

            return batch.id, job_ids

    def _insert_job_by_priority(self, job: QueuedJob) -> None:
        """Insert job into queue based on priority.

        Args:
            job: Job to insert
        """
        # Find insertion point based on priority (higher priority first)
        insert_index = 0
        for i, existing_job in enumerate(self.job_queue):
            if job.priority > existing_job.priority:
                insert_index = i
                break
            insert_index = i + 1

        self.job_queue.insert(insert_index, job)

    def _update_queue_positions(self) -> None:
        """Update queue positions for all jobs."""
        for i, job in enumerate(self.job_queue):
            job.queue_position = i

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancellation initiated, False otherwise
        """
        with self._lock:
            # Check if job is in queue
            for i, job in enumerate(self.job_queue):
                if job.id == job_id:
                    if not job.cancellable:
                        logger.warning(f"Job {job_id} is not cancellable")
                        return False

                    # Remove from queue
                    self.job_queue.pop(i)
                    job.state = JobState.CANCELLED
                    job.completed_at = datetime.now()

                    self.completed_jobs.append(job)
                    self._update_queue_positions()

                    logger.info(f"Cancelled queued job {job_id}")

                    # Update batch if applicable
                    if job.batch_id:
                        self._update_batch_stats(job.batch_id)

                    # Emit events
                    self._emit_queue_event(QueueEvent.JOB_CANCELLED, job=job)
                    if self.on_job_cancelled:
                        self.on_job_cancelled(job)

                    # Save state
                    if self.queue_persistence:
                        self._save_queue_state()

                    return True

            # Check if job is active
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]

                if not job.cancellable:
                    logger.warning(f"Job {job_id} is not cancellable")
                    return False

                job.state = JobState.CANCELLING
                logger.info(f"Cancelling active job {job_id}")

                # Cancel pipeline processing
                success = self.pipeline.cancel_processing()

                if success:
                    job.state = JobState.CANCELLED
                    job.completed_at = datetime.now()

                    # Move to completed
                    del self.active_jobs[job_id]
                    self.completed_jobs.append(job)

                    # Update batch if applicable
                    if job.batch_id:
                        self._update_batch_stats(job.batch_id)

                    # Emit events
                    self._emit_queue_event(QueueEvent.JOB_CANCELLED, job=job)
                    if self.on_job_cancelled:
                        self.on_job_cancelled(job)
                else:
                    job.state = JobState.FAILED
                    job.error_message = "Failed to cancel job"
                    job.completed_at = datetime.now()

                    # Move to completed
                    del self.active_jobs[job_id]
                    self.completed_jobs.append(job)

                    # Update batch if applicable
                    if job.batch_id:
                        self._update_batch_stats(job.batch_id)

                    # Emit events
                    self._emit_queue_event(
                        QueueEvent.JOB_FAILED, job=job, message="Failed to cancel job"
                    )
                    if self.on_job_failed:
                        self.on_job_failed(job, "Failed to cancel job")

                # Save state
                if self.queue_persistence:
                    self._save_queue_state()

                return success

            logger.warning(f"Job {job_id} not found")
            return False

    def reorder_job(self, job_id: str, new_position: int) -> bool:
        """Reorder a job in the queue.

        Args:
            job_id: Job ID to reorder
            new_position: New position in queue (0-based)

        Returns:
            True if reordered successfully, False otherwise
        """
        with self._lock:
            # Find job in queue
            job_index = None
            for i, job in enumerate(self.job_queue):
                if job.id == job_id:
                    job_index = i
                    break

            if job_index is None:
                logger.warning(f"Job {job_id} not found in queue")
                return False

            # Validate new position
            new_position = max(0, min(new_position, len(self.job_queue) - 1))

            if job_index == new_position:
                return True  # No change needed

            # Move job
            job = self.job_queue.pop(job_index)
            self.job_queue.insert(new_position, job)
            self._update_queue_positions()

            logger.info(
                f"Reordered job {job_id} from position {job_index} to {new_position}"
            )

            # Emit event
            self._emit_queue_event(QueueEvent.JOB_REORDERED, job=job)

            # Save state
            if self.queue_persistence:
                self._save_queue_state()

            return True

    def pause_queue(self) -> None:
        """Pause queue processing."""
        with self._lock:
            self.auto_process = False
            logger.info("Queue processing paused")
            self._emit_queue_event(QueueEvent.QUEUE_PAUSED)

    def resume_queue(self) -> None:
        """Resume queue processing."""
        with self._lock:
            self.auto_process = True
            logger.info("Queue processing resumed")
            self._emit_queue_event(QueueEvent.QUEUE_RESUMED)

    def clear_completed_jobs(self) -> int:
        """Clear completed jobs from memory.

        Returns:
            Number of jobs cleared
        """
        with self._lock:
            count = len(self.completed_jobs)
            self.completed_jobs.clear()

            # Also clear completed batches
            completed_batches = [
                batch_id
                for batch_id, batch in self.batches.items()
                if batch.is_complete()
            ]
            for batch_id in completed_batches:
                del self.batches[batch_id]

            logger.info(
                f"Cleared {count} completed jobs and "
                f"{len(completed_batches)} completed batches"
            )

            # Save state
            if self.queue_persistence:
                self._save_queue_state()

            return count

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status.

        Returns:
            Dictionary with queue statistics
        """
        with self._lock:
            return {
                "queued_jobs": len(self.job_queue),
                "active_jobs": len(self.active_jobs),
                "completed_jobs": len(self.completed_jobs),
                "total_batches": len(self.batches),
                "auto_process": self.auto_process,
                "max_queue_size": self.max_queue_size,
                "max_concurrent_jobs": self.max_concurrent_jobs,
            }

    def get_job(self, job_id: str) -> Optional[QueuedJob]:
        """Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job if found, None otherwise
        """
        with self._lock:
            # Check queue
            for job in self.job_queue:
                if job.id == job_id:
                    return job

            # Check active jobs
            if job_id in self.active_jobs:
                return self.active_jobs[job_id]

            # Check completed jobs
            for job in self.completed_jobs:
                if job.id == job_id:
                    return job

            return None

    def get_batch(self, batch_id: str) -> Optional[BatchInfo]:
        """Get batch by ID.

        Args:
            batch_id: Batch ID

        Returns:
            Batch if found, None otherwise
        """
        with self._lock:
            return self.batches.get(batch_id)

    def _try_start_next_job(self) -> None:
        """Try to start the next job in queue."""
        with self._lock:
            # Check if we can start more jobs
            if len(self.active_jobs) >= self.max_concurrent_jobs:
                return

            if not self.job_queue:
                return

            if not self.status_monitor.is_available():
                logger.debug("Auto1111 not available, waiting to start next job")
                return

            # Get next job from queue
            job = self.job_queue.pop(0)
            self._update_queue_positions()

            if job.state != JobState.QUEUED:
                logger.warning(f"Invalid job {job.id} in queue with state {job.state}")
                return

            # Start the job
            self.active_jobs[job.id] = job
            job.state = JobState.RUNNING
            job.started_at = datetime.now()

            logger.info(f"Starting job {job.id}: {job.description}")

            # Emit events
            self._emit_queue_event(QueueEvent.JOB_STARTED, job=job)
            if self.on_job_started:
                self.on_job_started(job)

            # Start pipeline processing
            success = False
            if job.source_path:
                success = self.pipeline.start_upscaling(job.source_path, job.config)
            elif job.source_data:
                success = self.pipeline.start_upscaling_from_data(
                    job.source_data, job.config
                )
            else:
                logger.error(f"Job {job.id} has no image data")

            if not success:
                job.state = JobState.FAILED
                job.error_message = "Failed to start pipeline"
                job.completed_at = datetime.now()

                # Move to completed
                del self.active_jobs[job.id]
                self.completed_jobs.append(job)

                # Update batch if applicable
                if job.batch_id:
                    self._update_batch_stats(job.batch_id)

                # Emit events
                self._emit_queue_event(
                    QueueEvent.JOB_FAILED, job=job, message="Failed to start pipeline"
                )
                if self.on_job_failed:
                    self.on_job_failed(job, "Failed to start pipeline")

            # Save state
            if self.queue_persistence:
                self._save_queue_state()

    def _update_batch_stats(self, batch_id: str) -> None:
        """Update batch statistics.

        Args:
            batch_id: Batch ID to update
        """
        if batch_id not in self.batches:
            return

        batch = self.batches[batch_id]
        batch.completed_jobs = 0
        batch.failed_jobs = 0
        batch.cancelled_jobs = 0

        # Count job states
        all_jobs = (
            list(self.job_queue) + list(self.active_jobs.values()) + self.completed_jobs
        )

        for job in all_jobs:
            if job.batch_id == batch_id:
                if job.state == JobState.COMPLETED:
                    batch.completed_jobs += 1
                elif job.state == JobState.FAILED:
                    batch.failed_jobs += 1
                elif job.state == JobState.CANCELLED:
                    batch.cancelled_jobs += 1

        # Check if batch is complete
        if batch.is_complete():
            logger.info(f"Batch {batch_id} completed")
            self._emit_queue_event(QueueEvent.BATCH_COMPLETED, batch=batch)

    def _emit_queue_event(
        self,
        event_type: QueueEvent,
        job: Optional[QueuedJob] = None,
        batch: Optional[BatchInfo] = None,
        message: Optional[str] = None,
    ) -> None:
        """Emit a queue event.

        Args:
            event_type: Type of event
            job: Job associated with event (optional)
            batch: Batch associated with event (optional)
            message: Additional message (optional)
        """
        if self.on_queue_event:
            event_data = QueueEventData(
                event_type=event_type, job=job, batch=batch, message=message
            )
            try:
                self.on_queue_event(event_data)
            except Exception as e:
                logger.error(f"Error in queue event callback: {e}")

    def _on_pipeline_progress(self, message: str, progress: float) -> None:
        """Handle pipeline progress updates."""
        with self._lock:
            # Find the active job (should only be one for Auto1111)
            for job in self.active_jobs.values():
                if job.state == JobState.RUNNING:
                    job.progress = progress

                    # Estimate ETA based on progress
                    if progress > 0 and job.started_at:
                        elapsed = datetime.now() - job.started_at
                        total_time = elapsed / progress
                        remaining_time = total_time - elapsed
                        job.eta = remaining_time

                    # Emit events
                    self._emit_queue_event(
                        QueueEvent.JOB_PROGRESS, job=job, message=message
                    )
                    if self.on_job_progress:
                        self.on_job_progress(job, progress)

                    break

    def _on_pipeline_completed(self, message: str) -> None:
        """Handle pipeline completion."""
        with self._lock:
            # Find the active job
            for job_id, job in list(self.active_jobs.items()):
                if job.state == JobState.RUNNING:
                    job.state = JobState.COMPLETED
                    job.progress = 1.0
                    job.completed_at = datetime.now()
                    job.eta = None

                    # Move to completed
                    del self.active_jobs[job_id]
                    self.completed_jobs.append(job)

                    logger.info(f"Job {job_id} completed: {message}")

                    # Update batch if applicable
                    if job.batch_id:
                        self._update_batch_stats(job.batch_id)

                    # Emit events
                    self._emit_queue_event(
                        QueueEvent.JOB_COMPLETED, job=job, message=message
                    )
                    if self.on_job_completed:
                        self.on_job_completed(job)

                    # Save state
                    if self.queue_persistence:
                        self._save_queue_state()

                    break

    def _on_pipeline_error(self, error_message: str) -> None:
        """Handle pipeline errors."""
        with self._lock:
            # Find the active job
            for job_id, job in list(self.active_jobs.items()):
                if job.state == JobState.RUNNING:
                    job.state = JobState.FAILED
                    job.error_message = error_message
                    job.completed_at = datetime.now()
                    job.eta = None

                    # Move to completed
                    del self.active_jobs[job_id]
                    self.completed_jobs.append(job)

                    logger.error(f"Job {job_id} failed: {error_message}")

                    # Update batch if applicable
                    if job.batch_id:
                        self._update_batch_stats(job.batch_id)

                    # Emit events
                    self._emit_queue_event(
                        QueueEvent.JOB_FAILED, job=job, message=error_message
                    )
                    if self.on_job_failed:
                        self.on_job_failed(job, error_message)

                    # Save state
                    if self.queue_persistence:
                        self._save_queue_state()

                    break

    def _on_pipeline_cancelled(self) -> None:
        """Handle pipeline cancellation."""
        with self._lock:
            # Find the active job
            for job_id, job in list(self.active_jobs.items()):
                if job.state in [JobState.RUNNING, JobState.CANCELLING]:
                    job.state = JobState.CANCELLED
                    job.completed_at = datetime.now()
                    job.eta = None

                    # Move to completed
                    del self.active_jobs[job_id]
                    self.completed_jobs.append(job)

                    logger.info(f"Job {job_id} cancelled")

                    # Update batch if applicable
                    if job.batch_id:
                        self._update_batch_stats(job.batch_id)

                    # Emit events
                    self._emit_queue_event(QueueEvent.JOB_CANCELLED, job=job)
                    if self.on_job_cancelled:
                        self.on_job_cancelled(job)

                    # Save state
                    if self.queue_persistence:
                        self._save_queue_state()

                    break

    def _save_queue_state(self) -> None:
        """Save queue state to file."""
        try:
            # Create state data
            state_data = {
                "version": "1.0",
                "timestamp": datetime.now().isoformat(),
                "queue": [job.to_dict() for job in self.job_queue],
                "active_jobs": [job.to_dict() for job in self.active_jobs.values()],
                "completed_jobs": [
                    job.to_dict() for job in self.completed_jobs[-50:]
                ],  # Keep last 50
                "batches": {
                    batch_id: batch.to_dict()
                    for batch_id, batch in self.batches.items()
                },
                "config": {
                    "max_concurrent_jobs": self.max_concurrent_jobs,
                    "max_queue_size": self.max_queue_size,
                    "auto_process": self.auto_process,
                },
            }

            # Write to file
            persistence_path = Path(self.persistence_file)
            with open(persistence_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Queue state saved to {persistence_path}")

        except Exception as e:
            logger.error(f"Failed to save queue state: {e}")

    def _load_queue_state(self) -> None:
        """Load queue state from file."""
        try:
            persistence_path = Path(self.persistence_file)
            if not persistence_path.exists():
                logger.debug("No queue state file found, starting with empty queue")
                return

            with open(persistence_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Load jobs (only queued jobs, not active or completed)
            for job_data in state_data.get("queue", []):
                try:
                    job = QueuedJob.from_dict(job_data)
                    # Reset state to queued in case it was saved in a different state
                    job.state = JobState.QUEUED
                    job.progress = 0.0
                    job.eta = None
                    self.job_queue.append(job)
                except Exception as e:
                    logger.warning(f"Failed to load job from state: {e}")

            # Load batches
            for batch_id, batch_data in state_data.get("batches", {}).items():
                try:
                    batch = BatchInfo.from_dict(batch_data)
                    self.batches[batch_id] = batch
                except Exception as e:
                    logger.warning(f"Failed to load batch {batch_id} from state: {e}")

            # Load configuration
            config = state_data.get("config", {})
            self.max_concurrent_jobs = config.get("max_concurrent_jobs", 1)
            self.max_queue_size = config.get("max_queue_size", 50)
            self.auto_process = config.get("auto_process", True)

            self._update_queue_positions()

            logger.info(
                f"Loaded queue state with {len(self.job_queue)} jobs and "
                f"{len(self.batches)} batches"
            )

        except Exception as e:
            logger.error(f"Failed to load queue state: {e}")

    # Legacy compatibility methods
    def queue_upscaling_job(
        self, image_path: str, config: Any, description: str = "Image upscaling"
    ) -> str:
        """Legacy method for backward compatibility."""
        return self.queue_single_job(
            source_path=image_path, config=config, description=description
        )

    def queue_upscaling_job_from_data(
        self,
        image_data: bytes,
        config: Any,
        description: str = "Image upscaling from data",
    ) -> str:
        """Legacy method for backward compatibility."""
        return self.queue_single_job(
            source_data=image_data, config=config, description=description
        )
