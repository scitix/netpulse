# 最佳实践

本文档提供了 NetPulse 系统的最佳实践指南，包括 API 使用、性能优化、安全配置、监控告警等方面的建议。

## 🎯 总体原则

### 1. 安全性优先
- 始终使用 HTTPS 进行生产环境通信
- 定期轮换 API 密钥
- 实施最小权限原则
- 监控异常访问行为

### 2. 性能优化
- 使用连接池和连接复用
- 实施适当的缓存策略
- 优化批量操作
- 监控系统资源使用

### 3. 可靠性保障
- 实施错误重试机制
- 使用断路器模式
- 监控系统健康状态
- 建立备份和恢复策略

## 🔌 API 使用最佳实践

### 1. 认证和授权
```python
# 推荐：使用环境变量存储API密钥
import os
from typing import Dict, Any

class NetPulseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.api_key = os.getenv('NETPULSE_API_KEY')
        if not self.api_key:
            raise ValueError("NETPULSE_API_KEY 环境变量未设置")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

# 不推荐：硬编码API密钥
api_key = "np_sk_1234567890abcdef"  # 不要这样做
```

### 2. 错误处理
```python
import requests
import time
from typing import Dict, Any, Optional

class NetPulseError(Exception):
    def __init__(self, message: str, status_code: int, retry_after: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(self.message)

def api_call_with_retry(url: str, headers: Dict, data: Dict = None, max_retries: int = 3) -> Dict[str, Any]:
    """带重试机制的API调用"""
    for attempt in range(max_retries):
        try:
            if data:
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # 速率限制
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"速率限制，{retry_after}秒后重试...")
                time.sleep(retry_after)
                continue
            elif e.response.status_code >= 500:  # 服务器错误
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"服务器错误，{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
            else:
                raise NetPulseError(e.response.text, e.response.status_code)
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"网络错误，{wait_time}秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                raise NetPulseError(f"网络错误: {e}", 0)
    
    raise NetPulseError("达到最大重试次数", 0)
```

### 3. 批量操作优化
```python
# 推荐：使用批量API
def batch_execute_commands(hostname: str, commands: list) -> Dict[str, Any]:
    """批量执行命令"""
    url = "http://localhost:9000/execute/batch"
    data = {
        "hostname": hostname,
        "commands": commands,
        "timeout": 60,
        "stop_on_error": False
    }
    return api_call_with_retry(url, headers, data)

# 不推荐：循环调用单个API
for command in commands:
    result = api_call_with_retry(f"{base_url}/execute", headers, {
        "hostname": hostname,
        "command": command
    })
```

### 4. 连接复用
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OptimizedNetPulseClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.session = requests.Session()
        
        # 配置连接池
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[500, 502, 503, 504]
            )
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置认证头
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def get_devices(self) -> Dict[str, Any]:
        """获取设备列表"""
        response = self.session.get(f"{self.base_url}/devices")
        response.raise_for_status()
        return response.json()
    
    def close(self):
        """关闭会话"""
        self.session.close()
```

## ⚡ 性能优化最佳实践

### 1. 异步操作
```python
import asyncio
import aiohttp
from typing import List, Dict, Any

class AsyncNetPulseClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def execute_commands_concurrent(self, devices: List[str], command: str) -> List[Dict[str, Any]]:
        """并发执行命令"""
        semaphore = asyncio.Semaphore(10)  # 限制并发数
        
        async def execute_single(hostname: str):
            async with semaphore:
                url = f"{self.base_url}/execute"
                data = {"hostname": hostname, "command": command}
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=self.headers, json=data) as response:
                        return await response.json()
        
        tasks = [execute_single(device) for device in devices]
        return await asyncio.gather(*tasks, return_exceptions=True)

# 使用示例
async def main():
    client = AsyncNetPulseClient("http://localhost:9000", "your_api_key")
    devices = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
    
    results = await client.execute_commands_concurrent(devices, "show version")
    for device, result in zip(devices, results):
        print(f"{device}: {result}")

asyncio.run(main())
```

### 2. 缓存策略
```python
import redis
import json
import hashlib
from typing import Dict, Any, Optional

