# Queue System Design Document

## Overview

This document outlines the design for implementing a proper queue system in the Finisher application to handle multiple image processing jobs efficiently. The current implementation has basic queue functionality through `JobManager`, but lacks the robustness needed for handling multiple simultaneous file drops and providing proper user feedback.

## Current State Analysis

### Existing Components

1. **JobManager** (`src/finisher/core/job_manager.py`)
   - Basic FIFO queue implementation
   - Single job processing (one at a time)
   - Job states: QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
   - Limited queue visibility and management

2. **Input Handling** (`src/finisher/core/input_handler.py`)
   - Handles single file drops, clipboard, and image data
   - No batch processing support
   - Each input triggers immediate job creation

3. **GUI** (`src/finisher/gui/main_window.py`)
   - Basic status display for current job
   - No queue visualization
   - Limited user control over queue

### Current Limitations

1. **Single File Processing**: Only handles one file at a time
2. **No Batch Support**: Cannot drop multiple files simultaneously
3. **Limited Queue Visibility**: Users can't see pending jobs
4. **No Queue Management**: Cannot reorder, cancel, or modify queued jobs
5. **No Persistence**: Queue is lost on application restart
6. **Poor User Feedback**: No indication of queue status or progress

## Design Goals

### Primary Objectives

1. **Batch Processing**: Support dropping 5+ images simultaneously
2. **Queue Visualization**: Clear display of all pending and active jobs
3. **User Control**: Ability to manage queue (reorder, cancel, pause)
4. **Robust Processing**: Handle Auto1111 availability gracefully
5. **Progress Tracking**: Real-time updates for all jobs
6. **Error Resilience**: Continue processing other jobs if one fails

### Secondary Objectives

1. **Queue Persistence**: Save/restore queue across sessions
2. **Configurable Limits**: Set max concurrent jobs and queue size
3. **Priority System**: Allow high-priority jobs
4. **Batch Operations**: Select multiple jobs for bulk actions

## Architecture Design

### Core Components

#### 1. Enhanced Queue Manager

**File**: `src/finisher/core/enhanced_queue_manager.py`

```python
class EnhancedQueueManager:
    """Advanced queue management with batch support and persistence."""
    
    def __init__(self):
        self.job_queue: List[QueuedJob] = []
        self.active_jobs: Dict[str, QueuedJob] = {}
        self.completed_jobs: List[QueuedJob] = []
        self.max_concurrent_jobs: int = 1  # Configurable
        self.auto_process: bool = True
        self.queue_persistence: bool = True
```

**Key Features**:
- Support for multiple concurrent jobs (when Auto1111 supports it)
- Job prioritization and reordering
- Batch job creation from multiple files
- Queue persistence to JSON file
- Event-driven updates for GUI

#### 2. Queue Data Models

**File**: `src/finisher/core/queue_models.py`

```python
@dataclass
class QueuedJob:
    """Enhanced job model with queue-specific metadata."""
    id: str
    type: JobType
    state: JobState
    priority: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Job data
    source_path: Optional[str] = None
    source_data: Optional[bytes] = None
    config: Optional[ProcessingConfig] = None
    
    # Progress tracking
    progress: float = 0.0
    eta: Optional[timedelta] = None
    
    # Queue metadata
    queue_position: int = 0
    batch_id: Optional[str] = None
    retry_count: int = 0
```

#### 3. Batch Input Handler

**File**: `src/finisher/core/batch_input_handler.py`

```python
class BatchInputHandler:
    """Handles multiple file inputs and batch operations."""
    
    def handle_multiple_files(self, file_paths: List[str]) -> str:
        """Create batch job from multiple files."""
        
    def handle_directory_drop(self, directory_path: str) -> str:
        """Process all images in dropped directory."""
        
    def validate_batch_input(self, inputs: List[str]) -> Tuple[List[str], List[str]]:
        """Validate inputs, return (valid, invalid) lists."""
```

### GUI Enhancements

#### 1. Queue Panel Component

**File**: `src/finisher/gui/queue_panel.py`

```python
class QueuePanel(QWidget):
    """Displays and manages the job queue."""
    
    def __init__(self):
        # Queue list widget
        self.queue_list = QListWidget()
        
        # Queue controls
        self.pause_button = QPushButton("Pause Queue")
        self.clear_button = QPushButton("Clear Completed")
        self.reorder_buttons = [QPushButton("↑"), QPushButton("↓")]
        
        # Queue statistics
        self.stats_label = QLabel()
```

**Features**:
- Drag-and-drop reordering of queued jobs
- Context menu for job actions (cancel, retry, priority)
- Real-time progress updates
- Batch selection and operations

#### 2. Enhanced Status Display

**File**: `src/finisher/gui/enhanced_status.py`

```python
class EnhancedStatusBar(QStatusBar):
    """Advanced status bar with queue information."""
    
    def update_queue_status(self, active: int, queued: int, completed: int):
        """Update queue statistics display."""
        
    def show_batch_progress(self, batch_id: str, completed: int, total: int):
        """Show progress for batch operations."""
```

### Integration Points

#### 1. Modified Application Controller

**Changes to**: `src/finisher/app_controller.py`

- Replace `JobManager` with `EnhancedQueueManager`
- Add batch input handling
- Implement queue event handling
- Add queue persistence management

#### 2. Enhanced Main Window

**Changes to**: `src/finisher/gui/main_window.py`

- Add `QueuePanel` to layout
- Implement queue-related menu actions
- Add keyboard shortcuts for queue operations
- Integrate enhanced status display

#### 3. Updated Input Handling

