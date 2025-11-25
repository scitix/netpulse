import types

import pytest

from netpulse.models import NodeInfo
from netpulse.utils.exceptions import HostAlreadyPinnedError, NodePreemptedError
from netpulse.worker import node


def _seed_node_info(worker: node.NodeWorker, count: int, capacity: int = 2):
    info = NodeInfo(
        hostname=worker.name,
        count=count,
        capacity=capacity,
        queue=node.g_config.get_node_queue_name(worker.name),
    )
    worker.rdb.hset(worker.node_info_map, worker.name, info.model_dump_json())
    return info


def test_node_worker_add_registers_host(monkeypatch, fake_redis_conn):
    """NodeWorker.add should mark host pinned, bump count, and track pid."""
    worker = node.NodeWorker()
    _seed_node_info(worker, count=0, capacity=2)

    started: list[types.SimpleNamespace] = []

    class DummyProcess:
        def __init__(self, target):
            self.target = target
            self.pid = 1234
            self.started = False

        def start(self):
            self.started = True
            started.append(self)  # type: ignore

    monkeypatch.setattr(node, "Process", DummyProcess)

    worker.add(q_name="NodeQ_stub", host="host-A")

    # host pinned and node count incremented
    assert worker.rdb.hget(worker.host_to_node_map, "host-A") == worker.name.encode()
    stored = worker.rdb.hget(worker.node_info_map, worker.name)
    assert stored is not None
    updated = NodeInfo.model_validate_json(stored)  # type: ignore
    assert updated.count == 1
    # pid map recorded and process started
    assert worker._pid_to_host_map[1234] == "host-A"
    assert started and started[0].started is True


def test_node_worker_add_rejects_capacity():
    """NodeWorker.add should raise when node reaches capacity."""
    worker = node.NodeWorker()
    _seed_node_info(worker, count=2, capacity=2)

    with pytest.raises(NodePreemptedError):
        worker.add(q_name="NodeQ_stub", host="host-capacity")

    # No mapping should be written when capacity rejected
    assert worker.rdb.hget(worker.host_to_node_map, "host-capacity") is None


def test_node_worker_add_rejects_pinned_host(monkeypatch):
    """NodeWorker.add should reject hosts already pinned in Redis."""
    worker = node.NodeWorker()
    _seed_node_info(worker=worker, count=0, capacity=2)
    worker.rdb.hset(worker.host_to_node_map, mapping={"host-A": worker.name})

    with pytest.raises(HostAlreadyPinnedError):
        worker.add(q_name="NodeQ_stub", host="host-A")


def test_node_worker_remove_enqueues_cleanup(monkeypatch):
    """remove should enqueue NodeWorker._remove with pid/host."""
    worker = node.NodeWorker()
    worker.listened_queue = "NodeQ_stub"
    worker._pid_to_host_map[42] = "host-A"
    enqueued: list[tuple[object, dict | None]] = []

    class DummyQueue:
        def __init__(self, name, connection=None):
            self.name = name
            self.connection = connection

        def enqueue(self, func, kwargs=None):
            enqueued.append((func, kwargs))

    monkeypatch.setattr(node, "Queue", DummyQueue)

    worker.remove(42)

    assert enqueued
    func, kwargs = enqueued[0]
    assert func is node.NodeWorker._remove
    assert kwargs == {"pid": 42, "host": "host-A"}


def test_node_worker_static_remove_cleans_mappings(fake_redis_conn):
    """_remove should drop host mapping and decrement node count."""
    worker = node.NodeWorker()
    node.g_node_worker = worker
    info = NodeInfo(
        hostname=worker.name,
        count=1,
        capacity=2,
        queue=node.g_config.get_node_queue_name(worker.name),
    )
    worker.rdb.hset(worker.node_info_map, worker.name, info.model_dump_json())
    worker.rdb.hset(worker.host_to_node_map, "host-A", worker.name)
    worker._pid_to_host_map[77] = "host-A"

    node.NodeWorker._remove(pid=77, host="host-A")

    assert worker.rdb.hget(worker.host_to_node_map, "host-A") is None
    stored = worker.rdb.hget(worker.node_info_map, worker.name)
    assert stored is not None
    updated = NodeInfo.model_validate_json(stored)  # type: ignore
    assert updated.count == 0
    assert 77 not in worker._pid_to_host_map
    node.g_node_worker = None


def test_pinned_worker_listen_delegates_to_base(monkeypatch):
    """PinnedWorker.listen should call the base RedisWorker.listen."""
    calls: list[str] = []

    def fake_listen(self, q_name):
        calls.append(q_name)

    from netpulse.worker import pinned

    monkeypatch.setattr(pinned.RedisWorker, "listen", fake_listen)

    worker = pinned.PinnedWorker(q_name="HostQ_stub", host="host-A")
    worker.listen("HostQ_stub")

    assert calls == ["HostQ_stub"]


def test_node_worker_sigterm_sigint_sets_flag_and_stops():
    """Signal handler should mark signaled and call request_stop on active worker."""
    worker = node.NodeWorker()
    dummy_calls: list[tuple[int, object]] = []

    def fake_request_stop(signum, frame):
        dummy_calls.append((signum, frame))

    worker._worker = types.SimpleNamespace(request_stop=fake_request_stop)  # type: ignore
    node.g_node_worker = worker

    node.sigterm_sigint_handler(signum=15, frame="frame")

    assert worker.signaled is True
    assert dummy_calls == [(15, "frame")]

    node.g_node_worker = None
