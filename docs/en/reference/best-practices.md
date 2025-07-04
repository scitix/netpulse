# Best Practices

This document outlines best practices for using NetPulse effectively and securely.

## Security Best Practices

### API Key Management
- **Use strong, unique API keys** for each environment
- **Rotate API keys regularly** (every 90 days recommended)
- **Store API keys securely** using environment variables or secret management systems
- **Never commit API keys** to version control

```python
# Good: Use environment variables
import os
api_key = os.getenv('NETPULSE_API_KEY')

# Bad: Hardcode API keys
api_key = "your-api-key-here"  # Never do this!
```

### Device Credentials
- **Use least privilege principle** for device access
- **Implement credential rotation** for device accounts
- **Use SSH keys** instead of passwords when possible
- **Store credentials securely** using encrypted storage

```python
# Good: Use SSH key authentication
device_config = {
    "host": "192.168.1.1",
    "username": "netpulse",
    "use_keys": True,
    "key_file": "/path/to/private/key"
}

# Better: Use environment variables for credentials
device_config = {
    "host": "192.168.1.1",
    "username": os.getenv('DEVICE_USERNAME'),
    "password": os.getenv('DEVICE_PASSWORD')
}
```

### Network Security
- **Use VPN or private networks** for device communication
- **Implement network segmentation** to isolate management traffic
- **Enable SSH host key verification** to prevent man-in-the-middle attacks
- **Use encrypted connections** (SSH over Telnet)

## Performance Best Practices

### Connection Management
- **Enable connection pooling** to reduce connection overhead
- **Use appropriate timeout values** based on network conditions
- **Implement connection keep-alive** for long-running operations
- **Monitor connection health** and implement automatic reconnection

```python
# Connection configuration example
connection_config = {
    "timeout": 30,
    "keepalive": True,
    "keepalive_interval": 60,
    "max_idle_time": 300,
    "max_connections": 10
}
```

### Batch Operations
- **Use batch operations** for multiple devices
- **Implement parallel processing** with appropriate concurrency limits
- **Handle failures gracefully** with retry mechanisms
- **Monitor batch job progress** and implement proper logging

```python
# Batch operation example
batch_config = {
    "devices": ["192.168.1.1", "192.168.1.2", "192.168.1.3"],
    "command": "show version",
    "parallel_limit": 5,
    "timeout": 60,
    "retry_count": 3
}
```

### Caching Strategy
- **Enable result caching** for frequently accessed data
- **Set appropriate TTL values** based on data freshness requirements
- **Use cache invalidation** for dynamic data
- **Monitor cache hit rates** and optimize accordingly

```python
# Caching configuration
cache_config = {
    "enabled": True,
    "ttl": 3600,  # 1 hour
    "max_size": 1000,
    "eviction_policy": "lru"
}
```

## Operational Best Practices

### Monitoring and Alerting
- **Implement comprehensive monitoring** for all system components
- **Set up proactive alerting** for critical issues
- **Monitor key metrics** (response time, error rate, connection health)
- **Use structured logging** for better troubleshooting

```python
# Monitoring configuration
monitoring_config = {
    "metrics_enabled": True,
    "health_check_interval": 30,
    "alert_thresholds": {
        "error_rate": 0.05,
        "response_time": 5.0,
        "connection_failures": 0.1
    }
}
```

### Logging Best Practices
- **Use structured logging** with consistent format
- **Include correlation IDs** for request tracing
- **Log at appropriate levels** (DEBUG, INFO, WARNING, ERROR)
- **Implement log rotation** to manage disk space

```python
import logging
import json

# Structured logging example
logger = logging.getLogger(__name__)

def log_operation(operation, device, result, duration):
    log_data = {
        "operation": operation,
        "device": device,
        "result": result,
        "duration": duration,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(json.dumps(log_data))
```

### Error Handling
- **Implement comprehensive error handling** for all operations
- **Use appropriate retry strategies** with exponential backoff
- **Log errors with sufficient context** for troubleshooting
- **Implement circuit breaker patterns** for failing services

```python
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

## Development Best Practices

### Code Organization
- **Use modular design** with clear separation of concerns
- **Implement proper abstraction layers** for different device types
- **Write comprehensive tests** for all functionality
- **Use version control** with meaningful commit messages

### Configuration Management
- **Use environment-specific configurations** (dev, staging, prod)
- **Implement configuration validation** at startup
- **Use configuration templates** for consistent deployments
- **Document all configuration options**

```python
# Configuration validation example
from pydantic import BaseModel, validator

