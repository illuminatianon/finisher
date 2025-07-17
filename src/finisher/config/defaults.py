"""Default configuration values for the application."""

# Default API configuration
DEFAULT_API_CONFIG = {
    "base_url": "http://127.0.0.1:7860",
    "timeout": 300,  # 5 minutes
    "retry_attempts": 3,
    "retry_delay": 1.0,
    "poll_interval": 2.0,  # seconds
    "idle_poll_interval": 10.0,  # seconds when idle
}

# Default processing configuration
DEFAULT_PROCESSING_CONFIG = {
    "upscaler": "Lanczos",  # Will be updated from API
    "scale_factor": 2.5,
    "denoising_strength": 0.15,
    "tile_overlap": 64,
    "steps": 25,
    "sampler_name": "Euler a",
    "cfg_scale": 10,
    "scheduler": "Automatic",
    "batch_size": 1,
    "save_images": False,  # For first pass
    "upscaling_resize": 1.5,  # For second pass
}

# Default UI configuration
DEFAULT_UI_CONFIG = {
    "window_width": 800,
    "window_height": 600,
    "window_x": None,
    "window_y": None,
    "theme": "default",
    "auto_save_config": True,
    "show_advanced_options": False,
    "confirm_emergency_stop": True,
}

# Default application configuration
DEFAULT_APP_CONFIG = {
    "log_level": "INFO",
    "log_file": None,  # None means no file logging
    "temp_dir": None,  # None means use system temp
    "max_temp_files": 10,
    "cleanup_on_exit": True,
    "check_updates": True,
}

# Combined default configuration
DEFAULT_CONFIG = {
    "api": DEFAULT_API_CONFIG,
    "processing": DEFAULT_PROCESSING_CONFIG,
    "ui": DEFAULT_UI_CONFIG,
    "app": DEFAULT_APP_CONFIG,
}

# Image processing limits
IMAGE_LIMITS = {
    "max_width": 4096,
    "max_height": 4096,
    "min_width": 64,
    "min_height": 64,
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "supported_formats": ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'],
}

# Status polling configuration
POLLING_CONFIG = {
    "progress_interval": 2.0,  # seconds during processing
    "idle_interval": 10.0,  # seconds when idle
    "error_interval": 30.0,  # seconds after error
    "max_retries": 5,
    "timeout": 10.0,  # seconds for status requests
}

# Job management configuration
JOB_CONFIG = {
    "timestamp_tolerance": 5,  # seconds for job ownership detection
    "cancel_timeout": 30.0,  # seconds to wait for cancellation
    "interrupt_timeout": 10.0,  # seconds to wait for interrupt
    "queue_check_interval": 1.0,  # seconds
}

# Error handling configuration
ERROR_CONFIG = {
    "max_consecutive_errors": 3,
    "error_cooldown": 60.0,  # seconds
    "show_error_details": True,
    "log_api_responses": False,  # For debugging
}
