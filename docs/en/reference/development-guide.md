# Development Guide

## Requirements

- Python 3.12+, Redis 6.0+, Git
- Docker 20.10+ (optional, for Redis)

## Setup

```bash
git clone git@github.com:scitix/netpulse.git
cd netpulse

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra api --extra tool --extra dev

# Start Redis
docker compose -f docker-compose.yaml up -d redis

# Verify
uv run python -c "import redis; r = redis.Redis(); print('OK' if r.ping() else 'FAIL')"
```

## Workflow

```bash
# 1. Create branch
git checkout -b feature/your-feature

# 2. Write code (PEP 8, type hints, 100 char line limit)

# 3. Lint and format
uv run ruff check --fix .
uv run ruff format .

# 4. Test
uv run pytest tests/unit/

# 5. Commit
git commit -m "feat: add new feature"
```

**Commit format**: `<type>: <description>` — types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Project Structure

```
netpulse/
├── netpulse/                 # Core code
│   ├── controller.py         # FastAPI entry point
│   ├── routes/               # API endpoints
│   ├── services/             # Business logic
│   ├── worker/               # Worker types
│   ├── models/               # Pydantic schemas
│   ├── plugins/              # Plugin system
│   │   ├── drivers/          # Device drivers
│   │   ├── templates/        # Template engines
│   │   ├── schedulers/       # Scheduling algorithms
│   │   └── webhooks/         # Event handlers
│   └── utils/                # Shared utilities
├── docs/                     # Documentation (MkDocs)
├── docker/                   # Dockerfiles
└── docker-compose.yaml       # Production compose
```

## Plugin Development

Create a new directory under the appropriate `netpulse/plugins/` subdirectory, inherit the base class, and export via `__all__`. See [Plugin System](../architecture/plugin-system.md).

## Running Services Locally

```bash
# Development mode
uv run python -m netpulse.controller     # Terminal 1
uv run python -m netpulse.worker fifo    # Terminal 2
uv run python -m netpulse.worker node    # Terminal 3

# Or use Docker
docker compose -f docker-compose.dev.yaml up -d
```

FastAPI auto-docs available at `http://localhost:9000/docs`.
