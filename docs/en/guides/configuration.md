# Configuration File Description

NetPulse uses YAML format configuration files for system configuration, with the default configuration file path being `config/config.yaml`. Configuration items can also be overridden through environment variables.

Additionally, NetPulse's logging module can be configured through a separate configuration file, with the default path being `config/log-config.yaml`.

## Global Configuration File

### Server Configuration
- `host`: API service listening address, default `0.0.0.0`
- `port`: API service listening port, default `9000`
- `api_key`: API access key, required
- `api_key_name`: HTTP header name for the API key, default `X-API-KEY`
- `gunicorn_worker`: Number of Gunicorn workers, default automatically calculated based on CPU cores

### Job Configuration
- `ttl`: Maximum lifetime of a task in the queue (seconds), default `1800`
- `timeout`: Task execution timeout (seconds), default `300`
- `result_ttl`: Task result retention time (seconds), default `300`

### Worker Configuration

- `scheduler`: Task scheduling plugin, options: `least_load`, `load_weighted_random`, etc., default `least_load`
- `ttl`: Worker heartbeat timeout (seconds), default `300`
- `pinned_per_node`: Maximum number of Pinned Workers running on each Node, default `32`

### Redis Configuration

- `host`: Redis server address, default `localhost`
- `port`: Redis server port, default `6379`
- `password`: Redis authentication password
- `timeout`: Redis connection timeout (seconds), default `30`
- `keepalive`: Redis connection keepalive time (seconds), default `30`

#### TLS Configuration
- `tls`: TLS configuration
    - `enabled`: Whether to enable TLS, default `false`
    - `ca`: CA certificate path
    - `cert`: Client certificate path
    - `key`: Client private key path

#### Sentinel Configuration
- `sentinel`: Sentinel configuration
    - `enabled`: Whether to enable Sentinel, default is `false`
    - `host`: Sentinel server address
    - `port`: Sentinel server port
    - `password`: Sentinel authentication password
    - `master_name`: Name of the master node

#### Key Configuration

- `key`: Redis key naming configuration
    - `host_to_node_map`: Key for host-to-node mapping, default `netpulse:host_to_node_map`
    - `node_info_map`: Key for node information mapping, default `netpulse:node_info_map`

### Plugin Configuration
- `driver`: Device driver plugin directory, default `netpulse/plugins/drivers/`
- `webhook`: Webhook plugin directory, default `netpulse/plugins/webhooks/`
- `template`: Template plugin directory, default `netpulse/plugins/templates/`
- `scheduler`: Scheduler plugin directory, default `netpulse/plugins/schedulers/`

### Log Configuration
- `config`: Log configuration file path, default `config/log-config.yaml`
- `level`: Log level, default `INFO`

## Log Configuration File

The log configuration file uses YAML format with the default path being `config/log-config.yaml`. Under normal circumstances, users do not need to modify this file unless they need to customize log formats or add new log handlers.

### Main Configuration Items
- `version`: Configuration file version, currently 1
- `filters`: Log filter configuration
    - `scrub`: Sensitive information filter, used to filter passwords, tokens, and other sensitive information in logs
- `formatters`: Log formatting configuration
    - `colorlog`: Color log formatter, supports colored log output
- `handlers`: Log handler configuration
    - `console`: Console output handler, using the color formatter
- `loggers`: Log level configuration for specific modules (using RQ/Netmiko/Paramiko as examples)
    - `rq.worker`: RQ worker log level
    - `netmiko`: Netmiko log level
    - `paramiko`: Paramiko log level
- `root`: Root log configuration
    - `handlers`: Log handlers to use
- `disable_existing_loggers`: Whether to disable existing loggers, default `false`

### Custom Features
- Use `ScrubFilter` filter to automatically filter sensitive information in logs
- Use `ColoredFormatter` formatter to implement colored log output
- Set the `logger` field to set independent log levels for different modules

## Environment Variable Override

All configuration items can be overridden through environment variables. The naming rule for environment variables is:
`NETPULSE_<SECTION>__<KEY>`, for example:

```bash
# Override API port
export NETPULSE_SERVER__PORT=8080

# Override Redis password
export NETPULSE_REDIS__PASSWORD=NewPassword123

# Override Redis TLS options
export NETPULSE_REDIS__TLS__ENABLED=false
```

!!! note
    Nested configuration items are connected with double underscores `__`. Environment variable overrides have higher priority than settings in the configuration file.


## Configuration Validation

The system automatically validates the validity of the configuration file at startup. If the configuration format or values are invalid, the system will fail to start and display relevant error messages.