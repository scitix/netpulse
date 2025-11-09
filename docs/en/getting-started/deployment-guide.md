# Deployment Guide

Netpulse adopts a different architecture model from traditional network automation tools (such as Netmiko, Nornir). Traditional tools are usually provided as Python packages, installed via `pip` and can be used directly in projects; while Netpulse is a complete server-side solution that integrates components like Redis, and after deployment can serve as a unified API server to manage all network devices.

!!! tip "Quick Experience"
    If you want to quickly experience NetPulse, we recommend using **Docker one-click deployment**, just one command to start the complete environment:
    ```bash
    git clone https://github.com/scitix/netpulse.git
    cd netpulse
    bash ./scripts/docker_auto_deploy.sh
    ```
    Deployment can be completed and started in 5 minutes!

| Deployment Method | Use Cases | Complexity | Recommendation |
|------------------|-----------|------------|----------------|
| **Docker One-Click Deployment** | Test environment, small-scale production, quick experience | ⭐ | ⭐⭐⭐⭐⭐ |
| **Kubernetes Deployment** | Enterprise-level, high availability, large-scale production | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Bare Metal/Virtual Environment Deployment** | Local development, feature debugging, CLI tools | ⭐⭐⭐ | ⭐⭐ |

!!! tip "Production Environment Recommendation"
    For production environments, we strongly recommend using Kubernetes deployment for better high availability, scalability, and operations management capabilities.

## Bare Metal/Development Environment Deployment

!!! warning
    This method is not recommended for production environments. Only recommended for local development debugging and CLI tool usage.

!!! tip "uv vs pip Main Differences"
    - **uv method**: Automatically manages virtual environment, use `uv run` command to run, recommended
    - **pip method**: Need to manually activate virtual environment, suitable for users familiar with traditional Python toolchain
    - **Production environment**: Recommended to use `gunicorn` to start, better performance, supports multi-process
    - **Development environment**: Can use `python -m` to start, convenient for debugging

### Method 1: Using uv Package Manager (Recommended)

uv is a modern Python package manager with faster installation speed and more accurate dependency resolution.

!!! tip "China User Recommendation"
    Domestic users are recommended to configure mirror source environment variables before using the official installation script, or directly use pip with Tsinghua mirror source for installation, which can significantly improve download speed.

1. **Install uv**:
    ```bash
    # Method 1: Official installation (recommended for global users)
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Method 2: Install using pip (recommended for China users)
    pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple
    ```

3. **Create Virtual Environment**:
    ```bash
    # Create virtual environment using uv
    uv venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate  # Linux/macOS
    # Or Windows: .venv\Scripts\activate
    ```

4. **Install NetPulse**:
    ```bash
    # Install core dependencies and API server
    uv sync --extra api
    
    # Or install full functionality (including tools)
    uv sync --extra api --extra tool
    ```

5. **Install and Configure Redis**:
    ```bash
    # Method 1: Install using apt (Ubuntu/Debian)
    sudo apt update
    sudo apt install redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    
    # Method 2: Start Redis using Docker
    docker run -d --name redis -p 6379:6379 redis:latest
    
    # Method 3: Install using yum (CentOS/RHEL)
    sudo yum install redis
    sudo systemctl start redis
    sudo systemctl enable redis
    ```

    !!! tip "Redis Installation Method Selection"
        - **apt/yum installation**: Suitable for production environment, better performance, high system integration
        - **Docker installation**: Suitable for development environment, good isolation, easy to manage

6. **Generate Certificates and Environment Configuration**:
    ```bash
    # Use project script to automatically generate certificates and environment variables
    bash ./scripts/setup_env.sh generate
    ```

    !!! tip "Script Function Description"
        This script will automatically complete the following operations:
        - Generate Redis TLS certificates (CA certificate, server certificate, DH parameters)
        - Create secure .env file (including Redis password and API Key)
        - Set correct file permissions
        - Display generated credential information

7. **Configure NetPulse**:
    ```bash
    # Edit according to your needs
    vim config/config.yaml
    ```

8. **Run NetPulse**:
    ```bash
    # Method 1: Run using uv (recommended, automatically manages virtual environment)
    uv run python -m netpulse.controller
    uv run python -m netpulse.worker fifo
    uv run python -m netpulse.worker node
    
    # Method 2: Start using gunicorn (recommended for production environment)
    uv run gunicorn -p controller.pid -c gunicorn.conf.py netpulse.controller:app
    uv run python -m netpulse.worker fifo
    uv run python -m netpulse.worker node
    ```

    !!! note "gunicorn Configuration Description"
        - Use `gunicorn.conf.py` configuration file, includes multi-process, timeout, logging, and other settings
        - Default worker process count: `2 * CPU cores + 1`
        - Supports UvicornWorker, provides better async performance
        - Production environment recommended to use gunicorn to start

