# Webhook Configuration

This guide describes how to configure and use NetPulse webhooks for event notifications.

## Overview

Webhooks allow NetPulse to send real-time notifications to external systems when specific events occur, such as job completion, device connection status changes, or system alerts.

## Configuration

### Webhook Endpoint Setup

```json
{
  "url": "https://your-webhook-endpoint.com/api/notifications",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-webhook-token"
  },
  "events": ["job.completed", "device.connected", "device.disconnected"],
  "retry_count": 3,
  "timeout": 30
}
```

### Supported Events

- `job.completed` — Job execution completed
- `job.failed` — Job execution failed
- `device.connected` — Device connection established
- `device.disconnected` — Device connection lost
- `system.alert` — System alert/error

## Webhook Payload

### Job Completion Event

```json
{
  "event": "job.completed",
  "timestamp": "2024-01-15T08:30:15+08:00",
  "data": {
    "job_id": "job_1234567890",
    "hostname": "192.168.1.1",
    "command": "show version",
    "status": "completed",
    "execution_time": 0.8,
    "output": "Cisco IOS XE Software..."
  }
}
```

### Device Connection Event

```json
{
  "event": "device.connected",
  "timestamp": "2024-01-15T08:30:15+08:00",
  "data": {
    "hostname": "192.168.1.1",
    "device_type": "cisco_ios",
    "connection_time": 0.5
  }
}
```

## Best Practices

- Use HTTPS endpoints for security
- Implement idempotent webhook handlers
- Set appropriate timeout and retry values
- Monitor webhook delivery status

---