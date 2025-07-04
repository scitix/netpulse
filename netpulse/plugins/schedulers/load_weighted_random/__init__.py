import random
from typing import Dict, List

from ....models import NodeInfo
from .. import BaseScheduler, WorkerUnavailableError


class LoadWeightedRandomScheduler(BaseScheduler):
    scheduler_name = "load_weighted_random"

    def __init__(self):
        pass

    def node_select(self, nodes: List[NodeInfo], host: str) -> NodeInfo:
        """
        Select nodes using hash and weighted random strategy.

        Algorithm:
            1. Filter out all nodes that are not fully loaded (n.count < n.capacity)
            2. Calculate the base weight based on remaining capacity
            3. Add perturbation to the weights based on the host hash
            4. Randomly select a node based on the perturbed weights
        """
        available_nodes = [n for n in nodes if n.count < n.capacity]
        if not available_nodes:
            raise WorkerUnavailableError("Insufficient capacity in node selection")

        # Calculate the base weight based on remaining capacity
        base_weights = [n.capacity - n.count for n in available_nodes]

        # Perturb the weights based on the host hash
        host_hash = hash(host) % 1000 / 1000  # 0 <= host_hash < 1
        perturbed_weights = [
            w * (0.95 + 0.1 * ((host_hash + i / len(available_nodes)) % 1))
            for i, w in enumerate(base_weights)
        ]

        total_weight = sum(perturbed_weights)
        if total_weight <= 0:
            return random.choice(available_nodes)

        # Select the node based on the perturbed weights
        rand = random.uniform(0, total_weight)
        cumulative = 0
        for i, w in enumerate(perturbed_weights):
            cumulative += w
            if rand <= cumulative:
                return available_nodes[i]

    def batch_node_select(self, nodes: List[NodeInfo], hosts: List[str]) -> List[NodeInfo]:
        """
        Batch scheduling with controlled randomness to reduce node contention.

        Algorithm:
        1. Track remaining capacity in real-time
        2. For each host:
            a. Get all nodes with remaining capacity
            b. Calculate weights as (remaining_capacity + 1)^2 to prioritize underloaded nodes
            c. Add per-scheduler random noise (10% range) to break consistency
            d. Select node using weighted random choice
        3. Update remaining capacity immediately after selection

        Complexity: O(M*N) where M=hosts, N=nodes
        """
        remaining: Dict[NodeInfo, int] = {n: n.capacity - n.count for n in nodes}
        result = []

        # Check if there is enough capacity
        total_remaining = sum(remaining.values())
        if len(hosts) > total_remaining:
            raise WorkerUnavailableError(
                f"Total capacity {total_remaining} < requested hosts {len(hosts)}"
            )

        for _ in hosts:
            # Filter out nodes with no remaining capacity
            candidates = [n for n in nodes if remaining[n] > 0]
            if not candidates:
                raise WorkerUnavailableError("No available nodes during selection")

            # As we are using randomization, we have to do this every time
            weights = [(remaining[n] + 1) ** 2 for n in candidates]
            noisy_weights = [w * random.uniform(0.95, 1.05) for w in weights]

            total = sum(noisy_weights)
            r = random.uniform(0, total)
            acc = 0
            selected = None
            for n, w in zip(candidates, noisy_weights):
                acc += w
                if r <= acc:
                    selected = n
                    break

            if selected is None or remaining[selected] <= 0:
                raise WorkerUnavailableError("Selection failed unexpectedly")

            remaining[selected] -= 1
            result.append(selected)

        return result


__all__ = ["LoadWeightedRandomScheduler"]
