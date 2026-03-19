# Quick Start

This guide gets you from zero to your first API call in minutes.

## Deploy

!!! tip "Requirements"
    - Docker 20.10+ and Docker Compose 2.0+
    - At least 2GB available memory
    - Port 9000 available

```bash
git clone https://github.com/scitix/netpulse.git
cd netpulse
bash ./scripts/docker_auto_deploy.sh
```

On success, the script outputs your API endpoint and API Key:
```
Deployment successful!
====================
API Endpoint: http://localhost:9000
API Key: np_90fbd8685671a2c0b34aa107...
```

**Save your API Key** — all API calls require it. You can also find it in the `.env` file.

```bash
# Verify the service is running
source .env
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/health
# Expected: {"code":200,"message":"success","data":"ok"}
```

## Test Device Connection

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios"
    }
  }' \
  http://localhost:9000/device/test
```

!!! note
    Replace IP, credentials, and `device_type` with your actual device info. `/device/test` is the **only synchronous** endpoint — it returns results immediately.

## Execute a Command

```bash
# Submit command (async — returns job ID)
response=$(curl -s -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/exec)

# Extract job ID and poll for result
task_id=$(echo "$response" | jq -r '.data.id')
sleep 3
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/job?id=$task_id | jq '.'
```

!!! warning "All device operations are async"
    `/device/exec` and `/device/bulk` return a job ID immediately. Poll `/job?id=xxx` for results.

## Push Configuration

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios"
    },
    "config": [
      "interface GigabitEthernet0/1",
      "description Management Interface",
      "no shutdown"
    ]
  }' \
  http://localhost:9000/device/exec
```

## Batch Operations

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "devices": [
      {"host": "192.168.1.1", "device_type": "cisco_ios", "username": "admin", "password": "pass1"},
      {"host": "192.168.1.2", "device_type": "cisco_ios", "username": "admin", "password": "pass2"}
    ],
    "command": "show ip interface brief"
  }' \
  http://localhost:9000/device/bulk
```

Returns a job ID per device. Query each via `/job?id=xxx`.

## Manage Jobs

```bash
# List all jobs
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/job

# Filter by status
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/job?status=finished

# Cancel a job
curl -X DELETE -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" http://localhost:9000/job?id=your_job_id
```

## Next Steps

- [Basic Concepts](basic-concepts.md) — Understand drivers, queues, and jobs
- [Deployment Guide](deployment-guide.md) — Production deployment options
- [API Overview](../api/api-overview.md) — Full endpoint reference
- [Postman Guide](postman-guide.md) — Test APIs with a GUI

---
