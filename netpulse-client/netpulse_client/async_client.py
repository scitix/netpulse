#!/usr/bin/env python3
"""
NetPulse 异步客户端

使用httpx提供统一的异步HTTP客户端接口
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from urllib.parse import urljoin

import httpx
from pydantic import ValidationError

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    JobError,
    NetPulseError,
    TimeoutError,
    ValidationError as SDKValidationError,
)
from .models import (
    ConnectionConfig,
    ConnectionArgs,
    CommandResult,
    ConfigResult,
    BatchResult,
    JobInfo,
    WorkerInfo,
    HealthCheckResult,
    ConnectionTestResult,
    OperationStatus,
    JobStatus,
    WorkerState,
    AsyncJobHandle,
    create_device_request,
    create_batch_device_request,
)

# 配置日志
logger = logging.getLogger(__name__)

class AsyncNetPulseClient:
    """NetPulse 异步客户端"""
    
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        driver: str = "netmiko",
        timeout: int = 300,
        max_concurrent: int = 100,
        verify_ssl: bool = True,
    ):
        """
        初始化异步客户端
        
        Args:
            endpoint: NetPulse API端点
            api_key: API密钥
            driver: 驱动类型
            timeout: 请求超时时间(秒)
            max_concurrent: 最大并发连接数
            verify_ssl: 是否验证SSL证书
        """
        self.config = ConnectionConfig(
            endpoint=endpoint.rstrip('/'),
            api_key=api_key,
            timeout=timeout,
            max_retries=3,
            retry_delay=1.0,
            verify_ssl=verify_ssl,
        )
        self.driver = driver
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
            "User-Agent": "NetPulse-Client/0.1.0",
        }
        
        # 异步客户端配置
        self.limits = httpx.Limits(
            max_connections=max_concurrent,
            max_keepalive_connections=20,
        )
        
        # 任务管理
        self._active_jobs: Dict[str, AsyncJobHandle] = {}
        self._job_callbacks: Dict[str, List[Callable]] = {}
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def _ensure_client(self):
        """确保客户端已初始化"""
        if self._client is None:
            timeout = httpx.Timeout(self.config.timeout)
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=self.limits,
                verify=self.config.verify_ssl,
                headers=self.headers,
            )
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _build_url(self, path: str) -> str:
        """构建完整URL"""
        return urljoin(self.config.endpoint, path)
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """处理HTTP响应"""
        try:
            data = response.json()
        except Exception as e:
            raise SDKValidationError(f"Invalid JSON response: {e}")
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 403:
            raise AuthenticationError("Insufficient permissions")
        elif response.status_code >= 500:
            raise ConnectionError(f"Server error: {response.status_code}")
        
        return data
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """发送异步HTTP请求"""
        await self._ensure_client()
        
        try:
            response = await self._client.request(method, url, **kwargs)
            response.raise_for_status()
            return self._handle_response(response)
        except httpx.TimeoutException:
            raise TimeoutError("Request timeout")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif e.response.status_code == 403:
                raise AuthenticationError("Insufficient permissions")
            else:
                raise ConnectionError(f"HTTP error: {e.response.status_code}")
        except httpx.ConnectError as e:
            raise ConnectionError(f"Request failed: {e}")
    
    async def _submit_job(self, url: str, payload: Dict[str, Any]) -> str:
        """提交任务并返回job_id"""
        data = await self._make_request("POST", url, json=payload)
        
        if data.get("code") != 0:
            raise JobError(f"API error: {data.get('message')}")
        
        return data["data"]["id"]
    
    # ========== 核心方法 ==========
    
    async def execute(
        self,
        device: ConnectionArgs,
        command: Optional[Union[str, List[str]]] = None,
        config: Optional[Union[str, List[str]]] = None,
        parse_with: Optional[str] = None,
        save: bool = False,
        dry_run: bool = False,
        wait: bool = True,
        timeout: int = 300,
        callback: Optional[Callable] = None,
    ) -> Union[CommandResult, ConfigResult, AsyncJobHandle]:
        """
        在设备上执行操作（命令或配置）- 对应 /device/execute 端点
        
        Args:
            device: 目标设备
            command: 要执行的命令（Pull操作）
            config: 要推送的配置（Push操作）
            parse_with: 解析器类型
            save: 是否保存配置
            dry_run: 是否为干运行模式
            wait: 是否等待完成
            timeout: 超时时间
            callback: 完成回调函数
            
        Returns:
            CommandResult/ConfigResult: 如果wait=True
            AsyncJobHandle: 如果wait=False
        """
        if not command and not config:
            raise ValueError("必须指定 command 或 config 参数")
        if command and config:
            raise ValueError("command 和 config 参数不能同时指定")
        
        # 构建设备连接参数
        connection_args = {
            "host": device.host,
            "username": device.username,
            "password": device.password,
            "device_type": device.device_type,
        }
        if device.port:
            connection_args["port"] = device.port
        if device.timeout:
            connection_args["timeout"] = device.timeout
        
        # 构建驱动参数
        driver_args = {}
        if save:
            driver_args["save"] = save
        if dry_run:
            driver_args["dry_run"] = dry_run
        
        # 构建请求选项
        options = {
            "queue_strategy": "pinned",
            "ttl": timeout,
        }
        
        if parse_with:
            options["parsing"] = {
                "name": parse_with,
                "template": f"file:///templates/{(command or config).replace(' ', '_') if isinstance((command or config), str) else (command or config)[0].replace(' ', '_')}.{parse_with}",
            }
        
        # 创建请求
        if command:
            request_data = create_device_request(
                driver="netmiko",
                connection_args=connection_args,
                command=command,
                driver_args=driver_args if driver_args else None,
                options=options,
            )
            operation_type = "command"
        else:
            request_data = create_device_request(
                driver="netmiko",
                connection_args=connection_args,
                config=config,
                driver_args=driver_args if driver_args else None,
                options=options,
            )
            operation_type = "config"
        
        # 提交任务
        job_id = await self._submit_job(
            self._build_url("/device/execute"),
            request_data.model_dump(exclude_none=True)
        )
        
        if not wait:
            # 创建任务句柄
            handle = AsyncJobHandle(
                job_id=job_id,
                task_type=f"single_{operation_type}",
                device_hosts=[device.host],
                submitted_at=time.time(),
                timeout=timeout
            )
            
            # 注册任务
            self._active_jobs[job_id] = handle
            if callback:
                self._job_callbacks[job_id] = [callback]
            
            return handle
        
        # 等待任务完成
        result = await self._wait_for_job(job_id, timeout)
        
        if command:
            return CommandResult(
                status=OperationStatus.SUCCESS if result["status"] == "completed" else OperationStatus.FAILED,
                data=result.get("result", {}).get("retval"),
                job_id=job_id,
                device_host=device.host,
                error=result.get("error"),
                execution_time=result.get("execution_time"),
            )
        else:
            return ConfigResult(
                status=OperationStatus.SUCCESS if result["status"] == "completed" else OperationStatus.FAILED,
                job_id=job_id,
                device_host=device.host,
                error=result.get("error"),
                execution_time=result.get("execution_time"),
            )
    
    async def bulk(
        self,
        devices: List[ConnectionArgs],
        command: Optional[Union[str, List[str]]] = None,
        config: Optional[Union[str, List[str]]] = None,
        parse_with: Optional[str] = None,
        save: bool = False,
        dry_run: bool = False,
        timeout: int = 600,
        callback: Optional[Callable] = None,
    ) -> AsyncJobHandle:
        """
        批量设备操作 - 对应 /device/bulk 端点
        
        Args:
            devices: 设备列表
            command: 要执行的命令（Pull操作）
            config: 要推送的配置（Push操作）
            parse_with: 解析器类型
            save: 是否保存配置
            dry_run: 是否为干运行模式
            timeout: 超时时间
            callback: 完成回调函数
            
        Returns:
            AsyncJobHandle: 异步任务句柄
        """
        if not command and not config:
            raise ValueError("必须指定 command 或 config 参数")
        if command and config:
            raise ValueError("command 和 config 参数不能同时指定")
        
        if not devices:
            raise ValueError("设备列表不能为空")
        
        # 构建设备列表
        device_list = []
        device_hosts = []
        for device in devices:
            device_dict = {
                "host": device.host,
                "username": device.username,
                "password": device.password,
            }
            if device.port:
                device_dict["port"] = device.port
            if device.timeout:
                device_dict["timeout"] = device.timeout
            device_list.append(device_dict)
            device_hosts.append(device.host)
        
        # 构建连接参数
        connection_args = {
            "device_type": devices[0].device_type,
            "timeout": 30,
            "keepalive": 120,
        }
        
        # 构建驱动参数
        driver_args = {}
        if save:
            driver_args["save"] = save
        if dry_run:
            driver_args["dry_run"] = dry_run
        
        # 构建请求选项
        options = {
            "queue_strategy": "pinned",
            "ttl": timeout,
        }
        
        if parse_with:
            options["parsing"] = {
                "name": parse_with,
                "template": f"file:///templates/{(command or config).replace(' ', '_') if isinstance((command or config), str) else (command or config)[0].replace(' ', '_')}.{parse_with}",
            }
        
        # 创建请求
        if command:
            request_data = create_batch_device_request(
                driver="netmiko",
                devices=device_list,
                connection_args=connection_args,
                command=command,
                driver_args=driver_args if driver_args else None,
                options=options,
            )
            operation_type = "batch_command"
        else:
            request_data = create_batch_device_request(
                driver="netmiko",
                devices=device_list,
                connection_args=connection_args,
                config=config,
                driver_args=driver_args if driver_args else None,
                options=options,
            )
            operation_type = "batch_config"
        
        # 提交任务
        job_id = await self._submit_job(
            self._build_url("/device/bulk"),
            request_data.model_dump(exclude_none=True)
        )
        
        # 创建任务句柄
        handle = AsyncJobHandle(
            job_id=job_id,
            task_type=operation_type,
            device_hosts=device_hosts,
            submitted_at=time.time(),
            timeout=timeout
        )
        
        # 注册任务
        self._active_jobs[job_id] = handle
        if callback:
            self._job_callbacks[job_id] = [callback]
        
        return handle
    
    # ========== 任务管理方法 ==========
    
    async def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """获取任务状态"""
        try:
            data = await self._make_request(
                "GET",
                self._build_url("/job"),
                params={"id": job_id}
            )
            
            if data.get("code") != 0:
                raise JobError(f"API error: {data.get('message')}")
            
            job_list = data.get("data", [])
            if not job_list:
                return None
            
            job_data = job_list[0]
            return JobInfo(
                job_id=job_data.get("id", ""),
                status=job_data.get("status", ""),
                queue=job_data.get("queue", ""),
                node=job_data.get("worker", ""),
                created_at=job_data.get("created_at"),
                started_at=job_data.get("started_at"),
                finished_at=job_data.get("ended_at"),
                result=job_data.get("result"),
            )
            
        except Exception as e:
            raise JobError(f"Failed to get job status: {e}")
    
    async def wait_for_job(
        self, 
        handle: AsyncJobHandle, 
        poll_interval: float = 0.4
    ) -> Union[CommandResult, ConfigResult]:
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < handle.timeout:
            try:
                job_info = await self.get_job_status(handle.job_id)
                
                if not job_info:
                    raise JobError(f"Job {handle.job_id} not found")
                
                if job_info.status in ["finished", "failed"]:
                    # 任务完成，执行回调
                    if handle.job_id in self._job_callbacks:
                        for callback in self._job_callbacks[handle.job_id]:
                            try:
                                await callback(job_info) if asyncio.iscoroutinefunction(callback) else callback(job_info)
                            except Exception as e:
                                print(f"Callback error: {e}")
                    
                    # 从活动任务中移除
                    if handle.job_id in self._active_jobs:
                        del self._active_jobs[handle.job_id]
                    if handle.job_id in self._job_callbacks:
                        del self._job_callbacks[handle.job_id]
                    
                    # 根据任务类型返回结果
                    if handle.task_type == "command":
                        return CommandResult(
                            status=job_info.status,
                            data=job_info.result.get("retval") if job_info.result else None,
                            job_id=handle.job_id,
                            device_host=handle.device_hosts[0] if handle.device_hosts else "unknown",
                            error=job_info.result.get("error") if job_info.result else None,
                            execution_time=time.time() - start_time,
                        )
                    else:  # config
                        return ConfigResult(
                            status=job_info.status,
                            job_id=handle.job_id,
                            device_host=handle.device_hosts[0] if handle.device_hosts else "unknown",
                            error=job_info.result.get("error") if job_info.result else None,
                            execution_time=time.time() - start_time,
                        )
                
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                raise JobError(f"Failed to wait for job: {e}")
        
        raise TimeoutError(f"Job {handle.job_id} timed out after {handle.timeout} seconds")
    
    async def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        try:
            data = await self._make_request(
                "DELETE",
                self._build_url("/job"),
                params={"id": job_id}
            )
            
            # 从活动任务中移除
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]
            if job_id in self._job_callbacks:
                del self._job_callbacks[job_id]
            
            return data.get("code") == 0
            
        except Exception as e:
            raise JobError(f"Failed to cancel job: {e}")
    
    # ========== 工作节点管理方法 ==========
    
    async def get_workers(
        self,
        queue: Optional[str] = None,
        node: Optional[str] = None,
    ) -> List[WorkerInfo]:
        """获取工作节点列表"""
        params = {}
        if queue:
            params["q_name"] = queue
        if node:
            params["node"] = node
        
        try:
            data = await self._make_request(
                "GET",
                self._build_url("/worker"),
                params=params
            )
            
            if data.get("code") != 0:
                raise JobError(f"API error: {data.get('message')}")
            
            workers = []
            for worker_data in data.get("data", []):
                workers.append(WorkerInfo(
                    name=worker_data.get("name", ""),
                    status=worker_data.get("status", ""),
                    pid=worker_data.get("pid"),
                    hostname=worker_data.get("hostname"),
                    queues=worker_data.get("queues"),
                    last_heartbeat=worker_data.get("last_heartbeat"),
                    birth_at=worker_data.get("birth_at"),
                    successful_job_count=worker_data.get("successful_job_count"),
                    failed_job_count=worker_data.get("failed_job_count"),
                ))
            
            return workers
            
        except Exception as e:
            raise JobError(f"Failed to get workers: {e}")
    
    # ========== 系统管理方法 ==========
    
    async def health_check(self) -> HealthCheckResult:
        """健康检查"""
        try:
            data = await self._make_request("GET", self._build_url("/health"))
            
            return HealthCheckResult(
                status=data.get("status", "unknown"),
                version=data.get("version"),
                uptime=data.get("uptime"),
            )
            
        except Exception as e:
            raise ConnectionError(f"Health check failed: {e}")
    
    async def test_connection(
        self,
        device: ConnectionArgs,
        timeout: int = 30,
    ) -> ConnectionTestResult:
        """测试设备连接"""
        try:
            # 构建设备连接参数
            connection_args = {
                "host": device.host,
                "username": device.username,
                "password": device.password,
                "device_type": device.device_type,
            }
            if device.port:
                connection_args["port"] = device.port
            if device.timeout:
                connection_args["timeout"] = device.timeout
            
            # 创建连接测试请求
            request_data = create_device_request(
                driver="netmiko",
                connection_args=connection_args,
                command="show version",  # 使用简单命令测试连接
                options={"ttl": timeout},
            )
            
            data = await self._make_request(
                "POST",
                self._build_url("/device/test"),
                json=request_data.model_dump(exclude_none=True)
            )
            
            if data.get("code") != 0:
                return ConnectionTestResult(
                    success=False,
                    message=data.get("message", "Connection test failed"),
                    details=data.get("data"),
                )
            
            return ConnectionTestResult(
                success=True,
                message="Connection successful",
                details=data.get("data"),
            )
            
        except Exception as e:
            return ConnectionTestResult(
                success=False,
                message=f"Connection test failed: {e}",
                details=None,
            )
    
    # ========== 任务监控方法 ==========
    
    def get_active_jobs(self) -> List[AsyncJobHandle]:
        """获取活动任务列表"""
        return list(self._active_jobs.values())
    
    def get_job_count(self) -> int:
        """获取活动任务数量"""
        return len(self._active_jobs)
    
    async def monitor_jobs(self, interval: float = 5.0):
        """监控所有活动任务"""
        while self._active_jobs:
            completed_jobs = []
            
            for job_id, handle in self._active_jobs.items():
                if handle.is_expired:
                    completed_jobs.append(job_id)
                    continue
                
                try:
                    job_info = await self.get_job_status(job_id)
                    if job_info and job_info.status in ["finished", "failed"]:
                        completed_jobs.append(job_id)
                        
                        # 执行回调
                        if job_id in self._job_callbacks:
                            for callback in self._job_callbacks[job_id]:
                                try:
                                    await callback(job_info) if asyncio.iscoroutinefunction(callback) else callback(job_info)
                                except Exception as e:
                                    print(f"Callback error: {e}")
                except Exception as e:
                    print(f"Error monitoring job {job_id}: {e}")
            
            # 移除已完成的任务
            for job_id in completed_jobs:
                if job_id in self._active_jobs:
                    del self._active_jobs[job_id]
                if job_id in self._job_callbacks:
                    del self._job_callbacks[job_id]
            
            await asyncio.sleep(interval)
    
    def add_job_callback(self, job_id: str, callback: Callable):
        """添加任务回调函数"""
        if job_id not in self._job_callbacks:
            self._job_callbacks[job_id] = []
        self._job_callbacks[job_id].append(callback)
    
    # ========== 兼容性方法 ==========
    
    async def execute_command(self, device: ConnectionArgs, command: Union[str, List[str]], **kwargs) -> Union[CommandResult, AsyncJobHandle]:
        """兼容性方法：执行命令"""
        return await self.execute(device, command=command, **kwargs)
    
    async def push_config(self, device: ConnectionArgs, config: Union[str, List[str]], **kwargs) -> Union[ConfigResult, AsyncJobHandle]:
        """兼容性方法：推送配置"""
        return await self.execute(device, config=config, **kwargs)
    
    async def batch_execute(self, devices: List[ConnectionArgs], command: Union[str, List[str]], **kwargs) -> AsyncJobHandle:
        """兼容性方法：批量执行命令"""
        return await self.bulk(devices, command=command, **kwargs)
    
    async def batch_config(self, devices: List[ConnectionArgs], config: Union[str, List[str]], **kwargs) -> AsyncJobHandle:
        """兼容性方法：批量推送配置"""
        return await self.bulk(devices, config=config, **kwargs)

    async def _wait_for_result_with_progressive_retry(self, job_id: str,
                                                    initial_delay: float = 0.4,
                                                    max_total_time: float = 120.0) -> Dict:
        """
        异步激进递进式重试等待任务结果
        
        轮询策略：
        - 初始延迟: 0.4秒
        - 递增步长序列: 0.1s -> 0.2s -> 0.3s -> 0.5s -> 1.5s -> 2.5s -> 4.0s -> 6.0s -> 9.0s -> 13.5s -> 20.0s -> 30.0s
        - 轮询间隔: 0.4s -> 0.5s -> 0.7s -> 1.0s -> 1.5s -> 3.0s -> 5.5s -> 9.5s -> 15.5s -> 24.5s -> 37.5s -> 57.5s
        - 最大间隔: 30秒
        - 最大总时长: 120秒
        
        示例轮询序列：
        第1次: 0.4s (初始)
        第2次: 0.5s (0.4s + 0.1s)
        第3次: 0.7s (0.5s + 0.2s) 
        第4次: 1.0s (0.7s + 0.3s)
        第5次: 1.5s (1.0s + 0.5s)
        第6次: 3.0s (1.5s + 1.5s)
        第7次: 5.5s (3.0s + 2.5s)
        第8次: 9.5s (5.5s + 4.0s)
        第9次: 15.5s (9.5s + 6.0s)
        第10次: 24.5s (15.5s + 9.0s)
        第11次: 37.5s (24.5s + 13.5s) -> 限制为30s
        第12次: 57.5s (30s + 20.0s) -> 限制为30s
        ...
        """
        delay = initial_delay
        total_elapsed = 0.0
        attempt = 0
        
        # 定义递增步长序列
        step_sequence = [0.1, 0.2, 0.3, 0.5, 1.5, 2.5, 4.0, 6.0, 9.0, 13.5, 20.0, 30.0]
        step_index = 0
        
        while total_elapsed < max_total_time:
            try:
                result = await self._make_request("GET", self._build_url("/job"), params={"id": job_id})
                
                if result.get("code") == 0 and result.get("data"):
                    job_data = result["data"][0] if isinstance(result["data"], list) else result["data"]
                    status = job_data.get("status")
                    
                    if status in ["finished", "failed"]:
                        logger.info(f"任务 {job_id} 完成，总耗时: {total_elapsed:.2f}秒，轮询次数: {attempt}")
                        return result
                    elif status == "queued":
                        logger.info(f"任务 {job_id} 排队中... (第{attempt}次轮询，已耗时{total_elapsed:.2f}秒)")
                    elif status == "started":
                        logger.info(f"任务 {job_id} 执行中... (第{attempt}次轮询，已耗时{total_elapsed:.2f}秒)")
                
                # 激进递进式延迟
                await asyncio.sleep(delay)
                total_elapsed += delay
                attempt += 1
                
                # 计算下一次延迟
                if step_index < len(step_sequence):
                    next_step = step_sequence[step_index]
                    step_index += 1
                else:
                    # 如果步长序列用完，使用最后一个步长
                    next_step = step_sequence[-1]
                
                delay = min(delay + next_step, 30.0)  # 限制最大间隔为30秒
                
                # 记录轮询信息
                if attempt % 3 == 0:  # 每3次轮询记录一次详细信息
                    logger.info(f"任务 {job_id} 轮询中... 第{attempt}次，当前延迟: {delay:.2f}s，总耗时: {total_elapsed:.2f}s")
                
            except Exception as e:
                logger.warning(f"查询任务状态失败 (尝试 {attempt + 1}): {e}")
                await asyncio.sleep(delay)
                total_elapsed += delay
                attempt += 1
                
                if step_index < len(step_sequence):
                    next_step = step_sequence[step_index]
                    step_index += 1
                else:
                    next_step = step_sequence[-1]
                
                delay = min(delay + next_step, 30.0)
        
        raise TimeoutError(f"等待任务 {job_id} 完成超时，总耗时: {total_elapsed:.2f}秒，轮询次数: {attempt}")
    
    # ==================== 异步方法 ====================
    
    async def aexec_command(self, device: Union[ConnectionArgs, Dict], command: Union[str, List[str]], driver: Optional[str] = None, **kwargs) -> CommandResult:
        """
        异步执行命令，支持ConnectionArgs实例或dict
        driver: 可选，临时覆盖实例driver
        """
        if hasattr(device, 'model_dump'):
            connection_args = device.model_dump()
        else:
            connection_args = device
        use_driver = driver or self.driver
        data = create_device_request(
            driver=use_driver,
            connection_args=connection_args,
            command=command,
            **kwargs
        )
        result = await self._make_request("POST", self._build_url("/device/execute"), json=data)
        if result.get("code") == 0 and result.get("data"):
            job_id = result["data"]["id"]
            job_result = await self._wait_for_result_with_progressive_retry(job_id)
            job_data = job_result["data"][0] if isinstance(job_result["data"], list) else job_result["data"]
            
            # 直接返回API的完整结构
            return CommandResult(**job_data)
        raise NetPulseError(f"Command execution failed: {result}")

    async def aexec_config(self, device: Union[ConnectionArgs, Dict], config: Union[str, List[str], Dict], driver: Optional[str] = None, **kwargs) -> ConfigResult:
        """
        异步推送配置，支持ConnectionArgs实例或dict
        driver: 可选，临时覆盖实例driver
        """
        if hasattr(device, 'model_dump'):
            connection_args = device.model_dump()
        else:
            connection_args = device
        use_driver = driver or self.driver
        data = create_device_request(
            driver=use_driver,
            connection_args=connection_args,
            config=config,
            **kwargs
        )
        result = await self._make_request("POST", self._build_url("/device/execute"), json=data)
        if result.get("code") == 0 and result.get("data"):
            job_id = result["data"]["id"]
            job_result = await self._wait_for_result_with_progressive_retry(job_id)
            job_data = job_result["data"][0] if isinstance(job_result["data"], list) else job_result["data"]
            
            # 直接返回API的完整结构
            return ConfigResult(**job_data)
        raise NetPulseError(f"Config execution failed: {result}")
    
    async def abulk_command(self, driver: Optional[str] = None, devices: List[Dict] = None, connection_args: Dict = None, command: Union[str, List[str]] = None, **kwargs) -> Dict:
        """异步批量执行命令，driver可选，默认self.driver"""
        use_driver = driver or self.driver
        data = create_batch_device_request(
            driver=use_driver,
            devices=devices,
            connection_args=connection_args,
            command=command,
            **kwargs
        )
        result = await self._make_request("POST", self._build_url("/device/bulk"), json=data)
        if result.get("code") == 0 and result.get("data"):
            batch_data = result["data"]
            if batch_data and batch_data.get("succeeded"):
                tasks = []
                for job in batch_data["succeeded"]:
                    job_id = job["id"]
                    tasks.append(self._wait_for_result_with_progressive_retry(job_id))
                await asyncio.gather(*tasks, return_exceptions=True)
        return result
    
    async def abulk_config(self, driver: Optional[str] = None, devices: List[Dict] = None, connection_args: Dict = None, config: Union[str, List[str], Dict] = None, **kwargs) -> Dict:
        """异步批量推送配置，driver可选，默认self.driver"""
        use_driver = driver or self.driver
        data = create_batch_device_request(
            driver=use_driver,
            devices=devices,
            connection_args=connection_args,
            config=config,
            **kwargs
        )
        result = await self._make_request("POST", self._build_url("/device/bulk"), json=data)
        if result.get("code") == 0 and result.get("data"):
            batch_data = result["data"]
            if batch_data and batch_data.get("succeeded"):
                tasks = []
                for job in batch_data["succeeded"]:
                    job_id = job["id"]
                    tasks.append(self._wait_for_result_with_progressive_retry(job_id))
                await asyncio.gather(*tasks, return_exceptions=True)
        return result
    
    # ==================== 异步任务管理 ====================
    
    async def aget_jobs(self, job_id: Optional[str] = None, queue: Optional[str] = None,
                       status: Optional[str] = None, node: Optional[str] = None,
                       host: Optional[str] = None) -> Dict:
        """异步获取任务列表"""
        params = {}
        if job_id:
            params["id"] = job_id
        if queue:
            params["queue"] = queue
        if status:
            params["status"] = status
        if node:
            params["node"] = node
        if host:
            params["host"] = host
        
        return await self._make_request("GET", self._build_url("/job"), params=params)
    
    async def adelete_jobs(self, job_id: Optional[str] = None, queue: Optional[str] = None,
                          host: Optional[str] = None) -> Dict:
        """异步删除任务"""
        params = {}
        if job_id:
            params["id"] = job_id
        if queue:
            params["queue"] = queue
        if host:
            params["host"] = host
        
        return await self._make_request("DELETE", self._build_url("/job"), params=params)
    
    # ==================== 异步Worker管理 ====================
    
    async def aget_workers(self, queue: Optional[str] = None, node: Optional[str] = None,
                          host: Optional[str] = None) -> Dict:
        """异步获取Worker列表"""
        params = {}
        if queue:
            params["queue"] = queue
        if node:
            params["node"] = node
        if host:
            params["host"] = host
        
        return await self._make_request("GET", self._build_url("/worker"), params=params)
    
    async def adelete_workers(self, name: Optional[str] = None, queue: Optional[str] = None,
                             node: Optional[str] = None, host: Optional[str] = None) -> Dict:
        """异步删除Worker"""
        params = {}
        if name:
            params["name"] = name
        if queue:
            params["queue"] = queue
        if node:
            params["node"] = node
        if host:
            params["host"] = host
        
        return await self._make_request("DELETE", self._build_url("/worker"), params=params)
    
    # ==================== 异步健康检测 ====================
    
    async def ahealth_check(self) -> HealthCheckResult:
        """健康检测"""
        result = await self._make_request("GET", self._build_url("/health"))
        if result.get("code") == 0 and result.get("data"):
            return HealthCheckResult(**result["data"])
        raise NetPulseError(f"Health check failed: {result}")
    
    # ==================== 异步连接测试 ====================
    
    async def atest_connection(self, device: Union[ConnectionArgs, Dict], driver: Optional[str] = None) -> ConnectionTestResult:
        """测试设备连接，支持ConnectionArgs实例或dict"""
        if hasattr(device, 'model_dump'):
            connection_args = device.model_dump()
        else:
            connection_args = device
        use_driver = driver or self.driver
        data = {
            "driver": use_driver,
            "connection_args": connection_args
        }
        result = await self._make_request("POST", self._build_url("/device/test-connection"), json=data)
        if result.get("code") == 0 and result.get("data"):
            return ConnectionTestResult(**result["data"])
        raise NetPulseError(f"Connection test failed: {result}")
    
    # ==================== 异步模板管理 ====================
    
    async def arender_template(self, name: str, template: str, context: Optional[Dict] = None) -> Dict:
        """异步渲染模板"""
        data = {
            "name": name,
            "template": template,
            "context": context or {}
        }
        return await self._make_request("POST", self._build_url("/template/render"), json=data)
    
    async def aparse_template(self, name: str, template: str, context: Optional[str] = None) -> Dict:
        """异步解析模板"""
        data = {
            "name": name,
            "template": template,
            "context": context
        }
        return await self._make_request("POST", self._build_url("/template/parse"), json=data)


# 工厂函数
async def create_async_client(
    endpoint: str,
    api_key: str,
    **kwargs
) -> AsyncNetPulseClient:
    """创建异步客户端实例"""
    return AsyncNetPulseClient(endpoint, api_key, **kwargs) 