class CachedNetPulseClient:
    def __init__(self, base_url: str, api_key: str, redis_url: str):
        self.client = NetPulseClient(base_url, api_key)
        self.redis = redis.from_url(redis_url)
    
    def _get_cache_key(self, method: str, params: Dict) -> str:
        """生成缓存键"""
        key_data = f"{method}:{json.dumps(params, sort_keys=True)}"
        return f"netpulse:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get_devices(self, use_cache: bool = True, ttl: int = 300) -> Dict[str, Any]:
        """获取设备列表（带缓存）"""
        if not use_cache:
            return self.client.get_devices()
        
        cache_key = self._get_cache_key("get_devices", {})
        cached_data = self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        data = self.client.get_devices()
        self.redis.setex(cache_key, ttl, json.dumps(data))
        return data
    
    def execute_command(self, hostname: str, command: str, use_cache: bool = False) -> Dict[str, Any]:
        """执行命令（只读命令可缓存）"""
        if use_cache and self._is_readonly_command(command):
            cache_key = self._get_cache_key("execute_command", {
                "hostname": hostname,
                "command": command
            })
            
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        
        result = self.client.execute_command(hostname, command)
        
        if use_cache and self._is_readonly_command(command):
            self.redis.setex(cache_key, 60, json.dumps(result))  # 缓存1分钟
        
        return result
    
    def _is_readonly_command(self, command: str) -> bool:
        """判断是否为只读命令"""
        readonly_commands = ["show", "display", "get", "ping", "traceroute"]
        return any(cmd in command.lower() for cmd in readonly_commands)
```

### 3. 连接池优化
```python
import asyncio
import aiohttp
from typing import Dict, Any

class ConnectionPoolManager:
    def __init__(self, max_connections: int = 100):
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=20,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        self.session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(connector=self.connector)
        return self.session
    
    async def close(self):
        """关闭连接池"""
        if self.session and not self.session.closed:
            await self.session.close()

# 使用示例
async def main():
    pool_manager = ConnectionPoolManager()
    
    try:
        session = await pool_manager.get_session()
        
        # 执行多个请求
        tasks = []
        for i in range(10):
            task = session.get(f"http://localhost:9000/devices")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        for response in responses:
            data = await response.json()
            print(data)
    
    finally:
        await pool_manager.close()
```

## 🔒 安全最佳实践

### 1. API密钥管理
```python
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any

class APIKeyManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def generate_api_key(self, user_id: str, permissions: list, expires_in_days: int = 90) -> str:
        """生成API密钥"""
        # 生成随机密钥
        api_key = f"np_sk_{secrets.token_urlsafe(32)}"
        
        # 计算过期时间
        expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        # 存储密钥信息
        key_data = {
            "user_id": user_id,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used": None
        }
        
        # 使用哈希存储敏感信息
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self.redis.setex(f"api_key:{key_hash}", expires_in_days * 24 * 3600, str(key_data))
        
        return api_key
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """验证API密钥"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_data = self.redis.get(f"api_key:{key_hash}")
        
        if not key_data:
            return {"valid": False, "reason": "key_not_found"}
        
        # 解析密钥数据
        key_info = eval(key_data.decode())
        expires_at = datetime.fromisoformat(key_info["expires_at"])
        
        if datetime.now() > expires_at:
            return {"valid": False, "reason": "key_expired"}
        
        # 更新最后使用时间
        key_info["last_used"] = datetime.now().isoformat()
        self.redis.setex(f"api_key:{key_hash}", 90 * 24 * 3600, str(key_info))
        
        return {"valid": True, "data": key_info}
    
    def revoke_api_key(self, api_key: str) -> bool:
        """撤销API密钥"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return bool(self.redis.delete(f"api_key:{key_hash}"))
```

### 2. 输入验证
```python
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ValidationError:
    field: str
    message: str
    code: str

class InputValidator:
    @staticmethod
    def validate_hostname(hostname: str) -> Optional[ValidationError]:
        """验证主机名"""
        if not hostname:
            return ValidationError("hostname", "主机名不能为空", "missing_required_field")
        
        # IPv4地址验证
        ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if re.match(ipv4_pattern, hostname):
            return None
        
        # 域名验证
        domain_pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        if re.match(domain_pattern, hostname):
            return None
        
        return ValidationError("hostname", "无效的主机名格式", "invalid_format")
    
    @staticmethod
    def validate_port(port: int) -> Optional[ValidationError]:
        """验证端口号"""
        if not isinstance(port, int):
            return ValidationError("port", "端口号必须是整数", "invalid_type")
        
        if port < 1 or port > 65535:
            return ValidationError("port", "端口号必须在1-65535之间", "out_of_range")
        
        return None
    
    @staticmethod
    def validate_command(command: str) -> Optional[ValidationError]:
        """验证命令"""
        if not command or not command.strip():
            return ValidationError("command", "命令不能为空", "missing_required_field")
        
        # 检查危险命令
        dangerous_commands = ["format", "delete", "erase", "reload", "shutdown"]
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return ValidationError("command", f"不允许执行危险命令: {dangerous}", "dangerous_command")
        
        return None

