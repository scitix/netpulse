from datetime import datetime, timedelta, timezone
from types import MethodType

import pytest

from netpulse.models import DriverConnectionArgs, JobAdditionalData, NodeInfo, QueueStrategy
from netpulse.services import manager as manager_module
from netpulse.services.manager import Manager
from netpulse.utils.exceptions import WorkerUnavailableError


def _dummy_job_func(*_args, **_kwargs):
    return "ok"


def _dummy_success(*_args, **_kwargs):
    return "success"


def _dummy_failure(*_args, **_kwargs):
    return "failure"


class FakeJob:
    id: str
    origin: str
    worker_name: str | None
    meta: dict
    created_at: datetime | None
    enqueued_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None

    def __init__(self, job_id: str, origin: str = "q", worker: str | None = "w"):
        self.id = job_id
        self.origin = origin
        self.worker_name = worker
        self.meta = {}
        self.created_at = None
        self.enqueued_at = None
        self.started_at = None
        self.ended_at = None

    def get_status(self):
        from rq.job import JobStatus

        return JobStatus.QUEUED

    def latest_result(self):
        return None


class StubScheduler:
    def __init__(self, node: NodeInfo):
        self.node = node

    def node_select(self, nodes: list[NodeInfo], host: str) -> NodeInfo:
        return self.node

    def batch_node_select(self, nodes: list[NodeInfo], hosts: list[str]) -> list[NodeInfo]:
        return [self.node for _ in hosts]


class StubWorker:
    def __init__(self, state: str, heartbeat_age: int, death_date: datetime | None = None):
        self._state = state
        self.death_date = death_date
        self.last_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=heartbeat_age)
        self.pid = 1
        self.hostname = "stub"

    def get_state(self) -> str:
        return self._state

    def queue_names(self) -> list[str]:
        return ["q"]

    successful_job_count = 0
    failed_job_count = 0


def test_check_worker_alive_respects_timeout(monkeypatch, app_config):
    """Worker liveness should depend on heartbeat age and death_date."""
    mgr = Manager()

    # Alive worker: heartbeat within ttl
    monkeypatch.setattr(
        manager_module.Worker,
        "all",
        classmethod(lambda cls, queue=None, connection=None: [StubWorker("busy", heartbeat_age=1)]),
    )
    assert mgr._check_worker_alive("anyq") is True

    # Dead worker: heartbeat far past ttl
    monkeypatch.setattr(
        manager_module.Worker,
        "all",
        classmethod(
            lambda cls, queue=None, connection=None: [
                StubWorker("busy", heartbeat_age=9999, death_date=datetime.now(timezone.utc))
            ]
        ),
    )
    assert mgr._check_worker_alive("anyq") is False


def test_dispatch_rpc_job_fifo_requires_worker(monkeypatch, app_config):
    """FIFO dispatch raises without worker and returns JobInResponse when alive."""
    mgr = Manager()
    mgr.scheduler = StubScheduler(NodeInfo(hostname="n", count=0, capacity=1, queue="NodeQ_n"))  # type: ignore

    # No worker alive -> raises
    monkeypatch.setattr(mgr, "_check_worker_alive", MethodType(lambda self, q: False, mgr))
    with pytest.raises(WorkerUnavailableError):
        mgr.dispatch_rpc_job(
            conn_arg=DriverConnectionArgs(host="1.1.1.1"),
            q_strategy=QueueStrategy.FIFO,
            func=lambda: None,
        )

    # Worker alive -> returns JobInResponse
    monkeypatch.setattr(mgr, "_check_worker_alive", MethodType(lambda self, q: True, mgr))
    monkeypatch.setattr(
        mgr,
        "_send_job",
        MethodType(lambda self, **kwargs: FakeJob(job_id="job-fifo", origin=kwargs["q_name"]), mgr),
    )
    resp = mgr.dispatch_rpc_job(
        conn_arg=DriverConnectionArgs(host="1.1.1.1"),
        q_strategy=QueueStrategy.FIFO,
        func=lambda: None,
    )
    assert resp.id == "job-fifo"
    assert resp.queue == app_config.get_fifo_queue_name()


