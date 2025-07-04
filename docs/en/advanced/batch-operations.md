# Batch Operations

This guide describes how to use NetPulse for large-scale device management and batch operations.

## Scenarios

- Simultaneously execute commands on hundreds or thousands of devices
- Batch push configurations
- Collect device information in bulk

## API Endpoints

- `POST /device/bulk` — Batch device operations (recommended)
- `POST /pull/batch` — Legacy batch command execution
- `POST /push/batch` — Legacy batch configuration push

## Request Example

### Batch Command Execution

```json
{
  "driver": "netmiko",
  "devices": [
    {"host": "192.168.1.1", "username": "admin", "password": "admin123"},
    {"host": "192.168.1.2", "username": "admin", "password": "admin123"}
  ],
  "connection_args": {
    "device_type": "cisco_ios",
    "timeout": 30
  },
  "command": "show version",
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

### Batch Configuration Push

```json
{
  "driver": "netmiko",
  "devices": [
    {"host": "192.168.1.1", "username": "admin", "password": "admin123"},
    {"host": "192.168.1.2", "username": "admin", "password": "admin123"}
  ],
  "connection_args": {
    "device_type": "cisco_ios",
    "timeout": 30
  },
  "config": "interface GigabitEthernet0/1\n description Batch Config",
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

## Best Practices

- Use batch APIs for large-scale operations to reduce connection overhead and improve efficiency.
- Set reasonable timeout and queue_strategy parameters for stability.
- Monitor job status and results via the `/job` API.

## Result Example

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
    }
  ],
  "summary": {
    "total": 2,
    "successful": 2,
    "failed": 0
  }
}
```

## FAQ

- **Q: How to handle failed devices in batch operations?**
  - A: Check the `results` field for each device's status and error message.
- **Q: Can I use different commands/configs for each device?**
  - A: Use multiple API calls or customize the payload accordingly.

---

For more details, see the API documentation. 