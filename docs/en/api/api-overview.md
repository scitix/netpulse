# API Overview

## Intro

NetPulse exposes a unified API set to manage network devices. This page lists all available endpoints and how to call them.

## Basics

### API endpoint
- Base URL: `http://localhost:9000`
- API version: v0.2
- Auth: API Key via `X-API-KEY`

### Authentication
Every request requires an API key. Supported placements:

1) Header (recommended)  
`X-API-KEY: your-api-key-here`

2) Query param  
`?X-API-KEY=your-api-key-here`

3) Cookie  
`X-API-KEY=your-api-key-here`

### Response format
```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

- `code: 200` – success  
- `code: -1` – business failure (details in `message`/`data`)

## Full endpoint list

> **Tip**: prefer the unified `/device/exec` endpoint; it auto-detects query vs. config.

| Method | Path | Description | Doc |
| --- | --- | --- | --- |
| **Device** ||||
| POST | `/device/exec` | Device ops (query/config) | [Device Operation API](./device-api.md) |
| POST | `/device/bulk` | Bulk device ops | [Device Operation API](./device-api.md) |
| POST | `/device/test` | Connection test | [Device Operation API](./device-api.md) |
| **Template** ||||
| POST | `/template/render` | Render (engine auto-detect) | [Template API](./template-api.md) |
| POST | `/template/render/{name}` | Render with specified engine | [Template API](./template-api.md) |
| POST | `/template/parse` | Parse output (auto-detect) | [Template API](./template-api.md) |
| POST | `/template/parse/{name}` | Parse with specified parser | [Template API](./template-api.md) |
| **Jobs** ||||
| GET | `/job` | Get job status/result | [Job API](./job-api.md) |
| DELETE | `/job` | Cancel job | [Job API](./job-api.md) |
| GET | `/worker` | Worker status | [Job API](./job-api.md) |
| DELETE | `/worker` | Delete worker | [Job API](./job-api.md) |
| GET | `/health` | Health check | [Job API](./job-api.md) |

## API categories

### 1) Device APIs
- `POST /device/exec` – unified query/config
- `POST /device/bulk` – bulk operations
- `POST /device/test` – connection test

Supported drivers: Netmiko (SSH), NAPALM (multi-vendor), PyEAPI (Arista), Paramiko (Linux).
See [Device Operation API](./device-api.md).

### 2) Template APIs
- `POST /template/render`
- `POST /template/parse`

Engines/parsers: Jinja2, TextFSM, TTP. See [Template API](./template-api.md).

### 3) Job APIs
- `GET /job`, `DELETE /job`
- `GET /worker`, `DELETE /worker`
- `GET /health`

See [Job API](./job-api.md).

## Supported drivers

### Netmiko (SSH)
- Device types: cisco_ios, cisco_nxos, juniper_junos, arista_eos, huawei, hp_comware, etc. Full list: [Netmiko platforms](https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md)
- Protocol: SSH
- Strength: broad vendor coverage

### NAPALM (multi-vendor)
- Device types: ios, iosxr, junos, eos, nxos, etc.
- Protocol: SSH/API
- Strength: standardized interface

### PyEAPI (Arista)
- Device type: Arista EOS
- Protocol: HTTP/HTTPS API
- Strength: native API performance

### Paramiko (Linux)
- Device type: Linux servers
- Protocol: SSH
- Strength: native SSH with file transfer, proxy, sudo, etc.

## Queue strategies

NetPulse picks a queue strategy based on driver:

### Pinned (device-bound)
- For Netmiko, NAPALM (SSH/Telnet long-lived)
- Dedicated worker per device; reuses connections
- Best when repeatedly touching the same device

### FIFO
- For PyEAPI (HTTP/HTTPS stateless), Paramiko
- New connection per job
- Good for stateless or long-running tasks

If you omit `queue_strategy`, defaults are applied (Netmiko/NAPALM → pinned; PyEAPI/Paramiko → fifo).

## Parameter quick reference

### Required

`connection_args` (for all ops):
```json
{
  "device_type": "cisco_ios",
  "host": "192.168.1.1",
  "username": "admin",
  "password": "password"
}
```

Operation (choose one):
- `command`: e.g., `"show version"`
- `config`: e.g., `["interface Gi0/1", "description Test"]`

### Optional

`driver_args` (driver-specific; see driver docs):
```json
{
  "read_timeout": 60,
  "delay_factor": 2
}
```

`options` (global):
```json
{
  "queue_strategy": "pinned",
  "ttl": 300,
  "parsing": {},
  "webhook": {}
}
```

> For most cases, `connection_args` + `command`/`config` is enough; defaults handle the rest.

## Error handling

Error response shape:
```json
{
  "code": -1,
  "message": "error description",
  "data": "details or object"
}
```

HTTP status codes:
- 200 – success
- 201 – created (job submitted)
- 400 – bad request
- 403 – auth failed (API key missing/invalid)
- 404 – not found
- 422 – validation failed
- 500 – server error

Note: even with HTTP 200, `code` can be `-1` for business failures.

## Quick start tips

Parameter guidance:
1. Start with `connection_args` + `command`/`config`.
2. Queue strategy: usually omit; driver picks.
3. Driver args: defaults are fine unless you need tuning.
4. Timeouts: raise only for slow devices or large batches.

Common scenarios:
- Simple show: `connection_args` + `command`
- Config push: add `driver_args.save: true`
- Slow device: raise `timeout`, `read_timeout`, `delay_factor`
- Bulk: use `/device/bulk`

See [API Best Practices](./api-best-practices.md) for more.

## Quick start

1) Health check
```bash
curl -H "X-API-KEY: your-key" http://localhost:9000/health
```

2) Connection test
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-key" \
  -d '{"driver":"netmiko","connection_args":{"device_type":"cisco_ios","host":"192.168.1.1","username":"admin","password":"password"}}' \
  http://localhost:9000/device/test
```

3) Run a show
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-key" \
  -d '{"driver":"netmiko","connection_args":{"device_type":"cisco_ios","host":"192.168.1.1","username":"admin","password":"password"},"command":"show version"}' \
  http://localhost:9000/device/exec
```

## Next steps

- [Device Operation API](./device-api.md)
- [Driver Selection](../drivers/index.md)
- [API Best Practices](./api-best-practices.md)
