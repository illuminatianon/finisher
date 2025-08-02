"""Comprehensive error handling system."""

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable, Dict, Any
from enum import Enum
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Error categories."""

    NETWORK = "NETWORK"
    API = "API"
    IMAGE = "IMAGE"
    FILE = "FILE"
    PROCESSING = "PROCESSING"
    CONFIGURATION = "CONFIGURATION"
    UI = "UI"
    SYSTEM = "SYSTEM"


class FinisherError(Exception):
    """Base exception for Finisher application."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize error.

        Args:
            message: Technical error message
            category: Error category
            severity: Error severity
            user_message: User-friendly message
            details: Additional error details
        """
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.user_message = user_message or self._generate_user_message(
            message, category
        )
        self.details = details or {}
        self.timestamp = datetime.now()

    @staticmethod
    def _generate_user_message(message: str, category: ErrorCategory) -> str:
        """Generate user-friendly message based on technical message.

        Args:
            message: Technical message
            category: Error category

        Returns:
            User-friendly message
        """
        category_messages = {
            ErrorCategory.NETWORK: "Network connection error. "
            "Please check your internet connection.",
            ErrorCategory.API: "Auto1111 server error. "
            "Please check if the server is running.",
            ErrorCategory.IMAGE: "Image processing error. "
            "Please check the image file.",
            ErrorCategory.FILE: "File error. "
            "Please check file permissions and path.",
            ErrorCategory.PROCESSING: "Processing error. "
            "The operation could not be completed.",
            ErrorCategory.CONFIGURATION: "Configuration error. "
            "Please check your settings.",
            ErrorCategory.UI: "Interface error. Please try again.",
            ErrorCategory.SYSTEM: "System error. Please restart the "
            "application if the problem persists.",
        }

        return category_messages.get(category, "An error occurred. Please try again.")


class NetworkError(FinisherError):
    """Network-related errors."""

    def __init__(self, message: str, user_message: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            user_message=user_message
            or "Network connection error. Please check your connection and "
            "Auto1111 server.",
            **kwargs,
        )


class APIError(FinisherError):
    """API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        user_message: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if status_code:
            details["status_code"] = status_code

        super().__init__(
            message,
            category=ErrorCategory.API,
            user_message=user_message or f"Auto1111 API error. {message}",
            details=details,
            **kwargs,
        )


class ImageError(FinisherError):
    """Image processing errors."""

    def __init__(self, message: str, user_message: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.IMAGE,
            user_message=user_message
            or "Image processing error. Please check the image format and "
            "try again.",
            **kwargs,
        )


