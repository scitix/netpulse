# Performance Tuning Guide

NetPulse supports various performance optimization parameters to help users adjust system performance according to actual requirements.

## Main Optimization Points

- Connection pool parameters (such as maximum connections, timeout)
- Caching (such as Redis cache, TTL settings)
- Database connection pool parameters

## Connection Pool Configuration

```yaml
connection_pool:
  max_size: 50           # Maximum connections
  min_size: 10           # Minimum connections
  max_idle_time: 300     # Idle timeout
  keepalive_interval: 60 # Keepalive interval
```

## Cache Configuration

```yaml
cache:
  ttl: 3600              # Cache validity period
  max_size: 1000         # Maximum cache entries
  eviction_policy: "lru" # Eviction policy
```

## Database Optimization

```yaml
database:
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
  echo: false
```

## Recommendations/Planning
- It is recommended to adjust connection pool and cache parameters based on actual concurrency.
- It is recommended to regularly monitor system resources and scale up in time.
- Complex dynamic worker pools, multi-level caching, etc. are recommended/planned features and are not currently implemented.

## Performance Tuning Overview

### Optimization Goals
- Improve API response speed
- Increase concurrent processing capability
- Reduce resource consumption
- Enhance system stability

### Optimization Dimensions
- System configuration optimization
- Connection pool tuning
- Cache strategy optimization
- Database optimization
- Network optimization

## System Configuration Optimization

### 1. Worker Configuration
```yaml
# Worker configuration optimization
worker:
  pool_size: 20          # Worker pool size
  max_connections: 100   # Maximum connections
  queue_size: 1000       # Queue size
  timeout: 30            # Timeout
```

### 2. Connection Pool Monitoring
```python
class ConnectionPoolMonitor:
    def __init__(self):
        self.metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "connection_requests": 0,
            "connection_wait_time": 0
        }
    
    def get_utilization(self):
        """Get connection pool utilization"""
        if self.metrics["total_connections"] == 0:
            return 0
        return (self.metrics["active_connections"] / 
                self.metrics["total_connections"]) * 100
    
    def should_expand(self):
        """Determine if expansion is needed"""
        utilization = self.get_utilization()
        return utilization > 80 and self.metrics["connection_requests"] > 10
```

## Connection Pool Tuning

### Connection Pool Parameter Description
```python
class ConnectionPoolConfig:
    def __init__(self):
        self.max_connections = 50      # Maximum connections
        self.min_connections = 10      # Minimum connections
        self.max_idle_time = 300       # Idle timeout
        self.connection_timeout = 30   # Connection timeout
        self.keepalive_interval = 60   # Keepalive interval
        self.keepalive_count = 3       # Keepalive count
```

### Dynamic Adjustment Strategy
```python
class AdaptiveConnectionPool:
    def __init__(self, initial_size=10, max_size=100):
        self.current_size = initial_size
        self.max_size = max_size
        self.monitor = ConnectionPoolMonitor()
    
    def adjust_pool_size(self):
        """Dynamically adjust connection pool size"""
        utilization = self.monitor.get_utilization()
        
        if utilization > 80 and self.current_size < self.max_size:
            # Expand
            new_size = min(self.current_size * 2, self.max_size)
            self.expand_pool(new_size)
        elif utilization < 30 and self.current_size > 10:
            # Shrink
            new_size = max(self.current_size // 2, 10)
            self.shrink_pool(new_size)
```

## Cache Strategy Optimization

### Multi-Level Cache Architecture
```python
class MultiLevelCache:
    def __init__(self):
        self.l1_cache = {}  # Memory cache
        self.l2_cache = Redis()  # Redis cache
        self.l3_cache = Database()  # Database cache
    
    async def get(self, key):
        """Multi-level cache query"""
        # L1 cache query
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # L2 cache query
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
        
        # L3 cache query
        value = await self.l3_cache.get(key)
        if value:
            await self.l2_cache.set(key, value)
            self.l1_cache[key] = value
            return value
        
        return None
```

### Cache Warming
```python
class CacheWarmer:
    def __init__(self, cache):
        self.cache = cache
    
    async def warm_up(self, keys):
        """Cache warming"""
        for key in keys:
            value = await self.fetch_from_source(key)
            await self.cache.set(key, value)
    
    async def warm_up_devices(self, hostnames):
        """Warm up device information cache"""
        for hostname in hostnames:
            # Warm up basic device information
            device_info = await self.get_device_info(hostname)
            await self.cache.set(f"device:{hostname}", device_info)
            
            # Warm up common command results
            common_commands = ["show version", "show interfaces"]
            for command in common_commands:
                result = await self.execute_command(hostname, command)
                await self.cache.set(f"cmd:{hostname}:{command}", result)
```

