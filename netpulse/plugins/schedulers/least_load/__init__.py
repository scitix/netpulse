from collections import defaultdict
from typing import Dict, List, Tuple

from ....models import NodeInfo
from .. import BaseScheduler, WorkerUnavailableError


class LeastLoadScheduler(BaseScheduler):
    scheduler_name = "least_load"

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
                - The node with the smallest alphabetical order of Hostname (deterministic)
        """
        # Select all available nodes
        available_nodes = [n for n in nodes if n.count < n.capacity]
        if not available_nodes:
            raise WorkerUnavailableError("Insufficient capacity in node selection")

        # Select the best node
        selected_node = None
        for node in available_nodes:
            if not selected_node:
                selected_node = node
                continue

            # 1. select the least count
            if node.count < selected_node.count:
                selected_node = node
            elif node.count == selected_node.count:
                # 2. select the max remaining capacity
                node_remaining = node.capacity - node.count
                selected_remaining = selected_node.capacity - selected_node.count
                if node_remaining > selected_remaining:
                    selected_node = node
                elif node_remaining == selected_remaining:
                    # 3. select the smallest alphabetical order of Hostname
                    if node.hostname < selected_node.hostname:
                        selected_node = node

        return selected_node

    def batch_node_select(self, nodes: List[NodeInfo], hosts: List[str]) -> List[NodeInfo | None]:
        """
        Batch schedule multiple hosts using minimum node amount.

        Algorithm:
        1. Calculate total available capacity and verify we can handle all hosts
        2. Group nodes by current load level for efficient assignment
        3. For each load level (starting from least loaded):
           - Assign hosts to nodes at this level optimally based on remaining capacity
           - Move to next load level if needed

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

        # Group nodes by their current load count for efficient access
        # {count: [(node, remaining_capacity), ...]}
        load_groups: Dict[int, List[Tuple[NodeInfo, int]]] = defaultdict(list)
        for node in nodes:
            if node.count < node.capacity:
                load_groups[node.count].append((node, node.capacity - node.count))

        # Sort each group by remaining capacity (desc) and hostname (asc)
        for count in load_groups:
            load_groups[count].sort(
                key=lambda x: (-x[1], x[0].hostname)  # -x[1] for desc capacity
            )

        # Initialize result array
        result: list[NodeInfo | None] = [None] * host_count
        host_index = 0

        # Process each load level from least to most loaded
        for count in sorted(load_groups.keys()):
            if host_index >= host_count:
                break

            nodes_at_level = load_groups[count]

            # Calculate how many hosts we can assign at this level
            hosts_for_level = min(
                sum(remaining for _, remaining in nodes_at_level),
                host_count - host_index,
            )

            # Assign hosts to nodes at this level
            remaining_in_level = hosts_for_level
            node_index = 0

            while remaining_in_level > 0 and node_index < len(nodes_at_level):
                node, remaining = nodes_at_level[node_index]
                # Assign as many hosts as this node can take
                assignments = min(remaining, remaining_in_level)

                # Store the assignments
                for _ in range(assignments):
                    result[host_index] = node
                    host_index += 1
                    remaining_in_level -= 1

                node_index += 1

        return result


__all__ = ["LeastLoadScheduler"]
