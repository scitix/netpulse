from typing import TYPE_CHECKING, Optional

from ...models import DeviceTestInfo, DriverConnectionArgs
from ...models.driver import DriverExecutionResult
from ...models.request import ExecutionRequest


class BaseDriver:
    """Driver is the abstract base class for all drivers."""

    driver_name: str = "base"

    def __init__(
        self,
        staged_file_id: Optional[str] = None,
        job_id: Optional[str] = None,
        **kwargs,
    ):
        self.staged_file_id = staged_file_id
        self.job_id = job_id or "unknown"
        self._session_reused = False

    def _get_base_metadata(self, start_time: float) -> dict:
        """
        Helper to construct a standardized metadata dictionary.
        """
        import time

        duration = time.perf_counter() - start_time
        return {
            "host": getattr(self.conn_args, "host", "unknown"),
            "duration_seconds": round(duration, 3),
            "session_reused": self._session_reused,
        }

    def _get_effective_source_path(self, local_path: Optional[str]) -> Optional[str]:
        """
        Standardized method to get the effective source path for file transfers.
        Returns the staging path if staged_file_id is present, otherwise local_path.
        """
        if self.staged_file_id:
            return self.staged_file_id
        return local_path

    def _get_effective_dest_path(
        self, local_path: Optional[str], fallback_name: Optional[str] = None
    ) -> str:
        """
        Standardized method to get the effective destination path for downloads.
        If local_path is not absolute, it will be placed in the staging area
        under a subfolder named by the Job ID to preserve the original filename.
        """
        import os

        if local_path and os.path.isabs(local_path):
            return local_path

        from ...utils import g_config

        staging_dir = str(g_config.storage.staging)
        download_dir = os.path.join(staging_dir, "downloads")

        # Professional Design: Isolated subfolder per job to keep original filenames
        job_dir = os.path.join(download_dir, f"dl_{self.job_id}")
        os.makedirs(job_dir, exist_ok=True)

        filename = os.path.basename(local_path) if local_path else (fallback_name or "download")
        return os.path.join(job_dir, filename)

    @classmethod
    def from_execution_request(cls, req: ExecutionRequest) -> "BaseDriver":
        """Create driver instance from a execution request."""
        raise NotImplementedError

    @classmethod
    def validate(cls, req: ExecutionRequest) -> None:
        """Validate the request without creating the driver instance."""
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def send(self, session, command: list[str]) -> list[DriverExecutionResult]:
        raise NotImplementedError

    def config(self, session, config: list[str]) -> list[DriverExecutionResult]:
        raise NotImplementedError

    def disconnect(self, session):
        raise NotImplementedError

    @classmethod
    def test(cls, connection_args: DriverConnectionArgs) -> DeviceTestInfo:
        """Validate connectivity and return device metadata if available."""
        raise NotImplementedError