**Changes to**: `src/finisher/core/input_handler.py`

- Support multiple file selection in file browser
- Handle multiple file drops simultaneously
- Integrate with batch input handler
- Maintain backward compatibility

## Implementation Strategy

### Phase 1: Core Queue Enhancement

1. **Create Enhanced Queue Manager**
   - Extend existing `JobManager` functionality
   - Add batch job creation
   - Implement queue persistence
   - Add event system for GUI updates

2. **Update Data Models**
   - Enhance `Job` class with queue metadata
   - Add batch tracking capabilities
   - Implement job prioritization

3. **Modify Application Controller**
   - Integrate enhanced queue manager
   - Update job creation workflow
   - Add queue event handling

### Phase 2: GUI Integration

1. **Create Queue Panel**
   - Design queue visualization component
   - Implement job list display
   - Add queue control buttons
   - Integrate with main window layout

2. **Enhance Status Display**
   - Update status bar for queue information
   - Add progress tracking for multiple jobs
   - Implement batch operation feedback

3. **Update Input Handling**
   - Support multiple file selection
   - Handle batch file drops
   - Integrate with enhanced queue manager

### Phase 3: Advanced Features

1. **Queue Persistence**
   - Save queue state to JSON file
   - Restore queue on application startup
   - Handle interrupted jobs gracefully

2. **Configuration Options**
   - Add queue settings to configuration
   - Implement concurrent job limits
   - Add auto-processing controls

3. **Error Handling & Recovery**
   - Implement job retry mechanisms
   - Handle Auto1111 disconnections
   - Provide detailed error reporting

## Technical Considerations

### Performance

1. **Memory Management**
   - Limit queue size to prevent memory issues
   - Implement job cleanup for completed items
   - Use lazy loading for large batches

2. **Threading**
   - Maintain thread safety for queue operations
   - Use Qt signals for GUI updates
   - Implement proper job cancellation

### User Experience

1. **Feedback**
   - Provide immediate feedback for batch drops
   - Show clear progress indicators
   - Display estimated completion times

2. **Control**
   - Allow queue pausing/resuming
   - Enable job reordering and cancellation
   - Provide batch operation shortcuts

### Compatibility

1. **Backward Compatibility**
   - Maintain existing single-file workflow
   - Preserve current configuration format
   - Support existing job types

2. **Auto1111 Integration**
   - Respect Auto1111 processing limits
   - Handle API availability gracefully
   - Implement proper error recovery

## Configuration Schema

### Queue Settings

```yaml
queue:
  max_size: 50                    # Maximum jobs in queue
  max_concurrent: 1               # Concurrent processing limit
  auto_process: true              # Start processing automatically
  persistence_enabled: true      # Save queue across sessions
  persistence_file: "queue.json" # Queue save file
  retry_failed_jobs: true        # Auto-retry failed jobs
  max_retries: 3                  # Maximum retry attempts
  cleanup_completed: true        # Auto-remove completed jobs
  cleanup_after_hours: 24        # Hours before cleanup
```

### Batch Processing

```yaml
batch:
  max_files_per_batch: 20        # Maximum files in single batch
  validate_before_queue: true    # Validate all files before queuing
  show_batch_summary: true       # Show summary before processing
  auto_generate_batch_names: true # Generate descriptive batch names
```

## Success Metrics

### Functional Requirements

- [ ] Support dropping 5+ images simultaneously
- [ ] Display all queued jobs with status
- [ ] Allow queue management (reorder, cancel, pause)
- [ ] Maintain queue across application restarts
- [ ] Process jobs sequentially as Auto1111 permits
- [ ] Provide real-time progress updates
- [ ] Handle errors gracefully without stopping queue

### Performance Requirements

- [ ] Queue operations complete within 100ms
- [ ] Support queues up to 50 jobs
- [ ] Memory usage scales linearly with queue size
- [ ] GUI remains responsive during batch operations

### User Experience Requirements

- [ ] Intuitive drag-and-drop queue management
- [ ] Clear visual feedback for all operations
- [ ] Keyboard shortcuts for common actions
- [ ] Contextual help and error messages
- [ ] Consistent behavior across all input methods

## Risk Mitigation

### Technical Risks

1. **Auto1111 Limitations**
   - Risk: API may not support concurrent requests
   - Mitigation: Implement sequential processing with queue

2. **Memory Usage**
   - Risk: Large queues may consume excessive memory
   - Mitigation: Implement queue size limits and cleanup

3. **Data Loss**
   - Risk: Queue lost on application crash
   - Mitigation: Implement frequent queue persistence

### User Experience Risks

1. **Complexity**
   - Risk: Advanced features may confuse users
   - Mitigation: Progressive disclosure and good defaults

2. **Performance**
   - Risk: Large batches may appear unresponsive
   - Mitigation: Chunked processing and progress feedback

## Future Enhancements

### Advanced Queue Features

1. **Smart Scheduling**
   - Optimize job order based on processing time
   - Group similar jobs for efficiency
   - Implement job dependencies

2. **Distributed Processing**
   - Support multiple Auto1111 instances
   - Load balancing across endpoints
   - Failover capabilities

3. **Advanced Analytics**
   - Processing time statistics
   - Success/failure rates
   - Performance optimization suggestions

### Integration Possibilities

1. **Cloud Storage**
   - Direct upload to cloud services
   - Automatic backup of processed images
   - Shared queue across devices

2. **Workflow Automation**
   - Scheduled processing
   - Folder watching for new images
   - Integration with other tools

This design provides a solid foundation for implementing a robust queue system that will significantly enhance the user experience while maintaining the application's reliability and performance.
