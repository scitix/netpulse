# Configuration Guide

This document introduces NetPulse's configuration methods and parameter descriptions.

## Configuration File

NetPulse uses YAML format configuration file, default path is `config/config.yaml`. All configuration items can be overridden through environment variables.

## Configuration File Structure

### Main Configuration File (`config/config.yaml`)

```yaml
server:
  host: 0.0.0.0              # API service listen address
  port: 9000                 # API service listen port
  api_key: ${NETPULSE_SERVER__API_KEY}  # API access key (required)
  api_key_name: X-API-KEY    # HTTP header name for API key
  gunicorn_worker: 4         # Gunicorn worker count (default auto-calculated based on CPU cores)

job:
  ttl: 1800                  # Maximum survival time of task in queue (seconds)
  timeout: 300               # Task execution timeout (seconds)
  result_ttl: 300            # Task result retention time (seconds)

worker:
  scheduler: "least_load"    # Task scheduling plugin: least_load, load_weighted_random
  ttl: 300                   # Worker heartbeat timeout (seconds)
  pinned_per_node: 32        # Maximum number of Pinned Workers running on each Node

redis:
  host: localhost             # Redis server address
  port: 6379                 # Redis server port
  password: null              # Redis authentication password
  timeout: 30                # Redis connection timeout (seconds)
  keepalive: 30              # Redis connection keepalive time (seconds)
  tls:                        # TLS configuration
    enabled: false           # Whether to enable TLS
    ca: null                  # CA certificate path
    cert: null                # Client certificate path
    key: null                 # Client private key path
  sentinel:                  # Sentinel configuration
    enabled: false           # Whether to enable Sentinel
    host: redis-sentinel     # Sentinel server address
    port: 26379              # Sentinel server port
    master_name: mymaster    # Master node name
    password: null           # Sentinel authentication password
  key:                       # Redis key naming configuration
    host_to_node_map: netpulse:host_to_node_map
    node_info_map: netpulse:node_info_map

credential:
  vault:
    url: http://localhost:8200          # Vault server URL
    token: ${VAULT_TOKEN}               # Vault authentication token
    mount_point: secret                 # KV v2 mount point
    timeout: 5                          # Connection timeout (seconds)

plugin:
  driver: netpulse/plugins/drivers/      # Device driver plugin directory
  webhook: netpulse/plugins/webhooks/    # Webhook plugin directory
  template: netpulse/plugins/templates/  # Template plugin directory
  scheduler: netpulse/plugins/schedulers/ # Scheduler plugin directory

log:
  config: config/log-config.yaml  # Log configuration file path
  level: INFO                      # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Environment Variables

All configuration items can be overridden through environment variables, environment variable naming rule is: `NETPULSE_<SECTION>__<KEY>`

### Common Environment Variable Examples

```bash
# Server configuration
export NETPULSE_SERVER__HOST=0.0.0.0
export NETPULSE_SERVER__PORT=9000
export NETPULSE_SERVER__API_KEY=your-api-key-here

# Redis configuration
export NETPULSE_REDIS__HOST=redis.example.com
export NETPULSE_REDIS__PORT=6379
export NETPULSE_REDIS__PASSWORD=your-redis-password

# Worker configuration
export NETPULSE_WORKER__SCHEDULER=load_weighted_random
export NETPULSE_WORKER__PINNED_PER_NODE=64
```

!!! note "Environment Variable Priority"
    Environment variables have higher priority than configuration file. Nested configuration items use double underscore `__` to connect, such as `NETPULSE_REDIS__TLS__ENABLED`.

See: [Environment Variables Reference](./environment-variables.md)

## Log Configuration

Log configuration file default path is `config/log-config.yaml`. Generally no need to modify unless custom log format is needed.

Main configuration items include:
- Log level settings
- Log formatting configuration
- Sensitive information filtering

## Configuration Validation

System will automatically validate configuration file validity at startup. If configuration format or values are invalid, system will fail to start and display related error information.

## Configuration Examples

### Development Environment

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

### Production Environment

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

credential:
  vault:
    url: http://localhost:8200
    token: ${VAULT_TOKEN}
    mount_point: secret
    timeout: 5

log:
  level: INFO
```

## Vault Configuration

NetPulse integrates with HashiCorp Vault for secure credential management. Vault configuration can be set through environment variables or `config.yaml`.

### Configuration Methods

**Method 1: Environment Variables (Recommended)**
```bash
export NETPULSE__CREDENTIAL__VAULT__URL=http://localhost:8200
export NETPULSE__CREDENTIAL__VAULT__TOKEN=your-vault-token
export NETPULSE__CREDENTIAL__VAULT__MOUNT_POINT=secret
export NETPULSE__CREDENTIAL__VAULT__TIMEOUT=5
```

**Method 2: config.yaml**
```yaml
credential:
  vault:
    url: http://localhost:8200
    token: ${VAULT_TOKEN}
    mount_point: secret
    timeout: 5
```

### Automatic Configuration (Docker Deployment)

When using Docker Compose deployment, Vault is automatically initialized and configured. The deployment script (`docker_auto_deploy.sh`) will:
1. Initialize Vault if needed
2. Generate `unseal_key` and `root_token`
3. Update `.env` file with `VAULT_UNSEAL_KEY` and `VAULT_TOKEN`
4. Enable KV v2 secret engine at `secret/` path

### Using credential_ref in Device Operations

After configuring Vault, you can use `credential_ref` in device operations:

```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "credential_ref": "sites/hq/admin"
  },
  "command": "show version"
}
```

See: [Vault Credential Management API](../api/credential-api.md)