9. **Verify Deployment**:
    ```bash
    # Test Redis connection
    redis-cli ping
    
    # Test API health endpoint
    source .env
    curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
    
    # Expected response: {"code": 0, "message": "success", "data": "ok"}
    ```

### Method 2: Using pip Installation

Traditional method, suitable for users familiar with pip.

1. **Create Virtual Environment**:
    ```bash
    # Create virtual environment
    python -m venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate  # Linux/macOS
    # Or Windows: .venv\Scripts\activate
    ```

2. **Install NetPulse**:
    ```bash
    pip install netpulse[api,tool]
    ```

3. **Install and Configure Redis**:
    ```bash
    # Method 1: Install using apt (Ubuntu/Debian)
    sudo apt update
    sudo apt install redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    
    # Method 2: Start Redis using Docker
    docker run -d --name redis -p 6379:6379 redis:latest
    
    # Method 3: Install using yum (CentOS/RHEL)
    sudo yum install redis
    sudo systemctl start redis
    sudo systemctl enable redis
    ```

    !!! tip "Redis Installation Method Selection"
        - **apt/yum installation**: Suitable for production environment, better performance, high system integration
        - **Docker installation**: Suitable for development environment, good isolation, easy to manage

4. **Generate Certificates and Environment Configuration**:
    ```bash
    # Use project script to automatically generate certificates and environment variables
    bash ./scripts/setup_env.sh generate
    ```

    !!! tip "Script Function Description"
        This script will automatically complete the following operations:
        - Generate Redis TLS certificates (CA certificate, server certificate, DH parameters)
        - Create secure .env file (including Redis password and API Key)
        - Set correct file permissions
        - Display generated credential information

5. **Configure NetPulse**:
    ```bash
    # Edit according to your needs
    vim config/config.yaml
    ```

6. **Run NetPulse**:
    ```bash
    # Method 1: Start using gunicorn (recommended for production environment)
    gunicorn -p controller.pid -c gunicorn.conf.py netpulse.controller:app
    
    # Method 2: Start directly using Python (development environment)
    python -m netpulse.controller
    ```

    !!! note "gunicorn Configuration Description"
        - Use `gunicorn.conf.py` configuration file, includes multi-process, timeout, logging, and other settings
        - Default worker process count: `2 * CPU cores + 1`
        - Supports UvicornWorker, provides better async performance
        - Production environment recommended to use gunicorn to start

    ```bash
    # Start different types of Workers
    python -m netpulse.worker fifo
    python -m netpulse.worker node
    ```

7. **Verify Deployment**:
    ```bash
    # Test Redis connection
    redis-cli ping
    
    # Test API health endpoint
    source .env
    curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
    
    # Expected response: {"code": 0, "message": "success", "data": "ok"}
    ```

## Docker Deployment

For single-machine environments, it is recommended to deploy NetPulse using Docker Compose. Depending on your needs and control level, you can choose from the following three deployment methods:

!!! warning "System Requirements"
    Docker 20.10+ and Docker Compose 2.0+ are required.

### Method A: Fully Automatic One-Click Deployment (Recommended)

The fastest method with minimal user interaction.

```bash
# Clone project and execute one-click deployment script
git clone https://github.com/scitix/netpulse.git
cd netpulse
bash ./scripts/docker_auto_deploy.sh
```

This script will automatically complete:

- Generate secure environment variables, automatically create .env file, and generate random API Key
- Create TLS certificates
- Start all Docker services
- Verify deployment
- Display connection information

**Expected Output:**