def test_dispatch_bulk_pinned(monkeypatch, app_config):
    """Pinned bulk dispatch sends jobs per-host when workers are available."""
    node = NodeInfo(hostname="node1", count=0, capacity=2, queue="NodeQ_node1")
    mgr = Manager()
    mgr.scheduler = StubScheduler(node)  # type: ignore

    monkeypatch.setattr(
        mgr, "_get_assigned_node_for_host", MethodType(lambda self, hosts: [None] * len(hosts), mgr)
    )
    monkeypatch.setattr(
        mgr, "_try_launch_pinned_worker", MethodType(lambda self, hosts, node: "HostQ_stub", mgr)
    )
    monkeypatch.setattr(mgr, "_check_worker_alive", MethodType(lambda self, q: True, mgr))
    sent_jobs: list[str] = []

    def fake_send(self, **kwargs) -> FakeJob:
        host = kwargs["kwargs"]["req"].connection_args.host
        job = FakeJob(job_id=f"job-{host}", origin=kwargs["q_name"])
        sent_jobs.append(host)
        return job

    monkeypatch.setattr(mgr, "_send_job", MethodType(fake_send, mgr))

    class ReqObj:
        connection_args: DriverConnectionArgs

        def __init__(self, host: str):
            self.connection_args = DriverConnectionArgs(host=host)

    conn_args = [DriverConnectionArgs(host="h1"), DriverConnectionArgs(host="h2")]
    kwargses = [{"req": ReqObj("h1")}, {"req": ReqObj("h2")}]

    jobs, failed = mgr.dispatch_bulk_rpc_jobs(
        conn_args=conn_args,
        q_strategy=QueueStrategy.PINNED,
        func=lambda: None,
        kwargses=kwargses,
    )

    assert failed == []
    assert {j.id for j in jobs} == {"job-h1", "job-h2"}
    assert set(sent_jobs) == {"h1", "h2"}


def test_dispatch_rpc_job_fifo_sets_callbacks_and_meta(monkeypatch, fake_redis_conn, app_config):
    """dispatch_rpc_job should enqueue to fifo queue with TTL, callbacks, and meta."""
    from rq import Queue

    mgr = Manager()
    monkeypatch.setattr(mgr, "_check_worker_alive", lambda q: True)

    resp = mgr.dispatch_rpc_job(
        conn_arg=DriverConnectionArgs(host="10.0.0.1"),
        q_strategy=QueueStrategy.FIFO,
        func=_dummy_job_func,
        ttl=123,
        kwargs={"req": "x"},
        on_success=_dummy_success,
        on_failure=_dummy_failure,
    )

    q = Queue(manager_module.g_config.get_fifo_queue_name(), connection=mgr.rdb)
    job = q.fetch_job(resp.id)
    assert job is not None
    assert job.origin == manager_module.g_config.get_fifo_queue_name()
    assert job.ttl == 123
    assert job.meta == JobAdditionalData().model_dump()
    assert job._success_callback_name and job._failure_callback_name
    assert job._success_callback_name.endswith("_dummy_success")
    assert job._failure_callback_name.endswith("_dummy_failure")
    assert job._success_callback_timeout == mgr.job_timeout
    assert job._failure_callback_timeout == mgr.job_timeout


def test_dispatch_rpc_job_pinned_uses_host_queue(monkeypatch, fake_redis_conn):
    """Pinned dispatch should target host queue when worker alive."""
    from rq import Queue

    mgr = Manager()
    node = NodeInfo(hostname="n1", count=0, capacity=1, queue="NodeQ_n1")
    monkeypatch.setattr(mgr, "_get_assigned_node_for_host", lambda host: node)
    monkeypatch.setattr(mgr, "_check_worker_alive", lambda q: True)

    resp = mgr.dispatch_rpc_job(
        conn_arg=DriverConnectionArgs(host="h1"),
        q_strategy=QueueStrategy.PINNED,
        func=_dummy_job_func,
        ttl=77,
        kwargs={"req": "y"},
        on_success=_dummy_success,
        on_failure=_dummy_failure,
    )

    host_q = manager_module.g_config.get_host_queue_name("h1")
    job = Queue(host_q, connection=mgr.rdb).fetch_job(resp.id)
    assert job is not None
    assert job.origin == host_q
    assert job.ttl == 77
    assert job._success_callback_name and job._failure_callback_name
    assert job._success_callback_name.endswith("_dummy_success")
    assert job._failure_callback_name.endswith("_dummy_failure")


