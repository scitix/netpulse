import logging
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    NetPulseError,
    TimeoutError,
)
from .models import (
    BatchResult,
    CommandResult,
    ConfigResult,
    ConnectionArgs,
    ConnectionTestResult,
    HealthCheckResult,
    JobInfo,
    WorkerInfo,
    create_batch_device_request,
    create_device_request,
)

# 配置日志
logger = logging.getLogger(__name__)


class NetPulseClient:
    """NetPulse API客户端"""

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        driver: str = "netmiko",
        timeout: int = 300,
        verify_ssl: bool = True,
    ):
        """初始化客户端

        Args:
            endpoint: API端点URL
            api_key: API密钥 (可选)
            driver: 默认驱动类型 (如netmiko/napalm/pyeapi)
            timeout: 请求超时时间(秒)
            verify_ssl: 是否验证SSL证书
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.driver = driver
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self._session = httpx.Client(
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
            headers={"Content-Type": "application/json", "User-Agent": "NetPulse-Client/0.1.0"},
        )

        if api_key:
            self._session.headers["X-API-KEY"] = api_key

    def _build_url(self, path: str) -> str:
        """构建完整的API URL"""
        return urljoin(self.endpoint, path)

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """发送HTTP请求"""
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            elif e.response.status_code == 404:
                raise ConnectionError(f"API endpoint not found: {url}") from e
            else:
                raise NetPulseError(f"HTTP error: {e}") from e
        except httpx.ConnectError:
            raise ConnectionError(f"Failed to connect to {url}")
        except httpx.TimeoutException:
            raise TimeoutError(f"Request timeout: {url}")
        except Exception as e:
            raise NetPulseError(f"Request failed: {e}")

    def _wait_for_result_with_progressive_retry(
        self, job_id: str, initial_delay: float = 0.4, max_total_time: float = 120.0
    ) -> Dict:
        """
        使用激进递进式重试等待任务结果

        轮询策略:
        - 初始延迟: 0.4秒
        - 递增步长序列: 0.1s -> 0.2s -> 0.3s -> 0.5s -> 1.5s -> 2.5s -> 4.0s
          -> 6.0s -> 9.0s -> 13.5s -> 20.0s -> 30.0s
        - 轮询间隔: 0.4s -> 0.5s -> 0.7s -> 1.0s -> 1.5s -> 3.0s -> 5.5s
          -> 9.5s -> 15.5s -> 24.5s -> 37.5s -> 57.5s
        - 最大间隔: 30秒
        - 最大总时长: 120秒

        示例轮询序列:
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
                result = self._make_request("GET", self._build_url("/job"), params={"id": job_id})

                if result.get("code") == 0 and result.get("data"):
                    job_data = (
                        result["data"][0] if isinstance(result["data"], list) else result["data"]
                    )
                    status = job_data.get("status")

                    if status in ["finished", "failed"]:
                        logger.info(
                            f"任务 {job_id} 完成, "
                            f"总耗时: {total_elapsed:.2f}秒, 轮询次数: {attempt}"
                        )
                        return result
                    elif status == "queued":
                        logger.info(
                            f"任务 {job_id} 排队中... "
                            f"(第{attempt}次轮询, 已耗时{total_elapsed:.2f}秒)"
                        )
                    elif status == "started":
                        logger.info(
                            f"任务 {job_id} 执行中... "
                            f"(第{attempt}次轮询, 已耗时{total_elapsed:.2f}秒)"
                        )

                # 激进递进式延迟
                time.sleep(delay)
                total_elapsed += delay
                attempt += 1

                # 计算下一次延迟
                if step_index < len(step_sequence):
                    next_step = step_sequence[step_index]
                    step_index += 1
                else:
                    # 如果步长序列用完, 使用最后一个步长
                    next_step = step_sequence[-1]

                delay = min(delay + next_step, 30.0)  # 限制最大间隔为30秒

                # 记录轮询信息
                if attempt % 3 == 0:  # 每3次轮询记录一次详细信息
                    logger.info(
                        f"任务 {job_id} 轮询中... 第{attempt}次, 当前延迟: {delay:.2f}s, "
                        f"总耗时: {total_elapsed:.2f}s"
                    )

            except Exception as e:
                logger.warning(f"查询任务状态失败 (尝试 {attempt + 1}): {e}")
                time.sleep(delay)
                total_elapsed += delay
                attempt += 1

                if step_index < len(step_sequence):
                    next_step = step_sequence[step_index]
                    step_index += 1
                else:
                    next_step = step_sequence[-1]

                delay = min(delay + next_step, 30.0)

        raise TimeoutError(
            f"等待任务 {job_id} 完成超时, 总耗时: {total_elapsed:.2f}秒, 轮询次数: {attempt}"
        )

    # ==================== 同步方法 ====================

    def exec_command(
        self,
        device: Union[ConnectionArgs, Dict],
        command: Union[str, List[str]],
        driver: Optional[str] = None,
        **kwargs,
    ) -> CommandResult:
        """
        同步执行命令, 支持ConnectionArgs实例或dict
        driver: 可选, 临时覆盖实例driver
        """
        if hasattr(device, "model_dump"):
            connection_args = device.model_dump()
        else:
            connection_args = device
        use_driver = driver or self.driver
        data = create_device_request(
            driver=use_driver, connection_args=connection_args, command=command, **kwargs
        )
        result = self._make_request("POST", self._build_url("/device/execute"), json=data)
        # print("[DEBUG] API原始返回:", result)  # 调试用
        if result.get("code") == 0 and result.get("data"):
            job_id = result["data"]["id"]
            job_result = self._wait_for_result_with_progressive_retry(job_id)
            # print("[DEBUG] job_result:", job_result)  # 调试用
            job_data = (
                job_result["data"][0]
                if isinstance(job_result["data"], list)
                else job_result["data"]
            )
            # print("[DEBUG] job_data:", job_data)  # 调试用

            # 直接返回API的完整结构
            return CommandResult(**job_data)
        raise NetPulseError(f"Command execution failed: {result}")

    def exec_config(
        self,
        device: Union[ConnectionArgs, Dict],
        config: Union[str, List[str], Dict],
        driver: Optional[str] = None,
        **kwargs,
    ) -> ConfigResult:
        """
        同步推送配置, 支持ConnectionArgs实例或dict
        driver: 可选, 临时覆盖实例driver
        """
        if hasattr(device, "model_dump"):
            connection_args = device.model_dump()
        else:
            connection_args = device
        use_driver = driver or self.driver
        data = create_device_request(
            driver=use_driver, connection_args=connection_args, config=config, **kwargs
        )
        result = self._make_request("POST", self._build_url("/device/execute"), json=data)
        if result.get("code") == 0 and result.get("data"):
            job_id = result["data"]["id"]
            job_result = self._wait_for_result_with_progressive_retry(job_id)
            job_data = (
                job_result["data"][0]
                if isinstance(job_result["data"], list)
                else job_result["data"]
            )

            # 直接返回API的完整结构
            return ConfigResult(**job_data)
        raise NetPulseError(f"Config execution failed: {result}")

    def bulk_command(
        self,
        devices: List[Union[ConnectionArgs, Dict]],
        connection_args: Dict,
        command: Union[str, List[str]],
        driver: Optional[str] = None,
        **kwargs,
    ) -> BatchResult:
        """
        同步批量执行命令, 支持ConnectionArgs实例或dict列表
        driver: 可选, 临时覆盖实例driver
        """
        devices_args = [d.model_dump() if hasattr(d, "model_dump") else d for d in devices]
        use_driver = driver or self.driver
        data = create_batch_device_request(
            driver=use_driver,
            devices=devices_args,
            connection_args=connection_args,
            command=command,
            **kwargs,
        )
        result = self._make_request("POST", self._build_url("/device/bulk"), json=data)
        if result.get("code") == 0 and result.get("data"):
            batch_data = result["data"]
            results = []
            if batch_data and batch_data.get("succeeded"):
                for job in batch_data["succeeded"]:
                    job_id = job["id"]
                    job_result = self._wait_for_result_with_progressive_retry(job_id)
                    job_data = (
                        job_result["data"][0]
                        if isinstance(job_result["data"], list)
                        else job_result["data"]
                    )
                    results.append(job_data)
            return BatchResult(
                status="finished",
                job_id=batch_data.get("batch_id", ""),
                results=results,
                error=None,
            )
        raise NetPulseError(f"Batch command execution failed: {result}")

    def bulk_config(
        self,
        devices: List[Union[ConnectionArgs, Dict]],
        connection_args: Dict,
        config: Union[str, List[str], Dict],
        driver: Optional[str] = None,
        **kwargs,
    ) -> BatchResult:
        """
        同步批量推送配置, 支持ConnectionArgs实例或dict列表
        driver: 可选, 临时覆盖实例driver
        """
        devices_args = [d.model_dump() if hasattr(d, "model_dump") else d for d in devices]
        use_driver = driver or self.driver
        data = create_batch_device_request(
            driver=use_driver,
            devices=devices_args,
            connection_args=connection_args,
            config=config,
            **kwargs,
        )
        result = self._make_request("POST", self._build_url("/device/bulk"), json=data)
        if result.get("code") == 0 and result.get("data"):
            batch_data = result["data"]
            results = []
            if batch_data and batch_data.get("succeeded"):
                for job in batch_data["succeeded"]:
                    job_id = job["id"]
                    job_result = self._wait_for_result_with_progressive_retry(job_id)
                    job_data = (
                        job_result["data"][0]
                        if isinstance(job_result["data"], list)
                        else job_result["data"]
                    )
                    results.append(job_data)
            return BatchResult(
                status="finished",
                job_id=batch_data.get("batch_id", ""),
                results=results,
                error=None,
            )
        raise NetPulseError(f"Batch config execution failed: {result}")

    # ==================== 任务管理 ====================

    def get_job_info(self, job_id: str) -> JobInfo:
        """获取任务信息"""
        result = self._make_request("GET", self._build_url(f"/job/{job_id}"))
        if result.get("code") == 0 and result.get("data"):
            return JobInfo(**result["data"])
        raise NetPulseError(f"Get job info failed: {result}")

    def get_jobs(
        self,
        job_id: Optional[str] = None,
        queue: Optional[str] = None,
        status: Optional[str] = None,
        node: Optional[str] = None,
        host: Optional[str] = None,
    ) -> List[JobInfo]:
        """获取任务列表"""
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

        result = self._make_request("GET", self._build_url("/job"), params=params)
        if result.get("code") == 0 and result.get("data"):
            return [JobInfo(**job) for job in result["data"]]
        raise NetPulseError(f"Get jobs failed: {result}")

    def delete_jobs(
        self, job_id: Optional[str] = None, queue: Optional[str] = None, host: Optional[str] = None
    ) -> Dict:
        """删除任务"""
        params = {}
        if job_id:
            params["id"] = job_id
        if queue:
            params["queue"] = queue
        if host:
            params["host"] = host

        return self._make_request("DELETE", self._build_url("/job"), params=params)

    # ==================== Worker管理 ====================

    def get_workers(
        self, queue: Optional[str] = None, node: Optional[str] = None, host: Optional[str] = None
    ) -> List[WorkerInfo]:
        """获取Worker列表"""
        params = {}
        if queue:
            params["queue"] = queue
        if node:
            params["node"] = node
        if host:
            params["host"] = host

        result = self._make_request("GET", self._build_url("/worker"), params=params)
        if result.get("code") == 0 and result.get("data"):
            return [WorkerInfo(**worker) for worker in result["data"]]
        raise NetPulseError(f"Get workers failed: {result}")

    def delete_workers(
        self,
        name: Optional[str] = None,
        queue: Optional[str] = None,
        node: Optional[str] = None,
        host: Optional[str] = None,
    ) -> Dict:
        """删除Worker"""
        params = {}
        if name:
            params["name"] = name
        if queue:
            params["queue"] = queue
        if node:
            params["node"] = node
        if host:
            params["host"] = host

        return self._make_request("DELETE", self._build_url("/worker"), params=params)

    # ==================== 健康检测 ====================

    def health_check(self) -> HealthCheckResult:
        """健康检测"""
        result = self._make_request("GET", self._build_url("/health"))
        if result.get("code") == 0 and result.get("data"):
            return HealthCheckResult(**result["data"])
        raise NetPulseError(f"Health check failed: {result}")

    # ==================== 连接测试 ====================

    def test_connection(
        self, device: Union[ConnectionArgs, Dict], driver: Optional[str] = None
    ) -> ConnectionTestResult:
        """测试设备连接, 支持ConnectionArgs实例或dict"""
        if hasattr(device, "model_dump"):
            connection_args = device.model_dump()
        else:
            connection_args = device
        use_driver = driver or self.driver
        data = {"driver": use_driver, "connection_args": connection_args}
        result = self._make_request("POST", self._build_url("/device/test-connection"), json=data)
        if result.get("code") == 0 and result.get("data"):
            return ConnectionTestResult(**result["data"])
        raise NetPulseError(f"Connection test failed: {result}")

    # ==================== 模板管理 ====================

    def render_template(self, name: str, template: str, context: Optional[Dict] = None) -> Dict:
        """渲染模板"""
        data = {"name": name, "template": template, "context": context or {}}
        return self._make_request("POST", self._build_url("/template/render"), json=data)

    def parse_template(self, name: str, template: str, context: Optional[str] = None) -> Dict:
        """解析模板"""
        data = {"name": name, "template": template, "context": context}
        return self._make_request("POST", self._build_url("/template/parse"), json=data)

    # ==================== 向后兼容方法 ====================

    def execute(
        self, device: ConnectionArgs, command: Union[str, List[str]], **kwargs
    ) -> CommandResult:
        """向后兼容的命令执行方法"""
        result = self.exec_command(device=device, command=command, **kwargs)

        if result.get("code") == 0 and result.get("data"):
            job_data = result["data"][0] if isinstance(result["data"], list) else result["data"]
            return CommandResult(
                status=job_data.get("status", "unknown"),
                data=job_data.get("result", {}).get("retval"),
                error=job_data.get("result", {}).get("error"),
                job_id=job_data.get("id", ""),
                device_host=device.host,
            )

        raise NetPulseError(f"Command execution failed: {result}")

    def configure(
        self, device: ConnectionArgs, config: Union[str, List[str]], **kwargs
    ) -> ConfigResult:
        """向后兼容的配置推送方法"""
        result = self.exec_config(device=device, config=config, **kwargs)

        if result.get("code") == 0 and result.get("data"):
            job_data = result["data"][0] if isinstance(result["data"], list) else result["data"]
            return ConfigResult(
                status=job_data.get("status", "unknown"),
                job_id=job_data.get("id", ""),
                device_host=device.host,
                error=job_data.get("result", {}).get("error"),
            )

        raise NetPulseError(f"Config execution failed: {result}")

    def close(self):
        """关闭客户端"""
        if self._session:
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
