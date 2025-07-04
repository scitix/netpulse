# SDK Guide

## Quick Start

## Authentication and Initialization

## Device Operations

## Batch Operations

## Tasks and Results

## Advanced Usage

## Frequently Asked Questions

## Overview

NetPulse SDK provides a Python client library that allows developers to easily integrate NetPulse API into their applications. The SDK supports both synchronous and asynchronous calling methods, adapting to different application scenarios.

## Installation

```bash
# Install from source (SDK is located in netpulse-client directory)
cd netpulse-client
pip install -e .

# Or use directly
export PYTHONPATH=/path/to/netpulse-client:$PYTHONPATH
```

### Basic Example

```python
from netpulse_client import NetPulseClient, ConnectionArgs

# Create client
client = NetPulseClient("http://localhost:9000", "your_api_key")

# Define device
device = ConnectionArgs(
    host="192.168.1.1",
    username="admin",
    password="admin123",
    device_type="cisco_ios"
)

# Execute command
result = client.exec_command(device, "show version")
print(f"Job ID: {result.job_id}")
print(f"Status: {result.status}")
```

## SDK Architecture

### Core Classes and Enums

```python
from enum import Enum
from typing import List, Dict, Any, Optional

class DriverName(str, Enum):
    """Supported driver types"""
    NETMIKO = "netmiko"
    NAPALM = "napalm"
    PYEAPI = "pyeapi"

class QueueStrategy(str, Enum):
    """Queue strategy"""
    PINNED = "pinned"
    FIFO = "fifo"

# Main data models
from netpulse_client import ConnectionArgs, CommandResult, ConfigResult, BatchResult
```

### Main Client Class

```python
from netpulse_client import NetPulseClient, ConnectionArgs

# Create client
client = NetPulseClient(
    endpoint="http://localhost:9000",
    api_key="your_api_key",
    timeout=300
)

# Define device
device = ConnectionArgs(
    host="192.168.1.1",
    username="admin",
    password="admin123",
    device_type="cisco_ios",
    port=22,
    timeout=30
)

# Execute command
result = client.exec_command(device, "show version")
print(f"Job ID: {result.job_id}")
print(f"Status: {result.status}")

# Push configuration
result = client.exec_config(device, "interface GigabitEthernet0/1\n description Test")
print(f"Configuration push job ID: {result.job_id}")
```

## Authentication and Initialization

### API Key Authentication

```python
from netpulse_client import NetPulseClient

# Initialize with API key
client = NetPulseClient(
    endpoint="http://localhost:9000",
    api_key="your_api_key"
)

# Test connection
try:
    health = client.health_check()
    print(f"API Status: {health['status']}")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Session Management

```python
# Create client with custom session
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'NetPulse-SDK/1.0',
    'Accept': 'application/json'
})

client = NetPulseClient(
    endpoint="http://localhost:9000",
    api_key="your_api_key",
    session=session
)
```

## Device Operations

### Single Device Commands

```python
from netpulse_client import NetPulseClient, ConnectionArgs

client = NetPulseClient("http://localhost:9000", "your_api_key")

# Define device
device = ConnectionArgs(
    host="192.168.1.1",
    username="admin",
    password="admin123",
    device_type="cisco_ios"
)

# Execute single command
result = client.exec_command(device, "show version")
print(f"Job ID: {result.job_id}")

# Wait for completion
job_result = client.wait_for_job(result.job_id)
print(f"Command output: {job_result.output}")
```

### Configuration Management

```python
# Push configuration
config = """
interface GigabitEthernet0/1
 description Test Interface
 no shutdown
"""

result = client.exec_config(device, config)
print(f"Config job ID: {result.job_id}")

# Wait for completion
job_result = client.wait_for_job(result.job_id)
if job_result.success:
    print("Configuration applied successfully")
else:
    print(f"Configuration failed: {job_result.error}")
```

### Connection Testing

```python
# Test device connection
try:
    test_result = client.test_connection(device)
    print(f"Connection successful: {test_result.device_info}")
except Exception as e:
    print(f"Connection failed: {e}")
```

## Batch Operations

### Multiple Commands

```python
# Execute multiple commands on single device
commands = [
    "show version",
    "show interfaces",
    "show ip route"
]

result = client.exec_commands(device, commands)
print(f"Batch job ID: {result.job_id}")

# Wait for completion
job_result = client.wait_for_job(result.job_id)
for cmd_result in job_result.results:
    print(f"Command: {cmd_result.command}")
    print(f"Output: {cmd_result.output}")
```

### Multiple Devices

```python
# Define multiple devices
devices = [
    ConnectionArgs(host="192.168.1.1", username="admin", password="admin123", device_type="cisco_ios"),
    ConnectionArgs(host="192.168.1.2", username="admin", password="admin123", device_type="cisco_ios"),
    ConnectionArgs(host="192.168.1.3", username="admin", password="admin123", device_type="cisco_ios")
]

# Execute same command on all devices
result = client.batch_execute(
    driver=DriverName.NETMIKO,
    devices=devices,
    command="show version"
)

print(f"Batch job ID: {result['job_id']}")
```

## Tasks and Results

### Job Management

```python
# Get job status
job_status = client.get_job(job_id)
print(f"Status: {job_status.status}")
print(f"Progress: {job_status.progress}")

