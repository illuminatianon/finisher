"""Queue panel component for displaying and managing the job queue."""

import logging
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QProgressBar,
    QMenu, QMessageBox, QSplitter, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QFont, QColor, QPalette

from ..core.queue_models import QueuedJob, BatchInfo, QueueEvent, QueueEventData, JobState

logger = logging.getLogger(__name__)


class QueueJobItem(QListWidgetItem):
    """Custom list item for queue jobs."""
    
    def __init__(self, job: QueuedJob):
        """Initialize job item.
        
        Args:
            job: QueuedJob instance
        """
        super().__init__()
        self.job = job
        self.update_display()
    
    def update_display(self) -> None:
        """Update the display text and styling."""
        # Create display text with better formatting
        display_name = self.job.get_display_name()

        # Format state with icons
        state_icons = {
            JobState.QUEUED: "⏳",
            JobState.RUNNING: "🔄",
            JobState.COMPLETED: "✅",
            JobState.FAILED: "❌",
            JobState.CANCELLED: "⏹️",
            JobState.CANCELLING: "🛑"
        }

        state_icon = state_icons.get(self.job.state, "❓")

        # Progress text
        if self.job.progress > 0 and self.job.state == JobState.RUNNING:
            progress_text = f" ({self.job.progress:.1%})"
        else:
            progress_text = ""

        # Batch indicator
        if self.job.batch_id:
            batch_text = " 📦"
        else:
            batch_text = ""

        # Priority indicator
        if self.job.priority > 0:
            priority_text = " ⬆️"
        elif self.job.priority < 0:
            priority_text = " ⬇️"
        else:
            priority_text = ""

        self.setText(f"{state_icon} {display_name}{progress_text}{batch_text}{priority_text}")

        # Set styling based on state with better colors
        if self.job.state == JobState.RUNNING:
            self.setBackground(QColor(230, 255, 230))  # Very light green
            self.setForeground(QColor(0, 100, 0))      # Dark green text
        elif self.job.state == JobState.COMPLETED:
            self.setBackground(QColor(240, 248, 255))  # Very light blue
            self.setForeground(QColor(70, 70, 70))     # Dark gray text
        elif self.job.state == JobState.FAILED:
            self.setBackground(QColor(255, 240, 240))  # Very light red
            self.setForeground(QColor(150, 0, 0))      # Dark red text
        elif self.job.state == JobState.CANCELLED:
            self.setBackground(QColor(255, 250, 230))  # Very light orange
            self.setForeground(QColor(150, 100, 0))    # Dark orange text
        elif self.job.state == JobState.QUEUED:
            if self.job.priority > 0:
                self.setBackground(QColor(255, 248, 220))  # Light yellow for high priority
                self.setForeground(QColor(100, 80, 0))     # Dark yellow text
            else:
                self.setBackground(QColor(255, 255, 255))  # White
                self.setForeground(QColor(0, 0, 0))        # Black text
        else:
            self.setBackground(QColor(255, 255, 255))  # White
            self.setForeground(QColor(0, 0, 0))        # Black text