```
Redis TLS certificates generated in redis/tls.
Note: The permissions of the private key are set to 644 to allow the Docker container to read the key. Please evaluate the security implications of this setting in your environment.
Clearing system environment variables...
Loading environment variables from .env file...
Verifying environment variables...
Environment variables loaded correctly:
  API Key: np_90fbd8685671a2c0b...
  Redis Password: ElkycJeV0d...
Stopping existing services...
Starting services...
[+] Running 6/6
 ✔ Network netpulse-network          Created                                                                                                                                                                                             0.0s
 ✔ Container netpulse-redis-1        Healthy                                                                                                                                                                                             5.7s
 ✔ Container netpulse-fifo-worker-1  Started                                                                                                                                                                                             5.9s
 ✔ Container netpulse-controller-1   Started                                                                                                                                                                                             5.9s
 ✔ Container netpulse-node-worker-2  Started                                                                                                                                                                                             6.1s
 ✔ Container netpulse-node-worker-1  Started                                                                                                                                                                                             5.8s
Waiting for services to start...
Verifying environment variables in container...
Environment variables are correctly set in container
Verifying deployment...
Services are running!

Deployment successful!
====================
API Endpoint: http://localhost:9000
API Key: np_90fbd8685671a2c0b34aa107...

Test your deployment:
curl -H "X-API-KEY: np_90fbd8685671a2c0b34aa107..." http://localhost:9000/health

View logs: docker compose logs -f
Stop services: docker compose down
```

---

### Method B: Semi-Automatic Setup

More control while automating tedious parts.

#### Step 1: Environment Setup

```bash
# Automatically generate secure environment variables
bash ./scripts/setup_env.sh generate
```

#### Step 2: Check and Customize (Optional)

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
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/health
```

---

### Method C: Manual Setup

Full control over every step of the deployment process.

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

Create or update your `.env` file with the following required variables:

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

- NetPulse API timezone is completely controlled by TZ environment variable
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


### Post-Deployment Management

#### Scale Services

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

## Kubernetes Deployment

For production environments, it is recommended to deploy NetPulse using Kubernetes.

The following deployment solution uses Redis Sentinel cluster and Nginx Ingress Controller, supporting high availability and load balancing.

### Preparation

1. Prepare Kubernetes cluster, at least 3 nodes for high availability.
2. Create dedicated namespace:
   ```bash
   kubectl create namespace netpulse
   ```
3. Set current context to use netpulse namespace (recommended):
   ```bash
   kubectl config set-context --current --namespace=netpulse
   ```

!!! tip "Namespace Setting Description"
    After setting the default namespace, all subsequent kubectl commands don't need to specify `-n netpulse` parameter:
    - **Before setting**: `kubectl get pods -n netpulse`
    - **After setting**: `kubectl get pods`
    
    This setting only affects the current kubectl session and won't affect other services or users.

!!! tip
    It is recommended to read Kubernetes manifest files before deployment to understand the configuration of each component and adjust according to actual situation.

### Import Secrets

**Method 1: Auto-generate and Deploy (Recommended)**
```bash
# Use automatic script to generate secure passwords and deploy
./scripts/k8s_setup_secrets.sh auto
```

**Method 2: Step-by-Step Operation**
```bash
# 1. Generate secure password file
./scripts/k8s_setup_secrets.sh generate

# 2. Manually deploy to cluster
kubectl apply -f ./k8s/00-secrets-deploy.yaml
```

**Method 3: Manual Edit Deployment**
```bash
# Edit placeholder passwords in original file
vim k8s/00-secrets.yaml
# Then deploy
kubectl apply -f ./k8s/00-secrets.yaml
```

!!! note "Script Function Description"
    The `auto` parameter function:
    - **Auto-generate** random Redis password and API Key
    - **Auto-create** `k8s/00-secrets-deploy.yaml` file
    - **Auto-deploy** Secret to Kubernetes cluster (if cluster is available)
    - Not deploying the application itself, only deploying authentication information
    
    Other available parameters:
    - `generate` - Only generate password file, don't deploy
    - `apply` - Only deploy to cluster (need password file first)
    - `cleanup` - Clean up temporary files
    
    !!! warning "Notes"
        If `auto` parameter doesn't auto-deploy, please manually execute:
        ```bash
        kubectl apply -f ./k8s/00-secrets-deploy.yaml
        ```
        
        **Important**: After updating Secret, need to restart Controller Pod to load new API Key:
        ```bash
        kubectl rollout restart deployment/netpulse-controller -n netpulse
        ```

### Deploy Redis Sentinel Cluster

```bash
kubectl apply -f ./k8s/01-redis.yaml
```

Wait for Redis cluster to start:
```bash
# View Redis Pod status
kubectl get pods -l app=redis

# View Redis Sentinel Pod status  
kubectl get pods -l app=redis-sentinel

# Wait for all Pods to become Ready status
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis-sentinel --timeout=300s
```

After deployment, you can view Redis cluster status with the following commands:

```bash
# View Redis Sentinel status
kubectl exec -it redis-sentinel-0 -- redis-cli -p 26379 sentinel masters

