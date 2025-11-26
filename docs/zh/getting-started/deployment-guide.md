# 部署指南

Netpulse 采用与传统网络自动化工具（如 Netmiko、Nornir）不同的架构模式。传统工具通常以 Python 包的形式提供，通过 `pip` 安装即可在项目中直接使用；而 Netpulse 是一个完整的服务端解决方案，集成了 Redis 等组件，因此推荐使用 Docker/Kubernetes 进行部署。

| 部署方式 | 适用场景 | 复杂度 | 推荐指数 |
|----------|----------|--------|----------|
| **Docker 一键部署** | 测试环境、小规模生产、快速体验 | ⭐ | ⭐⭐⭐⭐⭐ |
| **Kubernetes 部署** | 企业级、高可用、大规模生产 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **裸机/虚拟环境部署** | 本地开发、功能调试、CLI工具 | ⭐⭐⭐ | ⭐⭐ |

!!! tip "生产环境建议"
    对于生产环境，强烈建议使用 Kubernetes 部署以获得更好的高可用性、可扩展性和运维管理能力。

## 裸机/开发环境部署

!!! warning
    此方法不推荐用于生产环境。仅建议在本地开发调试及CLI工具使用。

### 方式 1：使用 uv 包管理器（推荐）

uv 是现代化的 Python 包管理器，安装速度更快，依赖解析更准确。

!!! tip "China用户推荐"
    国内用户建议配置镜像源环境变量后使用官方安装脚本，或直接使用 pip 配合清华镜像源安装，可大幅提升下载速度。


1. **安装 uv**：
    ```bash
    # 方式 1：官方安装（推荐全球用户）
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # 方式 2：使用 pip 安装（china用户推荐）
    pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple
    ```

3. **创建虚拟环境**：
    ```bash
    # 使用 uv 创建虚拟环境
    uv venv .venv
    
    # 激活虚拟环境
    source .venv/bin/activate  # Linux/macOS
    # 或者 Windows: .venv\Scripts\activate
    ```

4. **安装 NetPulse**：
    ```bash
    # 安装核心依赖和 API 服务器
    uv sync --extra api
    
    # 或者安装完整功能（包含工具）
    uv sync --extra api --extra tool
    ```

5. **安装和配置 Redis**：
    ```bash
    # 方式 1：使用 apt 安装（Ubuntu/Debian）
    sudo apt update
    sudo apt install redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    
    # 方式 2：使用 Docker 启动 Redis
    docker run -d --name redis -p 6379:6379 redis:latest
    
    # 方式 3：使用 yum 安装（CentOS/RHEL）
    sudo yum install redis
    sudo systemctl start redis
    sudo systemctl enable redis
    ```

    !!! tip "Redis 安装方式选择"
        - **apt/yum 安装**：适合生产环境，性能更好，系统集成度高
        - **Docker 安装**：适合开发环境，隔离性好，易于管理

6. **生成证书和环境配置**：
    ```bash
    # 使用项目脚本自动生成证书和环境变量
    bash ./scripts/setup_env.sh generate
    ```

    !!! tip "脚本功能说明"
        该脚本会自动完成以下操作：
        - 生成 Redis TLS 证书（CA 证书、服务器证书、DH 参数）
        - 创建安全的 .env 文件（包含 Redis 密码和 API Key）
        - 设置正确的文件权限
        - 显示生成的凭据信息

7. **配置 NetPulse**：
    ```bash
    # 根据您的需求进行编辑
    vim config/config.yaml
    ```

8. **运行 NetPulse**：
    ```bash
    # 方式 1：使用 uv 运行（推荐，自动管理虚拟环境）
    uv run python -m netpulse.controller
    uv run python -m netpulse.worker fifo
    uv run python -m netpulse.worker node
    
    # 方式 2：使用 gunicorn 启动（生产环境推荐）
    uv run gunicorn -p controller.pid -c gunicorn.conf.py netpulse.controller:app
    uv run python -m netpulse.worker fifo
    uv run python -m netpulse.worker node
    ```

    !!! note "gunicorn 配置说明"
        - 使用 `gunicorn.conf.py` 配置文件，包含多进程、超时、日志等设置
        - 默认工作进程数：`2 * CPU核心数 + 1`
        - 支持 UvicornWorker，提供更好的异步性能
        - 生产环境推荐使用 gunicorn 启动

