# RESTful API Guide

NetPulse provides RESTful APIs for network device operations. All operations are asynchronous, with task status and results managed through Redis Queue (RQ).

## API Overview

NetPulse offers three main categories of APIs:

- Device Operation APIs (command execution and configuration application)
- Template Operation APIs (template rendering and parsing)
- Task Management APIs (task and worker management)

Additionally, NetPulse provides Batch API forms for large-scale device operations, as discussed below.

## Authentication

All API requests require authentication via API Key. Supported methods:
- **Query parameter**: `?X-API-KEY=your_api_key`
- **Header**: `X-API-KEY: your_api_key`
- **Cookie**: `X-API-KEY=your_api_key`

## Unified Device Operation API

### POST /device/execute

A unified endpoint for device operations, automatically recognizing operation type (query or configuration).

**Request Example:**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123",
    "port": 22,
    "timeout": 30
  },
  "command": "show version",
  "driver_args": {
    "read_timeout": 30,
    "delay_factor": 2
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300,
    "parsing": {
      "name": "textfsm",
      "template": "file:///templates/show_version.textfsm"
    }
  }
}
```

**Configuration Example:**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123"
  },
  "config": "interface GigabitEthernet0/1\n description Test Interface",
  "driver_args": {
    "save": true,
    "exit_config_mode": true
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

### POST /device/bulk

Batch device operation endpoint, supports executing the same operation on multiple devices.

**Request Example:**
```json
{
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
    "timeout": 30,
    "keepalive": 120
  },
  "command": "show version",
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

### POST /device/test-connection

Test device connection status.

**Request Example:**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123"
  }
}
```

## Legacy API Endpoints

### POST /pull
- Execute commands on a device
- `POST /pull/batch`: Execute commands on multiple devices
- Support for parsing command output using templates

### POST /push
- Push configurations to a device
- `POST /push/batch`: Push configurations to multiple devices
- Support for rendering configurations using templates

## Template Operations

### POST /template/render
Render configurations using templates.

**Request Example:**
```json
{
  "name": "jinja2",
  "template": "interface {{ interface_name }}\n description {{ description }}",
  "context": {
    "interface_name": "GigabitEthernet0/1",
    "description": "Test Interface"
  }
}
```

### POST /template/parse
Parse command outputs using templates.

**Request Example:**
```json
{
  "name": "textfsm",
  "template": "file:///templates/show_version.textfsm",
  "context": "Cisco IOS Software, Version 15.2(4)S7..."
}
```

## Task Management

### GET /job
Query task status and results
- Filter by task ID, queue, status, or node
- Track task execution progress
- Access task results and errors

### DELETE /job
Cancel pending tasks
- Cancel by task ID or queue
- Only affects tasks that have not yet started

### GET /worker
List active worker nodes
- View worker node status
- View queues that plugin worker nodes are listening to

### DELETE /worker
Stop worker nodes
- Stop specific worker nodes
- Tasks in process will gracefully complete

## Batch API

Batch APIs allow you to send a set of commands or configurations in a single request, reducing the overhead of establishing multiple connections.

!!! tip
    If you need to operate on a large number of devices in a short period, it is strongly recommended to use Batch APIs for improved efficiency.

### Design Considerations

```mermaid
flowchart LR
A[1000 devices] -->|Batch API| B[A Controller]
B -->|Scheduling algorithm, Redis Pipelines| C[Workers]
```

1. **Connection Pressure**
    - 1 batch request vs 1000 individual requests
    - Redis Pipeline reduces communication pressure between Redis and components

2. **Scheduling Efficiency**
    - With Batch API, requests are sent to a single controller for processing
    - Processing these requests on the same controller allows for more efficient scheduling algorithms
    - Since controllers are stateless, scheduling conflicts may occur between multiple controllers; using Batch API can avoid such race conditions

3. **User Experience**
    - More concise request bodies reduce the complexity and redundancy of API calls

## Workflow Examples

The following are examples of using NetPulse API for configuration deployment and verification.

**1. Configuration Rendering and Pushing**

Push configurations to devices through the `POST /push` interface. The following example demonstrates using a Jinja2 template to render configurations, connecting to a Cisco device via SSH, and modifying the description of an interface on the device.

```http
POST /push HTTP/1.1
Host: example.com
X-API-KEY: YOUR_API_KEY_HERE
```

```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password123"
  },
  "config": {
    "interface": "GigabitEthernet0/1",
    "description": "Connected to core switch"
  },
  "rendering": {
    "name": "jinja2",
    "template": "file:///templates/interface.j2"
  }
}
```

**2. Pulling Results and Verification**

Execute commands on devices and parse the output through the `POST /pull` interface. The following example demonstrates executing the `show ip interface brief` command on a Cisco device via SSH and parsing the output using a TextFSM template.

```http
POST /pull HTTP/1.1
Host: example.com
X-API-KEY: YOUR_API_KEY_HERE
```

```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password123"
  },
  "command": "show ip interface brief",
  "parsing": {
    "name": "textfsm",
    "template": "file:///templates/show_ip_int_brief.textfsm"
  }
}
```

## API Reference

For detailed API specifications and parameters, please refer to the Postman documentation. 