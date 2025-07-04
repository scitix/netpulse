# First API Call

This guide will walk you through your first NetPulse API call and teach you basic network device management operations.

## Learning Objectives

Through this guide, you will learn:
- Understand basic NetPulse API concepts
- Configure network device connections
- Execute network commands
- Handle API responses
- Use best practices

## Prerequisites

Before starting, please ensure:
- ✅ NetPulse services are started and running
- ✅ You have obtained a valid API key
- ✅ You have available network devices (routers, switches, etc.)
- ✅ Devices support SSH connections

## API Authentication

NetPulse uses Bearer Token authentication:

```bash
# API key format
Authorization: Bearer YOUR_API_KEY

# Example
curl -H "Authorization: Bearer sk-1234567890abcdef" \
     http://localhost:9000/health
```

## Basic API Calls

### 1. Health Check

First, test if the API service is running normally:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00+08:00",
  "version": "1.0.0",
  "uptime": 3600
}
```

### 2. Get API Information

View API version and feature information:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/
```

**Expected Response:**
```json
{
  "name": "NetPulse API",
  "version": "0.1.0",
  "description": "Distributed RESTful API for network device management",
  "features": [
    "multi-vendor support",
    "persistent connections",
    "batch operations",
    "template engine"
  ],
  "supported_vendors": [
    "cisco_ios",
    "cisco_nxos",
    "arista_eos",
    "juniper_junos"
  ]
}
```

## Device Management

### 1. Add Network Device

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "your_password",
    "device_type": "cisco_ios",
    "port": 22,
    "timeout": 30
  }' \
  http://localhost:9000/devices
```

**Request Parameter Description:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `hostname` | string | ✅ | Device IP address or hostname | `192.168.1.1` |
| `username` | string | ✅ | Login username | `admin` |
| `password` | string | ✅ | Login password | `password123` |
| `device_type` | string | ✅ | Device type | `cisco_ios` |
| `port` | integer | ❌ | SSH port | `22` |
| `timeout` | integer | ❌ | Connection timeout | `30` |

**Expected Response:**
```json
{
  "success": true,
  "device_id": "dev_1234567890",
  "hostname": "192.168.1.1",
  "status": "connected",
  "message": "Device added successfully"
}
```

### 2. View Device List

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/devices
```

**Expected Response:**
```json
{
  "devices": [
    {
      "device_id": "dev_1234567890",
      "hostname": "192.168.1.1",
      "device_type": "cisco_ios",
      "status": "connected",
      "last_seen": "2024-01-01T12:00:00+08:00"
    }
  ],
  "total": 1
}
```

### 3. Test Device Connection

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1"
  }' \
  http://localhost:9000/devices/test
```

**Expected Response:**
```json
{
  "success": true,
  "hostname": "192.168.1.1",
  "connection_time": 0.5,
  "device_info": {
    "hostname": "Router-01",
    "model": "Cisco IOS XE",
    "version": "17.03.01"
  }
}
```

## Command Execution

### 1. Execute Single Command

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute
```

**Expected Response:**
```json
{
  "success": true,
  "hostname": "192.168.1.1",
  "command": "show version",
  "output": "Cisco IOS XE Software, Version 17.03.01...",
  "execution_time": 0.8,
  "timestamp": "2024-01-01T12:00:00+08:00"
}
```

### 2. Execute Multiple Commands

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "commands": [
      "show version",
      "show interfaces",
      "show ip interface brief"
    ]
  }' \
  http://localhost:9000/execute/batch
```

**Expected Response:**
```json
{
  "success": true,
  "hostname": "192.168.1.1",
  "results": [
    {
      "command": "show version",
      "output": "Cisco IOS XE Software...",
      "execution_time": 0.8
    },
    {
      "command": "show interfaces",
      "output": "Interface GigabitEthernet0/0...",
      "execution_time": 1.2
    },
    {
      "command": "show ip interface brief",
      "output": "Interface IP-Address OK? Method Status...",
      "execution_time": 0.5
    }
  ],
  "total_time": 2.5
}
```

### 3. Batch Device Operations

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostnames": ["192.168.1.1", "192.168.1.2", "192.168.1.3"],
    "command": "show version"
  }' \
  http://localhost:9000/execute/multi
```

**Expected Response:**
```json
{
  "success": true,
  "results": [
    {
      "hostname": "192.168.1.1",
      "success": true,
      "output": "Cisco IOS XE Software...",
      "execution_time": 0.8
    },
    {
      "hostname": "192.168.1.2",
      "success": true,
      "output": "Cisco IOS XE Software...",
      "execution_time": 0.9
    },
    {
      "hostname": "192.168.1.3",
      "success": false,
      "error": "Connection timeout",
      "execution_time": 30.0
    }
  ],
  "summary": {
    "total": 3,
    "successful": 2,
    "failed": 1
  }
}
```

