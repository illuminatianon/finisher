# Dependencies Documentation
## Finisher - AI Image Upscaling Tool

### Runtime Dependencies

#### Core HTTP and API Communication
**`requests>=2.31.0`**
- **Purpose**: HTTP client for Automatic1111 API communication
- **Usage**: 
  - GET requests to configuration endpoints (`/sdapi/v1/upscalers`, `/sdapi/v1/progress`)
  - POST requests to processing endpoints (`/sdapi/v1/img2img`, `/sdapi/v1/extra-single-image`)
  - POST requests to interrupt endpoint (`/sdapi/v1/interrupt`)
- **Features**: Session management, timeout handling, JSON parsing, error handling
- **License**: Apache 2.0

#### Image Processing and Manipulation
**`Pillow>=10.0.0`**
- **Purpose**: Image processing, format conversion, and metadata extraction
- **Usage**:
  - Load and validate image formats (PNG, JPEG, BMP)
  - Extract generation parameters from PNG text chunks
  - Convert between image formats for API compatibility
  - Base64 encoding/decoding for API communication
  - Image dimension validation and processing
- **Features**: Comprehensive image format support, metadata handling, efficient processing
- **License**: PIL Software License (PIL License)

#### Modern GUI Framework
**`PySide6>=6.5.0`**
- **Purpose**: Modern, cross-platform GUI framework based on Qt6
- **Usage**:
  - Main application window and UI components
  - Native drag-and-drop support for file operations
  - Professional-looking widgets and layouts
  - Built-in clipboard integration
  - Cross-platform consistency and native look-and-feel
- **Rationale**: Provides superior GUI capabilities compared to tkinter, with native drag-and-drop, better styling, and more robust cross-platform support
- **License**: LGPL/Commercial

### Development Dependencies

#### Testing Framework
**`pytest>=7.0.0`**
- **Purpose**: Primary testing framework
- **Usage**: Unit tests, integration tests, test discovery and execution
- **Features**: Fixtures, parametrized tests, comprehensive assertion support
- **License**: MIT

**`pytest-asyncio>=0.21.0`**
- **Purpose**: Async testing support for pytest
- **Usage**: Testing async functions and threading behavior
- **Features**: Async test execution, event loop management
- **License**: Apache 2.0

#### Code Quality and Formatting
**`black>=23.0.0`**
- **Purpose**: Automatic code formatting
- **Usage**: Consistent code style enforcement
- **Configuration**: Line length 88, automatic string quote normalization
- **License**: MIT

**`flake8>=6.0.0`**
- **Purpose**: Linting and style checking
- **Usage**: PEP 8 compliance, error detection, code quality enforcement
- **Features**: Plugin ecosystem, configurable rules
- **License**: MIT

**`mypy>=1.5.0`**
- **Purpose**: Static type checking
- **Usage**: Type annotation validation, error prevention
- **Features**: Gradual typing, IDE integration
- **License**: MIT

**`pre-commit>=3.0.0`**
- **Purpose**: Git hooks for code quality
- **Usage**: Automatic code quality checks before commits
- **Features**: Multi-language support, configurable hooks
- **License**: MIT

### Node.js Dependencies (for Release Management)

#### Semantic Release Core
**`semantic-release>=22.0.0`**
- **Purpose**: Automated versioning and release management
- **Usage**: Version bumping, changelog generation, GitHub releases
- **Features**: Conventional commits analysis, automated publishing
- **License**: MIT

#### Semantic Release Plugins
**`@semantic-release/changelog>=6.0.3`**
- **Purpose**: CHANGELOG.md generation
- **Usage**: Automatic changelog updates based on commits
- **License**: MIT

**`@semantic-release/git>=10.0.1`**
- **Purpose**: Git operations for releases
- **Usage**: Committing version updates and changelog
- **License**: MIT

### Standard Library Dependencies (No Installation Required)

#### Built-in Python Modules

**`json`**
- **Purpose**: JSON parsing and serialization
- **Usage**: API request/response handling, configuration management

**`base64`**
- **Purpose**: Base64 encoding/decoding
- **Usage**: Image data encoding for API communication

**`threading`**
- **Purpose**: Concurrent execution
- **Usage**: Non-blocking API calls, background processing

**`tempfile`**
- **Purpose**: Temporary file management
- **Usage**: Intermediate image storage during processing

**`pathlib`**
- **Purpose**: Modern path handling
- **Usage**: File system operations, path manipulation

**`logging`**
- **Purpose**: Application logging
- **Usage**: Debug information, error tracking, user feedback

### Optional Dependencies (Future Considerations)

#### Enhanced Image Processing
**`opencv-python`** (Future)
- **Purpose**: Advanced image processing capabilities
- **Usage**: Enhanced image validation, format conversion
- **Consideration**: Large dependency, may not be needed for current scope

#### Configuration Management
**`pydantic`** (Future)
- **Purpose**: Data validation and settings management
- **Usage**: API response validation, configuration schemas
- **Consideration**: Useful for larger applications with complex configuration

#### GUI Enhancements
**`qtawesome`** (Future)
- **Purpose**: Icon fonts for PySide6/PyQt applications
- **Usage**: Professional icons and symbols in the UI
- **Consideration**: Would enhance visual appeal but adds dependency

### Dependency Management Strategy

#### Version Pinning
- **Runtime Dependencies**: Minimum version specified with `>=`
- **Development Dependencies**: Minimum version specified with `>=`
- **Rationale**: Allow patch and minor updates while ensuring compatibility

#### Security Updates
- **Monitoring**: Dependabot alerts for security vulnerabilities
- **Updates**: Regular dependency updates through conventional commits
- **Testing**: Comprehensive testing before dependency updates

#### Compatibility Matrix
- **Python Versions**: 3.8, 3.9, 3.10, 3.11
- **Operating Systems**: Windows, macOS, Linux
- **Testing**: CI/CD pipeline tests all combinations

### Installation Commands

#### Development Setup
```bash
# Using uv (recommended)
uv venv
uv pip install -e ".[dev]"

# Traditional pip (alternative)
pip install -e ".[dev]"

# Node.js dependencies for releases
npm install
```

#### Production Installation
```bash
# Using uv
uv pip install finisher

# Traditional pip
pip install finisher
```

### Dependency Justification

#### Why These Specific Dependencies?
1. **requests**: Industry standard for HTTP clients, excellent Auto1111 API support
2. **Pillow**: Most comprehensive Python image library, excellent metadata support
3. **PySide6**: Modern GUI framework with native drag-and-drop, superior to tkinter
4. **pytest**: Most popular Python testing framework with excellent ecosystem
5. **black**: Opinionated formatter that eliminates style debates
6. **semantic-release**: Mature automation tool for version management

#### Alternatives Considered
- **httpx** vs **requests**: requests chosen for stability and widespread adoption
- **opencv-python** vs **Pillow**: Pillow sufficient for current needs, opencv too heavy
- **PyQt6** vs **PySide6**: PySide6 chosen for LGPL licensing and official Qt support
- **tkinter** vs **PySide6**: PySide6 chosen for superior GUI capabilities and native drag-and-drop
- **unittest** vs **pytest**: pytest chosen for better fixtures and ecosystem
