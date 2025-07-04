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
bash ./scripts/check_env.sh generate

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

## Reporting Issues

Please use GitHub Issues to report bugs or request features.

## Questions?

Feel free to open a discussion or contact the maintainers.
