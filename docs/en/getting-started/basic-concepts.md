# Basic Concepts

NetPulse is a distributed API controller for network device management. Understanding three core concepts will help you use the system effectively.

```
Client → API Request → Controller → Task Queue → Worker → Network Device
                       ↓              ↓             ↓
                  Driver Selection  Queue Strategy  Connection Reuse
```

## 1. Drivers

Drivers determine how NetPulse connects to devices. Choose based on your target device:

| Driver | Protocol | Best For |
|--------|----------|----------|
| **Netmiko** | SSH/Telnet | Most network devices (Cisco, Juniper, HP, etc.) |
| **NAPALM** | SSH/API | Configuration merge/rollback across vendors |
| **PyEAPI** | HTTP/HTTPS | Arista EOS devices |
| **Paramiko** | SSH | Linux servers (file transfer, sudo, proxy) |

```
Linux server?     → Paramiko
Arista device?    → PyEAPI
Need config rollback? → NAPALM
Everything else   → Netmiko (recommended)
```

See [Driver Selection](../drivers/index.md) for detailed comparisons and parameters.

## 2. Queue Strategies

NetPulse uses two queue strategies, automatically selected by driver:

| Strategy | Connection | Default For | Best For |
|----------|-----------|-------------|----------|
| **Pinned** | Persistent (reused) | Netmiko, NAPALM | Frequent ops on same device |
| **FIFO** | New each time | PyEAPI, Paramiko | Stateless or long-running tasks |

- **Pinned** workers bind 1:1 to a device, reusing SSH sessions to avoid reconnection overhead
- **FIFO** workers process tasks in order with a fresh connection each time

In most cases, let the system choose automatically by omitting `queue_strategy`.

## 3. Jobs

All device operations (`/device/exec`, `/device/bulk`) are **asynchronous**:

1. Submit request → get back a job ID immediately
2. Poll `/job?id=xxx` to get the result
3. Only `/device/test` is synchronous

**Job lifecycle:**

| Status | Description |
|--------|-------------|
| `queued` | Waiting for a worker |
| `started` | Executing on device |
| `finished` | Done — result available |
| `failed` | Error — check result for details |

Job results are stored in Redis with a configurable TTL (default 300s).

## System Components

| Component | Role |
|-----------|------|
| **Controller** | FastAPI server on port 9000. Receives requests, authenticates, dispatches to queues |
| **Node Worker** | Daemon that dynamically creates Pinned Workers for devices |
| **FIFO Worker** | Processes FIFO queue tasks with fresh connections |
| **Pinned Worker** | Binds to a single device, maintains persistent SSH session |
| **Redis** | Task queue, job results, state synchronization |

## Next Steps

- [Quick Start](quick-start.md) — Deploy and try it out
- [Deployment Guide](deployment-guide.md) — Production deployment options
- [API Overview](../api/api-overview.md) — Full endpoint reference
