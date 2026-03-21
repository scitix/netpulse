import logging
import time

from .manager import g_mgr
from .rediz import g_detached_task_registry, g_rdb

log = logging.getLogger(__name__)

# Redis key for distributed supervisor lock
_SUPERVISOR_LOCK_KEY = "netpulse:supervisor:lock"
_SUPERVISOR_LOCK_TTL = 5  # seconds — must be > supervisor interval


class DetachedTaskSupervisor:
    """
    Background supervisor that monitors the Detached Task Registry and triggers
    incremental log pushes via Webhooks based on the push_interval.

    Only ONE supervisor instance is active across all Gunicorn workers,
    coordinated via a Redis lock.
    """

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.running = False
        self.staging_cleanup_interval = 3600  # Clean staging every hour
        self.last_staging_cleanup = 0
        # Track last dispatch time locally to avoid race conditions with registry writes
        self._last_dispatch: dict[str, float] = {}

    def start(self):
        self.running = True
        log.info("NetPulse Supervisor started.")
        while self.running:
            try:
                # Only one supervisor instance runs across all Gunicorn workers.
                # Acquire a Redis lock with TTL — if we can't acquire, another
                # worker's supervisor is already handling it.
                acquired = g_rdb.conn.set(
                    _SUPERVISOR_LOCK_KEY, "1", nx=True, ex=_SUPERVISOR_LOCK_TTL
                )
                if acquired:
                    now = time.time()
                    self._check_tasks()

                    # Periodic cleaning of staging directory (24h TTL)
                    if now - self.last_staging_cleanup > self.staging_cleanup_interval:
                        self._cleanup_staging()
                        self.last_staging_cleanup = now
                else:
                    # Another supervisor holds the lock — sleep and retry
                    pass

            except Exception as e:
                log.error(f"Error in Supervisor loop: {e}")
            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def _cleanup_staging(self):
        """
        Cleanup files in staging older than configured retention hours.
        """
        import os
        import shutil

        from ..utils import g_config

        staging_dir = str(g_config.storage.staging)
        if not os.path.exists(staging_dir):
            return

        now = time.time()
        ttl = g_config.storage.retention_hours * 3600

        log.info(
            f"Starting staging cleanup in {staging_dir} "
            f"(TTL: {g_config.storage.retention_hours}h)..."
        )
        count = 0

        try:
            for filename in os.listdir(staging_dir):
                item_path = os.path.join(staging_dir, filename)

                # Prevent deleting protected directories if any (none for now)

                mtime = os.path.getmtime(item_path)
                if now - mtime > ttl:
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.remove(item_path)
                            count += 1
                        elif os.path.isdir(item_path):
                            # Recursively check subdirectories?
                            # For simplicity, we just remove the whole old directory in staging
                            shutil.rmtree(item_path)
                            count += 1
                    except Exception as e:
                        log.warning(f"Failed to remove {item_path}: {e}")

            if count > 0:
                log.info(f"Cleaned up {count} stale items from staging.")
        except Exception as e:
            log.warning(f"Error during staging cleanup: {e}")

    def _check_tasks(self):
        tasks = g_detached_task_registry.list_all()
        now = time.time()

        # Thresholds for cleanup
        completed_stale_threshold = 300  # 5 minutes
        launching_stale_threshold = 600  # 10 minutes
        # Tasks marked "running" but not synced for a long time should be checked
        running_auto_check_threshold = 600  # 10 minutes

        for task_id, meta in tasks.items():
            status = meta.get("status")
            last_sync = meta.get("last_sync", 0)
            created_at = meta.get("created_at", now)

            # 1. Cleanup stale completed or stuck launching tasks
            if status == "completed":
                if now - last_sync > completed_stale_threshold:
                    log.info(f"Purging stale completed detached task {task_id}")
                    g_detached_task_registry.unregister(task_id)
                    self._last_dispatch.pop(task_id, None)
                    continue
            elif status == "launching":
                if now - created_at > launching_stale_threshold:
                    log.info(f"Purging stuck launching detached task {task_id}")
                    g_detached_task_registry.unregister(task_id)
                    self._last_dispatch.pop(task_id, None)
                    continue

            # 2. Trigger push for active tasks with push_interval
            push_interval = meta.get("push_interval")
            last_dispatch = self._last_dispatch.get(task_id, 0)
            if push_interval:
                if status != "completed" and now - last_dispatch >= push_interval:
                    log.debug(f"Triggering push for task {task_id}")
                    self._trigger_push(task_id, meta)
            elif status == "running" and now - last_dispatch >= running_auto_check_threshold:
                # Even without push_interval, auto-sync "running" tasks occasionally
                # to ensure they are still alive.
                log.debug(f"Triggering auto-sync for running task {task_id}")
                # We don't trigger webhook push here, just a background sync
                # (handled by manage_detached_task updating the registry)
                self._trigger_push(task_id, meta, trigger_webhook=False)

    def _trigger_push(self, task_id: str, meta: dict, trigger_webhook: bool = True):
        """
        Dispatches a management job to read logs and trigger webhook/sync state.

        Important: This method does NOT write back to the registry to avoid
        race conditions with manage_detached_task (which updates status and
        last_offset). Dispatch throttling is handled via self._last_dispatch.
        """
        try:
            from ..models.common import DriverConnectionArgs, QueueStrategy
            from ..services.rpc import manage_detached_task, rpc_webhook_callback

            webhook_cfg = meta.get("webhook")
            # If we don't need webhook or don't have one, just sync state
            on_success = rpc_webhook_callback if (trigger_webhook and webhook_cfg) else None

            conn_arg = DriverConnectionArgs(**meta["connection_args"])

            # Reconstruct a dummy ExecutionRequest so the webhook callback can find the config
            from ..models.common import DriverName, WebHook
            from ..models.request import ExecutionRequest

            dummy_req = ExecutionRequest(
                driver=meta.get("driver", DriverName.PARAMIKO),
                connection_args=conn_arg,
                command=meta.get("command", ""),
                webhook=WebHook(**webhook_cfg) if webhook_cfg else None,
                detach=True,
            )

            # Dispatch job with the standard webhook callback (if requested)
            g_mgr.dispatch_rpc_job(
                conn_arg=conn_arg,
                q_strategy=QueueStrategy.PINNED,
                func=manage_detached_task,
                kwargs={
                    "task_id": task_id,
                    "action": "query",
                    "params": None,  # Let the worker fetch dynamic offset
                },
                on_success=on_success,
                on_failure=None,
                result_ttl=60,
                meta={
                    "task_id": task_id,
                    "req_payload": dummy_req.model_dump(mode="json"),
                    "webhook_event_type": "detached.log_push",
                },
            )

            # Track dispatch time locally — don't write back to registry
            # to avoid overwriting status/last_offset set by manage_detached_task
            self._last_dispatch[task_id] = time.time()

        except Exception as e:
            log.error(f"Failed to trigger push for task {task_id}: {e}")


g_supervisor = DetachedTaskSupervisor()
