# 部署指南

## 裸机部署

!!! warning
    此方法不推荐用于生产环境。仅建议在裸机安装 CLI 工具。

1. 安装 NetPulse：
    ```bash
    pip install netpulse[api,tool]
    ```

2. 配置 Redis：
    ```bash
    # 编辑 Redis 配置
    redis-server redis/redis.conf
    ```

3. 配置 NetPulse：
    ```bash
    # 根据您的需求进行编辑
    vim config/config.yaml
    ```

4. 启动 API 服务器：
    ```bash
    gunicorn -p controller.pid -c gunicorn.conf.py netpulse.controller:app
    ```

5. 启动 Worker：
    ```bash
    python worker.py fifo
    python worker.py node
    ```

## Docker 部署

单机使用环境下，建议使用 Docker 部署 NetPulse。

根据您的需求和控制级别，可以选择以下三种部署方式：

### 方式 A：全自动一键部署

最快的方式，最小化用户交互。

```bash
# 一键部署脚本
bash ./scripts/docker_auto_deploy.sh
```

此脚本将自动完成：

- ✅ 生成安全的环境变量
- ✅ 创建 TLS 证书
- ✅ 启动所有服务
- ✅ 验证部署
- ✅ 显示连接信息

**预期输出：**

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

### 方式 B：半自动设置

更多控制权，同时自动化繁琐部分。

#### 步骤 1：环境设置

```bash
# 自动生成安全的环境变量
bash ./scripts/setup_env.sh generate
```

#### 步骤 2：审查和自定义（可选）

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
curl -H "Authorization: Bearer $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/health

# 预期响应：{"code": 0, "message": "success", "data": "ok"}
```

---

### 部署方式对比

| 方式 | 设置时间 | 控制级别 | 推荐场景 |
|------|----------|----------|----------|
| **全自动** | ~2 分钟 | 低 | 快速测试、演示 |
| **半自动** | ~5 分钟 | 中等 | 开发、预发布 |
| **手动设置** | ~10 分钟 | 高 | 生产、自定义配置 |

---

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

## Kubernetes 高可用部署

生产环境中建议使用 Kubernetes 部署 NetPulse。

以下部署方案采用了 Redis 哨兵集群和 Nginx Ingress Controller，支持高可用和负载均衡。

### 准备工作

1. 准备 Kubernetes 集群，至少 3 个节点方可实现高可用。
2. 编辑 `k8s/00-secrets.yaml` 文件，修改其中的密码字段。

!!! tip
    建议在部署前阅读 Kubernetes manifest 文件，了解各组件的配置情况，按照实际情况进行调整。

### 导入 Secrets

```bash
kubectl apply -f ./k8s/00-secrets.yaml
```

### 部署 Redis 哨兵集群

```bash
kubectl apply -f ./k8s/01-redis.yaml
```

部署后可通过以下命令查看 Redis 集群状态：

```bash
kubectl exec -it redis-sentinel-0 -- redis-cli -p 26379 -a $REDIS_PASSWORD sentinel masters
```

### 部署应用

```bash
kubectl apply -f ./k8s/02-netpulse.yaml
```

部署后可通过以下命令查看应用状态：

```bash
kubectl get pods # 查看 Pod 状态
kubectl get svc  # 查看服务
```

### 部署 Nginx Ingress <small>(可选)</small>

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

!!! tips
    以下内容依赖 Nginx Ingress 的配置方式。请通过 `kubectl get svc -n ingress-nginx` 检查 IP 类型。如果为 NodePort 模式，可按以下教程进行。

    检查 NodePort：

    ```bash
    kubectl get svc -n ingress-nginx
    ```

    记录下 `ingress-nginx-controller` 的 NodePort 端口号，例如 30080。然后使用该端口号访问应用：

    ```
    curl http://netpulse.local:30080
    ```