# Test Redis connection
kubectl exec -it redis-nodes-0 -- redis-cli -a $REDIS_PASSWORD ping
```

### Deploy Application

```bash
kubectl apply -f ./k8s/02-netpulse.yaml
```
!!! tip "Local Image Registry Deployment Tip"
    For easier deployment, you can build images locally and push to local image registry (such as Harbor):
    
    1. **Build Images**:
    ```bash
    docker build -t your-registry/netpulse-controller:latest -f docker/controller.Dockerfile .
    docker build -t your-registry/netpulse-node-worker:latest -f docker/node-worker.Dockerfile .
    docker build -t your-registry/netpulse-fifo-worker:latest -f docker/fifo-worker.Dockerfile .
    ```
    
    2. **Push to Local Registry**:
    ```bash
    docker push your-registry/netpulse-controller:latest
    docker push your-registry/netpulse-node-worker:latest
    docker push your-registry/netpulse-fifo-worker:latest
    ```
    
    3. **Modify Image Address**:
    Edit image address in `k8s/02-netpulse.yaml` to your local registry address

### Configure Service Access

**Method 1: Use NodePort (Simple and Direct, Recommended)**
```bash
# Method 1: Modify existing Service to NodePort
kubectl patch svc netpulse -n netpulse -p '{"spec":{"type":"NodePort"}}'

# Method 2: Deploy dedicated NodePort Service (recommended)
kubectl apply -f ./k8s/04-nodeport.yaml

# View assigned port
kubectl get svc netpulse -n netpulse
kubectl get svc netpulse-nodeport -n netpulse

# NodePort access address: http://NODE_IP:30090
```

**Method 2: Use Ingress (Need to Deploy Nginx Ingress Controller First)**
```bash
# First deploy Nginx Ingress Controller (see detailed steps below)
# Then deploy Ingress resource
kubectl apply -f ./k8s/03-ingress.yaml
```


Wait for application to start:
```bash
# View all Pod status
kubectl get pods

# Wait for all application Pods to become Ready status
kubectl wait --for=condition=Ready pod -l app=netpulse --timeout=300s
```

After deployment, you can view application status with the following commands:

```bash
kubectl get pods # View Pod status
kubectl get svc  # View services
kubectl get deployments # View deployment status
```

### Application Component Description

After deployment, you will see the following components:

- **Controller (3 replicas)**: API service, handles HTTP requests
- **Node Worker (6 replicas)**: Node management Worker, each Pod supports up to 128 device connections
- **FIFO Worker (6 replicas)**: Queue processing Worker, handles query tasks
- **Service**: Internal service discovery, routes requests to Controller

### Scaling Management

**Manual Scaling**:
```bash
# Scale Node Worker to 12 replicas
kubectl scale deployment netpulse-node-worker --replicas=12 -n netpulse

# Scale FIFO Worker to 12 replicas
kubectl scale deployment netpulse-fifo-worker --replicas=12 -n netpulse

# Scale Controller to 5 replicas
kubectl scale deployment netpulse-controller --replicas=5 -n netpulse
```

### Deploy Nginx Ingress <small>(Optional)</small>

!!! note "Important Note"
    Nginx Ingress is only needed when advanced features like domain access, HTTPS, load balancing are required.
    For simple testing and development environments, NodePort method is recommended (see "Configure Service Access" above).

!!! tip
    For the latest deployment method of Nginx Ingress, please refer to [Ingress-Nginx Controller Documentation](https://kubernetes.github.io/ingress-nginx/). The following is only an example.

Deploying Nginx Ingress can achieve features like load balancing and HTTPS access.

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

    It is recommended to edit `k8s/03-ingress.yaml` file and change `netpulse.local` to the actual domain name used. If in local test environment, you can add the following content to `/etc/hosts` file:

    ```
    YOUR_NODE_IP_ADDR netpulse.local
    ```

    Replace `YOUR_NODE_IP_ADDR` with the actual node IP address.

4. **Access Application via Nginx Ingress**

!!! tip
    The following content depends on Nginx Ingress configuration method. Please check IP type through `kubectl get svc -n ingress-nginx`. If in NodePort mode, you can follow the tutorial below.

    Check NodePort:

    ```bash
    kubectl get svc -n ingress-nginx
    ```

    Record the NodePort port number of `ingress-nginx-controller`, for example 30080. Then use this port number to access the application:

    ```
    curl http://netpulse.local:30080
    ```

## Deployment Summary

### Complete Deployment Process

The following are the complete steps for Kubernetes deployment:

```bash
# 1. Create namespace
kubectl create namespace netpulse
kubectl config set-context --current --namespace=netpulse

