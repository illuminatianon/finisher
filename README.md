# Finisher - AI Image Upscaling Tool

A Python desktop application that provides AI-powered image upscaling using the Automatic1111 API with a simple drag-and-drop interface.

## Features

- **Two-Pass Upscaling**: Advanced upscaling pipeline using img2img + extra-single-image for optimal results
- **Drag & Drop Interface**: Simply drop images into the application window
- **Multiple Input Methods**: File browser, drag-and-drop, clipboard paste support
- **Real-Time Monitoring**: Live progress tracking and Auto1111 status monitoring
- **Job Management**: Queue management with cancellation and emergency interrupt
- **Smart Configuration**: Automatic detection of available upscalers, models, and samplers
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Metadata Preservation**: Extracts and uses generation parameters from images

## Requirements

- Python 3.9+
- Automatic1111 WebUI running with API enabled
- Required Python packages (see `pyproject.toml`)

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/illuminatianon/finisher.git
cd finisher

# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/illuminatianon/finisher.git
cd finisher

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## Quick Start

1. **Start Automatic1111 WebUI** with API enabled:
   ```bash
   python launch.py --api
   ```

2. **Run Finisher**:
   ```bash
   python -m finisher.main
   ```

3. **Configure Auto1111 endpoint** (if different from default):
   - Default: `http://127.0.0.1:7860`
   - The application will automatically detect available upscalers and models

4. **Process images**:
   - Drag and drop image files into the application window
   - Or click "Browse Files..." to select images
   - Or paste images from clipboard (Ctrl+V)

## Installation

```bash
# Using uv (recommended)
uv pip install finisher

# Using pip
pip install finisher
```

## Usage

```bash
finisher
```

## Development

```bash
# Setup development environment
uv venv
uv pip install -e ".[dev]"

# Install Node.js dependencies for releases
npm install

# Run tests
uv run pytest

# Format code
uv run black .

# Lint code
uv run flake8 .

# Type check
uv run mypy src/
```

## License

MIT