def validate_device_config(config: Dict[str, Any]) -> list:
    """验证设备配置"""
    errors = []
    
    # 验证主机名
    hostname_error = InputValidator.validate_hostname(config.get("hostname"))
    if hostname_error:
        errors.append(hostname_error)
    
    # 验证端口
    port_error = InputValidator.validate_port(config.get("port", 22))
    if port_error:
        errors.append(port_error)
    
    # 验证用户名
    if not config.get("username"):
        errors.append(ValidationError("username", "用户名不能为空", "missing_required_field"))
    
    # 验证密码
    if not config.get("password"):
        errors.append(ValidationError("password", "密码不能为空", "missing_required_field"))
    
    return errors
```

### 3. 访问控制
```python
from enum import Enum
from typing import List, Dict, Any

class Permission(Enum):
    READ_DEVICES = "read_devices"
    WRITE_DEVICES = "write_devices"
    EXECUTE_COMMANDS = "execute_commands"
    ADMIN = "admin"

class AccessControl:
    def __init__(self):
        self.permission_hierarchy = {
            Permission.READ_DEVICES: 1,
            Permission.WRITE_DEVICES: 2,
            Permission.EXECUTE_COMMANDS: 3,
            Permission.ADMIN: 4
        }
    
    def check_permission(self, user_permissions: List[str], required_permission: Permission) -> bool:
        """检查用户权限"""
        if Permission.ADMIN.value in user_permissions:
            return True
        
        if required_permission.value in user_permissions:
            return True
        
        return False
    
    def filter_devices_by_permission(self, devices: List[Dict], user_permissions: List[str]) -> List[Dict]:
        """根据权限过滤设备"""
        if Permission.ADMIN.value in user_permissions:
            return devices
        
        # 这里可以实现更复杂的权限逻辑
        # 例如：用户只能访问特定组的设备
        return devices

# 使用示例
def api_endpoint_with_permission_check(user_permissions: List[str], required_permission: Permission):
    """带权限检查的API端点"""
    access_control = AccessControl()
    
    if not access_control.check_permission(user_permissions, required_permission):
        raise NetPulseError("权限不足", 403)
    
    # 执行API逻辑
    pass
```

## 📊 监控和告警最佳实践

### 1. 健康检查
```python
import asyncio
import aiohttp
from typing import Dict, Any
from datetime import datetime

