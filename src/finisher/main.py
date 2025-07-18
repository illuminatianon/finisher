"""Main entry point for Finisher application."""

import sys
import logging
from typing import NoReturn
from PySide6.QtWidgets import QApplication

from .app_controller import ApplicationController
from .config import ApplicationSettings


def setup_logging(level: str = "INFO") -> None:
    """Set up application logging.

    Args:
        level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main() -> NoReturn:
    """Main entry point for the application."""
    # Create QApplication instance first
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Finisher")
    qt_app.setApplicationDisplayName("Finisher - AI Image Upscaling Tool")
    qt_app.setApplicationVersion("0.0.0")

    # Load settings for logging configuration
    settings = ApplicationSettings()

    # Set up logging
    log_level = settings.get('app.log_level', 'INFO')
    setup_logging(log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting Finisher - AI Image Upscaling Tool")

    try:
        # Create and run application
        app = ApplicationController()
        app.run()

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
