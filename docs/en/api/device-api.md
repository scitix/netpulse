# Device Operation API

The Device Operation APIs (`/device/*`) are the core of NetPulse. They auto-detect whether a request is a query or config operation, and work with every driver through a unified interface.

## Endpoints

### POST /device/exec

Unified device operation endpoint. Action is inferred from the payload:

- **Query** — request contains `command`
- **Config** — request contains `config`

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

**Response:**
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

All device operations are async. Poll `/job?id=<id>` for results.

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

Per-device fields in `devices[]` override the shared `connection_args`. Useful for mixed-vendor fleets where `device_type` differs per device.

**Response:**
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

`failed` lists hosts that couldn't be submitted (bad params, capacity). `succeeded` jobs still need polling.

### POST /device/test

Synchronous connection test — validates reachability and authentication. Returns immediately (no job polling needed).

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

**Response:**
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

## Parameters

### connection_args (required)

| Field | Required | Description |
|-------|----------|-------------|
| `host` | Yes | Device IP |
| `username` | Yes | Login username |
| `password` | Yes | Login password |
| `device_type` | Driver-specific | Required for Netmiko/NAPALM; not used by Paramiko |
| `port` | No | SSH port (default 22) |
| `timeout` | No | Connection timeout in seconds (default 30) |
| `secret` | No | Enable/privileged password |

> Driver-specific fields (`hostname` for NAPALM, `transport`/`port` for PyEAPI, `pkey` for Paramiko) are documented in each driver's page.

### driver_args (optional)

Driver-specific tuning. Common uses:

| Scenario | Fields |
|----------|--------|
| Slow devices | `read_timeout`, `delay_factor` (Netmiko) |
| Config push | `save`, `exit_config_mode` (Netmiko) |
| NAPALM safe changes | `revert_in`, `message` |
| PyEAPI JSON output | `encoding: "json"` |
| Paramiko sudo | `sudo: true`, `sudo_password` |

See driver docs for full options: [Netmiko](../drivers/netmiko.md) · [NAPALM](../drivers/napalm.md) · [PyEAPI](../drivers/pyeapi.md) · [Paramiko](../drivers/paramiko.md)

### Global options

| Field | Default | Description |
|-------|---------|-------------|
| `queue_strategy` | auto | `pinned` (persistent SSH) or `fifo` (stateless). Drivers pick appropriate default. |
| `ttl` | 300 (bulk: 600) | Job timeout in seconds |
| `parsing` | null | Output parsing config (TextFSM, TTP, etc.) |
| `rendering` | null | Template rendering config (Jinja2, etc.) |
| `webhook` | null | Webhook callback config |

Queue guidance:
- **pinned** — for SSH/Telnet drivers (Netmiko, NAPALM); enables persistent connection reuse
- **fifo** — for HTTP drivers (PyEAPI); fresh connection per job
