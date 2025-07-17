# Product Requirements Document (PRD)
## Finisher - AI Image Upscaling Tool

### Overview
Finisher is a Python tkinter desktop application that provides a simple drag-and-drop interface for AI-powered image upscaling using the Automatic1111 API.

### Core Functionality
- **Image Input**: Accept images via drag-and-drop or file browser
- **Two-Pass Upscaling**: 
  1. Initial upscale pass through Automatic1111 API
  2. Final enhancement pass using the first result
- **Automatic Output**: Results saved automatically by Auto1111 API

### Technical Stack
- **Frontend**: Python tkinter (native desktop GUI)
- **Backend**: Automatic1111 API integration
- **File Handling**: Local temporary storage for intermediate results

### User Flow
1. User drops image file/data into application window OR clicks "Open" to browse OR pastes image data
2. Application validates image format and converts to processable format
3. Application checks Auto1111 status and waits for availability if needed
4. First API call to Automatic1111 for initial upscale (job tracked in footer)
5. Second API call using first result as input (job tracked in footer)
6. Final upscaled image saved automatically by API
7. Success notification to user and footer status reset

### Requirements
#### Functional
- [ ] Enhanced drag-and-drop support (files, image data, clipboard paste)
- [ ] File browser fallback
- [ ] Automatic1111 API integration
- [ ] Two-pass processing pipeline
- [ ] Real-time Auto1111 status monitoring in footer
- [ ] Progress indicators with job tracking
- [ ] External job detection and display
- [ ] Job cancellation (queued and running jobs)
- [ ] Emergency interrupt functionality
- [ ] Error handling and user feedback

#### Technical
- [ ] Support common image formats (PNG, JPG, JPEG, etc.)
- [ ] Support direct image data input (clipboard, drag from browser)
- [ ] Temporary file management
- [ ] API configuration (endpoint, authentication)
- [ ] Async processing to prevent UI freeze
- [ ] Periodic Auto1111 status polling
- [ ] Job ownership tracking and identification

### API Integration Details
#### Automatic1111 Client Setup
- **Base URL**: Configurable Auto1111 server endpoint
- **Timeout**: 5 minutes for processing requests
- **HTTP Client**: Python requests library (equivalent to axios)

#### Two-Pass Processing Strategy
**Pass 1: img2img with SD upscale script**
- **Endpoint**: `/sdapi/v1/img2img`
- **Purpose**: Initial upscaling with AI enhancement
- **Parameters**:
  - `init_images`: Base64 encoded input image
  - `prompt`: Extracted from image metadata or empty
  - `negative_prompt`: Extracted from image metadata or empty
  - `script_name`: "SD upscale"
  - `script_args`: [upscaler_name, scale_factor, denoising_strength, tile_overlap]

**Pass 2: upscale for final enhancement**
- **Endpoint**: `/sdapi/v1/extra-single-image`
- **Purpose**: Final quality enhancement
- **Input**: Result from Pass 1

#### Configuration Endpoints
- **Get Available Upscalers**: `/sdapi/v1/upscalers`
- **Get Available Models**: `/sdapi/v1/sd-models`
- **Get Available Samplers**: `/sdapi/v1/samplers`
- **Get Available Schedulers**: `/sdapi/v1/schedulers`
- **Health Check**: `/sdapi/v1/memory` and `/sdapi/v1/progress`
- **Job Interruption**: `/sdapi/v1/interrupt` (POST request, no body needed)

#### API Parameters
**img2img Pass 1 Parameters**:
- `init_images`: [base64_encoded_image]
- `prompt`: Extracted from metadata or empty string
- `negative_prompt`: Extracted from metadata or empty string
- `script_name`: "SD upscale"
- `script_args`: [upscaler_name, scale_factor, denoising_strength, tile_overlap]
- `steps`: 25
- `sampler_name`: "Euler a"
- `cfg_scale`: 10
- `batch_size`: 1
- `save_images`: false (returns base64 for intermediate processing)
- `scheduler`: "Automatic"

