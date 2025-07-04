# Configuration Reference

This document provides a comprehensive reference for all NetPulse configuration options.

## Configuration Files

### Main Configuration (`config.yaml`)
```yaml
# Server Configuration
server:
  host: "0.0.0.0"
  port: 9000
  workers: 4
  reload: false
  
# Redis Configuration
redis:
  host: "localhost"
  port: 6379
  db: 0
  password: null
  
# Security Configuration
security:
  api_key: "your-api-key-here"
  secret_key: "your-secret-key-here"
  
# Logging Configuration
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/netpulse.log"
  
# Worker Configuration
worker:
  concurrency: 10
  max_retries: 3
  retry_delay: 5
  
# Connection Configuration
connection:
  timeout: 30
  max_connections: 100
  keepalive: true
  keepalive_interval: 60
```

### Environment Variables (`.env`)
```bash
# Server Settings
HOST=0.0.0.0
PORT=9000
WORKERS=4

# Redis Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Security Settings
API_KEY=your-api-key-here
SECRET_KEY=your-secret-key-here

# Timezone Settings
TZ=Asia/Shanghai

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=logs/netpulse.log

# Worker Settings
WORKER_CONCURRENCY=10
WORKER_MAX_RETRIES=3
WORKER_RETRY_DELAY=5
```

## Configuration Sections

### Server Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | string | `"0.0.0.0"` | Server bind address |
| `port` | integer | `9000` | Server listen port |
| `workers` | integer | `4` | Number of worker processes |
| `reload` | boolean | `false` | Enable auto-reload in development |

### Redis Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | string | `"localhost"` | Redis server host |
| `port` | integer | `6379` | Redis server port |
| `db` | integer | `0` | Redis database number |
| `password` | string | `null` | Redis password |
| `max_connections` | integer | `10` | Maximum Redis connections |

### Security Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | string | Required | API authentication key |
| `secret_key` | string | Required | Secret key for encryption |
| `token_expire` | integer | `3600` | Token expiration time (seconds) |
| `rate_limit` | integer | `100` | Rate limit per minute |

### Logging Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | string | `"INFO"` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `format` | string | Standard format | Log message format |
| `file` | string | `"logs/netpulse.log"` | Log file path |
| `max_size` | integer | `10485760` | Maximum log file size (bytes) |
| `backup_count` | integer | `5` | Number of backup log files |

### Worker Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `concurrency` | integer | `10` | Number of concurrent tasks |
| `max_retries` | integer | `3` | Maximum retry attempts |
| `retry_delay` | integer | `5` | Delay between retries (seconds) |
| `timeout` | integer | `300` | Task timeout (seconds) |
| `prefetch_multiplier` | integer | `4` | Task prefetch multiplier |

### Connection Configuration
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | integer | `30` | Connection timeout (seconds) |
| `max_connections` | integer | `100` | Maximum connections per device |
| `keepalive` | boolean | `true` | Enable connection keepalive |
| `keepalive_interval` | integer | `60` | Keepalive interval (seconds) |
| `max_idle_time` | integer | `300` | Maximum idle time (seconds) |

## Device Configuration

### Device Profile Example
```yaml
devices:
  cisco_ios:
    driver: "cisco_ios"
    device_type: "cisco_ios"
    connection_args:
      timeout: 30
      keepalive: true
      global_delay_factor: 1
    
  huawei_vrp:
    driver: "huawei_vrp"
    device_type: "huawei_vrp"
    connection_args:
      timeout: 30
      keepalive: true
      global_delay_factor: 1
```

### Connection Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `timeout` | integer | Connection timeout in seconds |
| `global_delay_factor` | float | Global delay factor for commands |
| `keepalive` | boolean | Enable SSH keepalive |
| `banner_timeout` | integer | Banner timeout in seconds |
| `auth_timeout` | integer | Authentication timeout in seconds |

## Template Configuration

### Template Settings
```yaml
templates:
  base_path: "templates"
  auto_reload: true
  cache_size: 1000
  
  # Jinja2 Settings
  jinja2:
    trim_blocks: true
    lstrip_blocks: true
    keep_trailing_newline: true
    
  # TextFSM Settings
  textfsm:
    template_path: "templates/textfsm"
    
  # TTP Settings
  ttp:
    template_path: "templates/ttp"
```

## Webhook Configuration

### Webhook Settings
```yaml
webhooks:
  enabled: true
  timeout: 30
  max_retries: 3
  retry_delay: 5
  
  # Event Types
  events:
    - "job.started"
    - "job.completed"
    - "job.failed"
    - "device.connected"
    - "device.disconnected"
```

## Performance Configuration

### Performance Tuning
```yaml
performance:
  # Connection Pool
  connection_pool:
    min_size: 5
    max_size: 20
    max_idle_time: 300
    
  # Cache Settings
  cache:
    enabled: true
    ttl: 3600
    max_size: 1000
    
  # Batch Processing
  batch:
    max_size: 100
    timeout: 300
    parallel_limit: 10
```

## Monitoring Configuration

### Monitoring Settings
```yaml
monitoring:
  enabled: true
  metrics_port: 9090
  health_check_interval: 30
  
  # Prometheus Settings
  prometheus:
    enabled: true
    port: 9090
    path: "/metrics"
    
  # Health Check
  health_check:
    enabled: true
    path: "/health"
    timeout: 5
```

## Advanced Configuration

### Custom Drivers
```yaml
drivers:
  custom_driver:
    module: "custom_drivers.my_driver"
    class: "MyDriver"
    default_args:
      timeout: 30
      port: 22
```

### Plugin Configuration
```yaml
plugins:
  enabled_plugins:
    - "netpulse.plugins.logging"
    - "netpulse.plugins.monitoring"
    - "netpulse.plugins.webhook"
    
  plugin_settings:
    logging:
      level: "INFO"
      format: "json"
```

## Configuration Validation

### Validation Rules
```python
from pydantic import BaseModel, validator

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 9000
    workers: int = 4
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
```

## Environment-specific Configuration

### Development Environment
```yaml
# config/development.yaml
server:
  reload: true
  workers: 1
  
logging:
  level: "DEBUG"
  
redis:
  host: "localhost"
```

### Production Environment
```yaml
# config/production.yaml
server:
  reload: false
  workers: 4
  
logging:
  level: "INFO"
  
redis:
  host: "redis-cluster"
  password: "${REDIS_PASSWORD}"
```

## Configuration Loading

### Configuration Priority
1. Environment variables
2. Configuration file
3. Default values

### Loading Example
```python
import os
from netpulse.config import Config

# Load configuration
config = Config.load(
    config_file=os.getenv('CONFIG_FILE', 'config.yaml'),
    env_file=os.getenv('ENV_FILE', '.env')
)
```

## Best Practices

### Security Best Practices
- Use environment variables for sensitive data
- Rotate API keys regularly
- Use strong secret keys
- Enable rate limiting

### Performance Best Practices
- Tune connection pool sizes
- Enable caching where appropriate
- Monitor resource usage
- Use batch operations

### Operational Best Practices
- Use structured logging
- Enable monitoring
- Set up health checks
- Configure proper timeouts

---

For more information about specific configuration topics, see:
- [Environment Variables](environment-variables.md)
- [Best Practices](best-practices.md)
- [Performance Tuning](../advanced/performance-tuning.md) 