class NetPulseConfig(BaseModel):
    api_key: str
    redis_host: str
    redis_port: int = 6379
    worker_concurrency: int = 10
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if len(v) < 32:
            raise ValueError('API key must be at least 32 characters')
        return v
```

### Testing Strategy
- **Implement unit tests** for core functionality
- **Use integration tests** for API endpoints
- **Implement end-to-end tests** for critical workflows
- **Use test fixtures** for consistent test data

```python
import pytest
from netpulse_sdk import NetPulseClient

@pytest.fixture
def client():
    return NetPulseClient(api_key="test-api-key")

def test_execute_command(client):
    """Test command execution"""
    result = client.execute_command("test-device", "show version")
    assert result.success
    assert result.output is not None
```

## Deployment Best Practices

### Infrastructure as Code
- **Use containerization** (Docker) for consistent deployments
- **Implement infrastructure as code** (Terraform, Ansible)
- **Use container orchestration** (Kubernetes, Docker Swarm)
- **Implement automated deployments** with CI/CD pipelines

### High Availability
- **Deploy multiple instances** for load distribution
- **Implement health checks** for automatic failover
- **Use load balancers** for traffic distribution
- **Implement data replication** for Redis and databases

```yaml
# Kubernetes deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: netpulse-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: netpulse-api
  template:
    metadata:
      labels:
        app: netpulse-api
    spec:
      containers:
      - name: netpulse-api
        image: netpulse:latest
        ports:
        - containerPort: 9000
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: netpulse-secrets
              key: api-key
```

### Backup and Recovery
- **Implement regular backups** for configuration and data
- **Test backup restoration** procedures regularly
- **Document recovery procedures** for different scenarios
- **Implement disaster recovery** plans

## Template Best Practices

### Jinja2 Templates
- **Use template inheritance** for common structures
- **Implement proper variable validation** in templates
- **Use filters and functions** for data transformation
- **Test templates** with various input data

```jinja2
{# Good: Use template inheritance #}
{% extends "base_config.j2" %}

{% block interface_config %}
{% for interface in interfaces %}
interface {{ interface.name }}
 description {{ interface.description }}
 ip address {{ interface.ip }} {{ interface.mask }}
{% if interface.shutdown %}
 shutdown
{% endif %}
{% endfor %}
{% endblock %}
```

### TextFSM Templates
- **Use descriptive variable names** in templates
- **Implement proper regex patterns** for reliable parsing
- **Test templates** with various command outputs
- **Document template usage** and limitations

```textfsm
# Good: Descriptive variable names and comments
Value INTERFACE_NAME (\S+)
Value IP_ADDRESS (\d+\.\d+\.\d+\.\d+)
Value SUBNET_MASK (\d+\.\d+\.\d+\.\d+)
Value STATUS (up|down)

Start
  ^${INTERFACE_NAME}\s+${IP_ADDRESS}\s+${SUBNET_MASK}\s+${STATUS} -> Record
```

## Troubleshooting Best Practices

### Diagnostic Information
- **Collect comprehensive logs** for troubleshooting
- **Include system information** in bug reports
- **Use correlation IDs** for request tracing
- **Implement debug modes** for detailed logging

### Performance Troubleshooting
- **Monitor key performance metrics** continuously
- **Implement performance profiling** for bottleneck identification
- **Use load testing** to identify performance limits
- **Optimize based on metrics** rather than assumptions

```python
# Performance monitoring example
import time
import psutil
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        logger.info(f"Function {func.__name__} took {end_time - start_time:.2f}s, "
                   f"memory delta: {end_memory - start_memory} bytes")
        
        return result
    return wrapper
```

## Maintenance Best Practices

### Regular Maintenance
- **Schedule regular system updates** for security patches
- **Implement log rotation** to manage disk space
- **Monitor system resources** and plan capacity
- **Review and optimize** configurations regularly

### Documentation
- **Maintain up-to-date documentation** for all procedures
- **Document configuration changes** and their impact
- **Create runbooks** for common operational tasks
- **Implement change management** processes

### Capacity Planning
- **Monitor resource utilization** trends
- **Plan for growth** in device count and traffic
- **Implement auto-scaling** where possible
- **Regular capacity reviews** and adjustments

---

For more information, see:
- [Log Analysis](../troubleshooting/log-analysis.md)
- [Performance Tuning](../advanced/performance-tuning.md) 