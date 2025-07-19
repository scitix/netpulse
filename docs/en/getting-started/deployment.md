# Deployment Guide

## Bare Metal Deployment

!!! warning
    This method is not recommended for production environments. Only recommended for bare metal CLI tool installation.

1. Install NetPulse:
    ```bash
    pip install netpulse[api,tool]
    ```

2. Configure Redis:
    ```bash
    # Edit Redis configuration
    redis-server redis/redis.conf
    ```

3. Configure NetPulse:
    ```bash
    # Edit according to your settings
    vim config/config.yaml
    ```

4. Start the API server:
    ```bash
    gunicorn -p controller.pid -c gunicorn.conf.py netpulse.controller:app
    ```

5. Start worker nodes:
    ```bash
    python worker.py fifo
    python worker.py node
    ```

## Docker Deployment

For single-machine usage environments, Docker deployment is recommended for NetPulse.

Based on your requirements and control level, you can choose from the following three deployment methods:

### Method A: Fully Automated One-Click Deployment

The fastest way with minimal user interaction.

```bash
# One-click deployment script
bash ./scripts/docker_auto_deploy.sh
```

This script will automatically complete:

- ✅ Generate secure environment variables
- ✅ Create TLS certificates
- ✅ Start all services
- ✅ Verify deployment
- ✅ Display connection information

**Expected Output:**

```
🚀 NetPulse One-Click Deployment
=================================
✅ Prerequisites check passed
📝 Setting up environment...
🔐 Generating TLS certificates...
🚀 Starting services...
⏳ Waiting for services to start...
🔍 Verifying deployment...
✅ Services are running!

🎉 Deployment successful!
========================
API Endpoint: http://localhost:9000
API Key: np_1234567890abcdef...
```

---

### Method B: Semi-Automated Setup

More control while automating tedious parts.

#### Step 1: Environment Setup

```bash
# Automatically generate secure environment variables
bash ./scripts/setup_env.sh generate
```

#### Step 2: Review and Customize (Optional)

```bash
# View generated .env file
cat .env

# Customize as needed
vim .env
```

#### Step 3: Deploy Services

```bash
# Generate TLS certificates
bash ./scripts/generate_redis_certs.sh

# Start services
docker compose up -d
```

#### Step 4: Verify Installation

```bash
# Check service status
docker compose ps

# Test API
source .env
curl -H "Authorization: Bearer $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
```

---

### Method C: Manual Setup

Complete control over every step of the deployment process.

#### Step 1: Create Environment Configuration

**Option 1: Copy from Template**

```bash
# Copy environment template
cp .env.example .env

# Edit with your own secure values
vim .env
```

**Option 2: Create from Scratch**

```bash
# Generate your own secure credentials
REDIS_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
API_KEY="np_$(openssl rand -hex 32)"

# Manually create .env file
cat > .env << EOF
# NetPulse Environment Configuration
NETPULSE_REDIS__PASSWORD=$REDIS_PASS
NETPULSE_SERVER__API_KEY=$API_KEY
TZ=Asia/Shanghai
NETPULSE_LOG_LEVEL=INFO
EOF

echo "✅ Your credentials:"
echo "Redis Password: $REDIS_PASS"
echo "API Key: $API_KEY"
```

#### Step 2: Environment Variable Reference

Create or update your `.env` file using the following required variables:

```bash
# Redis Authentication (Required)
NETPULSE_REDIS__PASSWORD=your_secure_redis_password

# API Authentication (Required)
NETPULSE_SERVER__API_KEY=your_secure_api_key

# Optional Configuration
TZ=Asia/Shanghai                    # Time zone (affects API response timestamps)
NETPULSE_LOG_LEVEL=INFO            # Log level: DEBUG, INFO, WARNING, ERROR
```

**Security Notes:**

- Use strong passwords (minimum 20 characters)
- API keys should start with `np_` for identification
- Never commit `.env` file to version control

**Timezone Configuration:**

- NetPulse API timezone is completely controlled by environment variable TZ
- Single source of truth: modify TZ value in `.env` file, entire system updates globally
- Priority: `.env TZ` > system `TZ` > default `Asia/Shanghai`
- API responses include timezone information (e.g., `2024-01-15T08:30:15+08:00`)

#### Step 3: Generate TLS Certificates

```bash
# Generate Redis TLS certificates
bash ./scripts/generate_redis_certs.sh

# Verify certificate files
ls -la redis/tls/
# Should display: ca.crt, ca.key, redis.crt, redis.key, redis.dh
```

#### Step 4: Start Services

```bash
# Start all services in detached mode
docker compose up -d

# Monitor startup logs
docker compose logs -f

# Check service health status
docker compose ps
```

#### Step 5: Manual Verification

