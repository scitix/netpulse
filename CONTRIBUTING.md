# Contributing to NetPulse

Thank you for your interest in contributing to NetPulse! This guide will help you get started.

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/your-username/netpulse.git
cd netpulse
```

### 2. Setup Development Environment

```bash
# Generate environment variables
bash ./scripts/setup_env.sh generate

# Start development services
docker compose up -d
```

### 3. Run Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
black --check .
```

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/amazing-feature`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request

## Code Style

- Follow PEP 8
- Use Black for formatting
- Use Ruff for linting
- Add type hints where appropriate

## Git Commit Guidelines

We use a simple commit message format to maintain clear code history.

### Commit Message Format

```
<type>: <description>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Test related changes
- **chore**: Other changes

### Examples

```
feat: Add user login functionality
fix: Fix API response error
docs: Update README installation guide
style: Adjust code formatting
refactor: Refactor user authentication module
test: Add login functionality tests
chore: Update dependency versions
```

### Pre-commit Checklist

- Code passes all tests
- Code passes linting checks
- New features include corresponding tests

### Setup Git Commit Template (Optional)

```bash
bash ./scripts/setup_git_template.sh
```

After setup, the commit message template will be automatically loaded when running `git commit`.

## Reporting Issues

Please use GitHub Issues to report bugs or request features.

## Questions?

Feel free to open a discussion or contact the maintainers.
