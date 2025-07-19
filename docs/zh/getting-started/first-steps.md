# 第一个API调用

本指南将带您完成 NetPulse API 的第一个调用，学习基础的网络设备管理操作。

## 学习目标

通过本指南，您将学会：
- 理解 NetPulse API 的基本概念
- 配置网络设备连接
- 执行网络命令
- 处理API响应
- 使用最佳实践

## 前置条件

在开始之前，请确保：
- ✅ NetPulse 服务已启动并运行
- ✅ 获取了有效的 API 密钥
- ✅ 有可用的网络设备（路由器、交换机等）
- ✅ 设备支持 SSH 连接

## API 认证

NetPulse 使用 API Key 认证方式。所有端点都需要认证：

```bash
# API密钥格式（Header方式）
X-API-KEY: YOUR_API_KEY

# 使用Header的示例
curl -H "X-API-KEY: your_api_key_here" \
     http://localhost:9000/health

# 使用查询参数的替代方式
curl "http://localhost:9000/health?X-API-KEY=your_api_key_here"
```

## 基础API调用

### 1. 健康检查

首先测试API服务是否正常运行：

```bash
curl -H "X-API-KEY: YOUR_API_KEY" \
     http://localhost:9000/health
```

**预期响应：**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00+08:00",
  "version": "1.0.0",
  "uptime": 3600
}
```

### 2. 获取API信息

查看API版本和功能信息：

```bash
curl -H "X-API-KEY: YOUR_API_KEY" \
     http://localhost:9000/
```

**预期响应：**
```json
{
  "name": "NetPulse API",
  "version": "0.1.0",
  "description": "Distributed RESTful API for network device management",
  "features": [
    "multi-vendor support",
    "persistent connections",
    "batch operations",
    "template engine"
  ],
  "supported_vendors": [
    "cisco_ios",
    "cisco_nxos",
    "arista_eos",
    "juniper_junos"
  ]
}
```

## 设备管理

### 1. 添加网络设备

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "your_password",
    "device_type": "cisco_ios",
    "port": 22,
    "timeout": 30
  }' \
  http://localhost:9000/devices
```

**请求参数说明：**

| 参数 | 类型 | 必需 | 说明 | 示例 |
|------|------|------|------|------|
| `hostname` | string | ✅ | 设备IP地址或主机名 | `192.168.1.1` |
| `username` | string | ✅ | 登录用户名 | `admin` |
| `password` | string | ✅ | 登录密码 | `password123` |
| `device_type` | string | ✅ | 设备类型 | `cisco_ios` |
| `port` | integer | ❌ | SSH端口 | `22` |
| `timeout` | integer | ❌ | 连接超时时间 | `30` |

**预期响应：**
```json
{
  "success": true,
  "device_id": "dev_1234567890",
  "hostname": "192.168.1.1",
  "status": "connected",
  "message": "Device added successfully"
}
```

### 2. 查看设备列表

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/devices
```

**预期响应：**
```json
{
  "devices": [
    {
      "device_id": "dev_1234567890",
      "hostname": "192.168.1.1",
      "device_type": "cisco_ios",
      "status": "connected",
      "last_seen": "2024-01-01T12:00:00+08:00"
    }
  ],
  "total": 1
}
```

### 3. 测试设备连接

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1"
  }' \
  http://localhost:9000/devices/test
```

**预期响应：**
```json
{
  "success": true,
  "hostname": "192.168.1.1",
  "connection_time": 0.5,
  "device_info": {
    "hostname": "Router-01",
    "model": "Cisco IOS XE",
    "version": "17.03.01"
  }
}
```

## 命令执行

### 1. 执行单个命令

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute
```

**预期响应：**
```json
{
  "success": true,
  "hostname": "192.168.1.1",
  "command": "show version",
  "output": "Cisco IOS XE Software, Version 17.03.01...",
  "execution_time": 0.8,
  "timestamp": "2024-01-01T12:00:00+08:00"
}
```

### 2. 执行多个命令

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "commands": [
      "show version",
      "show interfaces",
      "show ip interface brief"
    ]
  }' \
  http://localhost:9000/execute/batch
```

**预期响应：**
```json
{
  "success": true,
  "hostname": "192.168.1.1",
  "results": [
    {
      "command": "show version",
      "output": "Cisco IOS XE Software...",
      "execution_time": 0.8
    },
    {
      "command": "show interfaces",
      "output": "Interface GigabitEthernet0/0...",
      "execution_time": 1.2
    },
    {
      "command": "show ip interface brief",
      "output": "Interface IP-Address OK? Method Status...",
      "execution_time": 0.5
    }
  ],
  "total_time": 2.5
}
```

### 3. 批量设备操作

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostnames": ["192.168.1.1", "192.168.1.2", "192.168.1.3"],
    "command": "show version"
  }' \
  http://localhost:9000/execute/multi
