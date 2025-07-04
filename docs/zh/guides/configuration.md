# 配置指南

NetPulse 使用 YAML 格式的配置文件进行系统配置，默认配置文件路径为 `config/config.yaml`。配置项也可以通过环境变量进行覆盖。

此外，NetPulse 的日志模块可以通过单独的配置文件进行配置，默认路径为 `config/log-config.yaml`。

## 全局配置文件

### Server 配置
- `host`: API 服务监听地址，默认 `0.0.0.0`
- `port`: API 服务监听端口，默认 `9000`
- `api_key`: API 访问密钥，必填
- `api_key_name`: API 密钥的 HTTP 头名称，默认 `X-API-KEY`
- `gunicorn_worker`: Gunicorn worker 数量，默认根据 CPU 核数自动计算

### Job 配置
- `ttl`: 任务在队列中的最大存活时间（秒），默认 `1800`
- `timeout`: 任务执行超时时间（秒），默认 `300`
- `result_ttl`: 任务结果保留时间（秒），默认 `300`

### Worker 配置

- `scheduler`: 任务调度插件，可选值：`least_load`, `load_weighted_random` 等，默认 `least_load`
- `ttl`: Worker 心跳超时时间（秒），默认 `300`
- `pinned_per_node`: 每个 Node 上最多运行的 Pinned Worker 数量，默认 `32`

### Redis 配置

- `host`: Redis 服务器地址，默认 `localhost`
- `port`: Redis 服务器端口，默认 `6379`
- `password`: Redis 认证密码
- `timeout`: Redis 连接超时时间（秒），默认 `30`
- `keepalive`: Redis 连接保活时间（秒），默认 `30`

#### TLS 配置
- `tls`: TLS 配置
    - `enabled`: 是否启用 TLS，默认 `false`
    - `ca`: CA 证书路径
    - `cert`: 客户端证书路径
    - `key`: 客户端私钥路径

#### Sentinel 配置
- `sentinel`: Sentinel 配置
    - `enabled`: 是否启用 Sentinel，默认 `false`
    - `host`: Sentinel 服务器地址
    - `port`: Sentinel 服务器端口 
    - `password`: Sentinel 认证密码
    - `master_name`: 主节点名称

#### 键配置

- `key`: Redis key 命名配置
    - `host_to_node_map`: 主机到节点映射的 key，默认 `netpulse:host_to_node_map`
    - `node_info_map`: 节点信息映射的 key，默认 `netpulse:node_info_map`

### Plugin 配置
- `driver`: 设备驱动插件目录，默认 `netpulse/plugins/drivers/`
- `webhook`: Webhook 插件目录，默认 `netpulse/plugins/webhooks/`
- `template`: 模板插件目录，默认 `netpulse/plugins/templates/`
- `scheduler`: 调度器插件目录，默认 `netpulse/plugins/schedulers/`

### Log 配置
- `config`: 日志配置文件路径，默认 `config/log-config.yaml`
- `level`: 日志级别，默认 `INFO`

## 日志配置文件

日志配置文件采用 YAML 格式，默认路径为 `config/log-config.yaml`。正常情况下，用户不需要修改此文件，除非需要自定义日志格式或添加新的日志处理器。

### 主要配置项
- `version`: 配置文件版本，当前为 1
- `filters`: 日志过滤器配置
    - `scrub`: 敏感信息过滤，用于过滤日志中的密码、token 等敏感信息
- `formatters`: 日志格式化配置
    - `colorlog`: 彩色日志格式化器，支持带颜色的日志输出
- `handlers`: 日志处理器配置
    - `console`: 控制台输出处理器，使用彩色格式化器
- `loggers`: 特定模块的日志级别配置（以 RQ/Netmiko/Paramiko 为例）
    - `rq.worker`: RQ worker 日志级别
    - `netmiko`: Netmiko 日志级别
    - `paramiko`: Paramiko 日志级别
- `root`: 根日志配置
    - `handlers`: 使用的日志处理器
- `disable_existing_loggers`: 是否禁用已有日志器，默认 `false`

### 自定义功能
- 使用 `ScrubFilter` 过滤器自动过滤日志中的敏感信息
- 使用 `ColoredFormatter` 格式化器实现彩色日志输出
- 设置 `logger` 字段，为不同模块设置独立的日志级别


## 环境变量覆盖

所有配置项都可以通过环境变量进行覆盖，环境变量命名规则为：
`NETPULSE_<SECTION>__<KEY>`，例如：

```bash
# 覆盖 API 端口
export NETPULSE_SERVER__PORT=8080

# 覆盖 Redis 密码
export NETPULSE_REDIS__PASSWORD=NewPassword123

# 覆盖 Redis TLS 选项
export NETPULSE_REDIS__TLS__ENABLED=false
```

!!! note
    嵌套的配置项需要使用双下划线 `__` 连接。环境变量覆盖的优先级高于配置文件中的设置。


## 配置验证

系统启动时会自动验证配置文件的有效性，如果配置格式或值不合法，系统将无法启动并显示相关错误信息。
