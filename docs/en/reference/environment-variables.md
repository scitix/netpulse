# Environment Variables

This document lists available environment variables in NetPulse system. All environment variables use `NETPULSE_` prefix and connect nested configuration items through double underscore `__`.

## Naming Rules

Environment variable format: `NETPULSE_<SECTION>__<KEY>`

For example:
- `NETPULSE_SERVER__PORT` corresponds to `server.port` in configuration
- `NETPULSE_REDIS__TLS__ENABLED` corresponds to `redis.tls.enabled` in configuration

## Server Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_SERVER__HOST` | API service listen address | `0.0.0.0` |
| `NETPULSE_SERVER__PORT` | API service listen port | `9000` |
| `NETPULSE_SERVER__API_KEY` | API access key (required) | - |
| `NETPULSE_SERVER__API_KEY_NAME` | HTTP header name for API key | `X-API-KEY` |
| `NETPULSE_SERVER__GUNICORN_WORKER` | Gunicorn worker count | Auto-calculated |

## Redis Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_REDIS__HOST` | Redis server address | `localhost` |
| `NETPULSE_REDIS__PORT` | Redis server port | `6379` |
| `NETPULSE_REDIS__PASSWORD` | Redis authentication password | `null` |
| `NETPULSE_REDIS__TIMEOUT` | Redis connection timeout (seconds) | `30` |
| `NETPULSE_REDIS__KEEPALIVE` | Redis connection keepalive time (seconds) | `30` |

### Redis TLS Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_REDIS__TLS__ENABLED` | Whether to enable TLS | `false` |
| `NETPULSE_REDIS__TLS__CA` | CA certificate path | `null` |
| `NETPULSE_REDIS__TLS__CERT` | Client certificate path | `null` |
| `NETPULSE_REDIS__TLS__KEY` | Client private key path | `null` |

### Redis Sentinel Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_REDIS__SENTINEL__ENABLED` | Whether to enable Sentinel | `false` |
| `NETPULSE_REDIS__SENTINEL__HOST` | Sentinel server address | `redis-sentinel` |
| `NETPULSE_REDIS__SENTINEL__PORT` | Sentinel server port | `26379` |
| `NETPULSE_REDIS__SENTINEL__MASTER_NAME` | Master node name | `mymaster` |
| `NETPULSE_REDIS__SENTINEL__PASSWORD` | Sentinel authentication password | `null` |

### Redis Key Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_REDIS__KEY__HOST_TO_NODE_MAP` | Key for host to node mapping | `netpulse:host_to_node_map` |
| `NETPULSE_REDIS__KEY__NODE_INFO_MAP` | Key for node information mapping | `netpulse:node_info_map` |

## Worker Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_WORKER__SCHEDULER` | Task scheduling plugin | `least_load` |
| `NETPULSE_WORKER__TTL` | Worker heartbeat timeout (seconds) | `300` |
| `NETPULSE_WORKER__PINNED_PER_NODE` | Maximum number of Pinned Workers running on each Node | `32` |

## Job Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_JOB__TTL` | Maximum survival time of task in queue (seconds) | `1800` |
| `NETPULSE_JOB__TIMEOUT` | Task execution timeout (seconds) | `300` |
| `NETPULSE_JOB__RESULT_TTL` | Task result retention time (seconds) | `300` |

## Log Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_LOG__LEVEL` | Log level | `INFO` |
| `NETPULSE_LOG__CONFIG` | Log configuration file path | `config/log-config.yaml` |

## Plugin Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_PLUGIN__DRIVER` | Device driver plugin directory | `netpulse/plugins/drivers/` |
| `NETPULSE_PLUGIN__WEBHOOK` | Webhook plugin directory | `netpulse/plugins/webhooks/` |
| `NETPULSE_PLUGIN__TEMPLATE` | Template plugin directory | `netpulse/plugins/templates/` |
| `NETPULSE_PLUGIN__SCHEDULER` | Scheduler plugin directory | `netpulse/plugins/schedulers/` |

## Vault Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `VAULT_UNSEAL_KEY` | Vault unseal key (required for Vault unseal) | - |
| `VAULT_TOKEN` | Vault authentication token (required for Vault integration) | - |
| `NETPULSE__CREDENTIAL__VAULT__URL` | Vault server URL | `http://localhost:8200` |
| `NETPULSE__CREDENTIAL__VAULT__TOKEN` | Vault authentication token | `${VAULT_TOKEN}` |
| `NETPULSE__CREDENTIAL__VAULT__MOUNT_POINT` | KV v2 mount point | `secret` |
| `NETPULSE__CREDENTIAL__VAULT__TIMEOUT` | Connection timeout (seconds) | `5` |

!!! note "Vault Configuration Notes"
    - `VAULT_UNSEAL_KEY` and `VAULT_TOKEN` are automatically generated during Docker deployment
    - The deployment script (`docker_auto_deploy.sh`) will automatically update `.env` file with these values
    - For manual setup, you need to initialize Vault and set these values manually

## Other Configuration

| Environment Variable | Description | Default Value |
|---------------------|-------------|---------------|
| `NETPULSE_CONFIG_FILE` | Configuration file path | `config/config.yaml` |

## Usage Examples

### Development Environment

```bash
# .env file
NETPULSE_SERVER__API_KEY=dev-api-key-123
NETPULSE_REDIS__HOST=localhost
NETPULSE_REDIS__PORT=6379
NETPULSE_LOG__LEVEL=DEBUG
```

### Production Environment

```bash
# .env file
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

# Vault Configuration (Auto-generated by docker_auto_deploy.sh)
VAULT_UNSEAL_KEY=your-unseal-key-here
VAULT_TOKEN=your-vault-token-here
NETPULSE__CREDENTIAL__VAULT__URL=http://localhost:8200
NETPULSE__CREDENTIAL__VAULT__TOKEN=${VAULT_TOKEN}
NETPULSE__CREDENTIAL__VAULT__MOUNT_POINT=secret
NETPULSE__CREDENTIAL__VAULT__TIMEOUT=5
```

## Configuration Priority

Configuration loading priority (from high to low):
1. Environment variables
2. `.env` file
3. YAML configuration file
4. Default values