**Default Upscale Configuration**:
- `upscale_scale_factor`: 2.5
- `upscale_denoising_strength`: 0.15
- `upscale_tile_overlap`: 64
- `upscale_upscaler`: Retrieved from `/sdapi/v1/upscalers`

**extra-single-image Pass 2 Parameters**:
- `image`: Base64 encoded result from Pass 1
- `upscaling_resize`: Scale factor for final pass
- `upscaler_1`: Upscaler model name
- `save_images`: true (saves final result to Auto1111 output directory)
- Additional enhancement parameters TBD

#### Application Configuration
- **Configurable Settings**: Upscaler selection, scale factors, denoising strength
- **Fixed Settings**: Steps, sampler, CFG scale for consistency
- **User Preferences**: Save location, processing options

#### Python Implementation Requirements
- HTTP client with timeout handling (requests library)
- Base64 image encoding/decoding
- JSON request/response handling
- Error handling for network and API failures
- Image metadata extraction (Pillow/PIL)
- Temporary file management
- Configuration state management class
- Async/threading for non-blocking API calls

#### Configuration Options
- **Upscaler Model**: Configurable upscaler selection
- **Scale Factor**: Multiplier for image dimensions (2x, 4x, etc.)
- **Denoising Strength**: Quality vs preservation balance (0.15 default)
- **Tile Overlap**: Processing tile overlap in pixels (64 default)

#### Processing Pipeline
1. Read image metadata (prompt, negative_prompt if available)
2. First pass: img2img call with SD upscale script (save_images=false)
3. Extract base64 result from Pass 1 response
4. Second pass: extra-single-image using Pass 1 result (save_images=true)
5. Auto1111 saves final result automatically, discard returned base64
6. Notify user of completion

#### Image Metadata Handling
- **Library**: Python equivalent of Sharp (Pillow/PIL)
- **Format**: PNG text chunks containing generation parameters
- **Extraction**: Parse parameter string to extract prompts
- **Fallback**: Empty strings if metadata unavailable

#### File Management
- **Intermediate Storage**: Local temp directory for Pass 1 results
- **Format**: Base64 to binary conversion for image data
- **Cleanup**: Remove temporary files after processing
- **Output**: Auto1111 handles final image saving

#### Error Handling
- API call failures
- Invalid image formats
- Network connectivity issues
- Processing timeouts

#### Status Monitoring
**Progress Endpoint Response** (`/sdapi/v1/progress`):
```json
{
  "progress": 0.39,
  "eta_relative": 68.74,
  "state": {
    "skipped": false,
    "interrupted": false,
    "stopping_generation": false,
    "job": "Batch 1 out of 2",
    "job_count": 4,
    "job_timestamp": "20250717145219",
    "job_no": 1,
    "sampling_step": 8,
    "sampling_steps": 15
  },
  "current_image": "base64imagedata",
  "textinfo": null
}
```

**Upscalers Endpoint Response** (`/sdapi/v1/upscalers`):
```json
[
  {
    "name": "None",
    "model_name": null,
    "model_path": null,
    "model_url": null,
    "scale": 4
  },
  {
    "name": "Lanczos",
    "model_name": null,
    "model_path": null,
    "model_url": null,
    "scale": 4
  }
]
```

**Models Endpoint Response** (`/sdapi/v1/sd-models`):
```json
[
  {
    "title": "model_name.safetensors",
    "model_name": "model_name",
    "hash": "abc123",
    "sha256": "def456",
    "filename": "/path/to/model_name.safetensors",
    "config": "/path/to/config.yaml"
  }
]
```

**Samplers Endpoint Response** (`/sdapi/v1/samplers`):
```json
[
  {
    "name": "Euler",
    "aliases": ["euler"]
  },
  {
    "name": "Euler a",
    "aliases": ["euler_a"]
  }
]
```

**Schedulers Endpoint Response** (`/sdapi/v1/schedulers`):
```json
[
  {
    "name": "Automatic",
    "label": "Automatic"
  },
  {
    "name": "uniform",
    "label": "Uniform"
  }
]
```

#### Job Detection Strategy
- **Auto1111 Idle**: `progress` = 0 and no active job
- **Job Ownership**: Track job timestamps and compare with our initiated jobs
- **Availability Check**: Monitor `state.stopping_generation` and `progress` values
- **Queue Processing**: Only start new jobs when Auto1111 shows idle state

