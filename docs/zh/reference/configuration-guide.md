# 配置指南

本文档介绍 NetPulse 的配置方法和参数说明。

## 配置文件

NetPulse 使用 YAML 格式的配置文件，默认路径为 `config/config.yaml`。所有配置项都可以通过环境变量进行覆盖。

## 配置文件结构

### 主配置文件 (`config/config.yaml`)

```yaml
server:
  host: 0.0.0.0              # API 服务监听地址
  port: 9000                 # API 服务监听端口
  api_key: ${NETPULSE_SERVER__API_KEY}  # API 访问密钥（必填）
  api_key_name: X-API-KEY    # API 密钥的 HTTP 头名称
  gunicorn_worker: 4         # Gunicorn worker 数量（默认根据 CPU 核数自动计算）

job:
  ttl: 1800                  # 任务在队列中的最大存活时间（秒）
  timeout: 300               # 任务执行超时时间（秒）
  result_ttl: 300            # 任务结果保留时间（秒）

worker:
  scheduler: "least_load"    # 任务调度插件：least_load, load_weighted_random
  ttl: 300                   # Worker 心跳超时时间（秒）
  pinned_per_node: 32        # 每个 Node 上最多运行的 Pinned Worker 数量

redis:
  host: localhost             # Redis 服务器地址
  port: 6379                 # Redis 服务器端口
  password: null              # Redis 认证密码
  timeout: 30                # Redis 连接超时时间（秒）
  keepalive: 30              # Redis 连接保活时间（秒）
  tls:                        # TLS 配置
    enabled: false           # 是否启用 TLS
    ca: null                  # CA 证书路径
    cert: null                # 客户端证书路径
    key: null                 # 客户端私钥路径
  sentinel:                  # Sentinel 配置
    enabled: false           # 是否启用 Sentinel
    host: redis-sentinel     # Sentinel 服务器地址
    port: 26379              # Sentinel 服务器端口
    master_name: mymaster    # 主节点名称
    password: null           # Sentinel 认证密码
  key:                       # Redis key 命名配置
    host_to_node_map: netpulse:host_to_node_map
    node_info_map: netpulse:node_info_map

plugin:
  driver: netpulse/plugins/drivers/      # 设备驱动插件目录
  webhook: netpulse/plugins/webhooks/    # Webhook 插件目录
  template: netpulse/plugins/templates/  # 模板插件目录
  scheduler: netpulse/plugins/schedulers/ # 调度器插件目录

log:
  config: config/log-config.yaml  # 日志配置文件路径
  level: INFO                      # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 环境变量

所有配置项都可以通过环境变量进行覆盖，环境变量命名规则为：`NETPULSE_<SECTION>__<KEY>`

### 常用环境变量示例

```bash
# Server 配置
export NETPULSE_SERVER__HOST=0.0.0.0
export NETPULSE_SERVER__PORT=9000
export NETPULSE_SERVER__API_KEY=your-api-key-here

# Redis 配置
export NETPULSE_REDIS__HOST=redis.example.com
export NETPULSE_REDIS__PORT=6379
export NETPULSE_REDIS__PASSWORD=your-redis-password

# Worker 配置
export NETPULSE_WORKER__SCHEDULER=load_weighted_random
export NETPULSE_WORKER__PINNED_PER_NODE=64
```

!!! note "环境变量优先级"
    环境变量的优先级高于配置文件。嵌套配置项使用双下划线 `__` 连接，如 `NETPULSE_REDIS__TLS__ENABLED`。

详细的环境变量列表请参考 [环境变量参考](./environment-variables.md)。

## 日志配置

日志配置文件默认路径为 `config/log-config.yaml`。一般情况下不需要修改，除非需要自定义日志格式。

主要配置项包括：
- 日志级别设置
- 日志格式化配置
- 敏感信息过滤

## 配置验证

系统启动时会自动验证配置文件的有效性。如果配置格式或值不合法，系统将无法启动并显示相关错误信息。

## 配置示例

### 开发环境

```yaml
server:
  host: localhost
  port: 9000
  api_key: ${NETPULSE_SERVER__API_KEY}

redis:
  host: localhost
  port: 6379

worker:
  pinned_per_node: 16

log:
  level: DEBUG
```

### 生产环境

```yaml
server:
  host: 0.0.0.0
  port: 9000
  api_key: ${NETPULSE_SERVER__API_KEY}
  gunicorn_worker: 8

redis:
  host: redis-cluster.example.com
  port: 6379
  password: ${NETPULSE_REDIS__PASSWORD}
  tls:
    enabled: true
    ca: /etc/redis/tls/ca.crt
    cert: /etc/redis/tls/client.crt
    key: /etc/redis/tls/client.key

worker:
  scheduler: "load_weighted_random"
  pinned_per_node: 64

job:
  ttl: 3600
  timeout: 600

log:
  level: INFO
```
