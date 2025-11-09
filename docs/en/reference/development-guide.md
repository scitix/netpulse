# Development Guide

This document introduces how to set up NetPulse development environment.

## Environment Requirements

- Python 3.12+
- Redis 6.0+
- Git
- Docker 20.10+ and Docker Compose 2.0+ (optional)

## Quick Start

1. **Clone Project**
```bash
git clone git@github.com:scitix/netpulse.git
cd netpulse
```

2. **Install uv** (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Install Dependencies**
```bash
# Install development dependencies
uv sync --extra dev

# Or install full environment
uv sync --extra api --extra tool --extra dev
```

4. **Start Redis**
```bash
docker compose -f docker-compose.yaml up -d redis
```

5. **Verify Environment**
```bash
# Check Redis connection
uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis connection successful' if r.ping() else 'Redis connection failed')"
```

## Development Workflow

### Basic Process

1. **Create Feature Branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Write Code**
- Follow PEP 8 code style
- Add type annotations and docstrings
- Write appropriate comments

3. **Code Check and Formatting**
```bash
uv run black netpulse/
uv run ruff check netpulse/
```

4. **Commit Code**
```bash
git add .
git commit -m "feat: add new feature"
```

5. **Create Pull Request**

### Code Standards

**Tool Configuration**
- **Formatting**: Black
- **Checking**: Ruff
- **Documentation**: mkdocs-material

**Commit Message Standards**

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>
```

Types include:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `style`: Code format adjustment
- `refactor`: Code refactoring
- `test`: Test related
- `chore`: Build process or auxiliary tool changes

## Project Structure

```
netpulse/
├── netpulse/                 # Core code
│   ├── cli/                 # CLI tools
│   ├── models/              # Data models
│   ├── plugins/             # Plugin system
│   │   ├── drivers/         # Device drivers
│   │   ├── schedulers/      # Schedulers
│   │   ├── templates/       # Templates
│   │   └── webhooks/        # Webhooks
│   ├── routes/              # API routes
│   ├── services/            # Business logic
│   ├── server/              # Server
│   ├── utils/               # Utility functions
│   ├── worker/              # Worker processes
│   └── controller.py        # Controller
├── docs/                    # Documentation
├── docker/                  # Docker configuration
├── docker-compose.yaml      # Production environment configuration
└── docker-compose.dev.yaml  # Development environment configuration
```

## Plugin Development

NetPulse adopts plugin architecture, supporting custom drivers, schedulers, templates, and Webhooks.

### Driver Plugin
Create new driver module in `netpulse/plugins/drivers/` directory.

### Scheduler Plugin
Create new scheduler module in `netpulse/plugins/schedulers/` directory.

### Template Plugin
Create new template module in `netpulse/plugins/templates/` directory.

### Webhook Plugin
Create new Webhook module in `netpulse/plugins/webhooks/` directory.

## Debugging

### Log Configuration
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Using Debugger
```python
import pdb; pdb.set_trace()
```

### Docker Development

**Start Complete Environment**
```bash
docker compose up -d
```

**Development Environment**
```bash
docker compose -f docker-compose.dev.yaml up -d
```

## Common Questions

**Q: How to add new device driver?**
A: Refer to existing driver implementation, create new driver module in `netpulse/plugins/drivers/` directory.

**Q: How to debug API requests?**
A: Use FastAPI's automatic documentation feature, access `http://localhost:9000/docs`.

**Q: How to add new development dependencies?**
A: Use `uv add --extra dev package-name` command.

## Get Help

- **GitHub Issues**: Report issues and request features
- **Documentation**: View related documentation
