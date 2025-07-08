This repository is a Python 3.12+ network automation framework.

## Architecture summary
- **FastAPI controller** exposes REST APIs and verifies API keys
- **Redis + RQ** handle task queuing and state storage
- **Manager** dispatches jobs to NodeWorker, FifoWorker and PinnedWorker
- **Plugin system** loads drivers, templates, schedulers and webhooks
- **Persistent SSH** connections boost performance
- Deploy with Docker Compose or Kubernetes

## Directory structure
- `netpulse/` - core code for server, workers and plugins
- `config/` - configuration files
- `docker/` - image build definitions
- `k8s/` - Kubernetes manifests
- `scripts/` - helper scripts
- `docs/` - documentation sources
- `redis/` - local Redis setup
- `build/` - build artifacts

## Coding style
- Format using **Black** and lint with **Ruff** (line length 100)
- Follow PEP 8; use four-space indentation
- Keep comments and docstrings short and in English
- Use Pydantic models for data validation
- Prefer explicit error handling and logging
- New branch names must be English words or phrases

Use this summary to maintain consistency when extending the codebase.
