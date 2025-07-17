"""Core processing package for image handling and metadata."""

from .processor import ImageProcessor
from .metadata import MetadataExtractor
from .status_monitor import StatusMonitor, JobStatus
from .upscaling_pipeline import UpscalingPipeline
from .job_manager import JobManager, Job, JobType, JobState
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
