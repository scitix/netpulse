# API Best Practices

## Overview

This document provides best practices for using NetPulse API to help you build efficient and reliable network automation solutions.

## Authentication and Security

### API Key Management

#### Best Practices
```bash
# Use environment variables to store API keys
export NETPULSE_API_KEY="your-api-key-here"

# Use in requests
curl -H "X-API-KEY: $NETPULSE_API_KEY" \
     http://localhost:9000/health
```

#### Security Recommendations
- Regularly rotate API keys
- Do not hardcode keys in code
- Use HTTPS for transmission
- Limit API key access permissions

### Device Credential Management

#### Using Vault to Store Credentials (Recommended)

**Best Practice**: Use HashiCorp Vault to store device credentials, avoiding directly passing passwords in API requests.

```bash
# 1. Create credentials in Vault
curl -X POST \
  -H "X-API-KEY: $NETPULSE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin",
    "username": "admin",
    "password": "secure_password",
    "metadata": {
      "description": "HQ site admin credentials",
      "site": "hq"
    }
  }' \
  http://localhost:9000/credential/vault/create

# 2. Use credential reference in device operations
curl -X POST \
  -H "X-API-KEY: $NETPULSE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "credential_ref": "sites/hq/admin",
      "device_type": "cisco_ios"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute
```

#### Security Recommendations
- **Use Vault to store credentials**: Avoid exposing passwords in code, logs, or API requests
- **Plan credential paths**: Use hierarchical structures (e.g., `sites/{site}/{role}`) for easier management
- **Regular password rotation**: Regularly update passwords in Vault and create new versions
- **Principle of least privilege**: Create different Vault tokens with different permissions for different applications
- **Credential caching**: System automatically caches credentials to avoid repeated reads

#### Credential Path Naming Conventions

```python
# Recommended path structure
credential_paths = {
    "sites/hq/admin": "HQ site admin credentials",
    "sites/hq/readonly": "HQ site read-only credentials",
    "sites/branch1/admin": "Branch 1 admin credentials",
    "devices/core/backup": "Core device backup credentials",
    "environments/prod/admin": "Production environment admin credentials"
}
```

See: [Vault Credential Management API](./credential-api.md)

### Request Header Settings

```bash
# Standard request headers
curl -X POST \
  -H "X-API-KEY: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"key": "value"}' \
  http://localhost:9000/api/endpoint
```

## Connection Management

### Queue Strategy Selection

