# Performance Tuning

This document provides some performance optimization recommendations for reference. Actual effects may vary by environment, recommend adjusting based on actual situation.

## Configuration Parameter Adjustment

### Worker Configuration

Adjust Worker count based on actual concurrency requirements:

```yaml
worker:
  scheduler: "load_weighted_random"  # or "least_load"
  pinned_per_node: 64                # Adjust based on server resources
  ttl: 300                           # Worker heartbeat timeout
```

**Reference Recommendations** (for reference only):
- Small environment (< 50 devices): `pinned_per_node: 32`
- Medium environment (50-200 devices): `pinned_per_node: 64`
- Large environment (> 200 devices): `pinned_per_node: 128`

!!! note "Note"
    Actual effects depend on server resources, network conditions, and device response speed, recommend starting from small values and gradually adjusting.

### Job Configuration

Adjust timeout and retention time based on task type:

```yaml
job:
  ttl: 3600          # Task queue survival time (seconds)
  timeout: 600       # Task execution timeout (seconds)
  result_ttl: 1800   # Result retention time (seconds)
```

**Reference Recommendations**:
- Fast query commands (e.g., `show version`): `timeout: 300`
- Configuration change operations: `timeout: 600`
- Batch operations: `timeout: 1800`

### Gunicorn Worker

```yaml
server:
  gunicorn_worker: 8  # Recommended formula: 2 * CPU cores + 1
```

## Queue Strategy

### FIFO Queue
- Use Cases: One-time operations, HTTP short connections
- Characteristics: Simple and universal

### Pinned Queue
- Use Cases: Frequent operations on same device
- Characteristics: Supports connection reuse, may improve performance

## Monitoring and Troubleshooting

### View System Status

```bash
# Health check
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health

# View container resource usage
docker stats

# View logs
docker compose logs | grep -E "(timeout|ERROR)"
```

## Common Issues

### Slow Task Execution

Possible causes:
- Insufficient Worker count
- Network latency
- Slow device response

Can try:
- Appropriately increase `pinned_per_node`
- Use Pinned queue strategy
- Increase task timeout

### High Memory Usage

Can try:
- Reduce `pinned_per_node` count
- Lower `result_ttl` value
- Restart Worker service

## Notes

1. Parameter adjustments need to be tested and verified in actual environment
2. Recommend gradual adjustment, observe effects
3. Monitor system resource usage
4. Set timeout appropriately, avoid too long or too short
