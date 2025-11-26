# Device Operation API

## Overview

The Device Operation APIs (`/device/*`) are the core of NetPulse. They:

- **Auto-detect action** – infer query vs. config from request fields
- **Unified interface** – works with every implemented driver and device type
- **Simple to use** – one entry point reduces API complexity
- **Essentials built-in** – device actions, connection tests, bulk execution

## Endpoints

### POST /device/exec

Unified device operation endpoint. The action is inferred from the payload.

- **Query** – when the request contains `command`
- **Configuration** – when the request contains `config`
- **Queue choice** – queue strategy is auto-selected by driver (can be overridden)

**Query example**
```bash
curl -X POST "http://localhost:9000/device/exec" \
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

**Config example**
```bash
curl -X POST "http://localhost:9000/device/exec" \
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

Run the same action against multiple devices.

```bash
curl -X POST "http://localhost:9000/device/bulk" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "devices": [
      { "host": "192.168.1.1", "username": "admin", "password": "admin123" },
      { "host": "192.168.1.2", "username": "admin", "password": "admin123" }
    ],
    "connection_args": {
      "device_type": "cisco_ios",
      "timeout": 30
    },
    "command": "show version"
  }'
```

### POST /device/test

Connection test endpoint to validate reachability and authentication. Works with Netmiko, NAPALM, PyEAPI, Paramiko, etc.

```bash
curl -X POST "http://localhost:9000/device/test" \
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

Response example:
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

### Scenario 1: Simple show (most common)

Query device version:
```python
import requests

resp = requests.post(
    "http://localhost:9000/device/exec",
    headers={"X-API-KEY": "your_key", "Content-Type": "application/json"},
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

job_id = resp.json()["data"]["id"]
print(f"Job ID: {job_id}")
```

Minimal payload: connection parameters + `command`.

### Scenario 2: Push config and save

```python
requests.post(
    "http://localhost:9000/device/exec",
    headers={"X-API-KEY": "your_key", "Content-Type": "application/json"},
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
            "save": true,              # save config
            "exit_config_mode": true   # exit config mode
        }
    }
)
```

### Scenario 3: Slow device tuning

```python
requests.post(
    "http://localhost:9000/device/exec",
    headers={"X-API-KEY": "your_key", "Content-Type": "application/json"},
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin123",
            "timeout": 60
        },
        "command": "show running-config",
        "driver_args": {
            "read_timeout": 120,
            "delay_factor": 3
        },
        "ttl": 600
    }
)
```

Increase timeouts for sluggish devices.

## Parameters

### connection_args (required)

Basic connection settings for all drivers.

Required:
| Field | Type | Description | Example |
| --- | --- | --- | --- |
| device_type | string | Device type | `cisco_ios`, `juniper_junos`, `arista_eos` |
| host | string | Device IP | `192.168.1.1` |
| username | string | Login username | `admin` |
| password | string | Login password | `password123` |

Optional:
| Field | Type | Default | When to use |
| --- | --- | --- | --- |
| port | integer | 22 | Non-standard SSH port |
| timeout | integer | 30 | Connection timeout (s); raise for slow networks |
| secret | string | - | Enable/privileged password |
| enable_mode | boolean | true | Enter enable mode for config ops |

> Drivers may accept additional fields. See each driver doc.

### driver_args (optional)

Driver-specific tuning. Defaults work for most cases.

When to set:
- Slow devices: raise `read_timeout`, `delay_factor`
- Config push: use `save`, `exit_config_mode`
- Special needs: see driver docs

Examples:

**Netmiko (SSH)**
```json
{
  "read_timeout": 60,
  "delay_factor": 2,
  "save": true,
  "exit_config_mode": true
}
```

**NAPALM**
```json
{
  "optional_args": {
    "secret": "enable_password"
  }
}
```

**PyEAPI**
```json
{
  "transport": "https",
  "port": 443,
  "verify": false
}
```

See driver docs for full options: [Netmiko](../drivers/netmiko.md), [NAPALM](../drivers/napalm.md), [PyEAPI](../drivers/pyeapi.md), [Paramiko](../drivers/paramiko.md).

### options (global)

Global execution options at the root of the request body.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| queue_strategy | string | auto | `pinned` (SSH long-lived) or `fifo` (stateless HTTP). Netmiko/NAPALM default `pinned`; PyEAPI default `fifo`. |
| ttl | integer | 300 (bulk 600) | Job timeout in seconds. |
| parsing | object | null | Output parsing config (TextFSM, TTP, etc.). |
| rendering | object | null | Template rendering config (Jinja2, etc.). |
| webhook | object | null | Webhook callback config. |

Queue guidance:
- **pinned** – for SSH/Telnet long connections (Netmiko, NAPALM); enables reuse and better performance.
- **fifo** – for stateless HTTP/HTTPS (PyEAPI); new connection per job.

## Response models

### SubmitJobResponse
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

- `succeeded`: list of submitted jobs (`JobInResponse`)
- `failed`: list of hosts that failed to submit

### ConnectionTestResponse
Same structure as the example under `/device/test`.

## Bulk operations

Run the same request for multiple devices—useful for fleet ops.

### Bulk show
```python
import requests