9. **验证部署**：
    ```bash
    # 测试 Redis 连接
    redis-cli ping
    
    # 测试 API 健康端点
    source .env
    curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
    
    # 预期响应：{"code": 0, "message": "success", "data": "ok"}
    ```

### 方式 2：使用 pip 安装

传统方式，适合熟悉 pip 的用户。

1. **创建虚拟环境**：
    ```bash
    # 创建虚拟环境
    python -m venv .venv
    
    # 激活虚拟环境
    source .venv/bin/activate  # Linux/macOS
    # 或者 Windows: .venv\Scripts\activate
    ```

2. **安装 NetPulse**：
    ```bash
    pip install netpulse[api,tool]
    ```

3. **安装和配置 Redis**：
    ```bash
    # 方式 1：使用 apt 安装（Ubuntu/Debian）
    sudo apt update
    sudo apt install redis-server
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
    
    # 方式 2：使用 Docker 启动 Redis
    docker run -d --name redis -p 6379:6379 redis:latest
    
    # 方式 3：使用 yum 安装（CentOS/RHEL）
    sudo yum install redis
    sudo systemctl start redis
    sudo systemctl enable redis
    ```

    !!! tip "Redis 安装方式选择"
        - **apt/yum 安装**：适合生产环境，性能更好，系统集成度高
        - **Docker 安装**：适合开发环境，隔离性好，易于管理

4. **生成证书和环境配置**：
    ```bash
    # 使用项目脚本自动生成证书和环境变量
    bash ./scripts/setup_env.sh generate
    ```

    !!! tip "脚本功能说明"
        该脚本会自动完成以下操作：
        - 生成 Redis TLS 证书（CA 证书、服务器证书、DH 参数）
        - 创建安全的 .env 文件（包含 Redis 密码和 API Key）
        - 设置正确的文件权限
        - 显示生成的凭据信息

5. **配置 NetPulse**：
    ```bash
    # 根据您的需求进行编辑
    vim config/config.yaml
    ```

6. **运行 NetPulse**：
    ```bash
    # 方式 1：使用 gunicorn 启动（生产环境推荐）
    gunicorn -p controller.pid -c gunicorn.conf.py netpulse.controller:app
    
    # 方式 2：直接使用 Python 启动（开发环境）
    python -m netpulse.controller
    ```

    !!! note "gunicorn 配置说明"
        - 使用 `gunicorn.conf.py` 配置文件，包含多进程、超时、日志等设置
        - 默认工作进程数：`2 * CPU核心数 + 1`
        - 支持 UvicornWorker，提供更好的异步性能
        - 生产环境推荐使用 gunicorn 启动

    ```bash
    # 启动不同类型的 Worker
    python -m netpulse.worker fifo
    python -m netpulse.worker node
    ```

7. **验证部署**：
    ```bash
    # 测试 Redis 连接
    redis-cli ping
    
    # 测试 API 健康端点
    source .env
    curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
    
    # 预期响应：{"code": 0, "message": "success", "data": "ok"}
    ```

## Docker 部署

单机环境下，建议使用 Docker Compose部署 NetPulse。根据您的需求和控制级别，可以选择以下三种部署方式：

!!! warning "系统要求"
    需要满足 Docker 20.10+ 和 Docker Compose 2.0+ 版本要求。

### 方式 1：全自动一键部署（推荐）

最快的方式，最小化用户交互。 

```bash
# 克隆项目并执行一键部署脚本
git clone https://github.com/scitix/netpulse.git
cd netpulse
bash ./scripts/docker_auto_deploy.sh
```

此脚本将自动完成：

- 生成安全的环境变量，自动创建 .env 文件，并生成随机的 API Key
- 创建 TLS 证书
- 启动所有 Docker 服务
- 验证部署
- 显示连接信息

**预期输出：**

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

### 方式 2：半自动设置

更多控制权，同时自动化繁琐部分。

#### 步骤 1：环境设置

```bash
# 自动生成安全的环境变量
bash ./scripts/setup_env.sh generate
```

#### 步骤 2：检查和自定义（可选）

