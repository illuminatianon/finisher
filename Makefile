.PHONY: help install install-dev test lint format type-check clean pre-commit setup-dev

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup-dev: ## Set up development environment
	uv venv
	uv pip install -e ".[dev]"
	npm install
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

install: ## Install package
	uv pip install -e .

install-dev: ## Install package with development dependencies
	uv pip install -e ".[dev]"

test: ## Run tests
	uv run pytest -v

test-cov: ## Run tests with coverage
	uv run pytest --cov=src/finisher --cov-report=html --cov-report=term

lint: ## Run linting
	uv run black --check --diff .
	uv run flake8 .

format: ## Format code
	uv run black .

type-check: ## Run type checking
	uv run mypy src/

pre-commit: ## Run pre-commit hooks
	uv run pre-commit run --all-files

clean: ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

release-dry: ## Dry run semantic-release
	npx semantic-release --dry-run

build: ## Build package
	uv build

check-all: lint type-check test ## Run all checks
