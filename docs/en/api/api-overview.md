# API Overview

## Introduction

NetPulse provides a unified API interface to manage various network devices. This document introduces all API interfaces supported by NetPulse and their basic usage.

## Basic Information

### API Endpoint
- **Base URL**: `http://localhost:9000`
- **API Version**: v0.1
- **Authentication**: API Key (X-API-KEY Header)

### Authentication
All API requests require API Key authentication, supporting the following three methods:

1. **Header method** (recommended):
   ```
   X-API-KEY: your-api-key-here
   ```

2. **Query parameter method**:
   ```
   ?X-API-KEY=your-api-key-here
   ```

3. **Cookie method**:
   ```
   X-API-KEY=your-api-key-here
   ```

### Response Format
All API responses use a unified JSON format:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    // Specific data
  }
}
```

**Response Code Description**:
- `code: 200` - Request successful
- `code: -1` - Request failed (error details in `message` and `data`)

## Complete API Endpoint List

NetPulse provides the following API endpoints, all of which require API Key authentication.

> **⭐Recommended**: Prioritize using the `/device/execute` unified interface, which automatically identifies operation types and is simpler to use.

| HTTP Method | Endpoint Path | Description | Detailed Documentation |
|------------|--------------|-------------|----------------------|
| **Device Operations** | | | |
| `POST` | `/device/execute` | Device operations (query/configuration) ⭐Recommended | [Device Operation API](./device-api.md) |
| `POST` | `/device/bulk` | Batch device operations | [Device Operation API](./device-api.md) |
| `POST` | `/device/test-connection` | Device connection test | [Device Operation API](./device-api.md) |
| **Template Operations** | | | |
| `POST` | `/template/render` | Template rendering (auto-detect engine) | [Template Operation API](./template-api.md) |
| `POST` | `/template/render/{name}` | Render using specified engine | [Template Operation API](./template-api.md) |
| `POST` | `/template/parse` | Template parsing (auto-detect parser) | [Template Operation API](./template-api.md) |
| `POST` | `/template/parse/{name}` | Parse using specified parser | [Template Operation API](./template-api.md) |
| **Job Management** | | | |
| `GET` | `/job` | Query job status and results | [Job Management API](./job-api.md) |
| `DELETE` | `/job` | Cancel job | [Job Management API](./job-api.md) |
| `GET` | `/worker` | Query Worker status | [Job Management API](./job-api.md) |
| `DELETE` | `/worker` | Delete Worker | [Job Management API](./job-api.md) |
| `GET` | `/health` | System health check | [Job Management API](./job-api.md) |

## API Categories

### 1. Device Operation API
Device Operation API provides device query, configuration, and connection testing functions, supporting all driver types.

**Main Endpoints**:
- `POST /device/execute` - Unified device operations (auto-detect query/configuration)
- `POST /device/bulk` - Batch device operations
- `POST /device/test-connection` - Device connection test

**Supported Drivers**:
- Netmiko (SSH) - Universal SSH connection
- NAPALM (multi-vendor) - Standardized interface
- PyEAPI (Arista-specific) - HTTP/HTTPS API
- Paramiko (SSH) - Linux server management

For detailed information, see: [Device Operation API](./device-api.md)

### 2. Template Operation API
Provides configuration template rendering and command output parsing functions.

**Main Endpoints**:
- `POST /template/render` - Template rendering
- `POST /template/parse` - Output parsing

**Supported Engines**:
- Jinja2 - Configuration template rendering
- TextFSM - Command output parsing
- TTP - Configuration parsing

For detailed information, see: [Template Operation API](./template-api.md)

### 3. Job Management API
Provides job status query, job cancellation, and Worker management functions.

**Main Endpoints**:
- `GET /job` - Query job status
- `DELETE /job` - Cancel job
- `GET /worker` - Query Worker status
- `DELETE /worker` - Delete Worker
- `GET /health` - System health check

For detailed information, see: [Job Management API](./job-api.md)

## Supported Driver Types

### Netmiko (SSH)
- **Device Types**: cisco_ios, cisco_nxos, juniper_junos, arista_eos, huawei, hp_comware, and more. See the [Netmiko Platform Support](https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md) for the complete list of supported device types
- **Connection Method**: SSH
- **Features**: Strong universality, supports most mainstream network devices

### NAPALM (Multi-vendor)
- **Device Types**: ios, iosxr, junos, eos, nxos
- **Connection Method**: SSH/API
- **Features**: Standardized interface, cross-vendor compatibility

### PyEAPI (Arista-specific)
- **Device Types**: Arista EOS
- **Connection Method**: HTTP/HTTPS API
- **Features**: Native API support, excellent performance

### Paramiko (Linux Servers)
- **Device Types**: Linux servers (Ubuntu, CentOS, Debian, etc.)
- **Connection Method**: SSH
- **Features**: Native SSH, supports file transfer, proxy connections, sudo, etc.

## Queue Strategies

NetPulse supports two queue strategies, and the system will automatically select the appropriate strategy based on driver type:

### Device-bound Queue (pinned)
- **Applicable Drivers**: Netmiko, NAPALM (SSH/Telnet long connections)
- **Features**: Dedicated Worker per device, connection reuse
- **Advantages**: Reduces connection establishment overhead, improves performance
- **Use Cases**: Frequent operations on the same device, need to maintain connection state

### FIFO Queue (fifo)
- **Applicable Drivers**: PyEAPI (HTTP/HTTPS stateless connections), Paramiko (Linux servers)
- **Features**: First-in-first-out, new connection each time
- **Advantages**: Simple and efficient, suitable for stateless operations
- **Use Cases**: HTTP API calls, long-running tasks, no need to maintain connection state

> **Tip**: If `queue_strategy` is not specified, the system will automatically select based on driver type (Netmiko/NAPALM → `pinned`, PyEAPI/Paramiko → `fifo`)

## Core Parameters Quick Reference

### Required Parameters

**connection_args (Connection Parameters)** - Required for all operations:
```json
{
  "device_type": "cisco_ios",  // Device type
  "host": "192.168.1.1",      // Device IP
  "username": "admin",         // Username
  "password": "password"        // Password
}
```

**Operation Parameters** - Choose one:
- `command`: Query operation (e.g., `"show version"`)
- `config`: Configuration operation (e.g., `["interface Gi0/1", "description Test"]`)

### Optional Parameters

**driver_args (Driver Parameters)** - Varies by driver type, see driver-specific documentation:
```json
{
  "read_timeout": 60,      // Netmiko-specific
  "delay_factor": 2        // Netmiko-specific
}
```

**options (Global Options)** - Controls task behavior:
```json
{
  "queue_strategy": "pinned",  // Queue strategy (auto-selected, usually no need to specify)
  "ttl": 300,                  // Timeout (seconds)
  "parsing": {...},            // Output parsing (optional)
  "webhook": {...}             // Callback notification (optional)
}
```

> **Quick Start**: For most scenarios, just provide `connection_args` and `command`/`config`, other parameters use default values.

## Error Handling

### Error Response Format
All error responses use a unified format:
```json
{
  "code": -1,
  "message": "Error description",
  "data": "Specific error information or error detail object"
}
```

**HTTP Status Codes**:
- `200` - Request successful
- `201` - Resource created successfully (job submitted)
- `400` - Request parameter error
- `403` - Authentication failed (API Key invalid or missing)
- `404` - Resource not found
- `422` - Parameter validation failed
- `500` - Internal server error

> **Note**: Even if the HTTP status code is 200, if business logic fails, the `code` field in the response will still be `-1`.

## Quick Start Recommendations

### Parameter Selection Guide

1. **Required Parameters**: `connection_args` + `command`/`config` is enough to get started
2. **Queue Strategy**: Usually no need to specify, system will automatically select based on driver
3. **Driver Parameters**: Use default values for most scenarios, adjust for special needs
4. **Timeout Settings**: Default values are sufficient, increase for slow devices or batch operations

### Common Scenarios

- **Simple Query**: Just `connection_args` + `command`
- **Configuration Push**: Add `driver_args.save: true` to save configuration
- **Slow Devices**: Increase `timeout`, `read_timeout`, `delay_factor`
- **Batch Operations**: Use `/device/bulk` interface, system automatically optimizes

> **Detailed Guide**: See [API Best Practices](./api-best-practices.md) for more optimization tips

## Quick Start

### 1. Check System Health
```bash
curl -H "X-API-KEY: your-key" http://localhost:9000/health
```

### 2. Test Device Connection
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-key" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password"
    }
  }' \
  http://localhost:9000/device/test-connection
```

### 3. Execute Simple Query
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-key" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute
```

## Next Steps

- [Device Operation API](./device-api.md) - Core device operation interfaces
- [Driver Selection](../drivers/index.md) - Choose the right driver
- [API Best Practices](./api-best-practices.md) - Usage recommendations and optimization tips