# List all jobs
jobs = client.list_jobs()
for job in jobs:
    print(f"Job {job.id}: {job.status}")

# Cancel pending job
client.cancel_job(job_id)
```

### Result Handling

```python
# Wait for job completion with timeout
try:
    result = client.wait_for_job(job_id, timeout=300)
    if result.success:
        print(f"Success: {result.output}")
    else:
        print(f"Failed: {result.error}")
except TimeoutError:
    print("Job timed out")
```

## Advanced Usage

### Template Operations

```python
# Render template
template_data = {
    "name": "jinja2",
    "template": "interface {{ interface_name }}\n description {{ description }}",
    "context": {
        "interface_name": "GigabitEthernet0/1",
        "description": "Test Interface"
    }
}

rendered = client.render_template(template_data)
print(f"Rendered config: {rendered}")

# Parse command output
parse_data = {
    "name": "textfsm",
    "template": "file:///templates/show_version.textfsm",
    "context": "Cisco IOS Software, Version 15.2(4)S7..."
}

parsed = client.parse_output(parse_data)
print(f"Parsed data: {parsed}")
```

### Custom Options

```python
# Execute with custom options
options = {
    "queue_strategy": "pinned",
    "ttl": 600,
    "parsing": {
        "name": "textfsm",
        "template": "file:///templates/show_version.textfsm"
    }
}

result = client.exec_command(
    device, 
    "show version",
    options=options
)
```

### Error Handling

```python
from netpulse_client import NetPulseError

try:
    result = client.exec_command(device, "show version")
except NetPulseError as e:
    print(f"NetPulse error: {e}")
except requests.RequestException as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Frequently Asked Questions

### Q: How to handle timeouts?
A: Set appropriate timeout values and use try-catch blocks:

```python
client = NetPulseClient(
    endpoint="http://localhost:9000",
    api_key="your_api_key",
    timeout=300  # 5 minutes
)

try:
    result = client.wait_for_job(job_id, timeout=600)  # 10 minutes
except TimeoutError:
    print("Job timed out")
```

### Q: How to handle authentication errors?
A: Check your API key and endpoint:

```python
try:
    health = client.health_check()
except requests.HTTPError as e:
    if e.response.status_code == 401:
        print("Invalid API key")
    elif e.response.status_code == 404:
        print("Invalid endpoint")
```

### Q: How to improve performance?
A: Use batch operations and connection pooling:

```python
# Use batch operations for multiple devices
result = client.batch_execute(driver, devices, command)

# Reuse client instance
client = NetPulseClient(endpoint, api_key)
# ... use client multiple times
```

### Q: How to handle device connection failures?
A: Implement retry logic and error handling:

```python
import time

def execute_with_retry(client, device, command, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = client.exec_command(device, command)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Best Practices

### 1. Resource Management

```python
# Use context manager for automatic cleanup
with NetPulseClient(endpoint, api_key) as client:
    result = client.exec_command(device, "show version")
    # Client automatically closes session
```

### 2. Error Handling

```python
def safe_execute(client, device, command):
    try:
        result = client.exec_command(device, command)
        job_result = client.wait_for_job(result.job_id)
        return job_result
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return None
```

### 3. Configuration Management

```python
# Store sensitive data in environment variables
import os

client = NetPulseClient(
    endpoint=os.getenv("NETPULSE_ENDPOINT"),
    api_key=os.getenv("NETPULSE_API_KEY")
)
```

### 4. Logging

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use in your code
logger.info(f"Executing command on {device.host}")
result = client.exec_command(device, command)
logger.info(f"Job ID: {result.job_id}")
```

## Complete Example

```python
#!/usr/bin/env python3
"""
Complete example of using NetPulse SDK
"""

import os
import logging
from netpulse_client import NetPulseClient, ConnectionArgs, DriverName

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize client
    client = NetPulseClient(
        endpoint=os.getenv("NETPULSE_ENDPOINT", "http://localhost:9000"),
        api_key=os.getenv("NETPULSE_API_KEY")
    )
    
    # Define devices
    devices = [
        ConnectionArgs(
            host="192.168.1.1",
            username="admin",
            password="admin123",
            device_type="cisco_ios"
        ),
        ConnectionArgs(
            host="192.168.1.2",
            username="admin",
            password="admin123",
            device_type="cisco_ios"
        )
    ]
    
    try:
        # Test connections
        for device in devices:
            logger.info(f"Testing connection to {device.host}")
            test_result = client.test_connection(device)
            logger.info(f"Connection successful: {test_result.device_info}")
        
        # Execute commands on all devices
        logger.info("Executing commands on all devices")
        result = client.batch_execute(
            driver=DriverName.NETMIKO,
            devices=devices,
            command="show version"
        )
        
        # Wait for completion
        job_result = client.wait_for_job(result['job_id'])
        
        # Process results
        for device_result in job_result.results:
            logger.info(f"Device: {device_result.hostname}")
            if device_result.success:
                logger.info(f"Output: {device_result.output}")
            else:
                logger.error(f"Error: {device_result.error}")
                
    except Exception as e:
        logger.error(f"Operation failed: {e}")

if __name__ == "__main__":
    main()
```

This completes the NetPulse SDK guide. The SDK provides a comprehensive Python interface for interacting with NetPulse API, supporting both simple and complex network automation scenarios. 