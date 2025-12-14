# 环境变量

本文档列出 NetPulse 系统中可用的环境变量。所有环境变量都使用 `NETPULSE_` 前缀，并通过双下划线 `__` 连接嵌套配置项。

## 命名规则

环境变量格式：`NETPULSE_<SECTION>__<KEY>`

例如：
- `NETPULSE_SERVER__PORT` 对应配置中的 `server.port`
- `NETPULSE_REDIS__TLS__ENABLED` 对应配置中的 `redis.tls.enabled`

## 配置优先级

配置加载优先级（从高到低）：
1. 环境变量
2. `.env` 文件
3. YAML 配置文件
4. 默认值

## Server 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_SERVER__HOST` | API 服务监听地址 | `0.0.0.0` |
| `NETPULSE_SERVER__PORT` | API 服务监听端口 | `9000` |
| `NETPULSE_SERVER__API_KEY` | API 访问密钥（必填） | - |
| `NETPULSE_SERVER__API_KEY_NAME` | API 密钥的 HTTP 头名称 | `X-API-KEY` |
| `NETPULSE_SERVER__GUNICORN_WORKER` | Gunicorn worker 数量 | 自动计算 |

## Redis 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_REDIS__HOST` | Redis 服务器地址 | `localhost` |
| `NETPULSE_REDIS__PORT` | Redis 服务器端口 | `6379` |
| `NETPULSE_REDIS__PASSWORD` | Redis 认证密码 | `null` |
| `NETPULSE_REDIS__TIMEOUT` | Redis 连接超时时间（秒） | `30` |
| `NETPULSE_REDIS__KEEPALIVE` | Redis 连接保活时间（秒） | `30` |

### Redis TLS 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_REDIS__TLS__ENABLED` | 是否启用 TLS | `false` |
| `NETPULSE_REDIS__TLS__CA` | CA 证书路径 | `null` |
| `NETPULSE_REDIS__TLS__CERT` | 客户端证书路径 | `null` |
| `NETPULSE_REDIS__TLS__KEY` | 客户端私钥路径 | `null` |

### Redis Sentinel 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_REDIS__SENTINEL__ENABLED` | 是否启用 Sentinel | `false` |
| `NETPULSE_REDIS__SENTINEL__HOST` | Sentinel 服务器地址 | `redis-sentinel` |
| `NETPULSE_REDIS__SENTINEL__PORT` | Sentinel 服务器端口 | `26379` |
| `NETPULSE_REDIS__SENTINEL__MASTER_NAME` | 主节点名称 | `mymaster` |
| `NETPULSE_REDIS__SENTINEL__PASSWORD` | Sentinel 认证密码 | `null` |

### Redis Key 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_REDIS__KEY__HOST_TO_NODE_MAP` | 主机到节点映射的 key | `netpulse:host_to_node_map` |
| `NETPULSE_REDIS__KEY__NODE_INFO_MAP` | 节点信息映射的 key | `netpulse:node_info_map` |

## Worker 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_WORKER__SCHEDULER` | 任务调度插件 | `least_load` |
| `NETPULSE_WORKER__TTL` | Worker 心跳超时时间（秒） | `300` |
| `NETPULSE_WORKER__PINNED_PER_NODE` | 每个 Node 上最多运行的 Pinned Worker 数量 | `32` |

## Job 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_JOB__TTL` | 任务在队列中的最大存活时间（秒） | `1800` |
| `NETPULSE_JOB__TIMEOUT` | 任务执行超时时间（秒） | `300` |
| `NETPULSE_JOB__RESULT_TTL` | 任务结果保留时间（秒） | `300` |

## Log 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_LOG__LEVEL` | 日志级别 | `INFO` |
| `NETPULSE_LOG__CONFIG` | 日志配置文件路径 | `config/log-config.yaml` |

## Plugin 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_PLUGIN__DRIVER` | 设备驱动插件目录 | `netpulse/plugins/drivers/` |
| `NETPULSE_PLUGIN__WEBHOOK` | Webhook 插件目录 | `netpulse/plugins/webhooks/` |
| `NETPULSE_PLUGIN__TEMPLATE` | 模板插件目录 | `netpulse/plugins/templates/` |
| `NETPULSE_PLUGIN__SCHEDULER` | 调度器插件目录 | `netpulse/plugins/schedulers/` |
| `NETPULSE_PLUGIN__CREDENTIAL` | 凭据插件目录 | `netpulse/plugins/credentials/` |

## Credential 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_CREDENTIAL__ENABLED` | 是否启用凭据插件 | `false` |
| `NETPULSE_CREDENTIAL__NAME` | 凭据提供器名称（如 `vault_kv`） | `vault_kv` |
| `NETPULSE_CREDENTIAL__ADDR` | Vault 服务器地址（如 `http://vault:8200`） | - |
| `NETPULSE_CREDENTIAL__NAMESPACE` | Vault 命名空间 | - |
| `NETPULSE_CREDENTIAL__ALLOWED_PATHS` | 允许访问的路径前缀（逗号分隔，如 `kv/netpulse`） | - |
| `NETPULSE_CREDENTIAL__CACHE_TTL` | 凭据缓存时间（秒，0 表示禁用缓存） | `30` |
| `NETPULSE_CREDENTIAL__VERIFY` | TLS 验证（`true`/`false` 或 CA 证书路径） | `true` |
| `NETPULSE_VAULT_TOKEN` | Vault Token 认证方式（与 AppRole 二选一） | - |
| `NETPULSE_VAULT_ROLE_ID` | Vault AppRole role_id（与 Token 二选一） | - |
| `NETPULSE_VAULT_SECRET_ID` | Vault AppRole secret_id（与 Token 二选一） | - |

!!! note "认证方式说明"
    Vault 认证支持两种方式，选择其中一种：
    - **Token 认证**：设置 `NETPULSE_VAULT_TOKEN`
    - **AppRole 认证**：同时设置 `NETPULSE_VAULT_ROLE_ID` 和 `NETPULSE_VAULT_SECRET_ID`

## 其他配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `NETPULSE_CONFIG_FILE` | 配置文件路径 | `config/config.yaml` |

## 使用示例

### 开发环境

```bash
# .env 文件
NETPULSE_SERVER__API_KEY=dev-api-key-123
NETPULSE_REDIS__HOST=localhost
NETPULSE_REDIS__PORT=6379
NETPULSE_LOG__LEVEL=DEBUG
```

### 生产环境

```bash
# .env 文件
NETPULSE_SERVER__API_KEY=your-secure-api-key
NETPULSE_REDIS__HOST=redis-cluster.example.com
NETPULSE_REDIS__PORT=6379
NETPULSE_REDIS__PASSWORD=your-secure-password
NETPULSE_REDIS__TLS__ENABLED=true
NETPULSE_REDIS__TLS__CA=/etc/redis/tls/ca.crt
NETPULSE_REDIS__TLS__CERT=/etc/redis/tls/client.crt
NETPULSE_REDIS__TLS__KEY=/etc/redis/tls/client.key
NETPULSE_WORKER__PINNED_PER_NODE=64
NETPULSE_LOG__LEVEL=INFO
```
