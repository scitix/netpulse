# 性能调优指南

NetPulse 支持部分性能优化参数，帮助用户根据实际需求调整系统性能。

## 主要优化点

- 连接池参数（如最大连接数、超时时间）
- 缓存（如Redis缓存，ttl设置）
- 数据库连接池参数

## 连接池配置

```yaml
connection_pool:
  max_size: 50           # 最大连接数
  min_size: 10           # 最小连接数
  max_idle_time: 300     # 空闲超时时间
  keepalive_interval: 60 # 保活间隔
```

## 缓存配置

```yaml
cache:
  ttl: 3600              # 缓存有效期
  max_size: 1000         # 最大缓存条目
  eviction_policy: "lru" # 淘汰策略
```

## 数据库优化

```yaml
database:
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
  echo: false
```

## 建议/规划
- 建议根据实际并发量调整连接池和缓存参数。
- 建议定期监控系统资源，及时扩容。
- 复杂的动态worker池、多级缓存等为建议/规划功能，当前未实现。

## 性能调优概述

### 优化目标
- 提高API响应速度
- 增加并发处理能力
- 降低资源消耗
- 提升系统稳定性

### 优化维度
- 系统配置优化
- 连接池调优
- 缓存策略优化
- 数据库优化
- 网络优化

## 系统配置优化

### 1. Worker配置
```yaml
# worker配置优化
worker:
  pool_size: 20          # Worker池大小
  max_connections: 100   # 最大连接数
  queue_size: 1000       # 队列大小
  timeout: 30            # 超时时间
```

### 2. 连接池监控
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
        """获取连接池利用率"""
        if self.metrics["total_connections"] == 0:
            return 0
        return (self.metrics["active_connections"] / 
                self.metrics["total_connections"]) * 100
    
    def should_expand(self):
        """判断是否需要扩容"""
        utilization = self.get_utilization()
        return utilization > 80 and self.metrics["connection_requests"] > 10
```

## 连接池调优

### 连接池参数说明
```python
class ConnectionPoolConfig:
    def __init__(self):
        self.max_connections = 50      # 最大连接数
        self.min_connections = 10      # 最小连接数
        self.max_idle_time = 300       # 空闲超时时间
        self.connection_timeout = 30   # 连接超时时间
        self.keepalive_interval = 60   # 保活间隔
        self.keepalive_count = 3       # 保活次数
