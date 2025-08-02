# Finisher Agent Guidelines

This document provides instructions for agentic coding agents working in the `finisher` repository.

## Build, Lint, and Test

- **Build:** `uv build`
- **Lint:** `make lint` or `uv run black --check --diff . && uv run flake8 .`
- **Format:** `make format` or `uv run black .`
- **Type Check:** `make type-check` or `uv run mypy src/`
- **Test:** `make test` or `uv run pytest -v`
- **Run a single test:** `uv run pytest -v path/to/test_file.py::test_function_name`

## Code Style

- **Imports:** Use `black` and `flake8` defaults.
- **Formatting:** `black` is used with a line length of 88 characters.
- **Types:** The project uses `mypy` with strict type checking. All new code should have type hints.
- **Naming Conventions:** Follow standard Python conventions (snake_case for variables/functions, PascalCase for classes).
- **Error Handling:** Use try-except blocks for operations that can fail, like network requests or file I/O.
- **Pre-commit:** This repo uses pre-commit hooks. Run `uv run pre-commit run --all-files` before committing.
