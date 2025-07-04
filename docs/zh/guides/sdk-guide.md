# SDK 指南

## 快速开始

## 认证与初始化

## 设备操作

## 批量操作

## 任务与结果

## 高级用法

## 常见问题

## 概述

NetPulse SDK 提供了 Python 客户端库，让开发者能够方便地集成 NetPulse API 到自己的应用中。SDK 支持同步和异步两种调用方式，适应不同的应用场景。

## 安装

```bash
# 从源码安装（SDK位于netpulse-client目录）
cd netpulse-client
pip install -e .

# 或者直接使用
export PYTHONPATH=/path/to/netpulse-client:$PYTHONPATH
```

### 基础示例

```python
from netpulse_client import NetPulseClient, ConnectionArgs

# 创建客户端
client = NetPulseClient("http://localhost:9000", "your_api_key")

# 定义设备
device = ConnectionArgs(
    host="192.168.1.1",
    username="admin",
    password="admin123",
    device_type="cisco_ios"
)

# 执行命令
result = client.exec_command(device, "show version")
print(f"任务ID: {result.job_id}")
print(f"状态: {result.status}")
```

## SDK 架构

### 核心类和枚举

```python
from enum import Enum
from typing import List, Dict, Any, Optional

class DriverName(str, Enum):
    """支持的驱动类型"""
    NETMIKO = "netmiko"
    NAPALM = "napalm"
    PYEAPI = "pyeapi"

class QueueStrategy(str, Enum):
    """队列策略"""
    PINNED = "pinned"
    FIFO = "fifo"

# 主要数据模型
from netpulse_client import ConnectionArgs, CommandResult, ConfigResult, BatchResult
```

### 主客户端类

