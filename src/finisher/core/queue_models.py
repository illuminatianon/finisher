"""Enhanced queue data models for the finisher application."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List

from .job_manager import JobType, JobState
from ..api.models import ProcessingConfig

logger = logging.getLogger(__name__)


@dataclass
class QueuedJob:
    """Enhanced job model with queue-specific metadata."""
    
    # Core job information
    id: str
    type: JobType
    state: JobState
    description: str
    created_at: datetime
    
    # Timing information
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Job data
    source_path: Optional[str] = None
    source_data: Optional[bytes] = None
    config: Optional[ProcessingConfig] = None
    
    # Progress tracking
    progress: float = 0.0
    eta: Optional[timedelta] = None
    error_message: Optional[str] = None
    
    # Queue metadata
    priority: int = 0
    queue_position: int = 0
    batch_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Job control
    cancellable: bool = True
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.id:
            self.id = self._generate_job_id()
    
    @staticmethod
    def _generate_job_id() -> str:
        """Generate unique job ID.
        
        Returns:
            Job ID string
        """
        return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    @classmethod
    def from_legacy_job(cls, legacy_job) -> 'QueuedJob':
        """Create QueuedJob from legacy Job object.
        
        Args:
            legacy_job: Legacy Job object from job_manager
            
        Returns:
            QueuedJob instance
        """
        return cls(
            id=legacy_job.job_id,
            type=legacy_job.job_type,
            state=legacy_job.state,
            description=legacy_job.description,
            created_at=legacy_job.created_at,
            started_at=legacy_job.started_at,
            completed_at=legacy_job.completed_at,
            source_path=getattr(legacy_job, 'image_path', None),
            source_data=getattr(legacy_job, 'image_data', None),
            config=getattr(legacy_job, 'config', None),
            progress=legacy_job.progress,
            error_message=legacy_job.error_message,
            cancellable=legacy_job.cancellable
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization.
        
        Returns:
            Dictionary representation of the job
        """
        return {
            'id': self.id,
            'type': self.type.value,
            'state': self.state.value,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'source_path': self.source_path,
            'progress': self.progress,
            'eta_seconds': self.eta.total_seconds() if self.eta else None,
            'error_message': self.error_message,
            'priority': self.priority,
            'queue_position': self.queue_position,
            'batch_id': self.batch_id,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'cancellable': self.cancellable,
            # Note: source_data and config are not serialized for persistence
            # They will need to be reconstructed when loading
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedJob':
        """Create QueuedJob from dictionary.
        
        Args:
            data: Dictionary representation of the job
            
        Returns:
            QueuedJob instance
        """
        return cls(
            id=data['id'],
            type=JobType(data['type']),
            state=JobState(data['state']),
            description=data['description'],
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            source_path=data.get('source_path'),
            progress=data.get('progress', 0.0),
            eta=timedelta(seconds=data['eta_seconds']) if data.get('eta_seconds') else None,
            error_message=data.get('error_message'),
            priority=data.get('priority', 0),
            queue_position=data.get('queue_position', 0),
            batch_id=data.get('batch_id'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            cancellable=data.get('cancellable', True)
        )
    
    def can_retry(self) -> bool:
        """Check if job can be retried.
        
        Returns:
            True if job can be retried, False otherwise
        """
        return (self.state == JobState.FAILED and 
                self.retry_count < self.max_retries)
    
    def is_terminal_state(self) -> bool:
        """Check if job is in a terminal state.
        
        Returns:
            True if job is in terminal state, False otherwise
        """
        return self.state in {JobState.COMPLETED, JobState.CANCELLED, JobState.FAILED}
    
    def get_display_name(self) -> str:
        """Get display name for the job.
        
        Returns:
            Human-readable job name
        """
        if self.source_path:
            import os
            return os.path.basename(self.source_path)
        elif self.batch_id:
            return f"Batch {self.batch_id} - Job {self.queue_position + 1}"
        else:
            return self.description


@dataclass
class BatchInfo:
    """Information about a batch of jobs."""
    
    id: str
    name: str
    created_at: datetime
    job_ids: List[str] = field(default_factory=list)
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    cancelled_jobs: int = 0
    
    def __post_init__(self):
        """Post-initialization processing."""
        if not self.id:
            self.id = self._generate_batch_id()
        if not self.name:
            self.name = f"Batch {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @staticmethod
    def _generate_batch_id() -> str:
        """Generate unique batch ID.
        
        Returns:
            Batch ID string
        """
        return f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def get_progress(self) -> float:
        """Get batch progress as percentage.
        
        Returns:
            Progress percentage (0.0 to 1.0)
        """
        if self.total_jobs == 0:
            return 0.0
        return (self.completed_jobs + self.failed_jobs + self.cancelled_jobs) / self.total_jobs
    
    def is_complete(self) -> bool:
        """Check if batch is complete.
        
        Returns:
            True if all jobs are finished, False otherwise
        """
        return (self.completed_jobs + self.failed_jobs + self.cancelled_jobs) >= self.total_jobs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert batch to dictionary for serialization.
        
        Returns:
            Dictionary representation of the batch
        """
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'job_ids': self.job_ids,
            'total_jobs': self.total_jobs,
            'completed_jobs': self.completed_jobs,
            'failed_jobs': self.failed_jobs,
            'cancelled_jobs': self.cancelled_jobs
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchInfo':
        """Create BatchInfo from dictionary.
        
        Args:
            data: Dictionary representation of the batch
            
        Returns:
            BatchInfo instance
        """
        return cls(
            id=data['id'],
            name=data['name'],
            created_at=datetime.fromisoformat(data['created_at']),
            job_ids=data.get('job_ids', []),
            total_jobs=data.get('total_jobs', 0),
            completed_jobs=data.get('completed_jobs', 0),
            failed_jobs=data.get('failed_jobs', 0),
            cancelled_jobs=data.get('cancelled_jobs', 0)
        )


class QueueEvent(Enum):
    """Queue event types for notifications."""
    JOB_ADDED = "JOB_ADDED"
    JOB_STARTED = "JOB_STARTED"
    JOB_PROGRESS = "JOB_PROGRESS"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    JOB_CANCELLED = "JOB_CANCELLED"
    JOB_REORDERED = "JOB_REORDERED"
    BATCH_CREATED = "BATCH_CREATED"
    BATCH_COMPLETED = "BATCH_COMPLETED"
    QUEUE_PAUSED = "QUEUE_PAUSED"
    QUEUE_RESUMED = "QUEUE_RESUMED"
    QUEUE_CLEARED = "QUEUE_CLEARED"


@dataclass
class QueueEventData:
    """Data for queue events."""
    event_type: QueueEvent
    job: Optional[QueuedJob] = None
    batch: Optional[BatchInfo] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    additional_data: Dict[str, Any] = field(default_factory=dict)
