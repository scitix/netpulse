.PHONY: help deploy build up down logs ps watch scale lint format clean clean-all restart shell stats health

# Default target: show help information
help:
	@echo "NetPulse Common Operations"
	@echo "========================"
	@echo ""
	@echo "Docker Deployment:"
	@echo "  make deploy      - One-click Docker deployment (auto-generate env and certs)"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all Docker services"
	@echo "  make down        - Stop all Docker services"
	@echo "  make restart     - Restart all Docker services"
	@echo "  make logs        - View Docker service logs"
	@echo "  make ps          - Show Docker service status"
	@echo "  make watch       - Start Docker development mode (watch)"
	@echo "  make logs controller  - View logs (service or container name)"
	@echo "  make shell controller  - Open shell (service or container name)"
	@echo "  make stats       - Show Docker container resource usage"
	@echo "  make health      - Check service health status"
	@echo ""
	@echo "Scaling:"
	@echo "  make scale NODE=2 FIFO=1  - Scale workers (default: NODE=2, FIFO=1)"
	@echo ""
	@echo "Development:"
	@echo "  make lint        - Run code linting and auto-fix issues"
	@echo "  make format      - Format code"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Stop Docker services (preserves data volumes)"
	@echo "  make clean-all   - Remove Docker services and volumes (⚠️  WARNING: deletes Redis data)"
	@echo ""

# Docker deployment operations
deploy:
	@echo "🚀 Starting one-click Docker deployment..."
	bash ./scripts/docker_auto_deploy.sh

build:
	@echo "🔨 Building Docker images..."
	docker compose build

up:
	@echo "⬆️  Starting Docker services..."
	docker compose up -d

down:
	@echo "⬇️  Stopping Docker services..."
	docker compose down

restart:
	@echo "🔄 Restarting Docker services..."
	docker compose restart

logs:
	@SERVICE=$$(echo "$(filter-out $@,$(MAKECMDGOALS))" | head -1); \
	if [ -z "$$SERVICE" ]; then \
		echo "📋 Viewing all Docker service logs..."; \
		echo "💡 Tip: Use 'make logs controller' or 'make logs netpulse-controller-1'"; \
		docker compose logs -f; \
	else \
		echo "📋 Viewing logs for $$SERVICE..."; \
		if docker ps --format "{{.Names}}" | grep -q "^$$SERVICE$$"; then \
			docker logs -f $$SERVICE; \
		else \
			docker compose logs -f $$SERVICE; \
		fi; \
	fi
%:
	@:

ps:
	@echo "📊 Showing Docker service status..."
	docker compose ps

watch:
	@echo "👀 Starting Docker development mode (watch)..."
	docker compose watch

shell:
	@SERVICE=$$(echo "$(filter-out $@,$(MAKECMDGOALS))" | head -1); \
	if [ -z "$$SERVICE" ]; then \
		echo "⚠️  Usage: make shell <service-name-or-container-name>"; \
		echo "   Examples:"; \
		echo "     make shell controller          # Service name"; \
		echo "     make shell netpulse-controller-1  # Container name"; \
		echo "   Use 'make ps' to see all containers"; \
		exit 1; \
	fi; \
	if docker ps --format "{{.Names}}" | grep -q "^$$SERVICE$$"; then \
		echo "🐚 Opening shell in container $$SERVICE..."; \
		docker exec -it $$SERVICE /bin/bash 2>/dev/null || docker exec -it $$SERVICE /bin/sh; \
	elif docker compose ps $$SERVICE 2>/dev/null | grep -q "Up"; then \
		echo "🐚 Opening shell in service $$SERVICE..."; \
		docker compose exec $$SERVICE /bin/bash 2>/dev/null || docker compose exec $$SERVICE /bin/sh; \
	else \
		echo "❌ Container or service '$$SERVICE' not found or not running."; \
		echo "   Use 'make ps' to check available containers and services."; \
		exit 1; \
	fi

stats:
	@echo "📊 Showing Docker container resource usage..."
	docker stats --no-stream

health:
	@echo "🏥 Checking service health..."
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Scaling operations
scale:
	@NODE_COUNT=$${NODE:-2}; \
	FIFO_COUNT=$${FIFO:-1}; \
	echo "📈 Scaling workers (NODE=$$NODE_COUNT, FIFO=$$FIFO_COUNT)..."; \
	docker compose up -d --scale node-worker=$$NODE_COUNT --no-deps node-worker; \
	docker compose up -d --scale fifo-worker=$$FIFO_COUNT --no-deps fifo-worker; \
	echo "✅ Workers scaled successfully (node-worker: $$NODE_COUNT, fifo-worker: $$FIFO_COUNT)"

# Development operations
lint:
	@echo "🔍 Running code linting and auto-fixing..."
	ruff check --fix .

format:
	@echo "✨ Formatting code..."
	ruff format .

# Cleanup operations
clean:
	@echo "🧹 Stopping Docker services (data volumes preserved)..."
	docker compose down
	@echo "✅ Services stopped"

clean-all:
	@echo "⚠️  WARNING: This will delete all Docker services and data volumes!"
	@echo "⚠️  This includes Redis data (task queues, job states, etc.)"
	@read -p "Are you sure you want to continue? [y/N] " -n 1 -r; \
	echo; \
	if [ "$$REPLY" = "y" ] || [ "$$REPLY" = "Y" ]; then \
		echo "🧹 Removing Docker services and volumes..."; \
		docker compose down -v; \
		docker system prune -f; \
		echo "✅ All services and data removed"; \
	else \
		echo "❌ Cleanup cancelled"; \
	fi

