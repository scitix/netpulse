# NetPulse 快速开始

!!! info "NetPulse 架构说明"
    NetPulse 是一个基于服务器的网络自动化控制器，与Netmiko等单机工具不同，它需要部署在服务器上提供RESTful API服务，支持多用户并发访问和分布式任务处理。

本指南将帮助您快速体验NetPulse的基本功能，无需深入了解技术细节。

## 快速体验目标

通过本指南您将：启动 NetPulse 服务，执行第一个API调用，连接并操作网络设备，了解批量操作功能


## 一键启动

!!! tip "系统要求"
    - Docker 20.10+ 和 Docker Compose 2.0+
    - 至少 2GB 可用内存
    - 端口 9000 未被占用

### 1. 获取代码
```bash
git clone https://github.com/scitix/netpulse.git
cd netpulse
```

### 2. 一键部署

!!! tip "推荐方式"
    这是最简单快捷的部署方式，适合开发测试和生产环境。
    
    **前置要求：** 确保您的机器已安装 Docker 环境，首次部署时会自动下载所需镜像，请保持网络连接畅通。

```bash
bash ./scripts/docker_auto_deploy.sh
```

**预期输出：**
```bash
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
**重要：** 请记录下您的 API Key（如：`np_90fbd8685671a2c0b34aa107...`），后续所有 API 调用都需要使用此密钥。如需查看完整密钥，可在项目根目录的 `.env` 文件中找到。

### 3. 验证服务

!!! success "部署成功"
    如果看到上述输出，说明服务已成功启动！

```bash
# 查看服务状态
docker compose ps

# 测试API连接
curl -H "X-API-KEY: np_90fbd8685671a2c0b34aa107..." http://localhost:9000/health

# 看到以下消息，代表服务部署成功了
{"code":200,"message":"success","data":"ok"}
```

## 第一个API调用

### API 认证

NetPulse 使用 Header 认证方式，所有 API 请求都需要在 Header 中携带 API Key：

```bash
# 方式1：直接使用API Key（从.env文件或部署输出中获取）
curl -H "X-API-KEY: np_90fbd8685671a2c0b34aa107..." \
     http://localhost:9000/health

# 方式2：使用环境变量（推荐）
source .env
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/health
```

### 测试设备连接

!!! note "设备连接测试"
    在连接真实设备前，请确保设备网络可达且账号密码正确。
    
    **注意：** 请将示例中的 IP 地址、用户名和密码替换为您的实际设备信息。

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios"
    }
  }' \
  http://localhost:9000/device/test-connection
```

**连接参数说明：**

| 参数 | 类型 | 必需 | 说明 |
|:-----|:-----|:----:|:-----|
| `host` | string | ✅ | 设备IP地址 |
| `username` | string | ✅ | SSH用户名 |
| `password` | string | ✅ | SSH密码 |
| `device_type` | string | ✅ | 设备类型（如：cisco_ios, hp_comware, juniper_junos等） |

**预期响应：**
```json
{
  "code": 200,
  "message": "Connection test completed",
  "data": {
    "success": true,
    "connection_time": 2.64,
    "error_message": null,
    "device_info": {
      "prompt": "Router#",
      "device_type": "cisco_ios",
      "host": "192.168.1.1"
    },
    "timestamp": "2025-09-21T02:23:13.469090+08:00"
  }
}
```

### 执行网络命令

!!! info "命令执行"
    支持所有网络设备的标准命令，如 `show version`（Cisco）、`display version`（H3C/Huawei）等。不同厂商的命令语法可能不同。
    
    **注意：** 本示例使用Cisco IOS设备，其他厂商设备请参考相应的设备类型和命令语法。

```bash
# 执行命令
response=$(curl -s -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute)

# 查看响应
echo "$response" | jq '.'
```