```

**预期响应：**
```json
{
  "success": true,
  "results": [
    {
      "hostname": "192.168.1.1",
      "success": true,
      "output": "Cisco IOS XE Software...",
      "execution_time": 0.8
    },
    {
      "hostname": "192.168.1.2",
      "success": true,
      "output": "Cisco IOS XE Software...",
      "execution_time": 0.9
    },
    {
      "hostname": "192.168.1.3",
      "success": false,
      "error": "Connection timeout",
      "execution_time": 30.0
    }
  ],
  "summary": {
    "total": 3,
    "successful": 2,
    "failed": 1
  }
}
```

## 常用命令示例

### 设备信息查询

```bash
# 获取设备版本信息
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute

# 获取接口信息
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show interfaces"
  }' \
  http://localhost:9000/execute

# 获取路由表
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show ip route"
  }' \
  http://localhost:9000/execute
```

### 配置管理

```bash
# 查看当前配置
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show running-config"
  }' \
  http://localhost:9000/execute

# 保存配置
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "write memory"
  }' \
  http://localhost:9000/execute
```

## 错误处理

### 常见错误类型

#### 1. 认证错误
```json
{
  "error": "unauthorized",
  "message": "Invalid API key",
  "status_code": 401
}
```

#### 2. 设备连接错误
```json
{
  "error": "connection_failed",
  "message": "Unable to connect to device",
  "hostname": "192.168.1.1",
  "status_code": 500
}
```

#### 3. 命令执行错误
```json
{
  "error": "command_failed",
  "message": "Command execution failed",
  "hostname": "192.168.1.1",
  "command": "show invalid-command",
  "status_code": 400
}
```

### 错误处理最佳实践

```bash
# 使用 -w 参数获取HTTP状态码
curl -w "HTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute

# 使用 jq 解析JSON响应
curl -s -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute | jq '.output'
```

## 性能优化

### 1. 使用长连接

NetPulse 支持持久化连接，避免重复建立连接：

```bash
# 第一次连接会建立持久连接
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute

# 后续命令会复用连接，响应更快
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show interfaces"
  }' \
  http://localhost:9000/execute
```

### 2. 批量操作

对于多个命令，使用批量操作接口：

```bash
# 推荐：使用批量接口
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "commands": [
      "show version",
      "show interfaces",
      "show ip route"
    ]
  }' \
  http://localhost:9000/execute/batch
```

## 实用脚本示例

### Python 脚本

```python
import requests
import json

class NetPulseClient:
    def __init__(self, api_key, base_url="http://localhost:9000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def execute_command(self, hostname, command):
        """执行单个命令"""
        url = f"{self.base_url}/execute"
        data = {
            "hostname": hostname,
            "command": command
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()
    
    def batch_commands(self, hostname, commands):
        """批量执行命令"""
        url = f"{self.base_url}/execute/batch"
        data = {
            "hostname": hostname,
            "commands": commands
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

# 使用示例
client = NetPulseClient("YOUR_API_KEY")

# 执行单个命令
result = client.execute_command("192.168.1.1", "show version")
print(result["output"])

# 批量执行命令
commands = ["show version", "show interfaces", "show ip route"]
results = client.batch_commands("192.168.1.1", commands)
for result in results["results"]:
    print(f"Command: {result['command']}")
    print(f"Output: {result['output']}\n")
```

### Shell 脚本

```bash
#!/bin/bash

# NetPulse API 配置
API_KEY="YOUR_API_KEY"
API_URL="http://localhost:9000"
DEVICE_HOST="192.168.1.1"

# 执行命令函数
execute_command() {
    local command="$1"
    curl -s -X POST \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"hostname\": \"$DEVICE_HOST\",
            \"command\": \"$command\"
        }" \
        "$API_URL/execute" | jq -r '.output'
}

# 使用示例
echo "=== 设备版本信息 ==="
execute_command "show version"

echo -e "\n=== 接口状态 ==="
execute_command "show ip interface brief"

echo -e "\n=== 路由表 ==="
execute_command "show ip route"
```

## 下一步

现在您已经掌握了基础的API调用，建议继续学习：

- **[API参考](../guides/api.md)** - 完整的API文档
- **[批量操作](../advanced/batch-operations.md)** - 大规模设备管理
- **[模板系统](../advanced/templates.md)** - 使用模板简化操作
- **[错误处理](../reference/error-codes.md)** - 详细的错误代码说明

## 常见问题

### Q: API调用返回401错误？
A: 检查API密钥是否正确，确保使用 `Bearer` 前缀。

### Q: 设备连接超时？
A: 检查设备IP地址、用户名密码是否正确，确保网络连通性。

### Q: 命令执行失败？
A: 检查命令语法是否正确，确保设备支持该命令。

### Q: 如何提高API调用性能？
A: 使用批量操作接口，利用持久化连接特性。

---

<div align="center">

**恭喜！您已掌握 NetPulse API 的基础使用**

[API参考 →](../guides/api.md)

</div> 