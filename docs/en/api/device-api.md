# Device Operation API

## Overview

Device Operation API (`/device/*`) is the core interface of NetPulse, providing the following features:

- **Operation Identification** - Automatically identifies operation type (query/configuration) based on request parameters
- **Unified Interface** - Supports all implemented drivers and device types
- **Simplified Usage** - Reduces API call complexity through unified interface
- **Basic Functions** - Supports device operations, connection testing, and batch operations

## API Endpoints

### POST /device/execute

Unified device operation endpoint that identifies operation type based on request parameters.

**Function Description**:
- **Query Operation** - When request contains `command` field
- **Configuration Operation** - When request contains `config` field
- **Queue Selection** - Automatically selects queue strategy based on driver type (can be manually specified)

**Request Example**:

```bash
curl -X POST "http://localhost:9000/device/execute" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "admin123"
    },
    "command": "show version"
  }'
```

**Configuration Operation Example**:

```bash
curl -X POST "http://localhost:9000/device/execute" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "admin123"
    },
    "config": "interface GigabitEthernet0/1\n description Test Interface"
  }'
```

### POST /device/bulk

Batch device operation endpoint that supports executing the same operation on multiple devices.

**Request Example**:

```bash
curl -X POST "http://localhost:9000/device/bulk" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "devices": [
      {
        "host": "192.168.1.1",
        "username": "admin",
        "password": "admin123"
      },
      {
        "host": "192.168.1.2",
        "username": "admin",
        "password": "admin123"
      }
    ],
    "connection_args": {
      "device_type": "cisco_ios",
      "timeout": 30
    },
    "command": "show version"
  }'
```

### POST /device/test-connection

Test device connection status, used to verify device connection and authentication availability. Supports different driver types such as Netmiko, NAPALM, PyEAPI, and Paramiko.

**Request Example**:

```bash
curl -X POST "http://localhost:9000/device/test-connection" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "admin123"
    }
  }'
```

**Response Example**:

```json
{
  "code": 200,
  "message": "Connection test completed",
  "data": {
    "success": true,
    "connection_time": 2.5,
    "error_message": null,
    "device_info": {
      "prompt": "Router#",
      "device_type": "cisco_ios",
      "host": "192.168.1.1"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Quick Start

### Scenario 1: Simple Query (Most Common)

**Requirement**: Query device version information

```python
import requests

response = requests.post(
    "http://localhost:9000/device/execute",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin123"
        },
        "command": "show version"
    }
)

job_id = response.json()["data"]["id"]
print(f"Job ID: {job_id}")
```

**Note**: Just provide connection parameters and command, other parameters use default values.

### Scenario 2: Configuration Push (Need to Save)

**Requirement**: Configure interface and save

```python
response = requests.post(
    "http://localhost:9000/device/execute",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin123"
        },
        "config": [
            "interface GigabitEthernet0/1",
            " description Test",
            " no shutdown"
        ],
        "driver_args": {
            "save": True,              # Save configuration
            "exit_config_mode": True   # Exit configuration mode
        }
    }
)
```

**Note**: Configuration operations are recommended to set `save: true` to save configuration.

### Scenario 3: Slow Device Optimization

**Requirement**: Operate slow-responding devices, need to increase timeout

```python
response = requests.post(
    "http://localhost:9000/device/execute",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin123",
            "timeout": 60              # Increase connection timeout to 60 seconds
        },
        "command": "show running-config",
        "driver_args": {
            "read_timeout": 120,       # Read timeout 120 seconds
            "delay_factor": 3          # Delay factor 3 (slow devices)
        },
        "options": {
            "ttl": 600                 # Task timeout 600 seconds
        }
    }
)
```

**Note**: Slow devices need to increase various timeout parameters.

## Parameter Details

### connection_args (Connection Parameters)

Required for all operations, used to establish device connection.

**Required Parameters**:
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| device_type | string | Device type | `cisco_ios`, `juniper_junos`, `arista_eos` |
| host | string | Device IP address | `192.168.1.1` |
| username | string | Login username | `admin` |
| password | string | Login password | `password123` |

**Optional Parameters**:
| Parameter | Type | Default | Use Case |
|-----------|------|---------|----------|
| port | integer | 22 | Non-standard SSH port |
| timeout | integer | 30 | Connection timeout (seconds), can be increased for slow networks |
| secret | string | - | Privileged mode password (enable password) |
| enable_mode | boolean | true | Whether to enter privileged mode for configuration operations |

> **Tip**: Different drivers may have additional parameters in `connection_args`, see driver-specific documentation for details.

### driver_args (Driver Parameters)

Driver-specific parameters, vary by driver type and operation type. **Most scenarios don't need to specify**, use default values.

**When to Specify**:
- Slow devices: Increase `read_timeout`, `delay_factor`
- Configuration operations: Set `save`, `exit_config_mode`
- Special requirements: Refer to driver-specific documentation

**Common Parameters by Driver**:

**Netmiko** (SSH devices):
```json
{
  "read_timeout": 60,        // Read timeout (slow devices)
  "delay_factor": 2,         // Delay factor (slow devices)
  "save": true,              // Save after configuration operation
  "exit_config_mode": true   // Exit configuration mode after configuration operation
}
```

**NAPALM** (Multi-vendor):
```json
{
  "optional_args": {
    "secret": "enable_password"  // Privileged mode password
  }
}
```

**PyEAPI** (Arista-specific):
```json
{
  "transport": "https",      // Transport protocol
  "port": 443,               // API port
  "verify": false            // SSL verification
}
```

> **Detailed Parameter Description**: Please refer to driver-specific documentation ([Netmiko](../drivers/netmiko.md), [NAPALM](../drivers/napalm.md), [PyEAPI](../drivers/pyeapi.md), [Paramiko](../drivers/paramiko.md))

### options

Global options that control task execution behavior.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| queue_strategy | string | Auto-select | Queue strategy: `pinned` (SSH long connection, connection reuse) or `fifo` (HTTP short connection). Netmiko/NAPALM default `pinned`, PyEAPI default `fifo` |
| ttl | integer | 300 (600 for batch) | Task timeout (seconds). Single device operation default 300 seconds, batch operation default 600 seconds |
| parsing | object | null | Output parsing configuration (TextFSM/TTP, etc.) |
| rendering | object | null | Template rendering configuration (Jinja2, etc.) |
| webhook | object | null | Webhook callback configuration |

**Queue Strategy Selection Recommendations**:
- **`pinned`**: Suitable for SSH/Telnet long connections (Netmiko, NAPALM), supports connection reuse, improves performance
- **`fifo`**: Suitable for HTTP/HTTPS stateless connections (PyEAPI), creates new connection each time

## Response Models

### SubmitJobResponse

Job submission response (single device operation).

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "job_123456",
    "status": "queued",
    "queue": "pinned_192.168.1.1"
  }
}
```

