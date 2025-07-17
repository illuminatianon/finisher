# Contributing to Finisher

Thank you for your interest in contributing to Finisher!

## Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/finisher.git`
3. Set up development environment: `make setup-dev`

## Development Workflow

### Commit Messages
We use [Conventional Commits](https://www.conventionalcommits.org/) with Angular style:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat(api): add Auto1111 configuration manager
fix(gui): resolve drag-and-drop validation issue
docs: update installation instructions
```

### Code Quality
Before committing, ensure your code passes all checks:

```bash
make check-all  # Runs linting, type checking, and tests
```

### Pre-commit Hooks
Pre-commit hooks are automatically installed with `make setup-dev`. They will:
- Format code with Black
- Lint with Flake8
- Type check with MyPy
- Validate commit messages

### Testing
- Write tests for new features
- Ensure all tests pass: `make test`
- Check test coverage: `make test-cov`

### Pull Requests
1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make your changes
3. Ensure all checks pass: `make check-all`
4. Commit with conventional commit messages
5. Push and create a pull request

## Release Process
Releases are automated using semantic-release based on conventional commits:
- `feat:` triggers minor version bump
- `fix:` triggers patch version bump
- `feat!:` or `BREAKING CHANGE:` triggers major version bump

## Questions?
Feel free to open an issue for any questions about contributing!
