import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Optional

from rq import Queue, Worker
from rq.command import send_shutdown_command
from rq.exceptions import InvalidJobOperation, NoSuchJobError
from rq.job import Job
from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry
from rq.worker import BaseWorker

from redis.client import Pipeline

from ..models import (
    BatchFailedItem,
    DriverConnectionArgs,
    JobAdditionalData,
    NodeInfo,
    QueueStrategy,
)
from ..models.request import ExecutionRequest
from ..models.response import JobInResponse, WorkerInResponse
from ..plugins import schedulers
from ..utils import g_config
from ..utils.exceptions import JobOperationError, WorkerUnavailableError
from .rediz import g_rdb
from .rpc import (
    execute,
    rpc_callback_factory,
    rpc_exception_callback,
    rpc_webhook_callback,
    spawn,
)

log = logging.getLogger(__name__)


class Manager:
    """
    Job, Queue and Worker Manager
    """

    def __init__(self):
        self.job_timeout: int = g_config.job.timeout
        self.job_result_ttl: int = g_config.job.result_ttl
        self.job_ttl: int = g_config.job.ttl

        self.worker_ttl: int = g_config.worker.ttl

        try:
            self.scheduler = schedulers[g_config.worker.scheduler]()
        except Exception as e:
            log.error(f"Unable to load scheduler {g_config.worker.scheduler}: {e}")
            raise e

        # IP <=> Node Mapping
        self.host_to_node_map = g_config.redis.key.host_to_node_map

        # Node Name <=> Node Info Mapping (Node is a container)
        self.node_info_map = g_config.redis.key.node_info_map

        # Redis connection
        self.rdb = g_rdb.conn

    def _check_worker_alive(self, q_name: str) -> bool:
        """
        Check if a worker is alive in the queue

        From controller side, we totally rely on the worker's heartbeat.
        However, if the job is blocking, the worker will not send heartbeat.
        So we have to consider the job's ttl as well.
        """
        workers = Worker.all(queue=Queue(q_name, connection=self.rdb))

        def is_alive(w: BaseWorker) -> bool:
            if w.death_date or w.last_heartbeat is None:
                return False

            interval = w.last_heartbeat.astimezone(timezone.utc) - datetime.now(timezone.utc)
            interval = interval.total_seconds()

            state = w.get_state()
            if state == "busy":
                return interval <= max(self.job_timeout, self.worker_ttl) + 5
            else:
                return interval <= self.worker_ttl + 5

        for w in workers:
            if is_alive(w):
                return True

        log.debug(f"{q_name} has no alive worker")
        return False

    def _get_assigned_node_for_host(
        self, hosts: str | list[str]
    ) -> NodeInfo | list[NodeInfo | None] | None:
        """
        Get assigned node info for host(s).

        NOTE:
        - str -> str | None
        - list[str] -> list[ NodeInfo | None ]
        """
        is_single = isinstance(hosts, str)
        hosts = [hosts] if isinstance(hosts, str) else hosts

        host_mappings: list = self.rdb.hmget(self.host_to_node_map, hosts)  # type: ignore
        if not any(host_mappings):
            return None if is_single else [None] * len(hosts)  # type: ignore

        # Preserve the order
        valid_data = [
            (idx, mapping) for idx, mapping in enumerate(host_mappings) if mapping is not None
        ]

        node_keys = [mapping for _, mapping in valid_data]
        node_values: list = self.rdb.hmget(self.node_info_map, node_keys) if node_keys else []  # type: ignore

        final_results: list[NodeInfo | None] = [None] * len(hosts)
        for (idx, _), value in zip(valid_data, node_values):
            if value:
                try:
                    final_results[idx] = NodeInfo.model_validate_json(value)
                except Exception as e:
                    log.error(f"Error in validating node info: {e}")
                    raise e

        return final_results[0] if is_single else final_results

    def _try_launch_pinned_worker(self, hosts: str | list[str], node: NodeInfo):
        """
        Try to launch Pinned Worker(s) on assigned node

        NOTE: This could fail if:
        1. Another controller has assigned the host to another node and it's quicker than us.
        2. The node has no capacity to run a new worker. The job will timeout.

        For 1, we can just use the existing worker (ignore).
        For 2, we have to reschedule (TODO).
        """
        is_single = isinstance(hosts, str)
        hosts = [hosts] if isinstance(hosts, str) else hosts

        funcs = [spawn] * len(hosts)
        kwargses = [{"q_name": g_config.get_host_queue_name(host), "host": host} for host in hosts]

        log.info(f"Try to pin host {hosts} on node {node.hostname}")

        _ = self._send_batch_jobs(
            q_name=node.queue,
            funcs=funcs,
            kwargses=kwargses,
        )

        return kwargses[0]["q_name"] if is_single else [k["q_name"] for k in kwargses]

    def _force_delete_node(self, node: NodeInfo):
        """
        Forcefully delete a node and all workers. This should only
        be called when the node is not available.

        Normally, `host_to_node_map` and `node_info_map` should be
        managed by its owner (NodeWorker) to avoid race condition.
        However, if the node is forced killed/disconnected, we have
        to clean up for the node.
        """
        keys_to_delete = []
        for host, node_name in self.rdb.hscan_iter(self.host_to_node_map):
            if node_name.decode() == node.hostname:
                keys_to_delete.append(host.decode())

        with self.rdb.pipeline() as pipe:
            if len(keys_to_delete):
                pipe.hdel(self.host_to_node_map, *keys_to_delete)

            pipe.hdel(self.node_info_map, node.hostname)
            pipe.execute()

        # Remove all running workers
        for host in keys_to_delete:
            q_name = g_config.get_host_queue_name(host)
            workers = Worker.all(queue=Queue(q_name, connection=self.rdb))
            # assert len(workers) == 1
            for w in workers:
                send_shutdown_command(worker_name=w.name, connection=self.rdb)

    def _send_job(
        self,
        q_name: str,
        func: Callable,
        kwargs: Optional[dict] = None,
        ttl: Optional[int] = None,
        result_ttl: Optional[int] = None,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
        pipeline: Optional[Pipeline] = None,
    ):
        if not on_failure:
            on_failure = rpc_exception_callback

        # Wraps the function with timeout in a Callback object
        on_success_cb = rpc_callback_factory(on_success, timeout=self.job_timeout)
        on_failure_cb = rpc_callback_factory(on_failure, timeout=self.job_timeout)

        # Use request result_ttl if provided, otherwise use system default
        effective_result_ttl = result_ttl if result_ttl is not None else self.job_result_ttl

        q = Queue(q_name, connection=self.rdb)
        job = q.enqueue_call(
            func=func,
            timeout=self.job_timeout,  # time limit for job execution
            ttl=ttl if ttl else self.job_ttl,  # job ttl in redis
            result_ttl=effective_result_ttl,  # result ttl in redis (from request or system default)
            failure_ttl=effective_result_ttl,  # errors ttl in redis
            kwargs=kwargs,
            meta=JobAdditionalData().model_dump(),
            on_success=on_success_cb,
            on_failure=on_failure_cb,
            pipeline=pipeline,
        )

        return job

    def _send_batch_jobs(
        self,
        q_name: str,
        funcs: list[Callable],
        kwargses: list[dict],
        ttl: Optional[int] = None,
        result_ttl: Optional[int] = None,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
    ):
        """
        Send multiple jobs to a single queue.
        Pipeline is auto created in this method.
        """
        assert len(funcs) == len(kwargses), "Function and kwargs mismatch"

        if not on_failure:
            on_failure = rpc_exception_callback

        # Wraps the function with timeout in a Callback object
        on_success_cb = rpc_callback_factory(on_success, timeout=self.job_timeout)
        on_failure_cb = rpc_callback_factory(on_failure, timeout=self.job_timeout)

        # Use request result_ttl if provided, otherwise use system default
        effective_result_ttl = result_ttl if result_ttl is not None else self.job_result_ttl

        jobs = []
        for func, kwargs in zip(funcs, kwargses):
            job = Queue.prepare_data(
                func=func,
                timeout=self.job_timeout,  # time limit for job execution
                ttl=ttl if ttl else self.job_ttl,  # job ttl in redis
                result_ttl=effective_result_ttl,  # result ttl (from request or default)
                failure_ttl=effective_result_ttl,  # errors ttl in redis
                kwargs=kwargs,
                meta=JobAdditionalData().model_dump(),
                on_success=on_success_cb,
                on_failure=on_failure_cb,
            )
            jobs.append(job)

        q = Queue(q_name, connection=self.rdb)
        jobs = q.enqueue_many(jobs)

        return jobs

    def get_node(self, node: str) -> NodeInfo | None:
        """
        Get the node info from the redis
        """
        # check the map in redis
        node_info: str | None = self.rdb.hget(self.node_info_map, node)  # type: ignore
        if not node_info:
            return None

        return NodeInfo.model_validate_json(node_info)

    def get_all_nodes(self) -> list[NodeInfo]:
        """
        Get all nodes from the redis
        """
        # check the map in redis
        nodes: dict[str, str] = self.rdb.hgetall(self.node_info_map)  # type: ignore
        if not nodes:
            return []

        # key: hostname of the node, value: node info
        return [NodeInfo.model_validate_json(node) for node in nodes.values()]

    def dispatch_rpc_job(
        self,
        conn_arg: DriverConnectionArgs,
        q_strategy: QueueStrategy,
        func: Callable,
        ttl: Optional[int] = None,
        result_ttl: Optional[int] = None,
        kwargs: Optional[dict] = None,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
    ):
        """
        Entry point for RPC calls

        Args:
            conn_arg: Connection arguments for the driver
            q_strategy: Queue strategy for the job (PINNED / FIFO)
            func: Function to be executed
            ttl: Job TTL in seconds
            kwargs: Additional arguments for the function
        """
        if conn_arg:
            host = conn_arg.host

        if q_strategy == QueueStrategy.FIFO:
            q_name = g_config.get_fifo_queue_name()
            if not self._check_worker_alive(q_name):
                raise WorkerUnavailableError("No available FIFO worker to run the job")
        elif q_strategy == QueueStrategy.PINNED:
            assert host, "Host is required for Pinned Worker"
            q_name = g_config.get_host_queue_name(host)

            # Lifecycle of a Pinned Worker:
            # None => Assigned => Pinned
            #  (host_to_node_map) (worker existed)

            # If not assigned, select a node and try to assign it
            # NOTE: Optimistic locking. The host could be assigned by
            # another worker. Checking is done in the Node Worker.
            cnt = 0
            MAX_RETRIES = 3
            while cnt <= MAX_RETRIES:
                cnt += 1
                node: Optional[NodeInfo] = self._get_assigned_node_for_host(host)  # type: ignore
                if node is None:
                    try:
                        log.debug(f"Host {host} is not assigned to any node")
                        node = self.scheduler.node_select(nodes=self.get_all_nodes(), host=host)
                    except Exception as e:
                        log.error(f"Error in selecting node for host {host}: {e}")
                        continue

                # Check if the assigned node is alive.
                # NOTE: Only forced exited node will left stale data.
                # If so, we need to cleanup and reassign
                if node is not None and not self._check_worker_alive(node.queue):
                    log.warning(f"Node {node.hostname} is not available, force deleting...")
                    self._force_delete_node(node)
                    node = None

                if node:
                    log.info(f"Selected node {node.hostname} for host {host}")
                    break

            if not node:
                raise WorkerUnavailableError("No available node to run the job")

            # If host is assigned but has no workers, could be 2 reasons:
            # 1. Host has just been assigned to a node, we need to create
            #    a worker. (duplicate request is fine, we handled it)
            # 2. (FIX?) Worker just died, and host_to_node_map is not updated yet.
            if not self._check_worker_alive(q_name):
                q_name = self._try_launch_pinned_worker(hosts=host, node=node)
        else:
            raise ValueError("Invalid queue strategy")

        assert isinstance(q_name, str), "Queue name must be a string"

        job = self._send_job(
            q_name=q_name,
            ttl=ttl,
            result_ttl=result_ttl,
            func=func,
            kwargs=kwargs,
            on_success=on_success,
            on_failure=on_failure,
        )
        return JobInResponse.from_job(job)

    def dispatch_bulk_rpc_jobs(
        self,
        conn_args: list[DriverConnectionArgs],
        q_strategy: QueueStrategy,
        func: Callable,
        kwargses: list[dict],
        ttl: Optional[int] = None,
        result_ttl: Optional[int] = None,
        on_success: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
    ) -> tuple[list[JobInResponse], list[BatchFailedItem]]:
        assert len(conn_args) == len(kwargses), "conn_args and kwargs mismatch"

        if q_strategy == QueueStrategy.FIFO:
            q_name = g_config.get_fifo_queue_name()
            if not self._check_worker_alive(q_name):
                raise WorkerUnavailableError("No available FIFO worker to run the job")

            jobs = self._send_batch_jobs(
                q_name=q_name,
                funcs=[func] * len(conn_args),
                kwargses=kwargses,
                ttl=ttl,
                result_ttl=result_ttl,
                on_success=on_success,
                on_failure=on_failure,
            )
            return [JobInResponse.from_job(job) for job in jobs], []

        assert q_strategy == QueueStrategy.PINNED, "Invalid queue strategy"

        hosts: list[str] = [conn.host for conn in conn_args]  # type: ignore
        nodes: list[NodeInfo | None] = self._get_assigned_node_for_host(hosts)  # type: ignore
        assert len(hosts) == len(nodes), "Host and node number mismatch"

        assigned_host_idx: list[int] = []
        unassigned_host_idx: list[int] = []
        failed_hosts: list[BatchFailedItem] = []

        for idx, n in enumerate(nodes):
            if not n:
                unassigned_host_idx.append(idx)
            else:
                assigned_host_idx.append(idx)

        # Schedule unassigned hosts
        if len(unassigned_host_idx) > 0:
            try:
                selected_nodes = self.scheduler.batch_node_select(
                    self.get_all_nodes(), [hosts[i] for i in unassigned_host_idx]
                )
                if not selected_nodes:
                    raise WorkerUnavailableError("No available nodes to run the job")

                # Track which hosts failed scheduling
                node_group: dict[int, list[int]] = defaultdict(list)
                for idx, n in enumerate(selected_nodes):
                    original_idx = unassigned_host_idx[idx]
                    if not n:
                        failed_hosts.append(
                            BatchFailedItem(host=hosts[original_idx], reason="No capacity on nodes")
                        )
                    else:
                        # group by node index (in selected_nodes)
                        node_group[idx].append(original_idx)

                for node_idx, orig_indices in node_group.items():
                    n = selected_nodes[node_idx]
                    assert n is not None
                    if not self._check_worker_alive(n.queue):
                        self._force_delete_node(n)
                        for i in orig_indices:
                            failed_hosts.append(
                                BatchFailedItem(host=hosts[i], reason=f"Node {n.hostname} dead")
                            )
                        continue

                    try:
                        self._try_launch_pinned_worker(
                            hosts=[hosts[i] for i in orig_indices], node=n
                        )
                    except Exception as e:
                        for i in orig_indices:
                            failed_hosts.append(BatchFailedItem(host=hosts[i], reason=str(e)))

            except Exception as e:
                log.error(f"Error in selecting nodes for hosts: {e}")
                for i in unassigned_host_idx:
                    # Only add if not already added in node_group loop
                    if not any(f.host == hosts[i] for f in failed_hosts):
                        failed_hosts.append(BatchFailedItem(host=hosts[i], reason=str(e)))

        # Indices of hosts that are actually ready to be sent
        ready_idx = assigned_host_idx + [
            i for i in unassigned_host_idx if not any(f.host == hosts[i] for f in failed_hosts)
        ]

        # Send out all jobs except failed ones
        succeeded_jobs: list[Job] = []
        if ready_idx:
            try:
                with self.rdb.pipeline() as pipe:
                    succeeded_jobs = [
                        self._send_job(
                            q_name=g_config.get_host_queue_name(hosts[idx]),
                            ttl=ttl,
                            result_ttl=result_ttl,
                            func=func,
                            kwargs=kwargses[idx],
                            on_success=on_success,
                            on_failure=on_failure,
                            pipeline=pipe,
                        )
                        for idx in ready_idx
                    ]
                    pipe.execute(raise_on_error=True)
            except Exception as e:
                log.warning(f"Error in sending batch jobs: {e}")
                for i in ready_idx:
                    failed_hosts.append(BatchFailedItem(host=hosts[i], reason=f"Redis error: {e}"))
                succeeded_jobs = []

        return [JobInResponse.from_job(job) for job in succeeded_jobs], failed_hosts

    def execute_on_device(self, req: ExecutionRequest):
        # q_strategy must be set before calling. Assert for robustness.
        assert req.queue_strategy, "Queue strategy is required for execution request"

        failure_handler, success_handler = None, None

        # Add webhook handler
        if req.webhook:
            success_handler = failure_handler = rpc_webhook_callback

        # NOTE: DO NOT change attr "req". It's hardcoded in webhook handler.
        r = self.dispatch_rpc_job(
            conn_arg=req.connection_args,
            q_strategy=req.queue_strategy,
            ttl=req.ttl,
            result_ttl=req.result_ttl,
            func=execute,
            kwargs={"req": req},
            on_success=success_handler,
            on_failure=failure_handler,
        )

        return r

    def execute_on_bulk_devices(self, reqs: list[ExecutionRequest]):
        # q_strategy must be set before calling. Assert for robustness.
        assert reqs and len(reqs) > 0, "Empty execution request list"
        assert reqs[0].queue_strategy, "Queue strategy is required for execution request"

        failure_handler, success_handler = None, None
        if reqs[0].webhook:
            success_handler = failure_handler = rpc_webhook_callback

        # Use first request's result_ttl for all jobs in batch (they should be the same)
        return self.dispatch_bulk_rpc_jobs(
            conn_args=[req.connection_args for req in reqs],
            q_strategy=reqs[0].queue_strategy,
            ttl=reqs[0].ttl,
            result_ttl=reqs[0].result_ttl,
            func=execute,
            kwargses=[{"req": req} for req in reqs],
            on_success=success_handler,
            on_failure=failure_handler,
        )

    def _get_all_job_id(self):
        keys: list[bytes] = self.rdb.keys(f"{Job.redis_job_namespace_prefix}*")  # type: ignore
        return [k.decode().split(":")[-1] for k in keys]

    def _get_job_id_by_status(self, state: str, q_name: str):
        """
        status can only be filtered by one queue name
        """
        q = Queue(q_name, connection=self.rdb)

        registry = None
        if state == "started":
            registry = StartedJobRegistry(queue=q, connection=self.rdb)
        elif state == "finished":
            registry = FinishedJobRegistry(queue=q, connection=self.rdb)
        elif state == "failed":
            registry = FailedJobRegistry(queue=q, connection=self.rdb)

        if registry is None:
            log.error(f"Invalid state: {state}")
            return []

        return registry.get_job_ids()

    def _get_job_id_by_status_all_queues(self, state: str):
        """
        Get job IDs by status from all queues
        """
        if state not in ["started", "finished", "failed", "queued"]:
            log.error(f"Invalid state: {state}")
            return []

        all_job_ids = []

        # Get all unique queue names from active workers
        queue_names = set()
        workers = Worker.all(connection=self.rdb)
        for worker in workers:
            queue_names.update(worker.queue_names())

        # Also include common queue names that might not have active workers
        queue_names.add(g_config.get_fifo_queue_name())  # FifoQ

        # For queued status, we need to check the queue itself, not a registry
        if state == "queued":
            for q_name in queue_names:
                try:
                    q = Queue(q_name, connection=self.rdb)
                    queued_jobs = q.get_job_ids()
                    all_job_ids.extend(queued_jobs)
                except Exception as e:
                    log.debug(f"Error getting queued jobs from queue {q_name}: {e}")
                    continue
        else:
            # For other states, use registries
            for q_name in queue_names:
                try:
                    job_ids = self._get_job_id_by_status(state, q_name)
                    all_job_ids.extend(job_ids)
                except Exception as e:
                    log.debug(f"Error getting {state} jobs from queue {q_name}: {e}")
                    continue

        return list(set(all_job_ids))  # Remove duplicates

    def get_job_list_by_ids(self, job_ids: list[str]):
        """Fetch and render a list of jobs"""
        return [
            JobInResponse.from_job(j)
            for j in Job.fetch_many(job_ids, connection=self.rdb)
            if j is not None
        ]

    def get_job_list(
        self,
        q_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        """Fetch jobs by some filters"""
        if q_name:
            # Status must be filtered with a queue name
            if status:
                job_ids = self._get_job_id_by_status(status, q_name)
                return self.get_job_list_by_ids(job_ids)[:limit] if job_ids else []

            q = Queue(q_name, connection=self.rdb)
            jobs = [JobInResponse.from_job(j) for j in q.get_jobs(length=limit if limit else -1)]
            return jobs[:limit] if limit else jobs

        # Handle status filtering without queue name
        if status:
            job_ids = self._get_job_id_by_status_all_queues(status)
            return self.get_job_list_by_ids(job_ids)[:limit] if job_ids else []

        jobs = self._get_all_job_id()[:limit]
        return self.get_job_list_by_ids(jobs) if jobs else []

    def cancel_job(self, id: Optional[str] = None, q_name: Optional[str] = None):
        """
        Cancel jobs by id or queue name
        """
        if id:
            try:
                job = Job.fetch(id, connection=self.rdb)
                if job.get_status() == "queued":
                    job.cancel()
                    return [id]
                else:
                    raise JobOperationError("Cannot cancel a job not in 'queued' state")
            except NoSuchJobError:
                return []
            except (InvalidJobOperation, JobOperationError) as e:
                # Log the error and return empty list for failed operations
                log.warning(f"Error in cancelling job {id}: {e}")
                return []

        cancelled = []
        if not q_name:
            return cancelled

        q = Queue(q_name, connection=self.rdb)
        for j in q.get_jobs():
            if j.get_status() == "queued":
                j.cancel()
                cancelled.append(j.id)

        return cancelled

    def get_worker_list(self, q_name: Optional[str] = None):
        """Fetch worker info by queue name"""
        if q_name is None:
            workers = Worker.all(connection=self.rdb)
        else:
            workers = Worker.all(queue=Queue(q_name, connection=self.rdb))
        return [WorkerInResponse.from_worker(w) for w in workers]

    def kill_worker(
        self, name: Optional[str] = None, q_name: Optional[str] = None
    ) -> list[str] | None:
        """
        Kill workers by name. If name not given, use queue name.
        """
        if name:
            send_shutdown_command(worker_name=name, connection=self.rdb)
            return [name]

        killed = []
        if not q_name:
            return killed

        workers = Worker.all(queue=Queue(q_name, connection=self.rdb))
        for w in workers:
            send_shutdown_command(worker_name=w.name, connection=self.rdb)
            killed.append(w.name)

        return killed


g_mgr = Manager()