```bash
# 查看生成的 .env 文件
cat .env

# 根据需要自定义
vim .env
```

#### 步骤 3：部署服务

```bash
# 生成 TLS 证书
bash ./scripts/generate_redis_certs.sh

# 启动服务
docker compose up -d
```

#### 步骤 4：验证安装

```bash
# 检查服务状态
docker compose ps

# 测试 API
source .env
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/health
```

---

### 方式 C：手动设置

完全控制部署过程的每一步。

#### 步骤 1：创建环境配置

**选项 1：从模板复制**

```bash
# 复制环境模板
cp .env.example .env

# 使用您自己的安全值进行编辑
vim .env
```

**选项 2：从头创建**

```bash
# 生成您自己的安全凭据
REDIS_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
API_KEY="np_$(openssl rand -hex 32)"

# 手动创建 .env 文件
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

#### 步骤 2：环境变量参考

使用以下必需变量创建或更新您的 `.env` 文件：

```bash
# Redis Authentication (Required)
NETPULSE_REDIS__PASSWORD=your_secure_redis_password

# API Authentication (Required)
NETPULSE_SERVER__API_KEY=your_secure_api_key

# Optional Configuration
TZ=Asia/Shanghai                    # Time zone (affects API response timestamps)
NETPULSE_LOG_LEVEL=INFO            # Log level: DEBUG, INFO, WARNING, ERROR
```

**安全注意事项：**

- 使用强密码（最少20个字符）
- API 密钥应以 `np_` 开头以便识别
- 切勿将 `.env` 文件提交到版本控制

**时区配置：**

- NetPulse API 时区完全由环境变量 TZ 控制
- 单一数据源：修改 `.env` 文件中的 TZ 值，整个系统全局更新
- 优先级：`.env TZ` > 系统 `TZ` > 默认 `Asia/Shanghai`
- API 响应包含时区信息（如 `2024-01-15T08:30:15+08:00`）

#### 步骤 3：生成 TLS 证书

```bash
# 生成 Redis TLS 证书
bash ./scripts/generate_redis_certs.sh

# 验证证书文件
ls -la redis/tls/
# 应显示：ca.crt, ca.key, redis.crt, redis.key, redis.dh
```

#### 步骤 4：启动服务

```bash
# 以分离模式启动所有服务
docker compose up -d

# 监控启动日志
docker compose logs -f

# 检查服务健康状态
docker compose ps
```

#### 步骤 5：手动验证

```bash
# 加载环境变量
source .env

# 测试 Redis 连接
docker compose exec redis redis-cli --tls \
  --cert /etc/redis/tls/redis.crt \
  --key /etc/redis/tls/redis.key \
  --cacert /etc/redis/tls/ca.crt \
  -p 6379 -a "$NETPULSE_REDIS__PASSWORD" ping

# 测试 API 健康端点
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/health

# 预期响应：{"code": 0, "message": "success", "data": "ok"}
```


### 部署后管理

#### 扩展服务

```bash
# 扩展 worker 服务
docker compose up --scale node-worker=3 --scale fifo-worker=2 -d

# 查看扩展的服务
docker compose ps
```

#### 监控和日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f controller
docker compose logs -f redis

# 查看实时资源使用情况
docker stats
```

#### 服务管理

```bash
# 停止所有服务
docker compose down

# 重启特定服务
docker compose restart controller

# 重建并重启（代码更改后）
docker compose up --build -d

# 完全清理（移除卷）
docker compose down --volumes --remove-orphans
```

## Kubernetes部署

生产环境中建议使用 Kubernetes 部署 NetPulse。

以下部署方案采用了 Redis 哨兵集群和 Nginx Ingress Controller，支持高可用和负载均衡。

### 准备工作

1. 准备 Kubernetes 集群，至少 3 个节点方可实现高可用。
2. 创建专用的命名空间：
   ```bash
   kubectl create namespace netpulse
   ```
3. 设置当前上下文使用netpulse命名空间（推荐）：
   ```bash
   kubectl config set-context --current --namespace=netpulse
   ```

!!! tip "命名空间设置说明"
    设置默认命名空间后，后续所有kubectl命令都不需要指定 `-n netpulse` 参数：
    - **设置前**: `kubectl get pods -n netpulse`
    - **设置后**: `kubectl get pods`
    
    这个设置只影响当前kubectl会话，不会影响其他业务或用户。

