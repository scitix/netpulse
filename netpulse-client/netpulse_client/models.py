"""
NetPulse Client Models

这个模块定义了SDK使用的数据模型。
为了保持与主程序的一致性，我们直接使用主程序的模型，而不是重新定义。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# 定义基本的枚举类型
class DriverName(str, Enum):
    NETMIKO = "netmiko"
    NAPALM = "napalm"
    PYEAPI = "pyeapi"


class QueueStrategy(str, Enum):
    FIFO = "fifo"
    PINNED = "pinned"


# 定义基本的连接参数模型 - 与API中的DriverConnectionArgs保持一致
class ConnectionArgs(BaseModel):
    """设备连接参数模型 - 与API中的DriverConnectionArgs保持一致"""

    device_type: Optional[str] = Field(None, description="设备类型")
    host: Optional[str] = Field(None, description="设备IP地址")
    username: Optional[str] = Field(None, description="设备用户名")
    password: Optional[str] = Field(None, description="设备密码")

    # 允许额外字段，与API保持一致
    model_config = ConfigDict(extra="allow")

    def enforced_field_check(self):
        """
        ConnectionArgs could be auto-filled in Batch APIs.
        After that, we need to manually check.
        """
        if self.host is None:
            raise ValueError("host is None")
        return self


class NetmikoConnectionArgs(ConnectionArgs):
    """Netmiko专用连接参数"""

    pass


class NapalmConnectionArgs(ConnectionArgs):
    """NAPALM专用连接参数"""

    pass


class PyeapiConnectionArg(ConnectionArgs):
    """PyEAPI专用连接参数"""

    pass


# 为了向后兼容，提供Device别名
Device = ConnectionArgs


# 客户端专用模型
class ConnectionConfig(BaseModel):
    """连接配置"""

    endpoint: str = Field(..., description="NetPulse API端点")
    api_key: str = Field(..., description="API密钥")
    timeout: int = Field(300, description="请求超时时间(秒)")
    max_retries: int = Field(3, description="最大重试次数")
    retry_delay: float = Field(1.0, description="重试延迟(秒)")
    verify_ssl: bool = Field(True, description="是否验证SSL证书")


class JobResult(BaseModel):
    """任务结果"""

    type: str = Field(..., description="结果类型")
    retval: Optional[Any] = Field(None, description="返回值")
    error: Optional[Dict[str, Any]] = Field(None, description="错误信息")


# 根据API返回结构定义的结果模型
class ResultModel(BaseModel):
    """API返回的result字段结构"""

    type: int
    retval: Optional[Dict[str, Any]] = None  # 多命令时是dict
    error: Optional[Any] = None


class CommandResult(BaseModel):
    """命令执行结果 - 严格按照API返回结构"""

    id: str
    status: str
    created_at: str
    enqueued_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    queue: str
    worker: Optional[str] = None
    result: Optional[ResultModel] = None
    duration: Optional[float] = None
    queue_time: Optional[float] = None

    @property
    def data(self) -> Dict[str, str]:
        """直接获取所有命令输出，格式: {命令: 输出}"""
        if self.result and self.result.retval:
            return self.result.retval
        return {}

    @property
    def results(self) -> List[str]:
        """获取所有命令输出的列表，格式: [输出1, 输出2, ...]"""
        if self.result and self.result.retval:
            return list(self.result.retval.values())
        return []

    def __getitem__(self, key):
        """支持 result[0] 或 result['display version'] 访问"""
        if self.result and self.result.retval:
            if isinstance(key, int):
                # result[0] 返回第一个命令的输出
                return list(self.result.retval.values())[key]
            else:
                # result['display version'] 返回指定命令的输出
                return self.result.retval.get(key, "")
        return ""


class ConfigResult(BaseModel):
    """配置推送结果 - 严格按照API返回结构"""

    id: str
    status: str
    created_at: str
    enqueued_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    queue: str
    worker: Optional[str] = None
    result: Optional[ResultModel] = None
    duration: Optional[float] = None
    queue_time: Optional[float] = None

    @property
    def data(self) -> Dict[str, str]:
        """直接获取所有命令输出，格式: {命令: 输出}"""
        if self.result and self.result.retval:
            return self.result.retval
        return {}

    @property
    def results(self) -> List[str]:
        """获取所有命令输出的列表，格式: [输出1, 输出2, ...]"""
        if self.result and self.result.retval:
            return list(self.result.retval.values())
        return []

    def __getitem__(self, key):
        """支持 result[0] 或 result['display version'] 访问"""
        if self.result and self.result.retval:
            if isinstance(key, int):
                # result[0] 返回第一个命令的输出
                return list(self.result.retval.values())[key]
            else:
                # result['display version'] 返回指定命令的输出
                return self.result.retval.get(key, "")
        return ""


class BatchResult(BaseModel):
    """批量操作结果"""

    status: str = Field(..., description="执行状态")
    job_id: str = Field(..., description="任务ID")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="设备执行结果列表")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间(秒)")


class JobInfo(BaseModel):
    """任务信息"""

    job_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")


class WorkerInfo(BaseModel):
    """工作节点信息"""

    id: str = Field(..., description="节点ID")
    status: str = Field(..., description="节点状态")
    queue_size: int = Field(..., description="队列大小")
    active_jobs: int = Field(..., description="活跃任务数")
    last_heartbeat: str = Field(..., description="最后心跳时间")


class HealthCheckResult(BaseModel):
    """健康检查结果"""

    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="服务版本")
    uptime: float = Field(..., description="运行时间(秒)")


class ConnectionTestResult(BaseModel):
    """连接测试结果"""

    success: bool = Field(..., description="测试结果")
    message: str = Field(..., description="测试信息")
    connection_time: Optional[float] = Field(None, description="连接时间(秒)")
    error: Optional[str] = Field(None, description="错误信息")


# 状态枚举
class OperationStatus(str, Enum):
    """操作状态"""

    SUBMITTED = "submitted"
    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class JobStatus(str, Enum):
    """任务状态"""

    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"
    DEFERRED = "deferred"
    SCHEDULED = "scheduled"
    STOPPED = "stopped"
    CANCELED = "canceled"


class WorkerState(str, Enum):
    """工作节点状态"""

    BUSY = "busy"
    IDLE = "idle"
    SUSPENDED = "suspended"
    DEAD = "dead"


# 异步任务句柄
@dataclass
class AsyncJobHandle:
    """异步任务句柄"""

    job_id: str
    task_type: str  # command, config, batch_command, batch_config
    device_hosts: List[str]
    submitted_at: float
    timeout: int

    @property
    def is_expired(self) -> bool:
        """检查任务是否已超时"""
        import time

        return time.time() - self.submitted_at > self.timeout


# 工具函数
def create_device_request(
    driver: str,
    connection_args: Dict[str, Any],
    command: Optional[Union[str, List[str]]] = None,
    config: Optional[Union[str, List[str], Dict[str, Any]]] = None,
    driver_args: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """创建设备请求"""
    # 根据驱动类型选择合适的连接参数模型
    try:
        driver_name = DriverName(driver)
        if driver_name == DriverName.NETMIKO:
            conn_args = NetmikoConnectionArgs(**connection_args)
        elif driver_name == DriverName.NAPALM:
            conn_args = NapalmConnectionArgs(**connection_args)
        elif driver_name == DriverName.PYEAPI:
            conn_args = PyeapiConnectionArg(**connection_args)
        else:
            conn_args = ConnectionArgs(**connection_args)
    except ValueError:
        # 如果driver不是有效的DriverName，直接使用ConnectionArgs
        conn_args = ConnectionArgs(**connection_args)

    # 构建请求数据
    request = {
        "driver": driver,
        "connection_args": conn_args.model_dump(),
    }

    if command is not None:
        request["command"] = command
    if config is not None:
        request["config"] = config
    if driver_args is not None:
        request["driver_args"] = driver_args
    if options is not None:
        request["options"] = options

    return request


def create_batch_device_request(
    driver: str,
    devices: List[Dict[str, Any]],
    connection_args: Optional[Dict[str, Any]] = None,
    command: Optional[Union[str, List[str]]] = None,
    config: Optional[Union[str, List[str], Dict[str, Any]]] = None,
    driver_args: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """创建批量设备请求"""
    # 构建请求数据
    request = {
        "driver": driver,
        "devices": devices,
    }

    if connection_args is not None:
        request["connection_args"] = connection_args

    if command is not None:
        request["command"] = command
    if config is not None:
        request["config"] = config
    if driver_args is not None:
        request["driver_args"] = driver_args
    if options is not None:
        request["options"] = options

    return request