class FileError(FinisherError):
    """File handling errors."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        user_message: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if file_path:
            details["file_path"] = file_path

        super().__init__(
            message,
            category=ErrorCategory.FILE,
            user_message=user_message
            or "File error. Please check the file path and permissions.",
            details=details,
            **kwargs,
        )


class ProcessingError(FinisherError):
    """Processing pipeline errors."""

    def __init__(self, message: str, user_message: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING,
            user_message=user_message
            or "Processing error. The upscaling operation failed.",
            **kwargs,
        )


class ErrorHandler:
    """Centralized error handling system."""

    def __init__(self, root: Optional[tk.Tk] = None):
        """Initialize error handler.

        Args:
            root: Tkinter root window for GUI error dialogs
        """
        self.root = root
        self.error_count = 0
        self.last_error_time: Optional[datetime] = None
        self.error_cooldown = timedelta(seconds=60)

        # Callbacks
        self.on_error: Optional[Callable[[FinisherError], None]] = None
        self.on_critical_error: Optional[Callable[[FinisherError], None]] = None

        # Error suppression
        self.suppress_dialogs = False
        self.max_errors_per_minute = 5
        self.recent_errors: list = []

    def handle_exception(
        self, exc: Exception, context: str = "", show_dialog: bool = True
    ) -> FinisherError:
        """Handle any exception and convert to FinisherError.

        Args:
            exc: Exception to handle
            context: Context where error occurred
            show_dialog: Whether to show error dialog

        Returns:
            FinisherError instance
        """
        # Convert to FinisherError if needed
        if isinstance(exc, FinisherError):
            error = exc
        else:
            error = self._convert_exception(exc, context)

        # Log the error
        self._log_error(error, context)

        # Track error frequency
        self._track_error_frequency()

        # Show dialog if requested and not suppressed
        if show_dialog and not self.suppress_dialogs and self._should_show_dialog():
            self._show_error_dialog(error)

        # Call callbacks
        if error.severity == ErrorSeverity.CRITICAL and self.on_critical_error:
            self.on_critical_error(error)
        elif self.on_error:
            self.on_error(error)

        return error

    def handle_network_error(
        self, exc: requests.RequestException, context: str = ""
    ) -> NetworkError:
        """Handle network-specific errors.

        Args:
            exc: Network exception
            context: Context where error occurred

        Returns:
            NetworkError instance
        """
        if isinstance(exc, requests.Timeout):
            error = NetworkError(
                f"Request timeout: {exc}",
                user_message="Request timed out. The Auto1111 server may be "
                "busy or unreachable.",
            )
        elif isinstance(exc, requests.ConnectionError):
            error = NetworkError(
                f"Connection error: {exc}",
                user_message="Cannot connect to Auto1111 server. Please check "
                "if it's running and accessible.",
            )
        elif isinstance(exc, requests.HTTPError):
            status_code = getattr(exc.response, "status_code", None)
            error = APIError(
                f"HTTP error {status_code}: {exc}",
                status_code=status_code,
                user_message=f"Auto1111 server returned error {status_code}. "
                f"Please check server logs.",
            )
        else:
            error = NetworkError(f"Network error: {exc}")

        return self.handle_exception(error, context)

    def handle_image_error(
        self, exc: Exception, file_path: Optional[str] = None, context: str = ""
    ) -> ImageError:
        """Handle image processing errors.

        Args:
            exc: Image exception
            file_path: Path to problematic image
            context: Context where error occurred

        Returns:
            ImageError instance
        """
        details = {}
        if file_path:
            details["file_path"] = file_path

        if "cannot identify image file" in str(exc).lower():
            user_message = (
                "Invalid image file. Please select a valid image format "
                "(PNG, JPEG, etc.)."
            )
        elif "truncated" in str(exc).lower():
            user_message = (
                "Corrupted image file. The image appears to be incomplete or "
                "damaged."
            )
        elif "size" in str(exc).lower():
            user_message = (
                "Image size error. The image may be too large or have invalid "
                "dimensions."
            )
        else:
            user_message = "Image processing error. Please try a different image."

        error = ImageError(
            f"Image error: {exc}", user_message=user_message, details=details
        )

        return self.handle_exception(error, context)

    def handle_file_error(
        self, exc: Exception, file_path: Optional[str] = None, context: str = ""
    ) -> FileError:
        """Handle file operation errors.

        Args:
            exc: File exception
            file_path: Path to problematic file
            context: Context where error occurred

        Returns:
            FileError instance
        """
        details = {}
        if file_path:
            details["file_path"] = file_path

        if isinstance(exc, FileNotFoundError):
            user_message = f"File not found: {file_path or 'Unknown file'}"
        elif isinstance(exc, PermissionError):
            user_message = (
                f"Permission denied accessing file: {file_path or 'Unknown file'}"
            )
        elif isinstance(exc, OSError):
            user_message = f"File system error: {exc}"
        else:
            user_message = f"File error: {exc}"

        error = FileError(
            f"File error: {exc}",
            file_path=file_path,
            user_message=user_message,
            details=details,
        )

        return self.handle_exception(error, context)

    def _convert_exception(self, exc: Exception, context: str) -> FinisherError:
        """Convert generic exception to FinisherError.

        Args:
            exc: Exception to convert
            context: Context where error occurred

        Returns:
            FinisherError instance
        """
        # Determine category based on exception type
        if isinstance(exc, (requests.RequestException, ConnectionError)):
            category = ErrorCategory.NETWORK
        elif isinstance(exc, (IOError, OSError, FileNotFoundError, PermissionError)):
            category = ErrorCategory.FILE
        elif "image" in str(exc).lower() or "PIL" in str(type(exc).__name__):
            category = ErrorCategory.IMAGE
        else:
            category = ErrorCategory.SYSTEM

        # Determine severity
        if isinstance(exc, (MemoryError, SystemExit, KeyboardInterrupt)):
            severity = ErrorSeverity.CRITICAL
        elif isinstance(exc, (ValueError, TypeError, AttributeError)):
            severity = ErrorSeverity.ERROR
        else:
            severity = ErrorSeverity.WARNING

        return FinisherError(
            f"{context}: {exc}" if context else str(exc),
            category=category,
            severity=severity,
            details={"exception_type": type(exc).__name__},
        )

    def _log_error(self, error: FinisherError, context: str) -> None:
        """Log error with appropriate level.

        Args:
            error: Error to log
            context: Context where error occurred
        """
        log_message = f"{context}: {error}" if context else str(error)

        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(log_message)
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Log details if available
        if error.details:
            logger.debug(f"Error details: {error.details}")

    def _track_error_frequency(self) -> None:
        """Track error frequency for rate limiting."""
        now = datetime.now()

        # Remove old errors (older than 1 minute)
        self.recent_errors = [
            error_time
            for error_time in self.recent_errors
            if now - error_time < timedelta(minutes=1)
        ]

        # Add current error
        self.recent_errors.append(now)
        self.error_count += 1
        self.last_error_time = now

        # Suppress dialogs if too many errors
        if len(self.recent_errors) > self.max_errors_per_minute:
            self.suppress_dialogs = True
            logger.warning("Too many errors, suppressing error dialogs")

    def _should_show_dialog(self) -> bool:
        """Check if error dialog should be shown.

        Returns:
            True if dialog should be shown
        """
        if not self.root:
            return False

        # Don't show if recently shown
        if self.last_error_time and (
            datetime.now() - self.last_error_time < self.error_cooldown
        ):
            return False

        return True

    def _show_error_dialog(self, error: FinisherError) -> None:
        """Show error dialog to user.

        Args:
            error: Error to display
        """
        if not self.root:
            return

        try:
            title = f"Error - {error.category.value}"

            if error.severity == ErrorSeverity.CRITICAL:
                messagebox.showerror(title, error.user_message)
            elif error.severity == ErrorSeverity.ERROR:
                messagebox.showerror(title, error.user_message)
            elif error.severity == ErrorSeverity.WARNING:
                messagebox.showwarning(title, error.user_message)
            else:
                messagebox.showinfo(title, error.user_message)

        except Exception as e:
            logger.error(f"Failed to show error dialog: {e}")

    def reset_error_suppression(self) -> None:
        """Reset error suppression."""
        self.suppress_dialogs = False
        self.recent_errors.clear()
        logger.info("Error suppression reset")

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics.

        Returns:
            Error statistics dictionary
        """
        return {
            "total_errors": self.error_count,
            "recent_errors": len(self.recent_errors),
            "last_error_time": self.last_error_time,
            "dialogs_suppressed": self.suppress_dialogs,
        }