resp = requests.post(
    "http://localhost:9000/device/bulk",
    headers={"X-API-KEY": "your_key", "Content-Type": "application/json"},
    json={
        "driver": "netmiko",
        "devices": [
            {"host": "192.168.1.1", "username": "admin", "password": "admin123"},
            {"host": "192.168.1.2", "username": "admin", "password": "admin123"},
            {"host": "192.168.1.3", "username": "admin", "password": "admin123"}
        ],
        "connection_args": {"device_type": "cisco_ios", "timeout": 30},
        "command": "show interfaces status"
    }
)

data = resp.json()["data"]
print(f"Success: {len(data['succeeded']) if data['succeeded'] else 0}")
print(f"Failed: {len(data['failed']) if data['failed'] else 0}")
```

### Mixed-vendor bulk
```python
requests.post(
    "http://localhost:9000/device/bulk",
    headers={"X-API-KEY": "your_key", "Content-Type": "application/json"},
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

### Bulk config push
```python
requests.post(
    "http://localhost:9000/device/bulk",
    headers={"X-API-KEY": "your_key", "Content-Type": "application/json"},
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
            "exit_config_mode": true,
            "enter_config_mode": true,
            "cmd_verify": true
        },
        "queue_strategy": "pinned",
        "ttl": 600
    }
)
```

### Bulk response shape
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "succeeded": [
      { "id": "job_123456", "status": "queued", "queue": "pinned_192.168.1.1" }
    ],
    "failed": ["192.168.1.3"]
  }
}
```

- `succeeded`: job objects with IDs and status
- `failed`: host list; inspect job status for root cause

### Bulk best practices

1. Group devices (by vendor/site); batch size 10–50
2. Add retry logic and detailed error logging
3. Use pinned queues for better concurrency on SSH drivers
4. Monitor progress and alert on high failure rates

## Connection testing

### Supported drivers

#### Netmiko (SSH)
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

Full example with tuning:
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

#### NAPALM (multi-vendor)
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

Cisco IOS variant:
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

#### PyEAPI (Arista)
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

#### Paramiko (Linux servers)
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

Key-based auth:
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

### Connection parameters reference

**Netmiko**
| Field | Type | Default | Description |
| --- | --- | --- | --- |
| device_type | string | - | Device type (cisco_ios, cisco_nxos, juniper_junos, arista_eos) |
| host | string | - | Device IP |
| username | string | - | Username |
| password | string | - | Password |
| secret | string | - | Enable password |
| port | integer | 22 | SSH port |
| timeout | integer | 20 | Connect timeout |
| keepalive | integer | 60 | Keepalive |
| global_delay_factor | float | 1 | Delay factor |
| fast_cli | boolean | false | Fast CLI |
| verbose | boolean | false | Verbose output |

**NAPALM**
| Field | Type | Default | Description |
| --- | --- | --- | --- |
| device_type | string | - | ios, iosxr, junos, eos, nxos |
| hostname | string | - | Device IP |
| username | string | - | Username |
| password | string | - | Password |
| timeout | integer | 60 | Connect timeout |
| optional_args | object | {} | Optional args |

**PyEAPI**
| Field | Type | Default | Description |
| --- | --- | --- | --- |
| host | string | - | Device IP |
| username | string | - | Username |
| password | string | - | Password |
| transport | string | https | http/https |
| port | integer | 443 | Port |
| timeout | integer | 30 | Connect timeout |

### Common errors

**Connection timeout**
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

**Authentication failed**
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

> Connection tests are synchronous and return immediately; no job polling needed.

## Best practices

> See [API Best Practices](./api-best-practices.md) for a full guide.

- Driver choice: Netmiko (SSH), NAPALM (multi-vendor), PyEAPI (Arista), Paramiko (Linux)
- Queue strategy: usually leave auto; driver chooses
- Error handling: retries + detailed logging
- Job tracking: query `/job` or use webhooks

## Notes

1. All API calls require an API key (query, header, or cookie).
2. Device operations are async—poll job status for results (connection tests are sync).
3. Verify connection parameters (host/user/password).
4. Tune timeouts for slow networks/devices.
5. Queue strategy is auto-selected; manual override rarely needed.
6. Bulk: keep batch size around 10–50 to avoid overload.

---

## Related docs

- [API Overview](./api-overview.md)
- [Driver Selection](../drivers/index.md)
- [API Best Practices](./api-best-practices.md)
