# API 最佳实践

## 概述

本文档提供 NetPulse API 使用的最佳实践，帮助您构建高效、可靠的网络自动化解决方案。

## 认证和安全性

### API 密钥管理

#### 最佳实践
```bash
# 使用环境变量存储API密钥
export NETPULSE_API_KEY="your-api-key-here"

# 在请求中使用
curl -H "X-API-KEY: $NETPULSE_API_KEY" \
     http://localhost:9000/health
```

#### 安全建议
- 定期轮换API密钥
- 不要在代码中硬编码密钥
- 使用HTTPS进行传输
- 限制API密钥的访问权限

### 设备凭据管理

#### 使用 Vault 存储凭据（推荐）

**最佳实践**：使用 HashiCorp Vault 存储设备凭据，避免在 API 请求中直接传递密码。

```bash
# 1. 创建凭据到 Vault
curl -X POST \
  -H "X-API-KEY: $NETPULSE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin",
    "username": "admin",
    "password": "secure_password",
    "metadata": {
      "description": "HQ site admin credentials",
      "site": "hq"
    }
  }' \
  http://localhost:9000/credential/vault/create

# 2. 在设备操作中使用凭据引用
curl -X POST \
  -H "X-API-KEY: $NETPULSE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "credential_ref": "sites/hq/admin",
      "device_type": "cisco_ios"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute
```

#### 安全建议
- **使用 Vault 存储凭据**：避免在代码、日志、API 请求中暴露密码
- **凭据路径规划**：使用层级结构（如 `sites/{site}/{role}`）便于管理
- **定期轮换密码**：定期更新 Vault 中的密码并创建新版本
- **最小权限原则**：为不同应用创建不同权限的 Vault token
- **凭据缓存**：系统会自动缓存凭据，避免重复读取

#### 凭据路径命名规范

```python
# 推荐的路径结构
credential_paths = {
    "sites/hq/admin": "HQ站点管理员凭据",
    "sites/hq/readonly": "HQ站点只读凭据",
    "sites/branch1/admin": "分支1管理员凭据",
    "devices/core/backup": "核心设备备份凭据",
    "environments/prod/admin": "生产环境管理员凭据"
}
```

参考：[Vault 凭据管理 API](./credential-api.md)

### 请求头设置

```bash
# 标准请求头
curl -X POST \
  -H "X-API-KEY: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"key": "value"}' \
  http://localhost:9000/api/endpoint
```

## 连接管理

### 队列策略选择

