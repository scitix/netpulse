from typing import TYPE_CHECKING, Dict, Optional

from ...models import DeviceTestInfo, DriverConnectionArgs
from ...models.request import ExecutionRequest

if TYPE_CHECKING:
    from ...models.driver import DriverExecutionResult


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

    def _get_effective_source_path(self, local_path: Optional[str]) -> Optional[str]:
        """
        Standardized method to get the effective source path for file transfers.
        Returns the staging path if staged_file_id is present, otherwise local_path.
        """
        if self.staged_file_id:
            return self.staged_file_id
        return local_path

    def _get_effective_dest_path(self, local_path: Optional[str]) -> str:
        """
        Standardized method to get the effective destination path for downloads.
        If local_path is not absolute, it will be placed in the staging area.
        """
        import os

        if local_path and os.path.isabs(local_path):
            return local_path

        from ...utils import g_config

        staging_dir = str(g_config.storage.staging)
        download_dir = os.path.join(staging_dir, "downloads")
        os.makedirs(download_dir, exist_ok=True)

        filename = os.path.basename(local_path) if local_path else f"download_{self.job_id}"
        return os.path.join(download_dir, filename)

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

    def send(self, session, command: list[str]) -> "Dict[str, DriverExecutionResult]":
        raise NotImplementedError

    def config(self, session, config: list[str]) -> "Dict[str, DriverExecutionResult]":
        raise NotImplementedError

    def disconnect(self, session):
        raise NotImplementedError

    @classmethod
    def test(cls, connection_args: DriverConnectionArgs) -> DeviceTestInfo:
        """Validate connectivity and return device metadata if available."""
        raise NotImplementedError
