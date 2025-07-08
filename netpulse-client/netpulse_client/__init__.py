"""
NetPulse Client - 网络设备自动化客户端

提供同步和异步的网络设备操作接口，支持命令执行和配置推送。

核心方法（与API端点对应）：
- exec_command(): 同步执行命令 -> /device/execute
- exec_config(): 同步推送配置 -> /device/execute
- bulk_command(): 同步批量执行命令 -> /device/bulk
- bulk_config(): 同步批量推送配置 -> /device/bulk
- aexec_command(): 异步执行命令 -> /device/execute
- aexec_config(): 异步推送配置 -> /device/execute
- abulk_command(): 异步批量执行命令 -> /device/bulk
- abulk_config(): 异步批量推送配置 -> /device/bulk
- aget_jobs(): 异步获取任务列表 -> /job
- adelete_jobs(): 异步删除任务 -> /job
- aget_workers(): 异步获取Worker列表 -> /worker
- adelete_workers(): 异步删除Worker -> /worker
- ahealth_check(): 异步健康检查 -> /health
- atest_connection(): 异步测试连接 -> /device/test-connection
- arender_template(): 异步渲染模板 -> /template/render
- aparse_template(): 异步解析模板 -> /template/parse
"""

# 核心客户端类
from .async_client import AsyncJobHandle, AsyncNetPulseClient
from .client import NetPulseClient

# 异常类
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    JobError,
    NetPulseError,
    SDKValidationError,
    TimeoutError,
    ValidationError,
)

# 数据模型
# 工具函数
from .models import (
    BatchResult,
    CommandResult,
    ConfigResult,
    ConnectionArgs,  # 主要的连接参数模型
    ConnectionTestResult,
    Device,  # 向后兼容的Device别名
    HealthCheckResult,
    JobInfo,
    WorkerInfo,
    create_batch_device_request,
    create_device_request,
)

__version__ = "0.1.0"

__all__ = [
    # 客户端类
    "NetPulseClient",
    "AsyncNetPulseClient",
    "AsyncJobHandle",
    # 数据模型
    "ConnectionArgs",  # 主要的连接参数模型
    "Device",  # 向后兼容的Device别名
    "CommandResult",
    "ConfigResult",
    "BatchResult",
    "JobInfo",
    "WorkerInfo",
    "HealthCheckResult",
    "ConnectionTestResult",
    # 工具函数
    "create_device_request",
    "create_batch_device_request",
    # 异常类
    "NetPulseError",
    "AuthenticationError",
    "ConnectionError",
    "JobError",
    "TimeoutError",
    "ValidationError",
    "SDKValidationError",
]
