# Finisher

AI Image Upscaling Tool using Automatic1111 API

## Description

Finisher is a Python tkinter desktop application that provides a simple drag-and-drop interface for AI-powered image upscaling using the Automatic1111 API.

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
