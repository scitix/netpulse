# 日志分析指南

本文档介绍如何查看和分析 NetPulse 系统的日志，帮助快速定位和解决问题。

## 日志系统概览

### 日志配置
- **配置文件**: `config/log-config.yaml`
- **日志级别**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **默认级别**: INFO
- **输出格式**: 彩色控制台输出，包含时间戳、进程ID、日志级别、模块名、文件名和行号

### 日志特性
- **敏感信息过滤**: 自动过滤密码、token等敏感信息
- **彩色输出**: 不同级别使用不同颜色显示
- **模块化日志**: 支持为不同模块设置独立日志级别

## 查看日志的方法

### 1. Docker 环境查看日志

```bash
# 查看所有服务日志
docker compose logs

# 查看特定服务日志
docker compose logs api
docker compose logs worker
docker compose logs redis

# 实时跟踪日志
docker compose logs -f api

# 查看最近的日志
docker compose logs --tail=100 api

# 查看特定时间段的日志
docker compose logs --since="2024-01-01T10:00:00" api
```

### 2. 系统服务查看日志

```bash
# 查看 systemd 服务日志
journalctl -u netpulse-api -f
journalctl -u netpulse-worker -f

# 查看最近的日志
journalctl -u netpulse-api --tail=100

# 查看特定时间段的日志
journalctl -u netpulse-api --since="2024-01-01 10:00:00"
```

### 3. 直接查看日志文件

```bash
# 查看应用日志文件
tail -f /var/log/netpulse/netpulse.log

# 查看错误日志
grep "ERROR" /var/log/netpulse/netpulse.log

# 查看特定设备的日志
grep "192.168.1.1" /var/log/netpulse/netpulse.log
```

## 日志内容分析

### 日志格式说明
```
[2024-01-01 10:30:15 +0800] [12345] [INFO] [netpulse.api|routes.py:45] - API request received
```

- `2024-01-01 10:30:15 +0800`: 时间戳和时区
- `12345`: 进程ID
- `INFO`: 日志级别
- `netpulse.api|routes.py:45`: 模块名|文件名:行号
- `API request received`: 日志消息

### 常见日志级别

#### INFO 级别 - 正常运行信息
```
[INFO] - 服务启动成功
[INFO] - 设备连接建立
[INFO] - API请求处理完成
[INFO] - Worker任务执行成功
```

#### WARNING 级别 - 警告信息
```
[WARNING] - 设备连接超时
[WARNING] - Redis连接重试
[WARNING] - 配置参数使用默认值
```

#### ERROR 级别 - 错误信息
```
[ERROR] - 设备认证失败
[ERROR] - 数据库连接失败
[ERROR] - API请求处理异常
```

#### DEBUG 级别 - 调试信息
```
[DEBUG] - 详细的执行步骤
[DEBUG] - 请求参数详情
[DEBUG] - 内部状态信息
```

## 常见日志分析场景

### 1. 服务启动问题

**查看启动日志**:
```bash
docker compose logs api | grep -E "(Starting|Started|ERROR|CRITICAL)"
```

**常见启动错误**:
- 配置文件错误: `Error in reading config`
- 端口占用: `Address already in use`
- 依赖服务未启动: `Connection refused`

### 2. 设备连接问题

**查看设备连接日志**:
```bash
docker compose logs worker | grep -E "(connect|connection|timeout|failed)"
```

**常见连接错误**:
- 认证失败: `Authentication failed`
- 网络不通: `Connection timeout`
- 设备类型错误: `Unknown device type`

### 3. API请求问题

**查看API请求日志**:
```bash
docker compose logs api | grep -E "(POST|GET|PUT|DELETE)"
```

**常见API错误**:
- 认证失败: `Invalid API key`
- 参数错误: `Validation error`
- 内部错误: `Internal server error`

### 4. Worker任务问题

**查看Worker任务日志**:
```bash
docker compose logs worker | grep -E "(job|task|queue|worker)"
```

**常见Worker错误**:
- 任务超时: `Job timeout`
- 队列满: `Queue full`
- Worker异常退出: `Worker died`

## 日志分析工具

### 1. 使用 grep 过滤日志

```bash
# 过滤错误日志
grep "ERROR" netpulse.log

# 过滤特定设备的日志
grep "192.168.1.1" netpulse.log

# 过滤特定时间段的日志
grep "2024-01-01 10:" netpulse.log

# 过滤多个关键词
grep -E "(ERROR|CRITICAL)" netpulse.log
```

### 2. 使用 awk 分析日志

```bash
# 统计错误级别日志数量
awk '/ERROR/ {count++} END {print "ERROR count:", count}' netpulse.log

# 提取特定字段
awk '{print $1, $2, $4}' netpulse.log

# 按模块统计日志
awk '{print $4}' netpulse.log | sort | uniq -c
```

### 3. 使用 jq 分析JSON日志

```bash
# 如果日志是JSON格式
cat netpulse.log | jq '.level' | sort | uniq -c

# 提取错误信息
cat netpulse.log | jq 'select(.level=="ERROR") | .message'
```

## 📈 日志监控建议

### 1. 设置日志轮转

```bash
# 配置日志轮转
logrotate /etc/logrotate.d/netpulse

# 手动轮转日志
logrotate -f /etc/logrotate.d/netpulse
```

### 2. 监控关键指标

- **错误率**: ERROR级别日志数量
- **响应时间**: API请求处理时间
- **连接状态**: 设备连接成功/失败率
- **系统资源**: CPU、内存、磁盘使用率

### 3. 告警设置

```bash
# 监控错误日志数量
tail -f netpulse.log | grep "ERROR" | wc -l

# 监控服务状态
curl -f http://localhost:9000/health || echo "Service down"
```

## 🔍 调试技巧

### 1. 启用调试模式

```bash
# 设置环境变量
export NETPULSE_LOG_LEVEL=DEBUG

# 重启服务
docker compose restart api worker
```

### 2. 查看详细日志

```bash
# 查看完整的错误堆栈
docker compose logs api | grep -A 10 "Traceback"

# 查看特定请求的完整日志
docker compose logs api | grep -A 5 -B 5 "request_id"
```

### 3. 日志对比分析

```bash
# 对比不同时间的日志
diff <(grep "ERROR" netpulse.log.20240101) <(grep "ERROR" netpulse.log.20240102)
```

---

**通过合理的日志分析，可以快速定位问题根源，提高系统运维效率。** 