class QueuePanel(QWidget):
    """Panel for displaying and managing the job queue."""
    
    # Signals for queue operations
    job_cancelled = Signal(str)  # job_id
    job_reordered = Signal(str, int)  # job_id, new_position
    queue_paused = Signal()
    queue_resumed = Signal()
    queue_cleared = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize queue panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Queue manager reference (set externally)
        self.queue_manager = None
        
        # Job items cache
        self.job_items: Dict[str, QueueJobItem] = {}
        
        self._setup_ui()
        self._setup_context_menu()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(1000)  # Update every second
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Title
        title_label = QLabel("Job Queue")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Queue statistics
        self.stats_label = QLabel("📭 Queue is empty")
        self.stats_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                color: #495057;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.stats_label)
        
        # Splitter for queue list and details
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Queue list
        queue_group = QGroupBox("Jobs")
        queue_layout = QVBoxLayout(queue_group)
        
        self.queue_list = QListWidget()
        self.queue_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.queue_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.queue_list.itemDoubleClicked.connect(self._on_item_double_clicked)

        # Improve list styling
        self.queue_list.setAlternatingRowColors(True)
        self.queue_list.setSpacing(2)
        self.queue_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #e6f3ff;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
                min-height: 20px;
            }
            QListWidget::item:selected {
                background-color: #e6f3ff;
                border: 1px solid #0078d4;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)

        queue_layout.addWidget(self.queue_list)
        
        splitter.addWidget(queue_group)
        
        # Job details
        details_group = QGroupBox("Job Details")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        splitter.addWidget(details_group)
        
        # Set splitter proportions
        splitter.setSizes([300, 100])
        
        # Control buttons
        button_layout = QHBoxLayout()

        self.pause_button = QPushButton("⏸️ Pause Queue")
        self.pause_button.clicked.connect(self._toggle_queue_processing)
        self.pause_button.setStyleSheet("""
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """)
        button_layout.addWidget(self.pause_button)

        self.clear_button = QPushButton("🗑️ Clear Completed")
        self.clear_button.clicked.connect(self._clear_completed)
        self.clear_button.setStyleSheet(self.pause_button.styleSheet())
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        # Reorder buttons
        self.move_up_button = QPushButton("⬆️")
        self.move_up_button.setMaximumWidth(35)
        self.move_up_button.clicked.connect(self._move_job_up)
        self.move_up_button.setEnabled(False)
        self.move_up_button.setToolTip("Move job up in queue")
        self.move_up_button.setStyleSheet("""
            QPushButton {
                padding: 4px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background-color: #e9ecef;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #999;
            }
        """)
        button_layout.addWidget(self.move_up_button)

        self.move_down_button = QPushButton("⬇️")
        self.move_down_button.setMaximumWidth(35)
        self.move_down_button.clicked.connect(self._move_job_down)
        self.move_down_button.setEnabled(False)
        self.move_down_button.setToolTip("Move job down in queue")
        self.move_down_button.setStyleSheet(self.move_up_button.styleSheet())
        button_layout.addWidget(self.move_down_button)
        
        layout.addLayout(button_layout)
    
    def _setup_context_menu(self) -> None:
        """Set up context menu for queue items."""
        self.queue_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self._show_context_menu)
    
    def set_queue_manager(self, queue_manager) -> None:
        """Set the queue manager reference.
        
        Args:
            queue_manager: EnhancedQueueManager instance
        """
        self.queue_manager = queue_manager
        self._update_display()
    
    def handle_queue_event(self, event_data: QueueEventData) -> None:
        """Handle queue events.
        
        Args:
            event_data: Queue event data
        """
        # Update display when queue changes
        self._update_display()
        
        # Handle specific events
        if event_data.event_type == QueueEvent.QUEUE_PAUSED:
            self.pause_button.setText("▶️ Resume Queue")
        elif event_data.event_type == QueueEvent.QUEUE_RESUMED:
            self.pause_button.setText("⏸️ Pause Queue")
    
    def _update_display(self) -> None:
        """Update the queue display."""
        if not self.queue_manager:
            return
        
        # Get current selection
        selected_job_id = None
        current_item = self.queue_list.currentItem()
        if current_item and isinstance(current_item, QueueJobItem):
            selected_job_id = current_item.job.id
        
        # Clear and rebuild list
        self.queue_list.clear()
        self.job_items.clear()
        
        # Add queued jobs
        for job in self.queue_manager.job_queue:
            item = QueueJobItem(job)
            self.job_items[job.id] = item
            self.queue_list.addItem(item)
        
        # Add active jobs
        for job in self.queue_manager.active_jobs.values():
            item = QueueJobItem(job)
            self.job_items[job.id] = item
            self.queue_list.addItem(item)
        
        # Add recent completed jobs (last 10)
        recent_completed = self.queue_manager.completed_jobs[-10:]
        for job in recent_completed:
            item = QueueJobItem(job)
            self.job_items[job.id] = item
            self.queue_list.addItem(item)
        
        # Restore selection
        if selected_job_id and selected_job_id in self.job_items:
            self.queue_list.setCurrentItem(self.job_items[selected_job_id])
        
        # Update statistics with better formatting
        status = self.queue_manager.get_queue_status()

        # Create a more readable stats display
        stats_parts = []
        if status['queued_jobs'] > 0:
            stats_parts.append(f"⏳ {status['queued_jobs']} queued")
        if status['active_jobs'] > 0:
            stats_parts.append(f"🔄 {status['active_jobs']} active")
        if status['completed_jobs'] > 0:
            stats_parts.append(f"✅ {status['completed_jobs']} completed")

        if stats_parts:
            stats_text = " • ".join(stats_parts)
        else:
            stats_text = "📭 Queue is empty"

        # Add pause indicator
        if not status['auto_process']:
            stats_text += " • ⏸️ PAUSED"

        self.stats_label.setText(stats_text)
        
        # Update pause button
        if status['auto_process']:
            self.pause_button.setText("⏸️ Pause Queue")
        else:
            self.pause_button.setText("▶️ Resume Queue")
    
    def _on_selection_changed(self) -> None:
        """Handle selection change in queue list."""
        current_item = self.queue_list.currentItem()
        
        # Enable/disable reorder buttons
        can_reorder = (current_item and 
                      isinstance(current_item, QueueJobItem) and
                      current_item.job.state == JobState.QUEUED)
        
        self.move_up_button.setEnabled(can_reorder)
        self.move_down_button.setEnabled(can_reorder)
        
        # Update details
        if current_item and isinstance(current_item, QueueJobItem):
            self._show_job_details(current_item.job)
        else:
            self.details_text.clear()
    
    def _show_job_details(self, job: QueuedJob) -> None:
        """Show details for a job.
        
        Args:
            job: Job to show details for
        """
        details = []
        details.append(f"ID: {job.id}")
        details.append(f"Description: {job.description}")
        details.append(f"State: {job.state.value}")
        details.append(f"Created: {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if job.started_at:
            details.append(f"Started: {job.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if job.completed_at:
            details.append(f"Completed: {job.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if job.progress > 0:
            details.append(f"Progress: {job.progress:.1%}")
        
        if job.eta:
            details.append(f"ETA: {job.eta}")
        
        if job.error_message:
            details.append(f"Error: {job.error_message}")
        
        if job.batch_id:
            details.append(f"Batch ID: {job.batch_id}")
        
        if job.source_path:
            details.append(f"Source: {job.source_path}")
        
        self.details_text.setPlainText("\n".join(details))

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on queue item.

        Args:
            item: Clicked item
        """
        if isinstance(item, QueueJobItem):
            # For now, just show details - could open job details dialog
            self._show_job_details(item.job)

    def _show_context_menu(self, position) -> None:
        """Show context menu for queue item.

        Args:
            position: Menu position
        """
        item = self.queue_list.itemAt(position)
        if not isinstance(item, QueueJobItem):
            return

        job = item.job
        menu = QMenu(self)

        # Cancel action
        if job.state in [JobState.QUEUED, JobState.RUNNING] and job.cancellable:
            cancel_action = QAction("Cancel Job", self)
            cancel_action.triggered.connect(lambda: self._cancel_job(job.id))
            menu.addAction(cancel_action)

        # Retry action
        if job.state == JobState.FAILED and job.can_retry():
            retry_action = QAction("Retry Job", self)
            retry_action.triggered.connect(lambda: self._retry_job(job.id))
            menu.addAction(retry_action)

        # Priority actions
        if job.state == JobState.QUEUED:
            menu.addSeparator()

            high_priority_action = QAction("Set High Priority", self)
            high_priority_action.triggered.connect(lambda: self._set_job_priority(job.id, 10))
            menu.addAction(high_priority_action)

            normal_priority_action = QAction("Set Normal Priority", self)
            normal_priority_action.triggered.connect(lambda: self._set_job_priority(job.id, 0))
            menu.addAction(normal_priority_action)

            low_priority_action = QAction("Set Low Priority", self)
            low_priority_action.triggered.connect(lambda: self._set_job_priority(job.id, -10))
            menu.addAction(low_priority_action)

        # Show details action
        menu.addSeparator()
        details_action = QAction("Show Details", self)
        details_action.triggered.connect(lambda: self._show_job_details(job))
        menu.addAction(details_action)

        if menu.actions():
            menu.exec(self.queue_list.mapToGlobal(position))

    def _cancel_job(self, job_id: str) -> None:
        """Cancel a job.

        Args:
            job_id: Job ID to cancel
        """
        if self.queue_manager:
            success = self.queue_manager.cancel_job(job_id)
            if not success:
                QMessageBox.warning(self, "Cancel Failed",
                                  f"Failed to cancel job {job_id}")

    def _retry_job(self, job_id: str) -> None:
        """Retry a failed job.

        Args:
            job_id: Job ID to retry
        """
        # This would need to be implemented in the queue manager
        QMessageBox.information(self, "Retry Job",
                              "Job retry functionality not yet implemented")

    def _set_job_priority(self, job_id: str, priority: int) -> None:
        """Set job priority.

        Args:
            job_id: Job ID
            priority: New priority value
        """
        if self.queue_manager:
            job = self.queue_manager.get_job(job_id)
            if job and job.state == JobState.QUEUED:
                job.priority = priority
                # Re-sort the queue
                self.queue_manager.job_queue.sort(key=lambda j: j.priority, reverse=True)
                self.queue_manager._update_queue_positions()
                self._update_display()

    def _toggle_queue_processing(self) -> None:
        """Toggle queue processing (pause/resume)."""
        if not self.queue_manager:
            return

        status = self.queue_manager.get_queue_status()
        if status['auto_process']:
            self.queue_manager.pause_queue()
            self.queue_paused.emit()
        else:
            self.queue_manager.resume_queue()
            self.queue_resumed.emit()

    def _clear_completed(self) -> None:
        """Clear completed jobs."""
        if not self.queue_manager:
            return

        reply = QMessageBox.question(
            self, "Clear Completed Jobs",
            "Are you sure you want to clear all completed jobs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            count = self.queue_manager.clear_completed_jobs()
            QMessageBox.information(self, "Jobs Cleared",
                                  f"Cleared {count} completed jobs")
            self.queue_cleared.emit()

    def _move_job_up(self) -> None:
        """Move selected job up in queue."""
        if not self.queue_manager:
            return

        current_item = self.queue_list.currentItem()
        if not isinstance(current_item, QueueJobItem):
            return

        job = current_item.job
        if job.state != JobState.QUEUED:
            return

        current_pos = job.queue_position
        if current_pos > 0:
            new_pos = current_pos - 1
            if self.queue_manager.reorder_job(job.id, new_pos):
                self.job_reordered.emit(job.id, new_pos)

    def _move_job_down(self) -> None:
        """Move selected job down in queue."""
        if not self.queue_manager:
            return

        current_item = self.queue_list.currentItem()
        if not isinstance(current_item, QueueJobItem):
            return

        job = current_item.job
        if job.state != JobState.QUEUED:
            return

        current_pos = job.queue_position
        max_pos = len(self.queue_manager.job_queue) - 1
        if current_pos < max_pos:
            new_pos = current_pos + 1
            if self.queue_manager.reorder_job(job.id, new_pos):
                self.job_reordered.emit(job.id, new_pos)