!!! tip
    建议在部署前阅读 Kubernetes manifest 文件，了解各组件的配置情况，按照实际情况进行调整。

### 导入 Secrets

**方式1：自动生成并部署（推荐）**
```bash
# 使用自动脚本生成安全密码并部署
./scripts/k8s_setup_secrets.sh auto
```

**方式2：分步操作**
```bash
# 1. 生成安全密码文件
./scripts/k8s_setup_secrets.sh generate

# 2. 手动部署到集群
kubectl apply -f ./k8s/00-secrets-deploy.yaml
```

**方式3：手动编辑部署**
```bash
# 编辑原始文件中的占位符密码
vim k8s/00-secrets.yaml
# 然后部署
kubectl apply -f ./k8s/00-secrets.yaml
```

!!! note "脚本功能说明"
    `auto` 参数的作用：
    - **自动生成** 随机的Redis密码和API Key
    - **自动创建** `k8s/00-secrets-deploy.yaml` 文件
    - **自动部署** Secret到Kubernetes集群（如果集群可用）
    - 不是部署应用本身，只是部署认证信息
    
    其他可用参数：
    - `generate` - 只生成密码文件，不部署
    - `apply` - 只部署到集群（需要先有密码文件）
    - `cleanup` - 清理临时文件
    
    !!! warning "注意事项"
        如果 `auto` 参数没有自动部署，请手动执行：
        ```bash
        kubectl apply -f ./k8s/00-secrets-deploy.yaml
        ```
        
        **重要**：更新Secret后，需要重启Controller Pod才能加载新的API Key：
        ```bash
        kubectl rollout restart deployment/netpulse-controller -n netpulse
        ```

### 部署 Redis 哨兵集群

```bash
kubectl apply -f ./k8s/01-redis.yaml
```

等待Redis集群启动完成：
```bash
# 查看Redis Pod状态
kubectl get pods -l app=redis

# 查看Redis Sentinel Pod状态  
kubectl get pods -l app=redis-sentinel

# 等待所有Pod变为Ready状态
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis-sentinel --timeout=300s
```

部署后可通过以下命令查看 Redis 集群状态：

```bash
# 查看Redis哨兵状态
kubectl exec -it redis-sentinel-0 -- redis-cli -p 26379 sentinel masters

# 测试Redis连接
kubectl exec -it redis-nodes-0 -- redis-cli -a $REDIS_PASSWORD ping
```

### 部署应用

```bash
kubectl apply -f ./k8s/02-netpulse.yaml
```
!!! tip "本地镜像仓库部署提示"
    为了便于部署，可以本地构建镜像并推送到本地镜像仓库（如Harbor）：
    
    1. **构建镜像**：
    ```bash
    docker build -t your-registry/netpulse-controller:latest -f docker/controller.Dockerfile .
    docker build -t your-registry/netpulse-node-worker:latest -f docker/node-worker.Dockerfile .
    docker build -t your-registry/netpulse-fifo-worker:latest -f docker/fifo-worker.Dockerfile .
    ```
    
    2. **推送到本地仓库**：
    ```bash
    docker push your-registry/netpulse-controller:latest
    docker push your-registry/netpulse-node-worker:latest
    docker push your-registry/netpulse-fifo-worker:latest
    ```
    
    3. **修改镜像地址**：
    编辑 `k8s/02-netpulse.yaml` 中的镜像地址为你的本地仓库地址

### 配置服务访问

**方式1：使用NodePort（简单直接，推荐）**
```bash
# 方法1：修改现有Service为NodePort
kubectl patch svc netpulse -n netpulse -p '{"spec":{"type":"NodePort"}}'

# 方法2：部署专门的NodePort Service（推荐）
kubectl apply -f ./k8s/04-nodeport.yaml

# 查看分配的端口
kubectl get svc netpulse -n netpulse
kubectl get svc netpulse-nodeport -n netpulse

# NodePort访问地址：http://NODE_IP:30090
```

**方式2：使用Ingress（需要先部署Nginx Ingress Controller）**
```bash
# 先部署Nginx Ingress Controller（见下方详细步骤）
# 然后部署Ingress资源
kubectl apply -f ./k8s/03-ingress.yaml
```


