import os
import zoneinfo
from datetime import datetime, timezone
from typing import List, Optional

import rq
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_serializer,
    model_validator,
)

from .common import BatchFailedItem, DeviceTestInfo, JobAdditionalData, JobResult


def _serialize_datetime_with_tz(dt: Optional[datetime], _info=None) -> Optional[str]:
    """Convert datetime to configured timezone and ISO format"""
    DEFAULT_TZ = "Asia/Shanghai"

    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Fallback order: TZ -> Asia/Shanghai -> UTC
    configured_tz: zoneinfo.ZoneInfo | timezone | None = None
    try:
        tz_name = os.getenv("TZ", DEFAULT_TZ)
        configured_tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        try:
            configured_tz = zoneinfo.ZoneInfo(DEFAULT_TZ)
        except Exception:
            configured_tz = timezone.utc

    return dt.astimezone(configured_tz).isoformat()


class JobInResponse(BaseModel):
    """Wrapping rq.Job object for response"""

    id: str
    status: str

    created_at: Optional[datetime] = None
    enqueued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    queue: str
    worker: Optional[str] = None
    result: Optional[JobResult] = None
    task_id: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "job_123456",
                "status": "finished",
                "created_at": "2024-02-23T10:00:00+08:00",
                "queue": "fifo",
                "worker": "worker@hostname",
                "duration": 0.5,
                "result": {
                    "type": 1,
                    "retval": [
                        {
                            "command": "show version",
                            "output": "Arista vEOS\nHardware version: 4.25.4M",
                            "error": "",
                            "exit_status": 0,
                            "metadata": {"host": "172.17.0.1", "duration_seconds": 0.123},
                        }
                    ],
                },
            }
        }
    )

    @field_serializer("created_at", "enqueued_at", "started_at", "ended_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        return _serialize_datetime_with_tz(dt, _info)

    @computed_field
    @property
    def duration(self) -> Optional[float]:
        """Task execution duration (seconds)"""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None

    @computed_field
    @property
    def queue_time(self) -> Optional[float]:
        """Queue waiting time (seconds)"""
        if self.enqueued_at and self.started_at:
            return (self.started_at - self.enqueued_at).total_seconds()
        return None

    @classmethod
    def from_job(cls, job: "rq.job.Job") -> "JobInResponse":
        """
        Convert an `rq.Job` object to `JobResponse`.
        """
        import logging

        log = logging.getLogger(__name__)

        error = None
        try:
            meta = JobAdditionalData.model_validate(job.meta)
        except (ValidationError, TypeError) as e:
            log.warning(f"Error in validating JobMeta: {e}")
        else:
            error = meta.error

        result_in_job = job.latest_result()
        result = (
            JobResult(
                type=JobResult.ResultType(result_in_job.type.value),
                retval=result_in_job.return_value,
                error=(
                    {
                        "type": error[0],
                        "message": error[1],
                    }
                    if error
                    else None
                ),
            )
            if result_in_job
            else None
        )

        status = job.get_status()
        status = "unknown" if status is None else status.value

        return cls(
            id=job.id,
            status=status,
            queue=job.origin,
            created_at=job.created_at,
            enqueued_at=job.enqueued_at,
            started_at=job.started_at,
            ended_at=job.ended_at,
            worker=job.worker_name,
            result=result,
            task_id=meta.task_id if meta else None,
        )


class WorkerInResponse(BaseModel):
    """Wrapping rq.Worker object for response"""

    name: str
    status: str
    pid: Optional[int] = None
    hostname: Optional[str] = None
    queues: Optional[List[str]] = None
    last_heartbeat: Optional[datetime] = None
    birth_at: Optional[datetime] = None
    successful_job_count: Optional[int] = None
    failed_job_count: Optional[int] = None

    @field_serializer("last_heartbeat", "birth_at")
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        return _serialize_datetime_with_tz(dt, _info)

    @classmethod
    def from_worker(cls, worker: "rq.worker.BaseWorker") -> "WorkerInResponse":
        return cls(
            name=worker.name,
            status=worker.get_state(),
            pid=worker.pid,
            hostname=worker.hostname,
            queues=worker.queue_names(),
            last_heartbeat=worker.last_heartbeat,
            birth_at=worker.birth_date,
            successful_job_count=worker.successful_job_count,
            failed_job_count=worker.failed_job_count,
        )


class BatchSubmitJobResponse(BaseModel):
    succeeded: Optional[List[JobInResponse]] = None
    failed: Optional[List[BatchFailedItem]] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "succeeded": [
                    {
                        "id": "job_1",
                        "status": "queued",
                        "queue": "fifo",
                    }
                ],
                "failed": [
                    {
                        "host": "192.168.1.1",
                        "reason": "Vault key not found",
                    }
                ],
            }
        }
    )


class ConnectionTestResponse(BaseModel):
    """Response model for device connection testing"""

    success: bool
    latency: Optional[float] = Field(
        None, description="Time taken to establish the connection in seconds"
    )
    error: Optional[str] = Field(None, description="Error message if the connection failed")
    result: Optional[DeviceTestInfo] = Field(
        None, description="Device information if the connection succeeded"
    )
    timestamp: Optional[datetime] = Field(
        None, description="Timestamp of the test result is generated"
    )

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        return _serialize_datetime_with_tz(dt, _info)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "latency": 0.045,
                "result": {
                    "driver": "netmiko",
                    "host": "192.168.1.1",
                    "prompt": "router#",
                },
                "timestamp": "2024-02-23T10:05:00+08:00",
            }
        }
    )


class DetachedTaskInResponse(BaseModel):
    """Metadata for a detached task, with sensitive data masked."""

    task_id: str
    command: List[str]
    host: str
    driver: str
    status: str
    last_sync: Optional[datetime] = None
    created_at: Optional[datetime] = None
    push_interval: Optional[int] = None
    last_offset: Optional[int] = None
    connection_args: dict

    @field_serializer("last_sync", "created_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        return _serialize_datetime_with_tz(dt, _info)

    @field_serializer("connection_args")
    def mask_password(self, args: dict, _info):
        """Mask sensitive information in connection_args."""
        if not args or not isinstance(args, dict):
            return args
        masked = args.copy()
        for key in ["password", "secret", "private_key"]:
            if masked.get(key):
                masked[key] = "******"
        return masked

    @model_validator(mode="before")
    @classmethod
    def convert_timestamps(cls, data: dict):
        if not isinstance(data, dict):
            return data
        for field in ["last_sync", "created_at"]:
            val = data.get(field)
            if isinstance(val, (int, float)):
                data[field] = datetime.fromtimestamp(val, tz=timezone.utc)
        return data

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "task_abc_789",
                "command": ["stress --cpu 4 --timeout 60s"],
                "host": "192.168.1.100",
                "driver": "paramiko",
                "status": "running",
                "last_sync": "2024-02-23T10:10:00+08:00",
                "connection_args": {
                    "host": "192.168.1.100",
                    "username": "admin",
                    "password": "******",
                },
            }
        }
    )