#### Application Initialization
1. Initialize configuration manager class
2. Fetch available upscalers from `/sdapi/v1/upscalers`
3. Fetch available models from `/sdapi/v1/sd-models` (for validation)
4. Fetch available samplers from `/sdapi/v1/samplers` (for validation)
5. Fetch available schedulers from `/sdapi/v1/schedulers` (for validation)
6. Populate UI dropdowns with upscaler names
7. Set default upscaler selections
8. Begin periodic status monitoring

#### Configuration Manager Class Design
**Purpose**: Centralized API configuration and state management

**Key Methods**:
- `load_upscaler_options()`: Fetch and cache available upscalers
- `load_model_options()`: Fetch and cache available models
- `load_sampler_options()`: Fetch and cache available samplers
- `load_scheduler_options()`: Fetch and cache available schedulers
- `get_default_config()`: Return default processing configuration
- `validate_api_connection()`: Health check before processing
- `load_all_options()`: Batch load all configuration options

**State Management**:
- Loading states for each configuration type
- Error handling and retry logic
- Cached configuration data
- API connection status

**Error Handling Pattern**:
```python
try:
    self.loading = True
    response = requests.get(f"{base_url}/sdapi/v1/upscalers", timeout=30)
    response.raise_for_status()
    self.upscalers = [upscaler['name'] for upscaler in response.json()]
except requests.RequestException as error:
    self.error = str(error)
    raise error
finally:
    self.loading = False
```

#### Configuration Validation and Defaults
**Validation Strategy**:
- Validate selected upscaler exists in available options
- Fallback to first available upscaler if selection invalid
- Validate sampler and scheduler selections against API responses
- Cache configuration options to reduce API calls

**Default Configuration Selection**:
```python
DEFAULT_CONFIG = {
    'upscaler': None,  # Set to first available from API
    'scale_factor': 2.5,
    'denoising_strength': 0.15,
    'tile_overlap': 64,
    'steps': 25,
    'sampler_name': 'Euler a',
    'cfg_scale': 10,
    'scheduler': 'Automatic'
}
```

**Configuration Loading Pattern**:
- Load all options concurrently using threading/asyncio
- Handle individual endpoint failures gracefully
- Provide sensible defaults if API calls fail
- Cache results for application session
- Retry failed requests with exponential backoff

### Enhanced Input Handling
#### Multi-Source Image Input Support
**File Drop Support**:
- Standard file drag-and-drop from file explorer
- Primary support for PNG and JPEG formats
- Graceful handling of BMP and other formats with conversion
- File validation and format conversion as needed

**Direct Image Data Support**:
- Drag image directly from web browser into application
- Paste image from clipboard (Ctrl+V)
- Handle base64 image data from various sources
- Convert image data to processable format automatically

**Input Processing Pipeline**:
1. Detect input type (file path, image data, clipboard)
2. Validate image format and dimensions
3. Convert to standard format (PNG/base64) for API processing
4. Extract metadata if available
5. Prepare for upscaling pipeline

**Implementation Requirements**:
- tkinter drag-and-drop event handling
- Clipboard monitoring and image extraction
- PIL/Pillow for image format conversion
- Base64 encoding/decoding utilities
- MIME type detection for web-sourced images

### Footer Status System
#### Real-Time Auto1111 Monitoring
**Status Display Components**:
- Status text indicator (IDLE, PROCESSING, EXTERNAL, ERROR)
- Progress bar with percentage
- Job identification (Queue position for our jobs)
- ETA display when available

**Status States**:
- **IDLE**: Auto1111 ready, progress bar hidden
- **PROCESSING**: Our upscaling job in progress (first pass only)
- **FINALIZING**: Brief second pass completion (no progress bar needed)
- **EXTERNAL**: Foreign job detected, show external progress
- **CANCELLING**: Job interruption in progress
- **ERROR**: API connection or processing error