class HealthChecker:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def check_api_health(self) -> Dict[str, Any]:
        """检查API健康状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health", headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "healthy",
                            "timestamp": datetime.now().isoformat(),
                            "details": data
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "timestamp": datetime.now().isoformat(),
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def check_device_connectivity(self, devices: List[str]) -> Dict[str, Any]:
        """检查设备连接性"""
        results = {}
        
        async def check_single_device(hostname: str):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.api_url}/devices/test",
                        headers=self.headers,
                        json={"hostname": hostname}
                    ) as response:
                        if response.status == 200:
                            return {"status": "connected", "hostname": hostname}
                        else:
                            return {"status": "failed", "hostname": hostname, "error": f"HTTP {response.status}"}
            except Exception as e:
                return {"status": "error", "hostname": hostname, "error": str(e)}
        
        tasks = [check_single_device(device) for device in devices]
        device_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in device_results:
            if isinstance(result, dict):
                results[result["hostname"]] = result
        
        return results

# 使用示例
async def monitor_system():
    checker = HealthChecker("http://localhost:9000", "your_api_key")
    
    # 检查API健康状态
    api_health = await checker.check_api_health()
    print(f"API健康状态: {api_health}")
    
    # 检查设备连接性
    devices = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
    device_health = await checker.check_device_connectivity(devices)
    print(f"设备连接状态: {device_health}")

asyncio.run(monitor_system())
```

### 2. 性能监控
```python
import time
import psutil
import threading
from typing import Dict, Any
from collections import deque

class PerformanceMonitor:
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.api_response_times = deque(maxlen=max_samples)
        self.system_metrics = deque(maxlen=max_samples)
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """开始监控"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_system)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_system(self):
        """系统监控线程"""
        while self.monitoring:
            try:
                # 收集系统指标
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                metrics = {
                    "timestamp": time.time(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "memory_available": memory.available,
                    "disk_free": disk.free
                }
                
                self.system_metrics.append(metrics)
                time.sleep(60)  # 每分钟收集一次
                
            except Exception as e:
                print(f"监控错误: {e}")
                time.sleep(60)
    
    def record_api_call(self, response_time: float):
        """记录API调用响应时间"""
        self.api_response_times.append({
            "timestamp": time.time(),
            "response_time": response_time
        })
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if not self.api_response_times:
            return {"error": "没有API调用数据"}
        
        response_times = [item["response_time"] for item in self.api_response_times]
        
        return {
            "api_calls": {
                "total": len(response_times),
                "avg_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)]
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }

# 使用示例
monitor = PerformanceMonitor()
monitor.start_monitoring()

# 在API调用中记录响应时间
start_time = time.time()
# ... API调用 ...
response_time = time.time() - start_time
monitor.record_api_call(response_time)

# 获取性能统计
stats = monitor.get_performance_stats()
print(f"性能统计: {stats}")
```

### 3. 告警系统
```python
import smtplib
import requests
from email.mime.text import MIMEText
from typing import Dict, Any, List

class AlertSystem:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_history = []
    
    def send_email_alert(self, subject: str, message: str, recipients: List[str]):
        """发送邮件告警"""
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.config['smtp']['from']
            msg['To'] = ', '.join(recipients)
            
            with smtplib.SMTP(self.config['smtp']['host'], self.config['smtp']['port']) as server:
                if self.config['smtp']['use_tls']:
                    server.starttls()
                
                if self.config['smtp']['username']:
                    server.login(self.config['smtp']['username'], self.config['smtp']['password'])
                
                server.send_message(msg)
            
            print(f"邮件告警已发送: {subject}")
            
        except Exception as e:
            print(f"发送邮件告警失败: {e}")
    
    def send_webhook_alert(self, message: str):
        """发送Webhook告警"""
        try:
            response = requests.post(
                self.config['webhook']['url'],
                json={"text": message},
                headers=self.config['webhook']['headers'],
                timeout=10
            )
            response.raise_for_status()
            print(f"Webhook告警已发送: {message}")
            
        except Exception as e:
            print(f"发送Webhook告警失败: {e}")
    
    def check_and_alert(self, metrics: Dict[str, Any]):
        """检查指标并发送告警"""
        alerts = []
        
        # 检查API响应时间
        if metrics.get('api_calls', {}).get('avg_response_time', 0) > 5.0:
            alerts.append("API平均响应时间超过5秒")
        
        # 检查系统资源
        if metrics.get('system', {}).get('cpu_percent', 0) > 80:
            alerts.append("CPU使用率超过80%")
        
        if metrics.get('system', {}).get('memory_percent', 0) > 90:
            alerts.append("内存使用率超过90%")
        
        if metrics.get('system', {}).get('disk_percent', 0) > 85:
            alerts.append("磁盘使用率超过85%")
        
        # 发送告警
        if alerts:
            message = "\n".join(alerts)
            self.send_email_alert("NetPulse系统告警", message, self.config['alerts']['email_recipients'])
            self.send_webhook_alert(message)

# 配置示例
alert_config = {
    "smtp": {
        "host": "smtp.gmail.com",
        "port": 587,
        "use_tls": True,
        "username": "your_email@gmail.com",
        "password": "your_password",
        "from": "your_email@gmail.com"
    },
    "webhook": {
        "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        "headers": {"Content-Type": "application/json"}
    },
    "alerts": {
        "email_recipients": ["admin@example.com", "ops@example.com"]
    }
}

alert_system = AlertSystem(alert_config)
```

## 📚 相关文档

- [配置参数参考](./configuration.md)
- [环境变量参考](./environment-variables.md)
- [错误代码说明](./error-codes.md)
- [日志分析](../troubleshooting/log-analysis.md)

---

<div align="center">

**遵循最佳实践，构建稳定可靠的系统！**

[配置参数 →](./configuration.md) | [日志分析 →](../troubleshooting/log-analysis.md)

</div> 