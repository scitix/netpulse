from typing import List

from ....models import NodeInfo
from .. import BaseScheduler, WorkerUnavailableError


class GreedyScheduler(BaseScheduler):
    scheduler_name = "greedy"

    def __init__(self):
        pass

    def node_select(self, nodes: List[NodeInfo], host: str) -> NodeInfo | None:
        """
        Find first available node with capacity.
        """
        for n in nodes:
            if n.count < n.capacity:
                return n
        raise WorkerUnavailableError("Insufficient capacity in node selection")

    def batch_node_select(self, nodes: List[NodeInfo], hosts: List[str]) -> List[NodeInfo | None]:
        """
        Use least nodes for hosts.
        """
        host_count = len(hosts)
        if host_count == 0:
            return []

        # Check total capacity
        total_available = sum(n.capacity - n.count for n in nodes)
        if total_available < host_count:
            raise WorkerUnavailableError("Insufficient capacity in node selection")

        # Use a simple greedy algorithm to assign hosts to nodes
        available_nodes = [n for n in nodes if n.count < n.capacity]
        available_nodes.sort(key=lambda x: (-x.count, -(x.capacity - x.count), x.hostname))

        result = []
        remaining = host_count
        for node in available_nodes:
            if remaining <= 0:
                break
            assign = min(node.capacity - node.count, remaining)
            result.extend([node] * assign)
            remaining -= assign

        return result


__all__ = ["GreedyScheduler"]