#### FIFO Queue (Recommended for general operations)
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "credential_ref": "sites/hq/admin",
    "device_type": "cisco_ios"
  },
  "options": {
    "queue_strategy": "fifo"
  }
}
```

#### Pinned Queue (Recommended for frequent operations)
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "credential_ref": "sites/hq/admin",
    "device_type": "cisco_ios"
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

### Connection Parameter Optimization

#### Timeout Settings
```json
{
  "connection_args": {
    "host": "192.168.1.1",
    "credential_ref": "sites/hq/admin",
    "device_type": "cisco_ios",
    "timeout": 30,
    "read_timeout": 60,
    "delay_factor": 2
  }
}
```

#### Connection Reuse
```json
{
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

!!! note "Connection Reuse Note"
    When using `queue_strategy: "pinned"`, the system will automatically reuse connections without additional configuration.

## Batch Operation Optimization

### Device Grouping Strategy

#### Group by Vendor
```python
def group_devices_by_vendor(devices):
    """Group devices by vendor"""
    groups = {}
    for device in devices:
        vendor = get_vendor_from_device_type(device['device_type'])
        if vendor not in groups:
            groups[vendor] = []
        groups[vendor].append(device)
    return groups
```

#### Group by Geographic Location
```python
def group_devices_by_location(devices):
    """Group devices by geographic location"""
    groups = {}
    for device in devices:
        location = device.get('location', 'unknown')
        if location not in groups:
            groups[location] = []
        groups[location].append(device)
    return groups
```

### Batch Operation Best Practices

#### 1. Reasonable Batch Size
```python
# Recommended batch size: 10-50 devices
BATCH_SIZE = 20

def execute_batch_commands(devices, command):
    """Execute commands in batches"""
    results = []
    for i in range(0, len(devices), BATCH_SIZE):
        batch = devices[i:i + BATCH_SIZE]
        batch_result = execute_command_batch(batch, command)
        results.extend(batch_result)
    return results
```

#### 2. Error Handling and Retry
```python
import time
from typing import List, Dict

def execute_with_retry(devices: List[Dict], command: str, max_retries: int = 3):
    """Command execution with retry"""
    results = []
    failed_devices = []
    
    for device in devices:
        for attempt in range(max_retries):
            try:
                result = execute_single_command(device, command)
                results.append(result)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    failed_devices.append({
                        'device': device,
                        'error': str(e)
                    })
                else:
                    time.sleep(2 ** attempt)  # Exponential backoff
    
    return results, failed_devices
```

## Template Usage

### Jinja2 Template Best Practices

#### 1. Template Structure
```jinja2
{# Configuration template example #}
{% for interface in interfaces %}
interface {{ interface.name }}
 description {{ interface.description }}
 ip address {{ interface.ip_address }} {{ interface.subnet_mask }}
 no shutdown
{% endfor %}
```

#### 2. Variable Validation
```python
def validate_template_variables(template_vars):
    """Validate template variables"""
    required_vars = ['interfaces', 'hostname', 'domain_name']
    missing_vars = [var for var in required_vars if var not in template_vars]
    
    if missing_vars:
        raise ValueError(f"Missing required variables: {missing_vars}")
    
    return True
```

### TextFSM Parsing Best Practices

#### 1. Template Design
```textfsm
Value HOSTNAME (\S+)
Value UPTIME (.+)
Value VERSION (.+)

Start
  ^\s*${HOSTNAME}\s+uptime\s+is\s+${UPTIME}
  ^\s*.*Version\s+${VERSION}
  ^\s*$$
  ^.* -> Error
```

#### 2. Parse Result Processing
```python
def parse_command_output(output: str, template_name: str):
    """Parse command output"""
    try:
        parsed_result = parse_with_textfsm(output, template_name)
        return {
            'success': True,
            'data': parsed_result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'raw_output': output
        }
```

## Error Handling

### Common Error Code Handling

```python
def handle_api_response(response):
    """Handle API response"""
    if response.status_code == 200:
        data = response.json()
        if data['code'] == 200:
            return {'success': True, 'data': data['data']}
        else:
            return {'success': False, 'error': data['message']}
    elif response.status_code == 401:
        return {'success': False, 'error': 'Authentication failed, please check API key'}
    elif response.status_code == 404:
        return {'success': False, 'error': 'Resource not found'}
    elif response.status_code == 500:
        return {'success': False, 'error': 'Internal server error'}
    else:
        return {'success': False, 'error': f'Unknown error: {response.status_code}'}
```

### Retry Mechanism

```python
import requests
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    """Retry decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3, delay=2)
def api_request(url, headers, data):
    """API request with retry"""
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
```

## Performance Optimization

### 1. Connection Pool Management

```python
class ConnectionPool:
    """Connection pool management"""
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.active_connections = {}
    
    def get_connection(self, device_id):
        """Get connection"""
        if device_id in self.active_connections:
            return self.active_connections[device_id]
        return None
    
    def add_connection(self, device_id, connection):
        """Add connection"""
        if len(self.active_connections) < self.max_connections:
            self.active_connections[device_id] = connection
            return True
        return False
```

### 2. Async Processing

```python
import asyncio
import aiohttp

async def execute_commands_async(devices, command):
    """Async execute commands"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for device in devices:
            task = execute_single_command_async(session, device, command)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

async def execute_single_command_async(session, device, command):
    """Async execute single command"""
    url = "http://localhost:9000/device/execute"
    headers = {"X-API-KEY": f"{API_KEY}"}
    data = {
        "driver": "netmiko",
        "connection_args": device,
        "command": command
    }
    
    async with session.post(url, headers=headers, json=data) as response:
        return await response.json()
```

### 3. Caching Strategy

```python
import redis
import json
import hashlib

class ResultCache:
    """Result cache"""
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour
    
    def get_cache_key(self, device_id, command):
        """Generate cache key"""
        content = f"{device_id}:{command}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_cached_result(self, device_id, command):
        """Get cached result"""
        key = self.get_cache_key(device_id, command)
        result = self.redis.get(key)
        return json.loads(result) if result else None
    
    def cache_result(self, device_id, command, result):
        """Cache result"""
        key = self.get_cache_key(device_id, command)
        self.redis.setex(key, self.ttl, json.dumps(result))
```

## Monitoring and Logging

### 1. Job Monitoring

```python
def monitor_job_status(job_id):
    """Monitor job status"""
    while True:
        response = requests.get(
            f"http://localhost:9000/job?id={job_id}",
            headers={"X-API-KEY": f"{API_KEY}"}
        )
        data = response.json()
        
        if data['data']['status'] in ['completed', 'failed']:
            return data['data']
        
        time.sleep(5)  # Check every 5 seconds
```

### 2. Performance Metrics

```python
import time
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """Performance metrics"""
    total_devices: int
    successful_operations: int
    failed_operations: int
    total_time: float
    average_time_per_device: float

def calculate_performance_metrics(results):
    """Calculate performance metrics"""
    total_devices = len(results)
    successful = sum(1 for r in results if r.get('success', False))
    failed = total_devices - successful
    
    return PerformanceMetrics(
        total_devices=total_devices,
        successful_operations=successful,
        failed_operations=failed,
        total_time=0,  # Need actual calculation
        average_time_per_device=0  # Need actual calculation
    )
```

## Webhook Integration

### 1. Webhook Configuration

```json
{
  "options": {
    "webhook": {
      "url": "https://your-webhook-url.com/callback",
      "method": "POST",
      "headers": {
        "Content-Type": "application/json",
        "X-Custom-Header": "custom-value"
      },
      "timeout": 30
    }
  }
}
```

### 2. Webhook Processing

```python
from flask import Flask, request
import json

app = Flask(__name__)

@app.route('/webhook/callback', methods=['POST'])
def webhook_callback():
    """Handle webhook callback"""
    data = request.json
    
    # Handle different types of callbacks
    if data['type'] == 'job_completed':
        handle_job_completed(data)
    elif data['type'] == 'job_failed':
        handle_job_failed(data)
    elif data['type'] == 'device_connected':
        handle_device_connected(data)
    
    return {'status': 'success'}

def handle_job_completed(data):
    """Handle job completion callback"""
    job_id = data['job_id']
    result = data['result']
    
    # Log
    print(f"Job {job_id} completed successfully")
    
    # Send notification
    send_notification(f"Job {job_id} execution completed")
```

## Best Practices Summary

### 1. Development Phase
- Use development environment API keys
- Enable detailed logging
- Use small-scale test data
- Implement complete error handling

### 2. Production Phase
- Use strong password API keys
- Enable HTTPS transmission
- Implement monitoring and alerting
- Regularly backup configurations

### 3. Maintenance Phase
- Regularly check system status
- Monitor performance metrics
- Update security patches
- Optimize configuration parameters

## Related Documentation

- [API Overview](./api-overview.md) - Complete API documentation
- [Device Operation API](./device-api.md) - Core device operation interfaces
- [Vault Credential Management API](./credential-api.md) - Vault credential management interface
- [API Examples](./api-examples.md) - Real-world application scenarios