## Common Command Examples

### Device Information Queries

```bash
# Get device version information
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute

# Get interface information
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show interfaces"
  }' \
  http://localhost:9000/execute

# Get routing table
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show ip route"
  }' \
  http://localhost:9000/execute
```

### Configuration Management

```bash
# View current configuration
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show running-config"
  }' \
  http://localhost:9000/execute

# Save configuration
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "write memory"
  }' \
  http://localhost:9000/execute
```

## Error Handling

### Common Error Types

#### 1. Authentication Error
```json
{
  "error": "unauthorized",
  "message": "Invalid API key",
  "status_code": 401
}
```

#### 2. Device Connection Error
```json
{
  "error": "connection_failed",
  "message": "Unable to connect to device",
  "hostname": "192.168.1.1",
  "status_code": 500
}
```

#### 3. Command Execution Error
```json
{
  "error": "command_failed",
  "message": "Command execution failed",
  "hostname": "192.168.1.1",
  "command": "show invalid-command",
  "status_code": 400
}
```

### Error Handling Best Practices

```bash
# Use -w parameter to get HTTP status code
curl -w "HTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute

# Use jq to parse JSON response
curl -s -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute | jq '.output'
```

## Performance Optimization

### 1. Use Long Connections

NetPulse supports persistent connections to avoid repeated connection establishment:

```bash
# First connection will establish persistent connection
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show version"
  }' \
  http://localhost:9000/execute

# Subsequent commands will reuse connection for faster response
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "command": "show interfaces"
  }' \
  http://localhost:9000/execute
```

### 2. Batch Operations

For multiple commands, use the batch operation interface:

```bash
# Recommended: Use batch interface
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "192.168.1.1",
    "commands": [
      "show version",
      "show interfaces",
      "show ip route"
    ]
  }' \
  http://localhost:9000/execute/batch
```

## Practical Script Examples

### Python Script

```python
import requests
import json

class NetPulseClient:
    def __init__(self, api_key, base_url="http://localhost:9000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def execute_command(self, hostname, command):
        """Execute single command"""
        url = f"{self.base_url}/execute"
        data = {
            "hostname": hostname,
            "command": command
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()
    
    def batch_commands(self, hostname, commands):
        """Execute batch commands"""
        url = f"{self.base_url}/execute/batch"
        data = {
            "hostname": hostname,
            "commands": commands
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.json()

# Usage example
client = NetPulseClient("YOUR_API_KEY")

# Execute single command
result = client.execute_command("192.168.1.1", "show version")
print(result["output"])

# Execute batch commands
commands = ["show version", "show interfaces", "show ip route"]
results = client.batch_commands("192.168.1.1", commands)
for result in results["results"]:
    print(f"Command: {result['command']}")
    print(f"Output: {result['output']}\n")
```

### Shell Script

```bash
#!/bin/bash

# NetPulse API configuration
API_KEY="YOUR_API_KEY"
API_URL="http://localhost:9000"
DEVICE_HOST="192.168.1.1"

# Execute command function
execute_command() {
    local command="$1"
    curl -s -X POST \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"hostname\": \"$DEVICE_HOST\",
            \"command\": \"$command\"
        }" \
        "$API_URL/execute" | jq -r '.output'
}

# Usage example
echo "=== Device Version Information ==="
execute_command "show version"

echo -e "\n=== Interface Status ==="
execute_command "show ip interface brief"

echo -e "\n=== Routing Table ==="
execute_command "show ip route"
```

## Next Steps

Now that you have mastered basic API calls, we recommend continuing to learn:

- **[API Reference](../guides/api.md)** - Complete API documentation
- **[Batch Operations](../advanced/batch-operations.md)** - Large-scale device management
- **[Template System](../advanced/templates.md)** - Use templates to simplify operations
- **[Error Handling](../reference/error-codes.md)** - Detailed error code descriptions

## Frequently Asked Questions

### Q: API call returns 401 error?
A: Check if the API key is correct and ensure you're using the `Bearer` prefix.

### Q: Device connection timeout?
A: Check if the device IP address, username, and password are correct, and ensure network connectivity.

### Q: Command execution failed?
A: Check if the command syntax is correct and ensure the device supports the command.

### Q: How to improve API call performance?
A: Use batch operation interfaces and leverage persistent connection features.

---

<div align="center">

**Congratulations! You have mastered basic NetPulse API usage**

[API Reference →](../guides/api.md)

</div> 