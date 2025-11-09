# 性能调优

本文档提供一些性能优化建议，供参考。实际效果可能因环境而异，建议根据实际情况调整。

## 配置参数调整

### Worker 配置

根据实际并发需求调整 Worker 数量：

```yaml
worker:
  scheduler: "load_weighted_random"  # 或 "least_load"
  pinned_per_node: 64                # 根据服务器资源调整
  ttl: 300                           # Worker 心跳超时
```

**参考建议**（仅供参考）：
- 小型环境（< 50 设备）：`pinned_per_node: 32`
- 中型环境（50-200 设备）：`pinned_per_node: 64`
- 大型环境（> 200 设备）：`pinned_per_node: 128`

!!! note "注意"
    实际效果取决于服务器资源、网络状况和设备响应速度，建议从小值开始逐步调整。

### Job 配置

根据任务类型调整超时和保留时间：

```yaml
job:
  ttl: 3600          # 任务队列存活时间（秒）
  timeout: 600       # 任务执行超时（秒）
  result_ttl: 1800   # 结果保留时间（秒）
```

**参考建议**：
- 快速查询命令（如 `show version`）：`timeout: 300`
- 配置变更操作：`timeout: 600`
- 批量操作：`timeout: 1800`

### Gunicorn Worker

```yaml
server:
  gunicorn_worker: 8  # 建议公式：2 * CPU 核数 + 1
```

## 队列策略

### FIFO 队列
- 适用场景：一次性操作、HTTP 短连接
- 特点：简单通用

### Pinned 队列
- 适用场景：频繁操作同一设备
- 特点：支持连接复用，可能提升性能

## 监控和排查

### 查看系统状态

```bash
# 健康检查
curl -H "X-API-KEY: YOUR_API_KEY" http://localhost:9000/health

# 查看容器资源使用
docker stats

# 查看日志
docker compose logs | grep -E "(timeout|ERROR)"
```

## 常见问题

### 任务执行缓慢

可能原因：
- Worker 数量不足
- 网络延迟
- 设备响应慢

可尝试：
- 适当增加 `pinned_per_node`
- 使用 Pinned 队列策略
- 增加任务超时时间

### 内存使用过高

可尝试：
- 减少 `pinned_per_node` 数量
- 降低 `result_ttl` 值
- 重启 Worker 服务

## 注意事项

1. 参数调整需要根据实际环境测试验证
2. 建议逐步调整，观察效果
3. 监控系统资源使用情况
4. 合理设置超时时间，避免过长或过短