### BatchSubmitJobResponse

Batch job submission response.

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "succeeded": [
      {
        "id": "job_123456",
        "status": "queued",
        "queue": "pinned_192.168.1.1",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "failed": [
      "192.168.1.3",
      "192.168.1.5"
    ]
  }
}
```

**Description**:
- `succeeded`: List of successfully submitted tasks (`JobInResponse` objects)
- `failed`: List of failed device hosts (string array)

### ConnectionTestResponse

Connection test response.

```json
{
  "code": 200,
  "message": "Connection test completed",
  "data": {
    "success": true,
    "connection_time": 2.5,
    "error_message": null,
    "device_info": {
      "prompt": "Router#",
      "device_type": "cisco_ios",
      "host": "192.168.1.1"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## Batch Operations

Batch device operations support executing the same operation on multiple devices, suitable for large-scale network operations scenarios.

### Batch Query Operations

```python
# Batch query device status
response = requests.post(
    "http://localhost:9000/device/bulk",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "devices": [
            {"host": "192.168.1.1", "username": "admin", "password": "admin123"},
            {"host": "192.168.1.2", "username": "admin", "password": "admin123"},
            {"host": "192.168.1.3", "username": "admin", "password": "admin123"}
        ],
        "connection_args": {
            "device_type": "cisco_ios",
            "timeout": 30
        },
        "command": "show interfaces status"
    }
)

result = response.json()
data = result['data']
print(f"Success: {len(data['succeeded']) if data['succeeded'] else 0}")
print(f"Failed: {len(data['failed']) if data['failed'] else 0}")

# Handle failed devices
if data.get('failed'):
    print(f"Failed devices: {data['failed']}")
```

### Mixed Vendor Batch Operations

```python
# Mixed vendor device batch query
response = requests.post(
    "http://localhost:9000/device/bulk",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "devices": [
            {"host": "192.168.1.1", "device_type": "cisco_ios"},
            {"host": "192.168.1.2", "device_type": "cisco_nxos"},
            {"host": "192.168.1.3", "device_type": "juniper_junos"}
        ],
        "connection_args": {
            "username": "admin",
            "password": "admin123",
            "timeout": 60
        },
        "command": "show version"
    }
)
```

### Batch Configuration Operations

```python
# Batch push configuration
response = requests.post(
    "http://localhost:9000/device/bulk",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "devices": [
            {"host": "192.168.1.1"},
            {"host": "192.168.1.2"},
            {"host": "192.168.1.3"}
        ],
        "connection_args": {
            "device_type": "cisco_ios",
            "username": "admin",
            "password": "admin123",
            "secret": "enable_password"
        },
        "config": [
            "interface range GigabitEthernet0/1-10",
            "description User Ports",
            "switchport mode access",
            "switchport access vlan 200",
            "no shutdown"
        ],
        "driver_args": {
            "exit_config_mode": True,
            "enter_config_mode": True,
            "cmd_verify": True
        },
        "options": {
            "queue_strategy": "pinned",
            "ttl": 600
        }
    }
)
```

### Batch Operation Response Format

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "succeeded": [
      {
        "id": "job_123456",
        "status": "queued",
        "queue": "pinned_192.168.1.1"
      }
    ],
    "failed": [
      "192.168.1.3"
    ]
  }
}
```

**Description**:
- `succeeded`: List of successfully submitted task objects, each object contains task ID, status, etc.
- `failed`: List of failed device host addresses (string array), failure reasons need to be queried through task status

### Batch Operation Best Practices

1. **Device Grouping Strategy**: Group by vendor or geographic location, recommended batch size 10-50 devices
2. **Error Handling**: Implement retry mechanism, record detailed error information
3. **Performance Optimization**: Use device-bound queues, parallel processing of multiple devices
4. **Monitoring and Alerting**: Real-time monitoring of operation status, set failure rate alerts

## Device Connection Testing

### Supported Driver Types

#### Netmiko (SSH)

**Basic Connection Test**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 30
  }
}
```

**Complete Parameter Example**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password",
    "port": 22,
    "timeout": 60,
    "keepalive": 30,
    "global_delay_factor": 2,
    "fast_cli": false,
    "verbose": true
  }
}
```

#### NAPALM (Multi-vendor)

**Connection Test Example**:
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "eos",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 60,
    "optional_args": {
      "port": 22,
      "secret": "enable_password",
      "transport": "ssh"
    }
  }
}
```