**预期响应（立即返回）：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "job_12345",
    "status": "queued",
    "queue": "pinned_192.168.1.1",
    "created_at": "2025-09-21T02:25:13.469090+08:00"
  }
}
```

!!! warning "重要：设备操作是异步的"
    所有设备操作（`/device/execute`、`/device/bulk`）都是异步的：
    1. API 立即返回任务ID和状态（通常是 `queued`）
    2. 需要通过 `/job?id=xxx` 接口查询执行结果
    3. 只有 `/device/test-connection` 是同步的，立即返回结果
    
    **查询任务结果：**
    ```bash
    # 提取任务ID
    task_id=$(echo "$response" | jq -r '.data.id')
    
    # 等待几秒后查询任务结果
    sleep 3
    curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
         http://localhost:9000/job?id=$task_id | jq '.'
    ```
    
    **任务完成后的响应示例：**
    ```json
    {
      "code": 200,
      "message": "success",
      "data": [{
        "id": "job_12345",
        "status": "finished",
        "result": {
          "type": "success",
          "retval": {
            "show version": "Cisco IOS Software, Version 15.2..."
          }
        },
        "duration": 1.45
      }]
    }
    ```

### 配置推送

除了执行查询命令，NetPulse 还支持配置推送功能：

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios"
    },
    "config": [
      "interface GigabitEthernet0/1",
      "description Management Interface",
      "ip address 192.168.1.1 255.255.255.0",
      "no shutdown"
    ]
  }' \
  http://localhost:9000/device/execute
```

## 批量操作体验

### 批量设备配置

!!! warning "批量操作注意"
    批量操作前请确保所有设备网络可达，建议先在少量设备上测试。

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "username": "admin",
      "password": "your_password"
    },
    "devices": [
      {
        "host": "192.168.1.1",
        "device_type": "cisco_ios",
        "username": "admin",
        "password": "password1"
      },
      {
        "host": "192.168.1.2",
        "device_type": "cisco_ios",
        "username": "admin",
        "password": "password2"
      }
    ],
    "command": "show ip interface brief"
  }' \
  http://localhost:9000/device/bulk
```

**预期响应（立即返回）：**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "succeeded": [
      {
        "id": "job_abc123",
        "status": "queued",
        "queue": "pinned_192.168.1.1"
      },
      {
        "id": "job_def456",
        "status": "queued",
        "queue": "pinned_192.168.1.2"
      }
    ],
    "failed": []
  }
}
```

!!! note "批量操作说明"
    批量操作返回的是任务列表，每个设备对应一个任务。需要通过任务ID查询每个设备的执行结果。

## 任务管理

NetPulse 支持异步任务处理，您可以通过任务ID查询执行状态和结果。

### 查询任务状态

```bash
# 查询所有任务
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/job

# 按状态查询（finished, running, failed等）
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/job?status=finished

# 查询特定任务
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/job?id=your_job_id
```

### 取消任务

```bash
# 取消特定任务
curl -X DELETE \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  http://localhost:9000/job?id=your_job_id
```

## 最佳实践

### 错误处理

在实际使用中，建议检查API响应状态并处理错误：

```bash
# 执行命令并检查响应
response=$(curl -s -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute)

# 解析响应
if echo "$response" | jq -e '.code == 200' > /dev/null; then
    echo "命令执行成功"
    echo "$response" | jq -r '.data.output'
else
    echo "命令执行失败"
    echo "$response" | jq -r '.message'
fi
```

## 下一步学习

### 深入学习
- [基础概念](basic-concepts.md) - 了解系统架构和核心概念
- [部署指南](deployment-guide.md) - 学习生产环境部署
- [Postman使用指南](postman-guide.md) - 使用Postman快速体验API
- [API概览](../api/api-overview.md) - 深入了解所有API接口

## 遇到问题？

!!! failure "常见问题"
    - **服务启动失败** → 查看 [部署指南](deployment-guide.md)
    - **API调用错误** → 检查API Key是否正确，查看 [API概览](../api/api-overview.md)
    - **设备连接问题** → 确认设备网络可达，检查用户名密码是否正确
    - **任务执行失败** → 使用任务管理API查询详细错误信息


---
