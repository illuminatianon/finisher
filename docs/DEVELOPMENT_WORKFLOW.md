# Development Workflow Documentation
## Finisher - AI Image Upscaling Tool

### Repository Setup

#### Version Control
- **Platform**: GitHub
- **Repository**: `finisher` (AI Image Upscaling Tool)
- **Branching Strategy**: GitHub Flow (main branch + feature branches)

#### Package Management
- **Tool**: `uv` for Python virtual environment and dependency management
- **Configuration**: `pyproject.toml` for project metadata and dependencies
- **Virtual Environment**: Managed automatically by `uv`

### Release Management

#### Semantic Release
- **Tool**: `semantic-release` (Node.js version)
- **Package Manager**: `npm` for semantic-release tooling
- **Configuration**: `.releaserc.json` or `release.config.js`
- **Automation**: Automated versioning, changelog generation, and GitHub releases

#### Version Strategy
- **Semantic Versioning**: MAJOR.MINOR.PATCH (e.g., 1.2.3)
- **Automated Bumping**: Based on conventional commit types
- **Release Triggers**: Commits to main branch trigger release evaluation

### Commit Convention

#### Conventional Commits (Angular Style)
All commits must follow the Conventional Commits specification with Angular preset:

**Format**: `<type>[optional scope]: <description>`

**Types**:
- `feat`: New feature (triggers MINOR version bump)
- `fix`: Bug fix (triggers PATCH version bump)
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates
- `ci`: CI/CD configuration changes
- `build`: Build system changes

**Breaking Changes**: 
- Add `!` after type: `feat!: redesign API interface`
- Or include `BREAKING CHANGE:` in footer (triggers MAJOR version bump)

**Examples**:
```
feat(api): add Auto1111 configuration manager
fix(gui): resolve drag-and-drop file validation issue
docs: update installation instructions
chore(deps): update Pillow to v10.1.0
feat!: change image processing pipeline architecture
```

### Development Setup

#### Initial Setup
```bash
# Clone repository
git clone https://github.com/username/finisher.git
cd finisher

# Setup Python environment with uv
uv venv
uv pip install -e ".[dev]"

# Setup Node.js for semantic-release
npm install

# Install pre-commit hooks
pre-commit install
```

#### Project Configuration Files

**pyproject.toml**:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "finisher"
dynamic = ["version"]
description = "AI Image Upscaling Tool using Automatic1111 API"
authors = [{name = "Your Name", email = "your.email@example.com"}]
license = {text = "MIT"}
requires-python = ">=3.8"
dependencies = [
    "requests>=2.31.0",
    "Pillow>=10.0.0",
    "tkinterdnd2>=0.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.0.0",
]

[project.scripts]
finisher = "finisher.main:main"

[tool.hatch.version]
path = "src/finisher/__init__.py"
```

**package.json** (for semantic-release):
```json
{
  "name": "finisher",
  "version": "0.0.0-development",
  "private": true,
  "devDependencies": {
    "@semantic-release/changelog": "^6.0.3",
    "@semantic-release/git": "^10.0.1",
    "semantic-release": "^22.0.0"
  },
  "release": {
    "branches": ["main"],
    "plugins": [
      "@semantic-release/commit-analyzer",
      "@semantic-release/release-notes-generator",
      "@semantic-release/changelog",
      "@semantic-release/github",
      "@semantic-release/git"
    ]
  }
}
```

### Code Quality

#### Pre-commit Hooks
**`.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

#### Code Formatting
- **Black**: Automatic code formatting
- **Flake8**: Linting and style checking
- **MyPy**: Static type checking

### Testing Strategy

#### Test Framework
- **pytest**: Primary testing framework
- **pytest-asyncio**: For testing async functionality
- **Coverage**: Code coverage reporting

#### Test Structure
```
tests/
├── test_api/
│   ├── test_client.py
│   ├── test_config.py
│   └── test_models.py
├── test_core/
│   ├── test_processor.py
│   ├── test_metadata.py
│   └── test_utils.py
├── test_gui/
│   ├── test_main_window.py
│   └── test_components.py
└── conftest.py
```

### CI/CD Pipeline

#### GitHub Actions
**`.github/workflows/ci.yml`**:
```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v1
    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}
    - name: Install dependencies
      run: uv sync --all-extras
    - name: Run tests
      run: uv run pytest
    - name: Run linting
      run: |
        uv run black --check .
        uv run flake8 .
        uv run mypy src/

  release:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: actions/setup-node@v4
      with:
        node-version: 18
    - run: npm ci
    - run: npx semantic-release
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Release Process

#### Automated Release Flow
1. **Commit**: Developer commits with conventional commit message
2. **CI**: GitHub Actions runs tests and quality checks
3. **Analysis**: semantic-release analyzes commits for version bump
4. **Release**: If warranted, creates new version, updates CHANGELOG.md, creates GitHub release
5. **Distribution**: Future: automated distribution to package repositories

#### Manual Release Steps (if needed)
```bash
# Ensure clean working directory
git status

# Run semantic-release locally (dry-run)
npx semantic-release --dry-run

# Actual release (normally handled by CI)
npx semantic-release
```

### Documentation

#### Generated Files
- **CHANGELOG.md**: Auto-generated by semantic-release
- **Version**: Auto-updated in `src/finisher/__init__.py`
- **GitHub Releases**: Auto-created with release notes

#### Manual Documentation
- **README.md**: Installation and usage instructions
- **TECHNICAL_STACK.md**: Technical architecture documentation
- **DEVELOPMENT_WORKFLOW.md**: This document
- **PRD.md**: Product requirements and specifications