```bash
# Load environment variables
source .env

# Test Redis connection
docker compose exec redis redis-cli --tls \
  --cert /etc/redis/tls/redis.crt \
  --key /etc/redis/tls/redis.key \
  --cacert /etc/redis/tls/ca.crt \
  -p 6379 -a "$NETPULSE_REDIS__PASSWORD" ping

# Test API health endpoint
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/health

# Expected response: {"code": 0, "message": "success", "data": "ok"}
```

---

### Deployment Method Comparison

| Method | Setup Time | Control Level | Recommended Scenarios |
|--------|------------|---------------|----------------------|
| **Fully Automated** | ~2 minutes | Low | Quick testing, demos |
| **Semi-Automated** | ~5 minutes | Medium | Development, pre-release |
| **Manual Setup** | ~10 minutes | High | Production, custom configuration |

---

### Post-Deployment Management

#### Scaling Services

```bash
# Scale worker services
docker compose up --scale node-worker=3 --scale fifo-worker=2 -d

# View scaled services
docker compose ps
```

#### Monitoring and Logs

```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f controller
docker compose logs -f redis

# View real-time resource usage
docker stats
```

#### Service Management

```bash
# Stop all services
docker compose down

# Restart specific service
docker compose restart controller

# Rebuild and restart (after code changes)
docker compose up --build -d

# Complete cleanup (remove volumes)
docker compose down --volumes --remove-orphans
```

## Kubernetes High-Availability Deployment

For production environments, Kubernetes deployment is recommended for NetPulse.

The following deployment solution uses Redis Sentinel cluster and Nginx Ingress Controller, supporting high availability and load balancing.

### Prerequisites

1. Prepare a Kubernetes cluster with at least 3 nodes for high availability.
2. Edit the `k8s/00-secrets.yaml` file and modify the password fields.

!!! tip
    It's recommended to read the Kubernetes manifest files before deployment to understand the configuration of each component and adjust according to actual circumstances.

### Import Secrets

```bash
kubectl apply -f ./k8s/00-secrets.yaml
```

### Deploy Redis Sentinel Cluster

```bash
kubectl apply -f ./k8s/01-redis.yaml
```

After deployment, you can check Redis cluster status with:

```bash
kubectl exec -it redis-sentinel-0 -- redis-cli -p 26379 -a $REDIS_PASSWORD sentinel masters
```

### Deploy Application

```bash
kubectl apply -f ./k8s/02-netpulse.yaml
```

After deployment, you can check application status with:

```bash
kubectl get pods # Check Pod status
kubectl get svc  # Check services
```

### Deploy Nginx Ingress <small>(Optional)</small>

!!! tip
    For the latest deployment method of Nginx Ingress, please refer to the [Ingress-Nginx Controller documentation](https://kubernetes.github.io/ingress-nginx/). The following is only an example.

Deploying Nginx Ingress can achieve load balancing and HTTPS access.

1. **Deploy Nginx Ingress Controller**

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.2/deploy/static/provider/cloud/deploy.yaml
    ```

2. **Adjust Replica Count**

    ```bash
    kubectl scale deployment ingress-nginx-controller \
    --replicas=2 \
    -n ingress-nginx
    ```

3. **Deploy Nginx Ingress Resource**

    ```bash
    kubectl apply -f ./k8s/03-ingress.yaml
    ```

    It's recommended to edit the `k8s/03-ingress.yaml` file and change `netpulse.local` to the actual domain name used. If in a local test environment, you can add the following content to the `/etc/hosts` file:

    ```
    YOUR_NODE_IP_ADDR netpulse.local
    ```

    Replace `YOUR_NODE_IP_ADDR` with the actual node IP address.

4. **Access Application via Nginx Ingress**

!!! tips
    The following content depends on the Nginx Ingress configuration method. Please check the IP type through `kubectl get svc -n ingress-nginx`. If in NodePort mode, follow the tutorial below.

    Check NodePort:

    ```bash
    kubectl get svc -n ingress-nginx
    ```

    Note the NodePort port number of `ingress-nginx-controller`, for example 30080. Then use this port number to access the application:

    ```
    curl http://netpulse.local:30080
    ```

## Troubleshooting

### Common Issues

1. **"NETPULSE_REDIS__PASSWORD is required" error**
   
   Make sure you have created the `.env` file:
   ```bash
   bash ./scripts/setup_env.sh generate
   ```

2. **Redis connection failed**
   
   Check if TLS certificates exist:
   ```bash
   ls -la redis/tls/
   bash ./scripts/generate_redis_certs.sh
   ```

3. **API authentication failed**
   
   Verify your API key in `.env` file and use it in requests:
   ```bash
   source .env
   curl -H "Authorization: Bearer $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
   ```

### Getting Help

- Check logs: `docker compose logs -f`
- Verify environment: `bash ./scripts/setup_env.sh check`
- Review [Configuration Guide](../guides/configuration.md)

---

For production deployments, see [Kubernetes Deployment](#kubernetes-high-availability-deployment) section above. 