**Cisco IOS Example**:
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "optional_args": {
      "secret": "enable_password"
    }
  }
}
```

#### PyEAPI (Arista-specific)

**Connection Test Example**:
```json
{
  "driver": "pyeapi",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "transport": "https",
    "port": 443,
    "timeout": 30
  }
}
```

#### Paramiko (Linux Servers)

**Basic Connection Test**:
```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password",
    "port": 22,
    "timeout": 30.0
  }
}
```

**Key Authentication Example**:
```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "key_filename": "/path/to/private_key",
    "passphrase": "your_key_passphrase",
    "port": 22
  }
}
```

### Connection Parameter Description

**Netmiko Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| device_type | string | - | Device type (cisco_ios, cisco_nxos, juniper_junos, arista_eos) |
| host | string | - | Device IP address |
| username | string | - | Username |
| password | string | - | Password |
| secret | string | - | Privileged mode password |
| port | integer | 22 | SSH port |
| timeout | integer | 20 | Connection timeout |
| keepalive | integer | 60 | Keepalive time |
| global_delay_factor | float | 1 | Global delay factor |
| fast_cli | boolean | false | Fast CLI mode |
| verbose | boolean | false | Verbose output |

**NAPALM Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| device_type | string | - | Device type (ios, iosxr, junos, eos, nxos) |
| hostname | string | - | Device IP address |
| username | string | - | Username |
| password | string | - | Password |
| timeout | integer | 60 | Connection timeout |
| optional_args | object | {} | Optional parameters |

**PyEAPI Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| host | string | - | Device IP address |
| username | string | - | Username |
| password | string | - | Password |
| transport | string | https | Transport protocol (http/https) |
| port | integer | 443 | Port number |
| timeout | integer | 30 | Connection timeout |

### Common Errors

**Connection Timeout**:
```json
{
  "code": 200,
  "message": "Connection test failed",
  "data": {
    "success": false,
    "error_message": "Connection timeout after 30 seconds"
  }
}
```

**Authentication Failed**:
```json
{
  "code": 200,
  "message": "Connection test failed",
  "data": {
    "success": false,
    "error_message": "Authentication failed"
  }
}
```

> **Tip**: Connection test is a synchronous operation that returns results immediately, no need to query task status.

## Best Practices

> **For detailed best practices guide, see**: [API Best Practices](./api-best-practices.md)

### Quick Tips

- **Driver Selection**: Netmiko (universal SSH), NAPALM (multi-vendor), PyEAPI (Arista-specific), Paramiko (Linux servers)
- **Queue Strategy**: Usually no need to specify, system will automatically select based on driver
- **Error Handling**: Implement retry mechanism, record detailed error information
- **Task Tracking**: Use `/job` interface to query task status, or use webhook callbacks

## Notes

1. **Authentication Required**: All API requests require API Key authentication (supports Query parameter, Header, or Cookie three methods)
2. **Asynchronous Processing**: Device operations are asynchronous, need to query task status to get results (connection test is synchronous)
3. **Connection Parameters**: Ensure device connection parameters are correct, especially username and password
4. **Timeout Settings**: Adjust connection timeout based on network environment, slow devices need to increase timeout parameters
5. **Queue Management**: System will automatically select queue strategy, usually no need to manually specify
6. **Batch Operations**: Recommended batch size 10-50 devices to avoid system overload

---

## Related Documentation

- [API Overview](./api-overview.md) - Learn about all API interfaces
- [Driver Selection](../drivers/index.md) - Choose the right driver type
- [API Best Practices](./api-best-practices.md) - Usage recommendations and optimization tips