# 2. Generate and deploy Secrets
./scripts/k8s_setup_secrets.sh auto
# If auto doesn't auto-deploy, manually execute:
# kubectl apply -f ./k8s/00-secrets-deploy.yaml
# Important: After updating Secret, need to restart Controller
# kubectl rollout restart deployment/netpulse-controller -n netpulse

# 3. Deploy Redis Sentinel cluster
kubectl apply -f ./k8s/01-redis.yaml

# 4. Wait for Redis cluster to be ready
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis-sentinel --timeout=300s

# 5. Deploy NetPulse application
kubectl apply -f ./k8s/02-netpulse.yaml

# Optional: If you need to use local image registry (such as Harbor), first build and push images
# docker build -t your-registry/netpulse-controller:latest -f docker/controller.Dockerfile .
# docker build -t your-registry/netpulse-node-worker:latest -f docker/node-worker.Dockerfile .
# docker build -t your-registry/netpulse-fifo-worker:latest -f docker/fifo-worker.Dockerfile .
# docker push your-registry/netpulse-controller:latest
# docker push your-registry/netpulse-node-worker:latest
# docker push your-registry/netpulse-fifo-worker:latest
# Then modify image address in k8s/02-netpulse.yaml

# 6. Wait for application to be ready
kubectl wait --for=condition=Ready pod -l app=netpulse --timeout=300s

# 7. Configure service access (choose one method)
# Method 1: Use NodePort (simple and direct, recommended)
kubectl apply -f ./k8s/04-nodeport.yaml
kubectl get svc netpulse-nodeport -n netpulse
# Access address: http://NODE_IP:30090

# Method 2: Use Ingress (need to deploy Nginx Ingress Controller first)
# First deploy Nginx Ingress Controller, then:
# kubectl apply -f ./k8s/03-ingress.yaml

# 8. Verify deployment
kubectl get pods
kubectl get svc

# 8. View final deployment status
kubectl get all
kubectl get pods -o wide
```

### Verify Deployment

```bash
# Check all component status
kubectl get all

# View Pod distribution
kubectl get pods -o wide

# View resource usage
kubectl top pods

# Test API health check
# Method 1: Port forwarding
kubectl port-forward svc/netpulse 9000:9000 &
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health
# Close port forwarding
kill %1  # Or use pkill -f "kubectl port-forward"

# Method 2: NodePort access (if using NodePort)
# kubectl get svc netpulse-nodeport -o wide  # View NodePort port
# curl -H "X-API-KEY: YOUR_API_KEY" http://NODE_IP:30090/health

# Method 3: Ingress access (if using Ingress)
# curl -H "X-API-KEY: YOUR_API_KEY" http://YOUR_DOMAIN/health

```

### Performance Tuning

**Adjust replica count based on business load**:
```bash
# View current load
kubectl top pods

# Scale Workers to support more device connections
kubectl scale deployment netpulse-node-worker --replicas=12 -n netpulse
kubectl scale deployment netpulse-fifo-worker --replicas=12 -n netpulse

# Scale Controller to handle more API requests
kubectl scale deployment netpulse-controller --replicas=5 -n netpulse
```

**Connection Count Calculation**:
- Each Node Worker Pod supports up to 128 device connections
- 6 Pods = 768 connections
- 12 Pods = 1536 connections
- Can adjust replica count based on actual device count

**Resource Requirements Reference**:
- **Controller**: 4Gi-8Gi memory, 2-8 CPU cores
- **Node Worker**: 2Gi-4Gi memory, 1-4 CPU cores
- **FIFO Worker**: 2Gi-4Gi memory, 1-4 CPU cores
- **Redis**: About 1Gi memory per node

### Common Issue Troubleshooting

#### 1. **Service Startup Failure**

**Docker Deployment:**
```bash
# View detailed logs
docker compose logs -f controller

# Check port occupancy
netstat -tlnp | grep 9000
```

**Kubernetes Deployment:**
```bash
# View Pod status
kubectl get pods

# View detailed logs
kubectl logs -l app=netpulse,component=controller -n netpulse

# View Pod events
kubectl describe pod <pod-name>

# Check namespace
kubectl get namespaces
```

#### 2. **Service Access Issues**

**Check Service Status:**
```bash
# View Service status
kubectl get svc -n netpulse
kubectl describe svc netpulse -n netpulse