**Polling Strategy**:
- Poll `/sdapi/v1/progress` every 2 seconds during first pass (img2img)
- Poll every 10 seconds when idle for external job detection
- No polling needed during second pass (extra-single-image completes quickly)
- Reduce polling frequency when application not in focus
- Stop polling when application minimized

#### Job Ownership Tracking
**Our Job Identification**:
- Track job timestamps when we initiate first pass (img2img)
- Compare `job_timestamp` from progress endpoint
- Match against our initiated job times (±5 second tolerance)
- Internal state tracking for pass progression (no UI indication needed)

**External Job Detection**:
- Progress > 0 but timestamp doesn't match our jobs
- Display "EXTERNAL" status with progress from API
- Show external job progress bar and ETA
- Resume normal processing when external job completes

**Progress Display Logic**:
```python
def update_footer_status(progress_data):
    if progress_data['progress'] == 0:
        status = "IDLE"
        hide_progress_bar()
    elif is_our_job(progress_data['job_timestamp']):
        # Only show progress for first pass (img2img)
        if current_pass == 1:
            status = "PROCESSING"
            show_progress_bar(progress_data['progress'])
        else:
            status = "FINALIZING"
            hide_progress_bar()  # Second pass too quick for progress
    else:
        status = "EXTERNAL"
        show_progress_bar(progress_data['progress'])

    update_status_text(status)
    update_eta(progress_data.get('eta_relative'))
```

**Processing Flow States**:
1. **IDLE** → User drops image → **PROCESSING** (first pass starts)
2. **PROCESSING** → First pass completes → **FINALIZING** (second pass)
3. **FINALIZING** → Second pass completes → **IDLE** (job complete)
4. **PROCESSING/EXTERNAL** → User cancels → **CANCELLING** → **IDLE**

### Job Cancellation System
#### Cancellation Types
**Queued Job Cancellation**:
- Cancel jobs before they start processing
- Simply remove from internal queue, no API call needed
- Immediate return to IDLE state

**Running Job Cancellation**:
- Cancel our currently processing job
- POST request to `/sdapi/v1/interrupt`
- Status changes to "CANCELLING" until interruption completes
- Monitor progress endpoint for completion (progress returns to 0)

**Emergency Interrupt**:
- Always-available interrupt button for any job (ours or external)
- POST request to `/sdapi/v1/interrupt`
- Will terminate any currently running Auto1111 job
- Use with caution as it affects external jobs too

#### UI Components
**Cancel Button States**:
- **IDLE**: Button disabled/hidden
- **PROCESSING**: "Cancel Job" button enabled
- **FINALIZING**: Button disabled (too late to cancel, completes quickly)
- **EXTERNAL**: Button shows "Interrupt External Job" (with warning)
- **CANCELLING**: Button disabled, shows "Cancelling..."

**Emergency Interrupt Button**:
- Always visible red "Emergency Stop" button
- Confirmation dialog: "This will interrupt any running Auto1111 job. Continue?"
- Available regardless of job ownership
- Useful for clearing stuck external jobs

#### Implementation Logic
```python
def cancel_current_job():
    if job_state == "QUEUED":
        # Remove from internal queue
        clear_job_queue()
        set_status("IDLE")
    elif job_state == "PROCESSING":
        # Interrupt running job
        set_status("CANCELLING")
        response = requests.post(f"{base_url}/sdapi/v1/interrupt")
        if response.ok:
            # Monitor progress until job stops
            wait_for_job_completion()
        else:
            handle_interrupt_error()

def emergency_interrupt():
    if confirm_interrupt_dialog():
        set_status("CANCELLING")
        response = requests.post(f"{base_url}/sdapi/v1/interrupt")
        # Will interrupt any job, ours or external
        wait_for_job_completion()
```

#### Cancellation Behavior
**First Pass Cancellation**:
- Interrupt during img2img processing
- No second pass will be attempted
- Return to IDLE state when interruption completes

**Second Pass Cancellation**:
- Generally not needed (completes in seconds)
- If somehow caught during second pass, interrupt still works
- Partial results may be saved by Auto1111

**External Job Interruption**:
- Emergency interrupt affects external jobs
- Show warning dialog before interrupting external jobs
- Useful for clearing stuck or unwanted external processes