## Database Optimization

### Query Optimization
```python
class DatabaseOptimizer:
    def __init__(self, db):
        self.db = db
    
    async def optimize_queries(self):
        """Optimize database queries"""
        # Add indexes for frequently queried fields
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_status 
            ON jobs(status)
        """)
        
        await self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_hostname 
            ON jobs(hostname)
        """)
        
        # Optimize slow queries
        await self.db.execute("""
            ANALYZE TABLE jobs
        """)
```

### Connection Pool Optimization
```python
class DatabaseConnectionPool:
    def __init__(self):
        self.pool_size = 20
        self.max_overflow = 30
        self.pool_timeout = 30
        self.pool_recycle = 3600
    
    def get_optimal_pool_size(self, concurrent_users):
        """Calculate optimal pool size based on concurrent users"""
        # Rule of thumb: pool_size = concurrent_users * 2
        return min(concurrent_users * 2, 100)
    
    def adjust_pool_parameters(self, load_factor):
        """Adjust pool parameters based on load"""
        if load_factor > 0.8:
            # High load - increase pool size
            self.pool_size = min(self.pool_size * 1.5, 100)
            self.max_overflow = min(self.max_overflow * 1.5, 50)
        elif load_factor < 0.3:
            # Low load - decrease pool size
            self.pool_size = max(self.pool_size * 0.8, 10)
            self.max_overflow = max(self.max_overflow * 0.8, 10)
```

## Network Optimization

### Connection Reuse
```python
class ConnectionManager:
    def __init__(self):
        self.connections = {}
        self.max_connections_per_device = 5
    
    async def get_connection(self, device_info):
        """Get or create connection for device"""
        device_key = f"{device_info.host}:{device_info.port}"
        
        if device_key in self.connections:
            connection = self.connections[device_key]
            if connection.is_alive():
                return connection
        
        # Create new connection
        connection = await self.create_connection(device_info)
        self.connections[device_key] = connection
        return connection
    
    async def cleanup_idle_connections(self):
        """Clean up idle connections"""
        for device_key, connection in list(self.connections.items()):
            if not connection.is_alive() or connection.is_idle():
                await connection.close()
                del self.connections[device_key]
```

### Batch Operations
```python
class BatchProcessor:
    def __init__(self, max_batch_size=100):
        self.max_batch_size = max_batch_size
    
    async def process_batch(self, operations):
        """Process operations in batches"""
        results = []
        
        for i in range(0, len(operations), self.max_batch_size):
            batch = operations[i:i + self.max_batch_size]
            batch_results = await self.process_single_batch(batch)
            results.extend(batch_results)
        
        return results
    
    async def process_single_batch(self, batch):
        """Process a single batch of operations"""
        # Use connection pooling
        # Use parallel processing where possible
        # Implement retry logic
        pass
```

## Monitoring and Metrics

### Performance Metrics
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "api_response_time": [],
            "connection_pool_utilization": [],
            "cache_hit_rate": [],
            "database_query_time": [],
            "worker_queue_size": []
        }
    
    def record_metric(self, metric_name, value):
        """Record a performance metric"""
        if metric_name in self.metrics:
            self.metrics[metric_name].append({
                "value": value,
                "timestamp": time.time()
            })
    
    def get_average_metric(self, metric_name, window=300):
        """Get average metric over time window"""
        if metric_name not in self.metrics:
            return 0
        
        recent_metrics = [
            m for m in self.metrics[metric_name]
            if m["timestamp"] > time.time() - window
        ]
        
        if not recent_metrics:
            return 0
        
        return sum(m["value"] for m in recent_metrics) / len(recent_metrics)
```

### Alerting
```python
class PerformanceAlert:
    def __init__(self, monitor):
        self.monitor = monitor
        self.thresholds = {
            "api_response_time": 5.0,  # seconds
            "connection_pool_utilization": 0.9,  # 90%
            "cache_hit_rate": 0.7,  # 70%
            "database_query_time": 1.0,  # seconds
            "worker_queue_size": 1000
        }
    
    async def check_alerts(self):
        """Check for performance alerts"""
        alerts = []
        
        for metric_name, threshold in self.thresholds.items():
            current_value = self.monitor.get_average_metric(metric_name)
            
            if current_value > threshold:
                alerts.append({
                    "metric": metric_name,
                    "current_value": current_value,
                    "threshold": threshold,
                    "severity": "warning" if current_value < threshold * 1.5 else "critical"
                })
        
        return alerts
```

## Best Practices

### 1. Start with Baseline Measurements
```python