等待应用启动完成：
```bash
# 查看所有Pod状态
kubectl get pods

# 等待所有应用Pod变为Ready状态
kubectl wait --for=condition=Ready pod -l app=netpulse --timeout=300s
```

部署后可通过以下命令查看应用状态：

```bash
kubectl get pods # 查看 Pod 状态
kubectl get svc  # 查看服务
kubectl get deployments # 查看部署状态
```

### 应用组件说明

部署完成后，您将看到以下组件：

- **Controller (3个副本)**: API服务，处理HTTP请求
- **Node Worker (6个副本)**: 节点管理Worker，每个Pod最多支持128个设备连接
- **FIFO Worker (6个副本)**: 队列处理Worker，处理查询任务
- **Service**: 内部服务发现，将请求路由到Controller

### 扩容管理

**手动扩容**：
```bash
# 扩容Node Worker到12个副本
kubectl scale deployment netpulse-node-worker --replicas=12 -n netpulse

# 扩容FIFO Worker到12个副本
kubectl scale deployment netpulse-fifo-worker --replicas=12 -n netpulse

# 扩容Controller到5个副本
kubectl scale deployment netpulse-controller --replicas=5 -n netpulse
```

### 部署 Nginx Ingress <small>(可选)</small>

!!! note "重要说明"
    只有在需要域名访问、HTTPS、负载均衡等高级功能时才需要部署 Nginx Ingress。
    对于简单的测试和开发环境，推荐使用 NodePort 方式（见上方"配置服务访问"）。

