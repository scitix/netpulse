# Scheduler System

Schedulers select which **Node Worker** should host a new Pinned Worker when a device is first targeted. They don't route individual tasks — that happens via Redis queues.

## Algorithms

Default is `load_weighted_random`, suitable for most deployments.

| Algorithm | Deterministic | Conflict Risk | Best For |
|-----------|--------------|---------------|----------|
| `greedy` | Yes | High | Single-node or 1-2 node deployments |
| `least_load` | Yes | Medium | Multi-node, need predictable results |
| `least_load_random` | No | Low | High concurrency, 3+ nodes |
| `load_weighted_random` ⭐ | No | Very Low | Large-scale, high concurrency |

**Quick selection:**
```
Single node?              → greedy
Need deterministic output? → least_load
High concurrency?          → load_weighted_random (default)
```

## How Each Works

### greedy
Picks the **first** node with available capacity. Simple, fast, but concentrates load on one node.

### least_load
Three-phase selection: minimum current load → maximum remaining capacity → lexicographic hostname (for tie-breaking). Fully deterministic.

### least_load_random
Same as `least_load` for phases 1-2, but randomly picks among the best candidates instead of using hostname tie-breaking. Reduces scheduling conflicts in concurrent scenarios.

### load_weighted_random (default)
Weight = `(capacity - current_count)`. Adds a host-based hash perturbation + ±5% random noise, then does weighted random selection. Maximizes conflict reduction across high-concurrency batch operations.

## Scheduling Conflicts

A conflict occurs when two Controllers simultaneously pick the same node for different devices, and one request fails due to capacity limits. Randomized algorithms significantly reduce this probability.

| Algorithm | Conflict probability (3 nodes, each 50% loaded) |
|-----------|-------------------------------------------------|
| `greedy` | High — always picks node 1 |
| `least_load` | Medium — same node for same load state |
| `least_load_random` | Low |
| `load_weighted_random` | Very Low |

## Configuration

Set in `config/config.yaml`:

```yaml
worker:
  scheduler: "load_weighted_random"
```

After changing, restart the controller and node workers:

```bash
docker compose restart controller node-worker
```

!!! warning
    A misconfigured scheduler plugin prevents the system from working. Restart during low-traffic periods.