def test_dispatch_bulk_fifo_applies_ttl_and_callbacks(monkeypatch, fake_redis_conn):
    """FIFO bulk dispatch should enqueue all jobs with provided TTL and callbacks."""
    from rq import Queue

    mgr = Manager()
    monkeypatch.setattr(mgr, "_check_worker_alive", lambda q: True)

    conn_args = [DriverConnectionArgs(host="h1"), DriverConnectionArgs(host="h2")]
    kwargses = [{"req": "a"}, {"req": "b"}]

    jobs, failed = mgr.dispatch_bulk_rpc_jobs(
        conn_args=conn_args,
        q_strategy=QueueStrategy.FIFO,
        func=_dummy_job_func,
        kwargses=kwargses,
        ttl=200,
        on_success=_dummy_success,
        on_failure=_dummy_failure,
    )

    assert failed == []
    q = Queue(manager_module.g_config.get_fifo_queue_name(), connection=mgr.rdb)
    assert len(jobs) == 2
    for job_resp in jobs:
        job = q.fetch_job(job_resp.id)
        assert job is not None
        assert job.ttl == 200
        assert job.meta == JobAdditionalData().model_dump()
        assert job._success_callback_name and job._failure_callback_name
        assert job._success_callback_name.endswith("_dummy_success")
        assert job._failure_callback_name.endswith("_dummy_failure")


def test_dispatch_bulk_pinned_assigns_nodes_and_enqueues(monkeypatch, fake_redis_conn):
    """Pinned bulk dispatch should select nodes when mapping missing and enqueue per host."""
    from rq import Queue

    mgr = Manager()
    node = NodeInfo(
        hostname="node1",
        count=0,
        capacity=2,
        queue=manager_module.g_config.get_node_queue_name("node1"),
    )
    mgr.scheduler = StubScheduler(node)  # type: ignore

    mgr.rdb.hset(mgr.node_info_map, node.hostname, node.model_dump_json())

    monkeypatch.setattr(mgr, "_check_worker_alive", lambda q: True)
    launch_calls: list[tuple[list[str], NodeInfo]] = []

    def fake_launch(hosts, node):
        launch_calls.append((hosts, node))
        return [manager_module.g_config.get_host_queue_name(h) for h in hosts]

    monkeypatch.setattr(mgr, "_try_launch_pinned_worker", fake_launch)

    conn_args = [DriverConnectionArgs(host="h1"), DriverConnectionArgs(host="h2")]
    kwargses = [{"req": "r1"}, {"req": "r2"}]

    jobs, failed = mgr.dispatch_bulk_rpc_jobs(
        conn_args=conn_args,
        q_strategy=QueueStrategy.PINNED,
        func=_dummy_job_func,
        kwargses=kwargses,
        ttl=150,
        on_success=_dummy_success,
        on_failure=_dummy_failure,
    )

    assert failed == []
    launched_hosts = [h for hosts, _ in launch_calls for h in hosts]
    assert set(launched_hosts) == {"h1", "h2"}
    for host, job_resp in zip(["h1", "h2"], jobs):
        q = Queue(manager_module.g_config.get_host_queue_name(host), connection=mgr.rdb)
        job = q.fetch_job(job_resp.id)
        assert job is not None
        assert job.origin == manager_module.g_config.get_host_queue_name(host)
        assert job.ttl == 150
        assert job.meta == JobAdditionalData().model_dump()
        assert job._success_callback_name and job._failure_callback_name
        assert job._success_callback_name.endswith("_dummy_success")
        assert job._failure_callback_name.endswith("_dummy_failure")


def test_force_delete_node_cleans_mappings(monkeypatch, fake_redis_conn):
    """_force_delete_node should drop host/node mappings and signal shutdown."""
    from types import SimpleNamespace

    mgr = Manager()
    node = NodeInfo(hostname="nodeA", count=1, capacity=1, queue="NodeQ_nodeA")
    other_node = NodeInfo(hostname="nodeB", count=1, capacity=1, queue="NodeQ_nodeB")

    mgr.rdb.hset(mgr.host_to_node_map, mapping={"h1": node.hostname, "h2": other_node.hostname})
    mgr.rdb.hset(mgr.node_info_map, node.hostname, node.model_dump_json())
    mgr.rdb.hset(mgr.node_info_map, other_node.hostname, other_node.model_dump_json())

    shutdown_calls: list[str] = []

    def fake_shutdown(worker_name, connection=None):
        shutdown_calls.append(worker_name)

    def fake_worker_all(cls, queue=None, connection=None):
        return [SimpleNamespace(name=f"worker-{queue.name}")]  # type: ignore

    monkeypatch.setattr(manager_module, "send_shutdown_command", fake_shutdown)
    monkeypatch.setattr(manager_module.Worker, "all", classmethod(fake_worker_all))

    mgr._force_delete_node(node)

    assert mgr.rdb.hget(mgr.host_to_node_map, "h1") is None
    assert mgr.rdb.hget(mgr.host_to_node_map, "h2") == other_node.hostname.encode()
    assert mgr.rdb.hget(mgr.node_info_map, node.hostname) is None
    assert mgr.rdb.hget(mgr.node_info_map, other_node.hostname) is not None
    assert shutdown_calls == ["worker-HostQ_h1"]