```

### 动态调整策略
```python
class AdaptiveConnectionPool:
    def __init__(self, initial_size=10, max_size=100):
        self.current_size = initial_size
        self.max_size = max_size
        self.monitor = ConnectionPoolMonitor()
    
    def adjust_pool_size(self):
        """动态调整连接池大小"""
        utilization = self.monitor.get_utilization()
        
        if utilization > 80 and self.current_size < self.max_size:
            # 扩容
            new_size = min(self.current_size * 2, self.max_size)
            self.expand_pool(new_size)
        elif utilization < 30 and self.current_size > 10:
            # 缩容
            new_size = max(self.current_size // 2, 10)
            self.shrink_pool(new_size)
```

## 缓存策略优化

### 多级缓存架构
```python
class MultiLevelCache:
    def __init__(self):
        self.l1_cache = {}  # 内存缓存
        self.l2_cache = Redis()  # Redis缓存
        self.l3_cache = Database()  # 数据库缓存
    
    async def get(self, key):
        """多级缓存查询"""
        # L1缓存查询
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # L2缓存查询
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
        
        # L3缓存查询
        value = await self.l3_cache.get(key)
        if value:
            await self.l2_cache.set(key, value)
            self.l1_cache[key] = value
            return value
        
        return None
```

### 缓存预热
```python
class CacheWarmer:
    def __init__(self, cache):
        self.cache = cache
    
    async def warm_up(self, keys):
        """缓存预热"""
        for key in keys:
            value = await self.fetch_from_source(key)
            await self.cache.set(key, value)
    
    async def warm_up_devices(self, hostnames):
        """预热设备信息缓存"""
        for hostname in hostnames:
            # 预热设备基本信息
            device_info = await self.get_device_info(hostname)
            await self.cache.set(f"device:{hostname}", device_info)
            
            # 预热常用命令结果
            common_commands = ["show version", "show interfaces"]
            for command in common_commands:
                result = await self.execute_command(hostname, command)
                await self.cache.set(f"cmd:{hostname}:{command}", result)
```

## 数据库优化

### 查询优化
```python
class DatabaseOptimizer:
    def __init__(self, db):
        self.db = db
    
    async def optimize_queries(self):
        """查询优化"""
        # 创建索引
        await self.create_indexes()
        
        # 分析查询计划
        await self.analyze_query_plans()
        
        # 优化慢查询
        await self.optimize_slow_queries()
    
    async def create_indexes(self):
        """创建必要的索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_devices_hostname ON devices(hostname)",
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_logs_hostname ON logs(hostname)"
        ]
        
        for index_sql in indexes:
            await self.db.execute(index_sql)
```

### 数据分区
```python
class DataPartitioner:
    def __init__(self, db):
        self.db = db
    
    async def partition_logs_by_date(self):
        """按日期分区日志表"""
        partition_sql = """
        CREATE TABLE IF NOT EXISTS logs_2024_01 PARTITION OF logs
        FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
        """
        await self.db.execute(partition_sql)
```

## 网络优化

### 连接复用
```python
class ConnectionReuser:
    def __init__(self):
        self.connections = {}
        self.lock = asyncio.Lock()
    
    async def get_connection(self, hostname):
        """获取或复用连接"""
        async with self.lock:
            if hostname in self.connections:
                conn = self.connections[hostname]
                if conn.is_alive():
                    return conn
            
            # 创建新连接
            conn = await self.create_connection(hostname)
            self.connections[hostname] = conn
            return conn
    
    async def cleanup_idle_connections(self):
        """清理空闲连接"""
        current_time = time.time()
        async with self.lock:
            idle_hostnames = []
            for hostname, conn in self.connections.items():
                if current_time - conn.last_used > 300:  # 5分钟空闲
                    idle_hostnames.append(hostname)
            
            for hostname in idle_hostnames:
                conn = self.connections[hostname]
                await conn.close()
                del self.connections[hostname]
```

### 负载均衡
```python
class LoadBalancer:
    def __init__(self, workers):
        self.workers = workers
        self.current_index = 0
    
    def get_next_worker(self):
        """轮询选择Worker"""
        worker = self.workers[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.workers)
        return worker
    
    def get_least_loaded_worker(self):
        """选择负载最轻的Worker"""
        return min(self.workers, key=lambda w: w.get_load())
```

## 性能监控

### 关键指标
```python
class PerformanceMetrics:
    def __init__(self):
        self.metrics = {
            "api_response_time": [],
            "connection_pool_utilization": [],
            "cache_hit_rate": [],
            "database_query_time": [],
            "worker_queue_length": []
        }
    
    def record_api_response_time(self, response_time):
        """记录API响应时间"""
        self.metrics["api_response_time"].append(response_time)
        if len(self.metrics["api_response_time"]) > 1000:
            self.metrics["api_response_time"] = self.metrics["api_response_time"][-1000:]
    
    def get_average_response_time(self):
        """获取平均响应时间"""
        times = self.metrics["api_response_time"]
        return sum(times) / len(times) if times else 0
    
    def get_percentile_response_time(self, percentile=95):
        """获取百分位响应时间"""
        times = sorted(self.metrics["api_response_time"])
        if not times:
            return 0
        
        index = int(len(times) * percentile / 100)
        return times[index]
```

### 性能告警
```python
class PerformanceAlert:
    def __init__(self):
        self.thresholds = {
            "api_response_time": 2.0,      # 2秒
            "connection_pool_utilization": 90,  # 90%
            "cache_hit_rate": 80,          # 80%
            "database_query_time": 1.0     # 1秒
        }
    
    def check_alerts(self, metrics):
        """检查性能告警"""
        alerts = []
        
        if metrics.get("api_response_time", 0) > self.thresholds["api_response_time"]:
            alerts.append("API响应时间过长")
        
        if metrics.get("connection_pool_utilization", 0) > self.thresholds["connection_pool_utilization"]:
            alerts.append("连接池利用率过高")
        
        if metrics.get("cache_hit_rate", 100) < self.thresholds["cache_hit_rate"]:
            alerts.append("缓存命中率过低")
        
        return alerts
```

## 最佳实践

### 1. 系统调优
- 根据硬件配置调整Worker数量
- 合理设置连接池大小
- 启用连接复用
- 配置适当的超时时间

### 2. 缓存优化
- 使用多级缓存架构
- 实现缓存预热
- 设置合理的TTL
- 监控缓存命中率

### 3. 数据库优化
- 创建必要的索引
- 使用连接池
- 实现数据分区
- 定期清理历史数据

### 4. 网络优化
- 启用连接复用
- 实现负载均衡
- 优化网络配置
- 监控网络延迟

## 故障排除

### 性能问题诊断
```python
class PerformanceDiagnostic:
    def __init__(self):
        self.diagnostics = []
    
    def diagnose_slow_response(self):
        """诊断响应慢的问题"""
        checks = [
            self.check_connection_pool(),
            self.check_cache_performance(),
            self.check_database_performance(),
            self.check_network_latency()
        ]
        
        for check in checks:
            if check:
                self.diagnostics.append(check)
        
        return self.diagnostics
    
    def check_connection_pool(self):
        """检查连接池状态"""
        utilization = self.get_connection_pool_utilization()
        if utilization > 90:
            return f"连接池利用率过高: {utilization}%"
        return None
```

### 性能调优检查清单
- [ ] Worker数量是否合适
- [ ] 连接池大小是否合理
- [ ] 缓存配置是否优化
- [ ] 数据库查询是否高效
- [ ] 网络连接是否复用
- [ ] 监控指标是否正常

## 📚 相关文档

- **[长连接技术](../architecture/long-connection.md)** - 核心技术原理
- **[批量操作](batch-operations.md)** - 大规模设备管理

---

<div align="center">

**性能调优，让 NetPulse 运行更高效！**

</div> 