#### FIFO 队列 (推荐用于一般操作)
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "credential_ref": "sites/hq/admin",
    "device_type": "cisco_ios"
  },
  "options": {
    "queue_strategy": "fifo"
  }
}
```

#### Pinned 队列 (推荐用于频繁操作)
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "credential_ref": "sites/hq/admin",
    "device_type": "cisco_ios"
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

### 连接参数优化

#### 超时设置
```json
{
  "connection_args": {
    "host": "192.168.1.1",
    "credential_ref": "sites/hq/admin",
    "device_type": "cisco_ios",
    "timeout": 30,
    "read_timeout": 60,
    "delay_factor": 2
  }
}
```

#### 连接复用
```json
{
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

!!! note "连接复用说明"
    使用 `queue_strategy: "pinned"` 时，系统会自动复用连接，无需额外配置。

## 批量操作优化

### 设备分组策略

#### 按厂商分组
```python
def group_devices_by_vendor(devices):
    """按厂商分组设备"""
    groups = {}
    for device in devices:
        vendor = get_vendor_from_device_type(device['device_type'])
        if vendor not in groups:
            groups[vendor] = []
        groups[vendor].append(device)
    return groups
```

#### 按地理位置分组
```python
def group_devices_by_location(devices):
    """按地理位置分组设备"""
    groups = {}
    for device in devices:
        location = device.get('location', 'unknown')
        if location not in groups:
            groups[location] = []
        groups[location].append(device)
    return groups
```

### 批量操作最佳实践

#### 1. 合理的批次大小
```python
# 建议批次大小：10-50台设备
BATCH_SIZE = 20

def execute_batch_commands(devices, command):
    """分批执行命令"""
    results = []
    for i in range(0, len(devices), BATCH_SIZE):
        batch = devices[i:i + BATCH_SIZE]
        batch_result = execute_command_batch(batch, command)
        results.extend(batch_result)
    return results
```

#### 2. 错误处理和重试
```python
import time
from typing import List, Dict

def execute_with_retry(devices: List[Dict], command: str, max_retries: int = 3):
    """带重试的命令执行"""
    results = []
    failed_devices = []
    
    for device in devices:
        for attempt in range(max_retries):
            try:
                result = execute_single_command(device, command)
                results.append(result)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    failed_devices.append({
                        'device': device,
                        'error': str(e)
                    })
                else:
                    time.sleep(2 ** attempt)  # 指数退避
    
    return results, failed_devices
```

## 模板使用

### Jinja2 模板最佳实践

#### 1. 模板结构
```jinja2
{# 配置模板示例 #}
{% for interface in interfaces %}
interface {{ interface.name }}
 description {{ interface.description }}
 ip address {{ interface.ip_address }} {{ interface.subnet_mask }}
 no shutdown
{% endfor %}
```

#### 2. 变量验证
```python
def validate_template_variables(template_vars):
    """验证模板变量"""
    required_vars = ['interfaces', 'hostname', 'domain_name']
    missing_vars = [var for var in required_vars if var not in template_vars]
    
    if missing_vars:
        raise ValueError(f"Missing required variables: {missing_vars}")
    
    return True
```

### TextFSM 解析最佳实践

#### 1. 模板设计
```textfsm
Value HOSTNAME (\S+)
Value UPTIME (.+)
Value VERSION (.+)

Start
  ^\s*${HOSTNAME}\s+uptime\s+is\s+${UPTIME}
  ^\s*.*Version\s+${VERSION}
  ^\s*$$
  ^.* -> Error
```

#### 2. 解析结果处理
```python
def parse_command_output(output: str, template_name: str):
    """解析命令输出"""
    try:
        parsed_result = parse_with_textfsm(output, template_name)
        return {
            'success': True,
            'data': parsed_result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'raw_output': output
        }
```

## 错误处理

### 常见错误码处理

```python
def handle_api_response(response):
    """处理API响应"""
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 200:
            return {'success': True, 'data': data['data']}
        else:
            return {'success': False, 'error': data['message']}
    elif response.status_code == 401:
        return {'success': False, 'error': '认证失败，请检查API密钥'}
    elif response.status_code == 404:
        return {'success': False, 'error': '资源不存在'}
    elif response.status_code == 500:
        return {'success': False, 'error': '服务器内部错误'}
    else:
        return {'success': False, 'error': f'未知错误: {response.status_code}'}
```

### 重试机制

```python
import requests
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=2)
def api_request(url, headers, data):
    """带重试的API请求"""
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
```

## 性能优化

### 1. 连接池管理

```python
class ConnectionPool:
    """连接池管理"""
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.active_connections = {}
    
    def get_connection(self, device_id):
        """获取连接"""
        if device_id in self.active_connections:
            return self.active_connections[device_id]
        return None
    
    def add_connection(self, device_id, connection):
        """添加连接"""
        if len(self.active_connections) < self.max_connections:
            self.active_connections[device_id] = connection
            return True
        return False
```

### 2. 异步处理

```python
import asyncio
import aiohttp

async def execute_commands_async(devices, command):
    """异步执行命令"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for device in devices:
            task = execute_single_command_async(session, device, command)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

async def execute_single_command_async(session, device, command):
    """异步执行单个命令"""
    url = "http://localhost:9000/device/execute"
    headers = {"X-API-KEY": f"{API_KEY}"}
    data = {
        "driver": "netmiko",
        "connection_args": device,
        "command": command
    }
    
    async with session.post(url, headers=headers, json=data) as response:
        return await response.json()
```

### 3. 缓存策略

```python
import redis
import json
import hashlib

class ResultCache:
    """结果缓存"""
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 3600  # 1小时
    
    def get_cache_key(self, device_id, command):
        """生成缓存键"""
        content = f"{device_id}:{command}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cached_result(self, device_id, command):
        """获取缓存结果"""
        key = self.get_cache_key(device_id, command)
        result = self.redis.get(key)
        return json.loads(result) if result else None
    
    def cache_result(self, device_id, command, result):
        """缓存结果"""
        key = self.get_cache_key(device_id, command)
        self.redis.setex(key, self.ttl, json.dumps(result))
```

## 监控和日志

### 1. 任务监控

```python
def monitor_job_status(job_id):
    """监控任务状态"""
    while True:
        response = requests.get(
            f"http://localhost:9000/job?id={job_id}",
            headers={"X-API-KEY": f"{API_KEY}"}
        )
        data = response.json()
        
        if data['data']['status'] in ['completed', 'failed']:
            return data['data']
        
        time.sleep(5)  # 每5秒检查一次
```

### 2. 性能指标

```python
import time
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_devices: int
    successful_operations: int
    failed_operations: int
    total_time: float
    average_time_per_device: float

def calculate_performance_metrics(results):
    """计算性能指标"""
    total_devices = len(results)
    successful = sum(1 for r in results if r.get('success', False))
    failed = total_devices - successful
    
    return PerformanceMetrics(
        total_devices=total_devices,
        successful_operations=successful,
        failed_operations=failed,
        total_time=0,  # 需要实际计算
        average_time_per_device=0  # 需要实际计算
    )
```

## Webhook 集成

### 1. Webhook 配置

```json
{
  "options": {
    "webhook": {
      "url": "https://your-webhook-url.com/callback",
      "method": "POST",
      "headers": {
        "Content-Type": "application/json",
        "X-Custom-Header": "custom-value"
      },
      "timeout": 30
    }
  }
}
```

### 2. Webhook 处理

```python
from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/webhook/callback', methods=['POST'])
def webhook_callback():
    """处理webhook回调"""
    data = request.json
    
    # 处理不同类型的回调
    if data['type'] == 'job_completed':
        handle_job_completed(data)
    elif data['type'] == 'job_failed':
        handle_job_failed(data)
    elif data['type'] == 'device_connected':
        handle_device_connected(data)
    
    return {'status': 'success'}

def handle_job_completed(data):
    """处理任务完成回调"""
    job_id = data['job_id']
    result = data['result']
    
    # 记录日志
    print(f"Job {job_id} completed successfully")
    
    # 发送通知
    send_notification(f"任务 {job_id} 执行完成")
```

## 最佳实践总结

### 1. 开发阶段
- 使用开发环境的API密钥
- 启用详细日志记录
- 使用小规模测试数据
- 实现完整的错误处理

### 2. 生产阶段
- 使用强密码的API密钥
- 启用HTTPS传输
- 实现监控和告警
- 定期备份配置

### 3. 维护阶段
- 定期检查系统状态
- 监控性能指标
- 更新安全补丁
- 优化配置参数

## 相关文档

- [API概览](./api-overview.md) - 完整的API文档
- [设备操作 API](./device-api.md) - 设备操作核心接口
- [Vault 凭据管理 API](./credential-api.md) - Vault 凭据管理接口
- [API示例](./api-examples.md) - 实际应用场景 