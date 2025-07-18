# Technical Stack Documentation
## Finisher - AI Image Upscaling Tool

### Core Technology Stack

#### Frontend/GUI
- **Framework**: PySide6 (Qt6-based desktop GUI)
- **Version**: PySide6 6.5.0+ with Python 3.8+
- **Rationale**: Modern, professional GUI with native drag-and-drop, superior cross-platform support, and better styling capabilities

#### Backend/API Integration
- **HTTP Client**: Python `requests` library
- **Image Processing**: Pillow (PIL) for image manipulation and metadata extraction
- **Base64 Handling**: Built-in Python `base64` module
- **JSON Processing**: Built-in Python `json` module

#### Development Environment
- **Package Manager**: `uv` for virtual environment and dependency management
- **Python Version**: 3.8+ (for PySide6 compatibility and modern features)
- **Virtual Environment**: Managed by `uv`

### Dependencies

#### Core Runtime Dependencies
```toml
# pyproject.toml dependencies
[project]
dependencies = [
    "requests>=2.31.0",           # HTTP client for Auto1111 API
    "Pillow>=10.0.0",            # Image processing and metadata extraction
    "pyside6>=6.5.0",            # Modern GUI framework with native drag-and-drop
]
```

#### Development Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",            # Testing framework
    "pytest-asyncio>=0.21.0",   # Async testing support
    "black>=23.0.0",            # Code formatting
    "flake8>=6.0.0",            # Linting
    "mypy>=1.5.0",              # Type checking
    "pre-commit>=3.0.0",        # Git hooks for code quality
]
```

### Key Libraries and Their Purposes

#### `requests`
- **Purpose**: HTTP client for Auto1111 API communication
- **Usage**: GET/POST requests to Auto1111 endpoints
- **Features**: Timeout handling, JSON response parsing, error handling

#### `Pillow (PIL)`
- **Purpose**: Image processing and metadata extraction
- **Usage**: 
  - Load and validate image formats (PNG, JPEG, BMP)
  - Extract generation parameters from PNG metadata
  - Convert between image formats
  - Base64 encoding/decoding for API communication

#### `PySide6`
- **Purpose**: Modern GUI framework with comprehensive widget set
- **Usage**:
  - Main application window and all UI components
  - Native drag-and-drop functionality for files
  - Professional styling and theming
  - Cross-platform native look and feel
  - Built-in clipboard integration
- **Rationale**: Provides superior GUI capabilities with native drag-and-drop, better performance, and professional appearance

### Architecture Patterns

#### Configuration Management
- Centralized configuration class for API settings
- State management for upscalers, models, samplers, schedulers
- Caching mechanism for API responses
- Error handling and retry logic

#### Async Processing
- Threading for non-blocking API calls
- Progress monitoring without UI freeze
- Concurrent configuration loading
- Background status polling

#### Error Handling
- Comprehensive exception handling for API failures
- Network timeout management
- Image format validation
- User-friendly error messages

### File Structure
```
finisher/
├── src/
│   ├── finisher/
│   │   ├── __init__.py
│   │   ├── main.py              # Application entry point
│   │   ├── gui/
│   │   │   ├── __init__.py
│   │   │   ├── main_window.py   # Main PySide6 window
│   │   │   ├── components/      # UI components
│   │   │   └── utils.py         # GUI utilities
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── client.py        # Auto1111 API client
│   │   │   ├── config.py        # Configuration manager
│   │   │   └── models.py        # Data models
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── processor.py     # Image processing pipeline
│   │   │   ├── metadata.py      # Image metadata handling
│   │   │   └── utils.py         # Core utilities
│   │   └── config/
│   │       ├── __init__.py
│   │       ├── settings.py      # Application settings
│   │       └── defaults.py      # Default configurations
├── tests/
│   ├── __init__.py
│   ├── test_api/
│   ├── test_core/
│   └── test_gui/
├── docs/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── .gitignore
```

### Performance Considerations

#### Memory Management
- Efficient image handling with Pillow
- Temporary file cleanup after processing
- Base64 data management for large images

#### Network Optimization
- Connection pooling with requests.Session
- Appropriate timeout values (5 minutes for processing)
- Retry logic with exponential backoff

#### UI Responsiveness
- Threading for all API calls
- Progress updates without blocking main thread
- Efficient polling strategies based on application state

### Cross-Platform Compatibility
- **Windows**: Primary development target with native Qt support
- **macOS**: PySide6 provides native macOS look and feel
- **Linux**: PySide6 integrates well with all major desktop environments
- **Dependencies**: All dependencies are cross-platform compatible

### Security Considerations
- No sensitive data storage (API endpoints are user-configurable)
- Local-only processing (no external data transmission except to configured Auto1111)
- Input validation for image files and API responses
- Safe temporary file handling
