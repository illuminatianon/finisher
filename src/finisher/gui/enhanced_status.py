"""Enhanced status bar with queue information and batch progress."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

from ..core.queue_models import QueueEventData, QueueEvent, BatchInfo

logger = logging.getLogger(__name__)


class EnhancedStatusBar(QWidget):
    """Enhanced status bar with queue information and batch progress."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize enhanced status bar.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Queue manager reference (set externally)
        self.queue_manager = None
        
        # Current batch tracking
        self.current_batch: Optional[BatchInfo] = None
        
        self._setup_ui()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_queue_info)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        # Main status label
        self.status_label = QLabel("Ready")
        self.status_label.setMinimumWidth(200)
        layout.addWidget(self.status_label)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator1)
        
        # Queue information
        self.queue_label = QLabel("Queue: 0 jobs")
        self.queue_label.setMinimumWidth(100)
        layout.addWidget(self.queue_label)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator2)
        
        # Batch progress section
        batch_widget = QWidget()
        batch_layout = QVBoxLayout(batch_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        batch_layout.setSpacing(1)
        
        self.batch_label = QLabel("No active batch")
        batch_font = QFont()
        batch_font.setPointSize(8)
        self.batch_label.setFont(batch_font)
        # Use system colors for dark mode compatibility
        self.batch_label.setStyleSheet("color: palette(text);")
        batch_layout.addWidget(self.batch_label)
        
        self.batch_progress = QProgressBar()
        self.batch_progress.setMaximum(100)
        self.batch_progress.setFixedHeight(8)
        self.batch_progress.setVisible(False)
        batch_layout.addWidget(self.batch_progress)
        
        layout.addWidget(batch_widget)
        
        # Add stretch to push progress to the right
        layout.addStretch()
        
        # Current job progress
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(1)
        
        self.progress_label = QLabel("")
        progress_font = QFont()
        progress_font.setPointSize(8)
        self.progress_label.setFont(progress_font)
        self.progress_label.setStyleSheet("color: palette(text);")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_widget)
        
        # ETA label
        self.eta_label = QLabel("")
        self.eta_label.setMinimumWidth(80)
        eta_font = QFont()
        eta_font.setPointSize(8)
        self.eta_label.setFont(eta_font)
        self.eta_label.setStyleSheet("color: palette(text);")
        layout.addWidget(self.eta_label)
    
    def set_queue_manager(self, queue_manager) -> None:
        """Set the queue manager reference.
        
        Args:
            queue_manager: EnhancedQueueManager instance
        """
        self.queue_manager = queue_manager
        self._update_queue_info()
    
    def update_status(self, status: str, progress: Optional[float] = None) -> None:
        """Update main status and progress.
        
        Args:
            status: Status text
            progress: Progress value (0.0 to 1.0) or None to hide
        """
        self.status_label.setText(status)
        
        if progress is not None:
            progress_percent = int(progress * 100)
            self.progress_bar.setValue(progress_percent)
            self.progress_bar.setVisible(True)
            self.progress_label.setText(f"{progress_percent}%")
        else:
            self.progress_bar.setVisible(False)
            self.progress_label.setText("")
    
    def update_job_progress(self, job_name: str, progress: float, eta: Optional[timedelta] = None) -> None:
        """Update job-specific progress.
        
        Args:
            job_name: Name of the current job
            progress: Progress value (0.0 to 1.0)
            eta: Estimated time remaining
        """
        progress_percent = int(progress * 100)
        self.progress_bar.setValue(progress_percent)
        self.progress_bar.setVisible(True)
        self.progress_label.setText(f"{job_name} - {progress_percent}%")
        
        if eta:
            eta_text = self._format_eta(eta)
            self.eta_label.setText(f"ETA: {eta_text}")
        else:
            self.eta_label.setText("")
    
    def update_batch_progress(self, batch: BatchInfo) -> None:
        """Update batch progress display.
        
        Args:
            batch: Batch information
        """
        self.current_batch = batch
        
        if batch.total_jobs > 0:
            progress = batch.get_progress()
            progress_percent = int(progress * 100)
            
            completed = batch.completed_jobs + batch.failed_jobs + batch.cancelled_jobs
            self.batch_label.setText(f"Batch: {completed}/{batch.total_jobs} jobs")
            self.batch_progress.setValue(progress_percent)
            self.batch_progress.setVisible(True)
        else:
            self.batch_label.setText("No active batch")
            self.batch_progress.setVisible(False)
    
    def clear_batch_progress(self) -> None:
        """Clear batch progress display."""
        self.current_batch = None
        self.batch_label.setText("No active batch")
        self.batch_progress.setVisible(False)
    
    def handle_queue_event(self, event_data: QueueEventData) -> None:
        """Handle queue events.
        
        Args:
            event_data: Queue event data
        """
        # Update queue info immediately
        self._update_queue_info()
        
        # Handle batch events
        if event_data.batch:
            if event_data.event_type == QueueEvent.BATCH_CREATED:
                self.update_batch_progress(event_data.batch)
            elif event_data.event_type == QueueEvent.BATCH_COMPLETED:
                self.clear_batch_progress()
        
        # Update batch progress if we have a current batch
        if self.current_batch and self.queue_manager:
            updated_batch = self.queue_manager.get_batch(self.current_batch.id)
            if updated_batch:
                self.update_batch_progress(updated_batch)
            elif event_data.event_type == QueueEvent.BATCH_COMPLETED:
                self.clear_batch_progress()
    
    def _update_queue_info(self) -> None:
        """Update queue information display."""
        if not self.queue_manager:
            self.queue_label.setText("Queue: 0 jobs")
            return
        
        status = self.queue_manager.get_queue_status()
        
        # Format queue status
        queue_text_parts = []
        if status['queued_jobs'] > 0:
            queue_text_parts.append(f"{status['queued_jobs']} queued")
        if status['active_jobs'] > 0:
            queue_text_parts.append(f"{status['active_jobs']} active")
        if status['completed_jobs'] > 0:
            queue_text_parts.append(f"{status['completed_jobs']} completed")
        
        if queue_text_parts:
            queue_text = "Queue: " + ", ".join(queue_text_parts)
        else:
            queue_text = "Queue: empty"
        
        # Add pause indicator
        if not status['auto_process']:
            queue_text += " (PAUSED)"
        
        self.queue_label.setText(queue_text)
        
        # Update batch info if we have a current batch
        if self.current_batch:
            updated_batch = self.queue_manager.get_batch(self.current_batch.id)
            if updated_batch:
                self.update_batch_progress(updated_batch)
            else:
                self.clear_batch_progress()
    
    def _format_eta(self, eta: timedelta) -> str:
        """Format ETA for display.
        
        Args:
            eta: Time remaining
            
        Returns:
            Formatted ETA string
        """
        total_seconds = int(eta.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def show_processing_feedback(self, message: str) -> None:
        """Show processing feedback message.
        
        Args:
            message: Feedback message
        """
        self.status_label.setText(message)
    
    def show_error_message(self, message: str) -> None:
        """Show error message in status.
        
        Args:
            message: Error message
        """
        self.status_label.setText(f"Error: {message}")
        # Could add red styling here
    
    def reset_ui_state(self) -> None:
        """Reset UI to default state."""
        self.status_label.setText("Ready")
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.eta_label.setText("")
        self.clear_batch_progress()
