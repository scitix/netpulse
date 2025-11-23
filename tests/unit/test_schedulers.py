import random

import pytest

from netpulse.models import NodeInfo
from netpulse.plugins.schedulers.greedy import GreedyScheduler
from netpulse.plugins.schedulers.least_load import LeastLoadScheduler
from netpulse.plugins.schedulers.least_load_random import LeastLoadRandomScheduler
from netpulse.plugins.schedulers.load_weighted_random import LoadWeightedRandomScheduler
from netpulse.utils.exceptions import WorkerUnavailableError


def _nodes() -> list[NodeInfo]:
    return [
        NodeInfo(hostname="a", count=0, capacity=2, queue="q_a"),
        NodeInfo(hostname="b", count=1, capacity=3, queue="q_b"),
    ]


def test_greedy_scheduler_selects_first_available():
    sched = GreedyScheduler()
    nodes = _nodes()
    selected = sched.node_select(nodes, host="h")
    assert selected is not None
    assert selected.hostname == "a"

    nodes_full = [NodeInfo(hostname="a", count=2, capacity=2, queue="q_a")]
    with pytest.raises(WorkerUnavailableError):
        sched.node_select(nodes_full, host="h")


def test_least_load_scheduler_prefers_less_loaded_then_capacity_then_name():
    sched = LeastLoadScheduler()
    nodes = [
        NodeInfo(hostname="z", count=1, capacity=4, queue="q_z"),
        NodeInfo(hostname="a", count=1, capacity=5, queue="q_a"),
    ]
    selected = sched.node_select(nodes, host="h")
    assert selected is not None
    assert selected.hostname == "a"

    batch = sched.batch_node_select(nodes, hosts=["h1", "h2", "h3"])
    assert len(batch) == 3
    assert all(isinstance(n, NodeInfo) for n in batch)

    with pytest.raises(WorkerUnavailableError):
        sched.batch_node_select(
            nodes=[NodeInfo(hostname="x", count=2, capacity=2, queue="q")], hosts=["h1"]
        )


def test_least_load_random_scheduler_randomizes_best_candidates(monkeypatch):
    sched = LeastLoadRandomScheduler()
    nodes = [
        NodeInfo(hostname="a", count=1, capacity=3, queue="q_a"),
        NodeInfo(hostname="b", count=1, capacity=3, queue="q_b"),
    ]
    random.seed(0)
    choice1 = sched.node_select(nodes, host="h")
    random.seed(0)
    choice2 = sched.node_select(nodes, host="h")
    assert choice1.hostname == choice2.hostname

    batch = sched.batch_node_select(nodes, hosts=["h1", "h2"])
    assert len(batch) == 2
    assert all(isinstance(n, NodeInfo) for n in batch)


def test_load_weighted_random_scheduler_prefers_more_capacity(monkeypatch):
    sched = LoadWeightedRandomScheduler()
    nodes = [
        NodeInfo(hostname="low", count=1, capacity=2, queue="q_low"),
        NodeInfo(hostname="high", count=0, capacity=5, queue="q_high"),
    ]
    random.seed(1)
    chosen = sched.node_select(nodes, host="h")
    assert chosen.hostname in {"low", "high"}

    random.seed(1)
    batch = sched.batch_node_select(nodes, hosts=["h1", "h2", "h3"])
    assert len(batch) == 3
    assert batch.count(nodes[1]) >= batch.count(nodes[0])

    with pytest.raises(WorkerUnavailableError):
        sched.batch_node_select(
            [NodeInfo(hostname="x", count=1, capacity=1, queue="q")], hosts=["h1", "h2"]
        )