# Check Ingress status
kubectl get ingress -n netpulse
kubectl describe ingress netpulse-ingress -n netpulse
```

**NodePort Access:**
```bash
# View NodePort port
kubectl get svc netpulse-nodeport -n netpulse -o wide

# Access using NodePort (replace NODE_IP)
curl http://NODE_IP:30090/health

# Get node IP
kubectl get nodes -o wide
```

**Port Forwarding Test:**
```bash
# Local port forwarding test
kubectl port-forward svc/netpulse 9000:9000 -n netpulse &
curl http://localhost:9000/health
# Close port forwarding
kill %1  # Or use pkill -f "kubectl port-forward"
```

#### 3. **Redis Connection Failure**

**Docker Deployment:**
```bash
# Test Redis connection
docker compose exec redis redis-cli ping
```

**Kubernetes Deployment:**
```bash
# Test Redis connection
kubectl exec -it redis-nodes-0 -- redis-cli -a $REDIS_PASSWORD ping

# Check Redis Sentinel status
kubectl exec -it redis-sentinel-0 -- redis-cli -p 26379 sentinel masters

# View Redis Pod status
kubectl get pods -l app=redis
```

#### 3. **API Authentication Failure**
```bash
# Check API Key format
echo $NETPULSE_SERVER__API_KEY

# Test API authentication
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health

# Kubernetes environment test
kubectl port-forward svc/netpulse 9000:9000 &
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health
# Close port forwarding
kill %1  # Or use pkill -f "kubectl port-forward"
```

#### 4. **Kubernetes-Specific Issues**

**Namespace Issues:**
```bash
# Check current namespace
kubectl config view --minify | grep namespace

# Create namespace
kubectl create namespace netpulse

# Switch namespace
kubectl config set-context --current --namespace=netpulse
```

**Secrets Issues:**
```bash
# Check Secrets
kubectl get secrets

# View Secret content
kubectl get secret netpulse-secrets -o yaml

# Regenerate Secrets
./scripts/k8s_setup_secrets.sh auto
```

**Scaling Issues:**
```bash
# Check resource limits
kubectl describe nodes

# View Pod resource usage
kubectl top pods

# Check HPA status
kubectl get hpa
kubectl describe hpa netpulse-controller-hpa

# Manual scaling
kubectl scale deployment netpulse-node-worker --replicas=12 -n netpulse
```

**API Key Update Issues:**
```bash
# Regenerate and deploy API Key
./scripts/k8s_setup_secrets.sh auto

# Restart Controller to load new API Key
kubectl rollout restart deployment/netpulse-controller -n netpulse

# Verify new API Key is effective
curl -H "X-API-KEY: YOUR_NEW_API_KEY" http://YOUR_HOST:PORT/health
```

**Image Pull Issues:**
```bash
# Check image pull status
kubectl describe pod <pod-name>

# Use local image (need to transfer to each node in advance)
docker save -o netpulse-controller.tar localhost/netpulse-controller:latest
scp netpulse-controller.tar node1:/tmp/
ssh node1 "docker load -i /tmp/netpulse-controller.tar"
```

**Pod Distribution View:**
```bash
# View which nodes Pods are running on
kubectl get pods -o wide

# View Pod distribution statistics
kubectl get pods -o custom-columns="NAME:.metadata.name,NODE:.spec.nodeName" | sort -k2
```

### Post-Deployment Management

**Daily Operations Commands**:
```bash
# View cluster status
kubectl get all

# View resource usage
kubectl top pods
kubectl top nodes

# View logs
kubectl logs -l app=netpulse,component=controller -n netpulse --tail=100
kubectl logs -l app=netpulse,component=node-worker -n netpulse --tail=100

# Restart services
kubectl rollout restart deployment/netpulse-controller
kubectl rollout restart deployment/netpulse-node-worker
kubectl rollout restart deployment/netpulse-fifo-worker

# Note: Must restart Controller after updating API Key
kubectl rollout restart deployment/netpulse-controller
```


**Backup and Recovery**:
```bash
# Backup configuration
kubectl get configmap netpulse-config -o yaml > netpulse-config-backup.yaml
kubectl get secret netpulse-secrets -o yaml > netpulse-secrets-backup.yaml

# Restore configuration
kubectl apply -f netpulse-config-backup.yaml
kubectl apply -f netpulse-secrets-backup.yaml
```

### Next Steps

After deployment, we recommend:

1. **[Quick Start](quick-start.md)** - Learn basic API usage methods
2. **[Postman Usage Guide](postman-guide.md)** - Use Postman to quickly test APIs


