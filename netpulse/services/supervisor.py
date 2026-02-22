import logging
import time

from .manager import g_mgr
from .rediz import g_detached_task_registry

log = logging.getLogger(__name__)


class DetachedTaskSupervisor:
    """
    Background supervisor that monitors the Detached Task Registry and triggers
    incremental log pushes via Webhooks based on the push_interval.
    """

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self.running = False
        self.staging_cleanup_interval = 3600  # Clean staging every hour
        self.last_staging_cleanup = 0

    def start(self):
        self.running = True
        log.info("NetPulse Supervisor started.")
        while self.running:
            try:
                now = time.time()
                self._check_tasks()

                # Periodic cleaning of staging directory (24h TTL)
                if now - self.last_staging_cleanup > self.staging_cleanup_interval:
                    self._cleanup_staging()
                    self.last_staging_cleanup = now

            except Exception as e:
                log.error(f"Error in Supervisor loop: {e}")
            time.sleep(self.interval)

    def stop(self):
        self.running = False

    def _cleanup_staging(self):
        """
        Cleanup files in staging/downloads older than 24 hours.
        """
        import os

        from ..utils import g_config

        staging_dir = str(g_config.storage.staging)
        download_dir = os.path.join(staging_dir, "downloads")

        if not os.path.exists(download_dir):
            return

        now = time.time()
        ttl = 86400  # 24 hours in seconds

        log.info(f"Starting staging cleanup in {download_dir}...")
        count = 0
        import shutil
        try:
            for filename in os.listdir(download_dir):
                item_path = os.path.join(download_dir, filename)
                mtime = os.path.getmtime(item_path)
                if now - mtime > ttl:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    count += 1
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
                    continue
            elif status == "launching":
                if now - created_at > launching_stale_threshold:
                    log.info(f"Purging stuck launching detached task {task_id}")
                    g_detached_task_registry.unregister(task_id)
                    continue

            # 2. Trigger push for active tasks with push_interval
            push_interval = meta.get("push_interval")
            if push_interval:
                if status != "completed" and now - last_sync >= push_interval:
                    log.debug(f"Triggering push for task {task_id}")
                    self._trigger_push(task_id, meta)
            elif status == "running" and now - last_sync >= running_auto_check_threshold:
                # Even without push_interval, auto-sync "running" tasks occasionally
                # to ensure they are still alive.
                log.debug(f"Triggering auto-sync for running task {task_id}")
                # We don't trigger webhook push here, just a background sync
                # (handled by manage_detached_task updating the registry)
                self._trigger_push(task_id, meta, trigger_webhook=False)

    def _trigger_push(self, task_id: str, meta: dict, trigger_webhook: bool = True):
        """
        Dispatches a management job to read logs and trigger webhook/sync state.
        """
        last_offset = meta.get("last_offset", 0)

        # Update last_sync immediately to avoid double triggers
        meta["last_sync"] = time.time()
        g_detached_task_registry.register(task_id, meta)

        try:
            from ..models.common import DriverConnectionArgs, QueueStrategy
            from ..models.request import ExecutionRequest, WebHook
            from ..services.rpc import manage_detached_task, rpc_webhook_callback

            webhook_cfg = meta.get("webhook")
            # If we don't need webhook or don't have one, just sync state
            on_success = rpc_webhook_callback if (trigger_webhook and webhook_cfg) else None

            conn_arg = DriverConnectionArgs(**meta["connection_args"])

            req = ExecutionRequest(
                driver=meta["driver"],
                connection_args=meta["connection_args"],
                command=meta.get("command", ""),
                detach=True,
                webhook=WebHook(**webhook_cfg) if webhook_cfg else None,
            )

            # Dispatch job with the standard webhook callback (if requested)
            g_mgr.dispatch_rpc_job(
                conn_arg=conn_arg,
                q_strategy=QueueStrategy.PINNED,
                func=manage_detached_task,
                kwargs={
                    "task_id": task_id,
                    "action": "query",
                    "params": {"offset": last_offset},
                    "req": req,
                },
                on_success=on_success,
                on_failure=None,
                result_ttl=60,
                meta={"task_id": task_id},
            )

        except Exception as e:
            log.error(f"Failed to trigger push for task {task_id}: {e}")


g_supervisor = DetachedTaskSupervisor()
