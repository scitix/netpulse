from datetime import datetime, timedelta, timezone
from types import MethodType

import pytest

from netpulse.models import DriverConnectionArgs, NodeInfo, QueueStrategy
from netpulse.services import manager as manager_module
from netpulse.services.manager import Manager
from netpulse.utils.exceptions import WorkerUnavailableError


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

    def get_status(self) -> str:
        return "queued"

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
