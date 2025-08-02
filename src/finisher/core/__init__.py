"""Core processing package for image handling and metadata."""

from .processor import ImageProcessor
from .metadata import MetadataExtractor
from .status_monitor import StatusMonitor, JobStatus
from .upscaling_pipeline import UpscalingPipeline
from .job_manager import JobManager, Job, JobType, JobState
from .queue_models import QueuedJob, BatchInfo, QueueEvent, QueueEventData
from .enhanced_queue_manager import EnhancedQueueManager
from .batch_input_handler import BatchInputHandler
from .input_handler import InputHandler, ClipboardMonitor, DragDropHandler
from .error_handler import (
    ErrorHandler, FinisherError, NetworkError, APIError,
    ImageError, FileError, ProcessingError, ErrorSeverity, ErrorCategory
)
from .utils import (
    encode_image_to_base64,
    decode_base64_to_image,
    validate_image_format,
    create_temp_file,
    cleanup_temp_files,
)

__all__ = [
    "ImageProcessor",
    "MetadataExtractor",
    "StatusMonitor",
    "JobStatus",
    "UpscalingPipeline",
    "JobManager",
    "Job",
    "JobType",
    "JobState",
    "QueuedJob",
    "BatchInfo",
    "QueueEvent",
    "QueueEventData",
    "EnhancedQueueManager",
    "BatchInputHandler",
    "InputHandler",
    "ClipboardMonitor",
    "DragDropHandler",
    "ErrorHandler",
    "FinisherError",
    "NetworkError",
    "APIError",
    "ImageError",
    "FileError",
    "ProcessingError",
    "ErrorSeverity",
    "ErrorCategory",
    "encode_image_to_base64",
    "decode_base64_to_image",
    "validate_image_format",
    "create_temp_file",
    "cleanup_temp_files",
]