!!! tip
    Nginx Ingress 的最新部署方式请查看 [Ingress-Nginx Controller 文档](https://kubernetes.github.io/ingress-nginx/)。以下仅为示例。

部署 Nginx Ingress 可以实现负载均衡和 HTTPS 访问等功能。

1. **部署 Nginx Ingress Controller**

    ```bash
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.2/deploy/static/provider/cloud/deploy.yaml
    ```

2. **调整副本数**

    ```bash
    kubectl scale deployment ingress-nginx-controller \
    --replicas=2 \
    -n ingress-nginx
    ```

3. **部署 Nginx Ingress 资源**

    ```bash
    kubectl apply -f ./k8s/03-ingress.yaml
    ```

    建议编辑 `k8s/03-ingress.yaml` 文件，修改 `netpulse.local` 为实际使用的域名。如果在本地测试环境中，可在 `/etc/hosts` 文件中添加以下内容：

    ```
    YOUR_NODE_IP_ADDR netpulse.local
    ```

    将 `YOUR_NODE_IP_ADDR` 替换为实际的节点 IP 地址。

4. **通过 Nginx Ingress 访问应用**

!!! tip
    以下内容依赖 Nginx Ingress 的配置方式。请通过 `kubectl get svc -n ingress-nginx` 检查 IP 类型。如果为 NodePort 模式，可按以下教程进行。

    检查 NodePort：

    ```bash
    kubectl get svc -n ingress-nginx
    ```

    记录下 `ingress-nginx-controller` 的 NodePort 端口号，例如 30080。然后使用该端口号访问应用：

    ```
    curl http://netpulse.local:30080
    ```

## 部署总结

### 完整部署流程

以下是Kubernetes部署的完整步骤：

```bash
# 1. 创建命名空间
kubectl create namespace netpulse
kubectl config set-context --current --namespace=netpulse

# 2. 生成并部署Secrets
./scripts/k8s_setup_secrets.sh auto
# 如果auto没有自动部署，手动执行：
# kubectl apply -f ./k8s/00-secrets-deploy.yaml
# 重要：更新Secret后需要重启Controller
# kubectl rollout restart deployment/netpulse-controller -n netpulse

# 3. 部署Redis哨兵集群
kubectl apply -f ./k8s/01-redis.yaml

# 4. 等待Redis集群就绪
kubectl wait --for=condition=Ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=Ready pod -l app=redis-sentinel --timeout=300s

# 5. 部署NetPulse应用
kubectl apply -f ./k8s/02-netpulse.yaml

# 可选：如果需要使用本地镜像仓库（如Harbor），先构建并推送镜像
# docker build -t your-registry/netpulse-controller:latest -f docker/controller.Dockerfile .
# docker build -t your-registry/netpulse-node-worker:latest -f docker/node-worker.Dockerfile .
# docker build -t your-registry/netpulse-fifo-worker:latest -f docker/fifo-worker.Dockerfile .
# docker push your-registry/netpulse-controller:latest
# docker push your-registry/netpulse-node-worker:latest
# docker push your-registry/netpulse-fifo-worker:latest
# 然后修改 k8s/02-netpulse.yaml 中的镜像地址

# 6. 等待应用就绪
kubectl wait --for=condition=Ready pod -l app=netpulse --timeout=300s

# 7. 配置服务访问（选择一种方式）
# 方式1：使用NodePort（简单直接，推荐）
kubectl apply -f ./k8s/04-nodeport.yaml
kubectl get svc netpulse-nodeport -n netpulse
# 访问地址：http://NODE_IP:30090

# 方式2：使用Ingress（需要先部署Nginx Ingress Controller）
# 先部署Nginx Ingress Controller，然后：
# kubectl apply -f ./k8s/03-ingress.yaml

# 8. 验证部署
kubectl get pods
kubectl get svc

# 8. 查看最终部署状态
kubectl get all
kubectl get pods -o wide
```

### 验证部署

```bash
# 检查所有组件状态
kubectl get all

# 查看Pod分布情况
kubectl get pods -o wide

# 查看资源使用情况
kubectl top pods

# 测试API健康检查
# 方式1：端口转发
kubectl port-forward svc/netpulse 9000:9000 &
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health
# 关闭端口转发
kill %1  # 或者使用 pkill -f "kubectl port-forward"

# 方式2：NodePort访问（如果使用NodePort）
# kubectl get svc netpulse-nodeport -o wide  # 查看NodePort端口
# curl -H "X-API-KEY: YOUR_API_KEY" http://NODE_IP:30090/health

# 方式3：Ingress访问（如果使用Ingress）
# curl -H "X-API-KEY: YOUR_API_KEY" http://YOUR_DOMAIN/health

```

### 性能调优

**根据业务负载调整副本数**：
```bash
# 查看当前负载
kubectl top pods

# 扩容Worker以支持更多设备连接
kubectl scale deployment netpulse-node-worker --replicas=12 -n netpulse
kubectl scale deployment netpulse-fifo-worker --replicas=12 -n netpulse

# 扩容Controller以处理更多API请求
kubectl scale deployment netpulse-controller --replicas=5 -n netpulse
```

**连接数计算**：
- 每个Node Worker Pod最多支持128个设备连接
- 6个Pod = 768个连接
- 12个Pod = 1536个连接
- 可根据实际设备数量调整副本数

**资源需求参考**：
- **Controller**: 4Gi-8Gi内存，2-8个CPU核心
- **Node Worker**: 2Gi-4Gi内存，1-4个CPU核心
- **FIFO Worker**: 2Gi-4Gi内存，1-4个CPU核心
- **Redis**: 每个节点约1Gi内存

### 常见问题排查

#### 1. **服务启动失败**

**Docker部署：**
```bash
# 查看详细日志
docker compose logs -f controller

# 检查端口占用
netstat -tlnp | grep 9000
```

**Kubernetes部署：**
```bash
# 查看Pod状态
kubectl get pods

# 查看详细日志
kubectl logs -l app=netpulse,component=controller -n netpulse

# 查看Pod事件
kubectl describe pod <pod-name>

# 检查命名空间
kubectl get namespaces
```

#### 2. **服务访问问题**

**检查Service状态：**
```bash
# 查看Service状态
kubectl get svc -n netpulse
kubectl describe svc netpulse -n netpulse

# 检查Ingress状态
kubectl get ingress -n netpulse
kubectl describe ingress netpulse-ingress -n netpulse
```

**NodePort访问：**
```bash
# 查看NodePort端口
kubectl get svc netpulse-nodeport -n netpulse -o wide

# 使用NodePort访问（替换NODE_IP）
curl http://NODE_IP:30090/health

# 获取节点IP
kubectl get nodes -o wide
```

**端口转发测试：**
```bash
# 本地端口转发测试
kubectl port-forward svc/netpulse 9000:9000 -n netpulse &
curl http://localhost:9000/health
# 关闭端口转发
kill %1  # 或者使用 pkill -f "kubectl port-forward"
```

#### 3. **Redis 连接失败**

**Docker部署：**
```bash
# 测试 Redis 连接
docker compose exec redis redis-cli ping
```

**Kubernetes部署：**
```bash
# 测试 Redis 连接
kubectl exec -it redis-nodes-0 -- redis-cli -a $REDIS_PASSWORD ping

# 检查Redis哨兵状态
kubectl exec -it redis-sentinel-0 -- redis-cli -p 26379 sentinel masters

# 查看Redis Pod状态
kubectl get pods -l app=redis
```

#### 3. **API 认证失败**
```bash
# 检查 API Key 格式
echo $NETPULSE_SERVER__API_KEY

# 测试 API 认证
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health

# Kubernetes环境测试
kubectl port-forward svc/netpulse 9000:9000 &
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health
# 关闭端口转发
kill %1  # 或者使用 pkill -f "kubectl port-forward"
```

#### 4. **Kubernetes特定问题**

**命名空间问题：**
```bash
# 检查当前命名空间
kubectl config view --minify | grep namespace

# 创建命名空间
kubectl create namespace netpulse

# 切换命名空间
kubectl config set-context --current --namespace=netpulse
```

**Secrets问题：**
```bash
# 检查Secrets
kubectl get secrets

# 查看Secret内容
kubectl get secret netpulse-secrets -o yaml

# 重新生成Secrets
./scripts/k8s_setup_secrets.sh auto
```

**扩容问题：**
```bash
# 检查资源限制
kubectl describe nodes

# 查看Pod资源使用
kubectl top pods

# 检查HPA状态
kubectl get hpa
kubectl describe hpa netpulse-controller-hpa

# 手动扩容
kubectl scale deployment netpulse-node-worker --replicas=12 -n netpulse
```

**API Key更新问题：**
```bash
# 重新生成并部署API Key
./scripts/k8s_setup_secrets.sh auto

# 重启Controller以加载新的API Key
kubectl rollout restart deployment/netpulse-controller -n netpulse

# 验证新API Key是否生效
curl -H "X-API-KEY: YOUR_NEW_API_KEY" http://YOUR_HOST:PORT/health
```

**镜像拉取问题：**
```bash
# 检查镜像拉取状态
kubectl describe pod <pod-name>

# 使用本地镜像（需要预先传输到各节点）
docker save -o netpulse-controller.tar localhost/netpulse-controller:latest
scp netpulse-controller.tar node1:/tmp/
ssh node1 "docker load -i /tmp/netpulse-controller.tar"
```

**Pod分布查看：**
```bash
# 查看Pod在哪些节点上运行
kubectl get pods -o wide

# 查看Pod分布统计
kubectl get pods -o custom-columns="NAME:.metadata.name,NODE:.spec.nodeName" | sort -k2
```

### 部署后管理

**日常运维命令**：
```bash
# 查看集群状态
kubectl get all

# 查看资源使用情况
kubectl top pods
kubectl top nodes

# 查看日志
kubectl logs -l app=netpulse,component=controller -n netpulse --tail=100
kubectl logs -l app=netpulse,component=node-worker -n netpulse --tail=100

# 重启服务
kubectl rollout restart deployment/netpulse-controller
kubectl rollout restart deployment/netpulse-node-worker
kubectl rollout restart deployment/netpulse-fifo-worker

# 注意：更新API Key后必须重启Controller
kubectl rollout restart deployment/netpulse-controller
```


**备份和恢复**：
```bash
# 备份配置
kubectl get configmap netpulse-config -o yaml > netpulse-config-backup.yaml
kubectl get secret netpulse-secrets -o yaml > netpulse-secrets-backup.yaml

# 恢复配置
kubectl apply -f netpulse-config-backup.yaml
kubectl apply -f netpulse-secrets-backup.yaml
```

### 下一步

部署完成后，建议您：

1. **[快速开始](quick-start.md)** - 学习基础API使用方法
2. **[Postman 使用指南](postman-guide.md)** - 使用 Postman 快速测试 API


