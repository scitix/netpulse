import random
from collections import defaultdict
from typing import Dict, List, Tuple

from ....models import NodeInfo
from .. import BaseScheduler, WorkerUnavailableError


class LeastLoadRandomScheduler(BaseScheduler):
    scheduler_name = "least_load_random"

    def __init__(self):
        pass

    def node_select(self, nodes: List[NodeInfo], host: str) -> NodeInfo | None:
        """
        Select nodes using evenly distributed load balancing strategy.

        Algorithm:
            1. Filter out all nodes that are not fully loaded (n.count < n.capacity)
            2. Select the best node from the candidate nodes, with the following priorities:
                - The node with the least number of currently bound hosts (n.count is the smallest)
                - The node with the largest remaining capacity (n.capacity - n.count is the largest)
                - Select the node **randomly** from the best candidates
        """
        available_nodes = [n for n in nodes if n.count < n.capacity]

        if not available_nodes:
            raise WorkerUnavailableError("Insufficient capacity in node selection")

        # 1. find the min count
        min_count = min(n.count for n in available_nodes)
        phase1_candidates = [n for n in available_nodes if n.count == min_count]

        # 2. find the max remaining capacity
        max_remaining = max(n.capacity - n.count for n in phase1_candidates)
        phase2_candidates = [
            n for n in phase1_candidates if (n.capacity - n.count) == max_remaining
        ]

        # 3. random select
        selected_node = random.choice(phase2_candidates)

        return selected_node

    def batch_node_select(self, nodes: List[NodeInfo], hosts: List[str]) -> List[NodeInfo | None]:
        """
        Batch schedule multiple hosts using least load random strategy.

        Algorithm:
        1. Group nodes by their current load level
        2. For each load level (from least loaded):
           - Find nodes with maximum remaining capacity
           - Randomly distribute hosts among these nodes based on their capacity

        Time complexity: O(N log N) where N is number of nodes
        Space complexity: O(N)
        """
        host_count = len(hosts)
        if not hosts:
            return []

        # Quick capacity check
        total_available = sum(n.capacity - n.count for n in nodes)
        if total_available < host_count:
            raise WorkerUnavailableError("Insufficient capacity in node selection")

        # Group available nodes by count
        count_groups: Dict[int, List[Tuple[NodeInfo, int]]] = defaultdict(list)
        for node in nodes:
            if node.count < node.capacity:
                count_groups[node.count].append((node, node.capacity - node.count))

        result: list[NodeInfo | None] = [None] * host_count
        host_index = 0

        # Process each load level
        for count in sorted(count_groups.keys()):
            if host_index >= host_count:
                break

            nodes_at_count = count_groups[count]

            # Find max remaining capacity at this level
            max_remaining = max(remaining for _, remaining in nodes_at_count)
            best_nodes = [
                (node, remaining)
                for node, remaining in nodes_at_count
                if remaining == max_remaining
            ]

            # Calculate hosts we can assign at this level
            total_capacity = sum(remaining for _, remaining in best_nodes)
            hosts_for_level = min(total_capacity, host_count - host_index)

            # Randomly distribute hosts while respecting node capacities
            remaining_hosts = hosts_for_level
            while remaining_hosts > 0:
                # Randomly select from available nodes
                node_idx = random.randrange(len(best_nodes))
                node, remaining = best_nodes[node_idx]

                if remaining == 0:
                    # Remove fully utilized node
                    best_nodes.pop(node_idx)
                    continue

                # Assign a host to this node
                result[host_index] = node
                host_index += 1
                remaining_hosts -= 1

                # Update remaining capacity
                best_nodes[node_idx] = (node, remaining - 1)

        return result


__all__ = ["LeastLoadRandomScheduler"]