```python
from netpulse_client import NetPulseClient, ConnectionArgs

# 创建客户端
client = NetPulseClient(
    endpoint="http://localhost:9000",
    api_key="your_api_key",
    timeout=300
)

# 定义设备
device = ConnectionArgs(
    host="192.168.1.1",
    username="admin",
    password="admin123",
    device_type="cisco_ios",
    port=22,
    timeout=30
)

# 执行命令
result = client.exec_command(device, "show version")
print(f"任务ID: {result.job_id}")
print(f"状态: {result.status}")

# 推送配置
result = client.exec_config(device, "interface GigabitEthernet0/1\n description Test")
print(f"配置推送任务ID: {result.job_id}")
```
        """
        推送配置到设备
        
        Args:
            driver: 驱动类型
            device: 设备信息
            config: 配置内容
            options: 可选配置
            
        Returns:
            API响应结果
        """
        payload = {
            "driver": driver.value,
            "connection_args": self._build_connection_args(device),
            "config": config
        }
        
        if options:
            payload["options"] = options
        
        response = self.session.post(
            f"{self.base_url}/device/execute",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def batch_execute(self,
                     driver: Driver,
                     devices: List[DeviceInfo],
                     command: str | List[str] = None,
                     config: str | Dict[str, Any] = None,
                     global_connection_args: Optional[Dict[str, Any]] = None,
                     options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        批量执行操作
        
        Args:
            driver: 驱动类型
            devices: 设备列表
            command: 要执行的命令（Pull操作）
            config: 要推送的配置（Push操作）
            global_connection_args: 全局连接参数
            options: 可选配置
            
        Returns:
            API响应结果
        """
        # 构建设备列表
        device_list = []
        for device in devices:
            device_dict = self._build_connection_args(device)
            device_list.append(device_dict)
        
        payload = {
            "driver": driver.value,
            "devices": device_list
        }
        
        # 添加全局连接参数
        if global_connection_args:
            payload["connection_args"] = global_connection_args
        
        # 添加操作类型
        if command is not None:
            payload["command"] = command
        elif config is not None:
            payload["config"] = config
        else:
            raise ValueError("必须指定 command 或 config 参数")
        
        # 添加全局连接参数（可选）
        if global_connection_args:
            payload["connection_args"] = global_connection_args
        
        if options:
            payload["options"] = options
        
        response = self.session.post(
            f"{self.base_url}/device/bulk",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def _build_connection_args(self, device: DeviceInfo) -> Dict[str, Any]:
        """构建连接参数"""
        connection_args = {
            "host": device.host,
            "username": device.username,
            "password": device.password,
            "device_type": device.device_type,
            "port": device.port,
            "timeout": device.timeout,
            "secret": device.secret
        }
        
        # 清理None值
        return {k: v for k, v in connection_args.items() if v is not None}
    
    def close(self):
        """关闭客户端会话"""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

## 使用示例

### 1. 单设备操作

```python
from netpulse_sdk import NetPulseClient, Driver, DeviceInfo

# 使用上下文管理器
with NetPulseClient("http://localhost:8000") as client:
    device = DeviceInfo(
        host="192.168.1.1",
        username="admin",
        password="admin123",
        device_type="cisco_ios"
    )
    
    # Pull操作 - 执行命令
    result = client.execute_command(
        driver=Driver.NETMIKO,
        device=device,
        command="show version",
        options={
            "parsing": {
                "name": "textfsm",
                "template": "cisco_ios_show_version.textfsm"
            }
        }
    )
    
    print(f"任务ID: {result['data']['job_id']}")
    
    # Push操作 - 推送配置
    config_result = client.push_config(
        driver=Driver.NETMIKO,
        device=device,
        config=[
            "interface GigabitEthernet0/1",
            "description Configured by SDK",
            "no shutdown"
        ]
    )
    
    print(f"配置任务ID: {config_result['data']['job_id']}")
```

### 2. 批量操作

```python
# 定义多个设备
devices = [
    DeviceInfo(
        host="192.168.1.1",
        username="admin",
        password="admin123",
        device_type="cisco_ios"
    ),
    DeviceInfo(
        host="192.168.1.2",
        username="admin",
        password="admin123",
        device_type="cisco_ios"
    ),
    DeviceInfo(
        host="192.168.1.3",
        username="admin", 
        password="admin123",
        device_type="cisco_nxos"
    )
]

with NetPulseClient() as client:
    # 批量执行命令
    batch_result = client.batch_execute(
        driver=Driver.NETMIKO,
        devices=devices,
        command=["show version", "show ip interface brief"],
        options={
            "parsing": {
                "name": "textfsm",
                "template": "cisco_combined.textfsm"
            },
            "ttl": 600
        }
    )
    
    print(f"批量任务数: {batch_result['data']['total']}")
    
    for job in batch_result['data']['jobs']:
        print(f"设备 {job['host']}: 任务ID {job['job_id']}")
```

### 3. 模板渲染

```python
# 使用Jinja2模板推送配置
interface_data = {
    "interfaces": [
        {"name": "GigabitEthernet0/1", "description": "Server1", "vlan": 100},
        {"name": "GigabitEthernet0/2", "description": "Server2", "vlan": 200}
    ]
}

with NetPulseClient() as client:
    result = client.push_config(
        driver=Driver.NETMIKO,
        device=device,
        config=interface_data,
        options={
            "rendering": {
                "name": "jinja2",
                "template": "interface_batch.j2",
                "context": {
                    "site": "DC01",
                    "rack": "R001"
                }
            }
        }
    )
```

### 4. Webhook回调

```python
# 配置Webhook回调
with NetPulseClient() as client:
    result = client.execute_command(
        driver=Driver.NETMIKO,
        device=device,
        command="show running-config",
        options={
            "webhook": {
                "url": "https://my-server.com/netpulse/callback",
                "method": "POST",
                "headers": {
                    "Authorization": "Bearer my-token",
                    "Content-Type": "application/json"
                },
                "timeout": 15
            }
        }
    )
```

## 异步SDK

### AsyncNetPulseClient

```python
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional

class AsyncNetPulseClient:
    """NetPulse API 异步客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def execute_command(self,
                            driver: Driver,
                            device: DeviceInfo,
                            command: str | List[str],
                            options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """异步执行单个设备命令"""
        payload = {
            "driver": driver.value,
            "connection_args": self._build_connection_args(device),
            "command": command
        }
        
        if options:
            payload["options"] = options
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/device/execute",
                json=payload
            ) as response:
                response.raise_for_status()
                return await response.json()
    
    async def push_config(self,
                         driver: Driver,
                         device: DeviceInfo,
                         config: str | Dict[str, Any],
                         options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """异步推送配置到设备"""
        payload = {
            "driver": driver.value,
            "connection_args": self._build_connection_args(device),
            "config": config
        }
        
        if options:
            payload["options"] = options
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/device/execute",
                json=payload
            ) as response:
                response.raise_for_status()
                return await response.json()
    
    async def batch_execute_concurrent(self,
                                     requests: List[Dict[str, Any]],
                                     max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """并发执行多个请求"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single(request_data):
            async with semaphore:
                if "command" in request_data:
                    return await self.execute_command(**request_data)
                elif "config" in request_data:
                    return await self.push_config(**request_data)
                else:
                    raise ValueError("请求数据必须包含 command 或 config")
        
        tasks = [execute_single(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    def _build_connection_args(self, device: DeviceInfo) -> Dict[str, Any]:
        """构建连接参数"""
        connection_args = {
            "host": device.host,
            "username": device.username,
            "password": device.password,
            "device_type": device.device_type,
            "port": device.port,
            "timeout": device.timeout,
            "secret": device.secret
        }
        
        return {k: v for k, v in connection_args.items() if v is not None}
```

### 异步使用示例

```python
import asyncio

async def async_example():
    client = AsyncNetPulseClient("http://localhost:8000")
    
    # 并发执行多个设备命令
    device_requests = [
        {
            "driver": Driver.NETMIKO,
            "device": DeviceInfo(
                host=f"192.168.1.{i}",
                username="admin",
                password="admin123",
                device_type="cisco_ios"
            ),
            "command": "show version"
        }
        for i in range(1, 11)  # 10台设备
    ]
    
    # 限制并发数为3
    results = await client.batch_execute_concurrent(
        device_requests, 
        max_concurrent=3
    )
    
    # 统计结果
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    failed_count = len(results) - success_count
    
    print(f"成功: {success_count}, 失败: {failed_count}")
    
    # 处理结果
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"设备 192.168.1.{i+1} 执行失败: {result}")
        else:
            print(f"设备 192.168.1.{i+1} 任务ID: {result['data']['job_id']}")

# 运行异步示例
asyncio.run(async_example())
```

## 高级功能

### 1. 重试机制

```python
import time
from requests.exceptions import RequestException

class NetPulseClientWithRetry(NetPulseClient):
    """带重试机制的客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 timeout: int = 30, max_retries: int = 3, backoff_factor: float = 1.0):
        super().__init__(base_url, timeout)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    def execute_command_with_retry(self, *args, **kwargs) -> Dict[str, Any]:
        """带重试的命令执行"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return self.execute_command(*args, **kwargs)
            except RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    sleep_time = self.backoff_factor * (2 ** attempt)
                    print(f"重试第 {attempt + 1} 次，等待 {sleep_time} 秒...")
                    time.sleep(sleep_time)
                else:
                    raise last_exception
        
        raise last_exception

# 使用示例
with NetPulseClientWithRetry(max_retries=3, backoff_factor=1.5) as client:
    result = client.execute_command_with_retry(
        driver=Driver.NETMIKO,
        device=device,
        command="show version"
    )
```

### 2. 连接池管理

```python
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

class NetPulseClientWithPool(NetPulseClient):
    """使用连接池的客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 timeout: int = 30, pool_connections: int = 10, pool_maxsize: int = 20):
        super().__init__(base_url, timeout)
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # 配置HTTP适配器
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
```

### 3. 日志记录

```python
import logging
from functools import wraps

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_api_calls(func):
    """API调用日志装饰器"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 脱敏处理
        safe_kwargs = kwargs.copy()
        if 'device' in safe_kwargs:
            device = safe_kwargs['device']
            if hasattr(device, 'password'):
                device.password = "***"
            if hasattr(device, 'secret'):
                device.secret = "***"
        
        logger.info(f"调用 {func.__name__}: args={args}, kwargs={safe_kwargs}")
        
        try:
            result = func(self, *args, **kwargs)
            logger.info(f"{func.__name__} 成功")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} 失败: {e}")
            raise
    
    return wrapper

class NetPulseClientWithLogging(NetPulseClient):
    """带日志记录的客户端"""
    
    @log_api_calls
    def execute_command(self, *args, **kwargs):
        return super().execute_command(*args, **kwargs)
    
    @log_api_calls
    def push_config(self, *args, **kwargs):
        return super().push_config(*args, **kwargs)
    
    @log_api_calls
    def batch_execute(self, *args, **kwargs):
        return super().batch_execute(*args, **kwargs)
```

## 最佳实践

### 1. 环境变量配置

```python
import os
from netpulse_sdk import NetPulseClient, DeviceInfo

# 使用环境变量
def create_device_from_env(host: str) -> DeviceInfo:
    return DeviceInfo(
        host=host,
        username=os.getenv("DEVICE_USERNAME"),
        password=os.getenv("DEVICE_PASSWORD"),
        device_type=os.getenv("DEVICE_TYPE", "cisco_ios")
    )

# 使用示例
device = create_device_from_env("192.168.1.1")
```

### 2. 配置管理

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class NetPulseConfig:
    """SDK配置类"""
    base_url: str = "http://localhost:8000"
    timeout: int = 30
    max_retries: int = 3
    default_options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.default_options is None:
            self.default_options = {}

def create_configured_client(config: NetPulseConfig) -> NetPulseClient:
    """根据配置创建客户端"""
    return NetPulseClientWithRetry(
        base_url=config.base_url,
        timeout=config.timeout,
        max_retries=config.max_retries
    )
```

### 3. 错误处理

```python
from requests.exceptions import RequestException, HTTPError, Timeout

def handle_netpulse_errors(func):
    """NetPulse错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            if e.response.status_code == 400:
                logger.error("请求参数错误")
            elif e.response.status_code == 422:
                logger.error("设备不支持或参数验证失败")
            elif e.response.status_code == 500:
                logger.error("服务器内部错误")
            raise
        except Timeout:
            logger.error("请求超时")
            raise
        except RequestException as e:
            logger.error(f"网络请求异常: {e}")
            raise
    
    return wrapper
```

## 批量操作高级功能

### 1. 批量操作工具类

```python
from collections import defaultdict
from typing import List, Dict, Any, Iterator, Tuple
import asyncio
import aiohttp
from tqdm import tqdm
import time

class BatchOperationHelper:
    """批量操作辅助工具类"""
    
    def __init__(self, client: NetPulseClient):
        self.client = client
    
    def batch_by_device_type(self, devices: List[DeviceInfo], 
                           batch_size: int = 50) -> Iterator[Tuple[str, List[DeviceInfo]]]:
        """按设备类型和批次大小分组处理"""
        # 按设备类型分组
        grouped = defaultdict(list)
        for device in devices:
            device_type = device.device_type or 'unknown'
            grouped[device_type].append(device)
        
        # 每组按批次大小分割
        for device_type, device_list in grouped.items():
            for i in range(0, len(device_list), batch_size):
                batch = device_list[i:i + batch_size]
                yield device_type, batch
    
    def execute_with_progress(self, operations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """带进度条的批次执行"""
        results = []
        with tqdm(total=len(operations), desc="执行批次") as pbar:
            for i, operation in enumerate(operations):
                try:
                    result = self.client.batch_execute(**operation)
                    results.append(result)
                    pbar.set_description(f"完成批次 {i+1}/{len(operations)}")
                except Exception as e:
                    results.append({"error": str(e)})
                    pbar.set_description(f"批次 {i+1} 失败: {str(e)}")
                finally:
                    pbar.update(1)
        
        return results
    
    def execute_with_retry(self, operation: Dict[str, Any], 
                          max_retries: int = 3) -> Dict[str, Any]:
        """带重试的批量执行"""
        for attempt in range(max_retries):
            try:
                return self.client.batch_execute(**operation)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)  # 指数退避
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    def smart_batch_execute(self, driver: Driver, devices: List[DeviceInfo],
                          command: str = None, config: str = None,
                          global_connection_args: Dict[str, Any] = None,
                          batch_size: int = 50, 
                          max_retries: int = 3) -> List[Dict[str, Any]]:
        """智能批量执行：自动分组、进度跟踪、失败重试"""
        results = []
        
        # 按设备类型分组
        for device_type, batch in self.batch_by_device_type(devices, batch_size):
            operation = {
                "driver": driver,
                "devices": batch,
                "global_connection_args": global_connection_args or {"device_type": device_type},
                "command": command,
                "config": config,
                "options": {"ttl": 600}  # 批量操作使用较长超时
            }
            
            try:
                result = self.execute_with_retry(operation, max_retries)
                results.append(result)
            except Exception as e:
                results.append({
                    "error": str(e),
                    "device_type": device_type,
                    "device_count": len(batch)
                })
        
        return results
```

### 2. 异步批量操作

```python
import asyncio
import aiohttp
from typing import List, Dict, Any

class AsyncBatchOperationHelper:
    """异步批量操作辅助工具"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    async def execute_batch_async(self, operations: List[Dict[str, Any]], 
                                max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """异步执行多个批次，控制并发数"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single_batch(session, operation):
            async with semaphore:
                try:
                    async with session.post(
                        f"{self.base_url}/device/bulk", 
                        json=operation,
                        timeout=aiohttp.ClientTimeout(total=300)
                    ) as response:
                        return await response.json()
                except Exception as e:
                    return {"error": str(e)}
        
        async with aiohttp.ClientSession() as session:
            tasks = [execute_single_batch(session, op) for op in operations]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
    
    async def parallel_device_operations(self, devices: List[DeviceInfo],
                                       driver: Driver, command: str = None,
                                       config: str = None,
                                       max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """并行执行多个单设备操作"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_single_device(session, device):
            async with semaphore:
                payload = {
                    "driver": driver.value,
                    "connection_args": {
                        "host": device.host,
                        "username": device.username,
                        "password": device.password,
                        "device_type": device.device_type
                    }
                }
                
                if command:
                    payload["command"] = command
                if config:
                    payload["config"] = config
                
                try:
                    async with session.post(
                        f"{self.base_url}/device/execute",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=120)
                    ) as response:
                        result = await response.json()
                        result["device_host"] = device.host
                        return result
                except Exception as e:
                    return {"error": str(e), "device_host": device.host}
        
        async with aiohttp.ClientSession() as session:
            tasks = [execute_single_device(session, device) for device in devices]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
```

### 3. 批量操作结果分析

```python
from typing import List, Dict, Any, Tuple

class BatchResultAnalyzer:
    """批量操作结果分析器"""
    
    @staticmethod
    def analyze_batch_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析批量操作结果"""
        total_jobs = 0
        succeeded_jobs = 0
        failed_jobs = 0
        failed_devices = []
        
        for result in results:
            if "error" in result:
                failed_jobs += 1
                continue
            
            if "data" in result and "succeeded" in result["data"]:
                succeeded_count = len(result["data"]["succeeded"])
                failed_count = len(result["data"]["failed"])
                
                total_jobs += succeeded_count + failed_count
                succeeded_jobs += succeeded_count
                failed_jobs += failed_count
                
                failed_devices.extend(result["data"]["failed"])
        
        return {
            "total_jobs": total_jobs,
            "succeeded_jobs": succeeded_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": succeeded_jobs / total_jobs if total_jobs > 0 else 0,
            "failed_devices": failed_devices
        }
    
    @staticmethod
    def generate_summary_report(analysis: Dict[str, Any]) -> str:
        """生成汇总报告"""
        report = f"""
批量操作执行报告
================
总任务数: {analysis['total_jobs']}
成功任务: {analysis['succeeded_jobs']}
失败任务: {analysis['failed_jobs']}
成功率: {analysis['success_rate']:.2%}

失败设备列表:
{chr(10).join(f"- {device}" for device in analysis['failed_devices'])}
        """
        return report.strip()
```

### 4. 使用示例

```python
# 基础批量操作
def basic_batch_example():
    client = NetPulseClient()
    helper = BatchOperationHelper(client)
    
    devices = [
        DeviceInfo(host="192.168.1.1", device_type="cisco_ios"),
        DeviceInfo(host="192.168.1.2", device_type="cisco_ios"),
        DeviceInfo(host="192.168.1.3", device_type="cisco_nxos"),
    ]
    
    # 智能批量执行
    results = helper.smart_batch_execute(
        driver=Driver.NETMIKO,
        devices=devices,
        command="show version",
        global_connection_args={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    # 分析结果
    analyzer = BatchResultAnalyzer()
    analysis = analyzer.analyze_batch_results(results)
    print(analyzer.generate_summary_report(analysis))

# 异步批量操作
async def async_batch_example():
    helper = AsyncBatchOperationHelper()
    
    devices = [
        DeviceInfo(host="192.168.1.1", device_type="cisco_ios"),
        DeviceInfo(host="192.168.1.2", device_type="cisco_ios"),
    ]
    
    # 并行设备操作
    results = await helper.parallel_device_operations(
        devices=devices,
        driver=Driver.NETMIKO,
        command="show version"
    )
    
    for result in results:
        if "error" in result:
            print(f"设备 {result['device_host']} 失败: {result['error']}")
        else:
            print(f"设备 {result['device_host']} 成功: 任务ID {result['data']['id']}")

# 大规模批量操作
def large_scale_batch_example():
    client = NetPulseClient()
    helper = BatchOperationHelper(client)
    
    # 模拟大量设备
    devices = [
        DeviceInfo(host=f"192.168.{i//254 + 1}.{i%254 + 1}", device_type="cisco_ios")
        for i in range(1000)
    ]
    
    # 分批执行
    all_results = []
    for device_type, batch in helper.batch_by_device_type(devices, batch_size=50):
        operation = {
            "driver": Driver.NETMIKO,
            "devices": batch,
            "global_connection_args": {
                "username": "admin",
                "password": "admin123",
                "device_type": device_type
            },
            "command": "show version",
            "options": {"ttl": 1200}  # 20分钟超时
        }
        
        try:
            result = helper.execute_with_retry(operation, max_retries=3)
            all_results.append(result)
        except Exception as e:
            print(f"批次失败: {e}")
    
    # 分析总体结果
    analyzer = BatchResultAnalyzer()
    analysis = analyzer.analyze_batch_results(all_results)
    print(analyzer.generate_summary_report(analysis))
```

## 故障排查

### 常见问题

1. **连接超时**
   ```python
   # 增加超时时间
   client = NetPulseClient(timeout=60)
   ```

2. **SSL证书验证失败**
   ```python
   # 禁用SSL验证（仅开发环境）
   import urllib3
   urllib3.disable_warnings()
   
   client.session.verify = False
   ```

3. **大批量操作内存不足**
   ```python
   # 使用批量操作工具类
   helper = BatchOperationHelper(client)
   results = helper.smart_batch_execute(
       driver=Driver.NETMIKO,
       devices=devices,
       command="show version",
       batch_size=25  # 减小批次大小
   )
   ```

### 调试技巧

```python
# 启用详细日志
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)

# 查看原始请求
import http.client
http.client.HTTPConnection.debuglevel = 1
```

通过以上SDK使用指南，开发者可以快速上手NetPulse Python SDK，实现高效的网络设备自动化管理。SDK提供了丰富的批量操作功能，能够满足从小规模到大规模设备管理的各种需求。 