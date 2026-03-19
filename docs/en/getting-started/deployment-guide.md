# Deployment Guide

NetPulse is a server-side solution (not a pip library). It bundles Redis, Workers, and a FastAPI controller into a deployable stack.

| Method | Use Case | Complexity |
|--------|----------|------------|
| **Docker one-click** | Dev/test, small production | Low |
| **Kubernetes** | Enterprise, high availability | Medium |
| **Bare metal** | Local development, debugging | Medium |

## Docker Deployment (Recommended)

!!! tip "Requirements"
    Docker 20.10+ and Docker Compose 2.0+

### One-Click Deployment

```bash
git clone https://github.com/scitix/netpulse.git
cd netpulse
bash ./scripts/docker_auto_deploy.sh
```

This script auto-generates TLS certs, `.env` file, API key, and starts all services. Your API key is printed at the end and saved in `.env`.

### Semi-Automatic Setup

For more control:

```bash
# 1. Generate environment config
bash ./scripts/setup_env.sh generate

# 2. (Optional) Customize
vim .env

# 3. Generate TLS certs and start
bash ./scripts/generate_redis_certs.sh
docker compose up -d

# 4. Verify
source .env
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
```

### Manual Setup

Full control over credentials:

```bash
# Generate credentials
REDIS_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
API_KEY="np_$(openssl rand -hex 32)"

cat > .env << EOF
NETPULSE_REDIS__PASSWORD=$REDIS_PASS
NETPULSE_SERVER__API_KEY=$API_KEY
TZ=Asia/Shanghai
NETPULSE_LOG_LEVEL=INFO
EOF

# Generate TLS certs and start
bash ./scripts/generate_redis_certs.sh
docker compose up -d
```

### Docker Management

```bash
# Scale workers
docker compose up --scale node-worker=3 --scale fifo-worker=2 -d

# View logs
docker compose logs -f              # All services
docker compose logs -f controller   # Specific service

# Restart / stop / clean
docker compose restart controller
docker compose down
docker compose down --volumes --remove-orphans  # Full cleanup
```

## Kubernetes Deployment

For production with high availability using Redis Sentinel and multi-replica workers.

### Quick Steps

```bash
# 1. Create namespace
kubectl create namespace netpulse
kubectl config set-context --current --namespace=netpulse

# 2. Deploy secrets
./scripts/k8s_setup_secrets.sh auto

# 3. Deploy Redis Sentinel
kubectl apply -f ./k8s/01-redis.yaml
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis-sentinel --timeout=300s

# 4. Deploy application
kubectl apply -f ./k8s/02-netpulse.yaml
kubectl wait --for=condition=Ready pod -l app=netpulse --timeout=300s

# 5. Expose service (choose one)
kubectl apply -f ./k8s/04-nodeport.yaml   # NodePort → http://NODE_IP:30090
# OR
kubectl apply -f ./k8s/03-ingress.yaml    # Ingress (needs Nginx Ingress Controller)

# 6. Verify
kubectl get all
```

### Components After Deployment

- **Controller** (3 replicas) — API gateway
- **Node Worker** (6 replicas) — Each supports up to 128 device connections
- **FIFO Worker** (6 replicas) — Queue processing
- **Redis Sentinel** — HA Redis cluster

### Scaling

```bash
kubectl scale deployment netpulse-node-worker --replicas=12
kubectl scale deployment netpulse-fifo-worker --replicas=12
kubectl scale deployment netpulse-controller --replicas=5
```

**Connection capacity**: Each Node Worker pod supports ~128 connections. 6 pods = 768, 12 pods = 1536.

### Secret Management

```bash
# Regenerate and deploy secrets
./scripts/k8s_setup_secrets.sh auto

# Restart controller to pick up new API key
kubectl rollout restart deployment/netpulse-controller
```

## Bare Metal / Development

!!! warning
    Not recommended for production. Use for local development and debugging only.

```bash
# 1. Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv && source .venv/bin/activate
uv sync --extra api

# 2. Start Redis (via Docker or system package)
docker run -d --name redis -p 6379:6379 redis:latest

# 3. Generate config
bash ./scripts/setup_env.sh generate

# 4. Start services
uv run python -m netpulse.controller
uv run python -m netpulse.worker fifo   # In another terminal
uv run python -m netpulse.worker node   # In another terminal

# 5. Verify
source .env
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
```

For production bare metal, use gunicorn:
```bash
uv run gunicorn -c gunicorn.conf.py netpulse.controller:app
```

## Troubleshooting

| Problem | Check |
|---------|-------|
| Container won't start | `docker compose logs`, port 9000 in use? |
| API returns 403 | Verify API key: `cat .env \| grep API_KEY` |
| Redis connection failed | `docker compose ps redis`, `docker compose logs redis` |
| K8s pods not ready | `kubectl describe pod <name>`, check image pull and secrets |

See [Troubleshooting](../reference/troubleshooting.md) for more details.
