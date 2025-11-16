import os
import zoneinfo
from datetime import datetime, timezone
from typing import Any, List, Optional

import rq
from pydantic import BaseModel, ValidationError, computed_field, field_serializer

from .common import JobAdditionalData, JobResult


def _serialize_datetime_with_tz(dt: Optional[datetime], _info=None) -> Optional[str]:
    """Convert datetime to configured timezone and ISO format"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Fallback order: TZ -> Asia/Shanghai -> UTC
    configured_tz: zoneinfo.ZoneInfo = None
    try:
        tz_name = os.getenv("TZ", "Asia/Shanghai")
        configured_tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        try:
            configured_tz = zoneinfo.ZoneInfo("Asia/Shanghai")
        except Exception:
            configured_tz = timezone.utc

    return dt.astimezone(configured_tz).isoformat()


class BaseResponse(BaseModel):
    code: int = 200
    message: Optional[str] = None
    data: Optional[Any] = None


class JobInResponse(BaseModel):
    """Wrapping rq.Job object for response"""

    id: str
    status: str

    created_at: datetime
    enqueued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    queue: str
    worker: Optional[str] = None
    result: Optional[JobResult] = None

    @field_serializer("created_at", "enqueued_at", "started_at", "ended_at")
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
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
        except ValidationError as e:
            # Print a warning and continue
            log.warning(f"Error in validating JobMeta: {e}")
        else:
            error = meta.error

        result = job.latest_result()
        if result:
            # We ignore exc_string as it's too verbose in response
            result = JobResult(
                type=result.type.value,
                retval=result.return_value,
                error=(
                    {
                        "type": error[0],
                        "message": error[1],
                    }
                    if error
                    else None
                ),
            )

        return cls(
            id=job.id,
            status=job.get_status(),
            queue=job.origin,
            created_at=job.created_at,
            enqueued_at=job.enqueued_at,
            started_at=job.started_at,
            ended_at=job.ended_at,
            worker=job.worker_name,
            result=result,
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


class SubmitJobResponse(BaseResponse):
    """Any route submits a job should use this model"""

    data: Optional[JobInResponse] = None


class BatchSubmitJobResponse(BaseResponse):
    class BatchSubmitJobData(BaseModel):
        succeeded: Optional[List[JobInResponse]] = None
        failed: Optional[List[str]] = None

    data: Optional[BatchSubmitJobData] = None


class GetJobResponse(BaseResponse):
    data: Optional[List[JobInResponse]] = None


class DeleteJobResponse(BaseResponse):
    data: List[str] = None


class GetWorkerResponse(BaseResponse):
    data: Optional[List[WorkerInResponse]] = None


class DeleteWorkerResponse(BaseResponse):
    data: List[str] = None


class ConnectionTestResponse(BaseResponse):
    """Response model for device connection testing"""

    class ConnectionTestData(BaseModel):
        success: bool
        connection_time: Optional[float] = None  # Connection time in seconds
        error_message: Optional[str] = None  # Error message if connection failed
        device_info: Optional[dict] = None  # Device information if connection succeeded
        timestamp: datetime

        @field_serializer("timestamp")
        def serialize_datetime(self, dt: datetime, _info) -> str:
            return _serialize_datetime_with_tz(dt, _info)

    data: Optional[ConnectionTestData] = None
