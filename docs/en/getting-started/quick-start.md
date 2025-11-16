# NetPulse Quick Start

!!! info "NetPulse Architecture Overview"
    NetPulse is a server-based network automation controller. Unlike standalone tools like Netmiko, it needs to be deployed on a server to provide RESTful API services, supporting multi-user concurrent access and distributed task processing.

This guide will help you quickly experience the basic features of NetPulse without needing to understand technical details in depth.

## Quick Experience Goals

Through this guide you will: start the NetPulse service, execute your first API call, connect and operate network devices, understand batch operation features

## Deployment Environment Preparation

!!! info "Server Deployment Description"
    NetPulse is a program that needs to be deployed on a server. You need to prepare a server to run the NetPulse service. This server needs to be able to connect to the network devices you want to manage.
    
    **Server Requirements:**
    - The server needs to be able to access target network devices over the network (SSH/HTTP/HTTPS)
    - It is recommended to use a dedicated server or virtual machine to ensure network connectivity and security
    - Software and hardware requirements are as follows (using Docker deployment)

## One-Click Startup

!!! tip "System Requirements"
    - Docker 20.10+ and Docker Compose 2.0+
    - At least 2GB available memory
    - Port 9000 is not occupied

### 1. Get Code
```bash
git clone https://github.com/scitix/netpulse.git
cd netpulse
```

### 2. One-Click Deployment

!!! tip "Recommended Method"
    This is the simplest and fastest deployment method, suitable for development, testing, and production environments.
    
    **Prerequisites:** Ensure your machine has Docker installed. The required images will be automatically downloaded on first deployment, please keep your network connection active.

```bash
bash ./scripts/docker_auto_deploy.sh
```

**Expected Output:**
```bash
Redis TLS certificates generated in redis/tls.
Note: The permissions of the private key are set to 644 to allow the Docker container to read the key. Please evaluate the security implications of this setting in your environment.
Clearing system environment variables...
Loading environment variables from .env file...
Verifying environment variables...
Environment variables loaded correctly:
  API Key: np_90fbd8685671a2c0b...
  Redis Password: ElkycJeV0d...
Stopping existing services...
Starting services...
[+] Running 6/6
 ✔ Network netpulse-network          Created                                                                                                                                                                                             0.0s
 ✔ Container netpulse-redis-1        Healthy                                                                                                                                                                                             5.7s
 ✔ Container netpulse-fifo-worker-1  Started                                                                                                                                                                                             5.9s
 ✔ Container netpulse-controller-1   Started                                                                                                                                                                                             5.9s
 ✔ Container netpulse-node-worker-2  Started                                                                                                                                                                                             6.1s
 ✔ Container netpulse-node-worker-1  Started                                                                                                                                                                                             5.8s
Waiting for services to start...
Verifying environment variables in container...
Environment variables are correctly set in container
Verifying deployment...
Services are running!

Deployment successful!
====================
API Endpoint: http://localhost:9000
API Key: np_90fbd8685671a2c0b34aa107...

Test your deployment:
curl -H "X-API-KEY: np_90fbd8685671a2c0b34aa107..." http://localhost:9000/health

View logs: docker compose logs -f
Stop services: docker compose down
```
**Important:** Please record your API Key (e.g., `np_90fbd8685671a2c0b34aa107...`), as all subsequent API calls will require this key. To view the complete key, you can find it in the `.env` file in the project root directory.

### 3. Verify Service

!!! success "Deployment Successful"
    If you see the above output, the service has been successfully started!

```bash
# Check service status
docker compose ps

# Test API connection
curl -H "X-API-KEY: np_90fbd8685671a2c0b34aa107..." http://localhost:9000/health

# If you see the following message, the service deployment is successful
{"code":200,"message":"success","data":"ok"}
```

## First API Call

### API Authentication

NetPulse uses Header authentication. All API requests need to carry the API Key in the Header:

```bash
# Method 1: Use API Key directly (obtained from .env file or deployment output)
curl -H "X-API-KEY: np_90fbd8685671a2c0b34aa107..." \
     http://localhost:9000/health

# Method 2: Use environment variable (recommended)
source .env
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/health
```

### Test Device Connection

!!! note "Device Connection Test"
    Before connecting to a real device, please ensure the device is network-reachable and the account credentials are correct.
    
    **Note:** Please replace the IP address, username, and password in the example with your actual device information.

**Method 1: Direct username/password**

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
  http://localhost:9000/device/test-connection
```

**Method 2: Use Vault credentials (Recommended)**

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "credential_ref": "sites/hq/admin",
      "device_type": "cisco_ios"
    }
  }' \
  http://localhost:9000/device/test-connection
```

!!! tip "Using Vault Credentials"
    Use `credential_ref` to reference credentials stored in Vault, avoiding directly passing passwords in requests for better security. See [Vault Credential Management API](../api/credential-api.md) for details.

**Connection Parameter Description:**

| Parameter | Type | Required | Description |
|:----------|:-----|:--------:|:------------|
| `host` | string | ✅ | Device IP address |
| `username` | string | ⚠️ | SSH username (or use `credential_ref`) |
| `password` | string | ⚠️ | SSH password (or use `credential_ref`) |
| `credential_ref` | string | ⚠️ | Vault credential reference (recommended) |
| `device_type` | string | ✅ | Device type (e.g., cisco_ios, hp_comware, juniper_junos, etc.) |

**Expected Response:**
```json
{
  "code": 200,
  "message": "Connection test completed",
  "data": {
    "success": true,
    "connection_time": 2.64,
    "error_message": null,
    "device_info": {
      "prompt": "Router#",
      "device_type": "cisco_ios",
      "host": "192.168.1.1"
    },
    "timestamp": "2025-09-21T02:23:13.469090+08:00"
  }
}
```

### Execute Network Command

!!! info "Command Execution"
    Supports standard commands for all network devices, such as `show version` (Cisco), `display version` (H3C/Huawei), etc. Command syntax may differ between vendors.
    
    **Note:** This example uses a Cisco IOS device. For other vendor devices, please refer to the corresponding device type and command syntax.

```bash
# Execute command (using Vault credentials)
response=$(curl -s -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "credential_ref": "sites/hq/admin",
      "device_type": "cisco_ios"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute)

# View response
echo "$response" | jq '.'
```

**Expected Response (immediate return):**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "job_12345",
    "status": "queued",
    "queue": "pinned_192.168.1.1",
    "created_at": "2025-09-21T02:25:13.469090+08:00"
  }
}
```

!!! warning "Important: Device Operations are Asynchronous"
    All device operations (`/device/execute`, `/device/bulk`) are asynchronous:
    1. API immediately returns task ID and status (usually `queued`)
    2. Need to query execution results through `/job?id=xxx` interface
    3. Only `/device/test-connection` is synchronous and returns results immediately
    
    **Query Task Results:**
    ```bash
    # Extract task ID
    task_id=$(echo "$response" | jq -r '.data.id')
    
    # Wait a few seconds then query task results
    sleep 3
    curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
         http://localhost:9000/job?id=$task_id | jq '.'
    ```
    
    **Response Example After Task Completion:**
    ```json
    {
      "code": 200,
      "message": "success",
      "data": [{
        "id": "job_12345",
        "status": "finished",
        "result": {
          "type": "success",
          "retval": {
            "show version": "Cisco IOS Software, Version 15.2..."
          }
        },
        "duration": 1.45
      }]
    }
    ```

### Configuration Push

In addition to executing query commands, NetPulse also supports configuration push functionality:

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
      "ip address 192.168.1.1 255.255.255.0",
      "no shutdown"
    ]
  }' \
  http://localhost:9000/device/execute
```

## Batch Operation Experience

### Batch Device Configuration

!!! warning "Batch Operation Notes"
    Before batch operations, please ensure all devices are network-reachable. It is recommended to test on a small number of devices first.

```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "username": "admin",
      "password": "your_password"
    },
    "devices": [
      {
        "host": "192.168.1.1",
        "device_type": "cisco_ios",
        "username": "admin",
        "password": "password1"
      },
      {
        "host": "192.168.1.2",
        "device_type": "cisco_ios",
        "username": "admin",
        "password": "password2"
      }
    ],
    "command": "show ip interface brief"
  }' \
  http://localhost:9000/device/bulk
```

**Expected Response (immediate return):**
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "succeeded": [
      {
        "id": "job_abc123",
        "status": "queued",
        "queue": "pinned_192.168.1.1"
      },
      {
        "id": "job_def456",
        "status": "queued",
        "queue": "pinned_192.168.1.2"
      }
    ],
    "failed": []
  }
}
```

!!! note "Batch Operation Description"
    Batch operations return a task list, with each device corresponding to one task. You need to query the execution results for each device through the task ID.

## Task Management

NetPulse supports asynchronous task processing. You can query execution status and results through task IDs.

### Query Task Status

```bash
# Query all tasks
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/job

# Query by status (finished, running, failed, etc.)
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/job?status=finished

# Query specific task
curl -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
     http://localhost:9000/job?id=your_job_id
```

### Cancel Task

```bash
# Cancel specific task
curl -X DELETE \
  -H "X-API-KEY: $NETPULSE_SERVER__API_KEY" \
  http://localhost:9000/job?id=your_job_id
```

## Best Practices

### Error Handling

In actual use, it is recommended to check API response status and handle errors:

```bash
# Execute command and check response
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
  http://localhost:9000/device/execute)

# Parse response
if echo "$response" | jq -e '.code == 200' > /dev/null; then
    echo "Command executed successfully"
    echo "$response" | jq -r '.data.output'
else
    echo "Command execution failed"
    echo "$response" | jq -r '.message'
fi
```

## Next Steps

### Further Learning
- [Basic Concepts](basic-concepts.md) - Understand system architecture and core concepts
- [Deployment Guide](deployment-guide.md) - Learn production environment deployment
- [Postman Guide](postman-guide.md) - Use Postman to quickly experience APIs
- [API Overview](../api/api-overview.md) - Deep dive into all API interfaces

## Encountering Issues?

!!! failure "Common Issues"
    - **Service startup failed** → See [Deployment Guide](deployment-guide.md)
    - **API call error** → Check if API Key is correct, see [API Overview](../api/api-overview.md)
    - **Device connection issues** → Confirm device is network-reachable, check if username and password are correct
    - **Task execution failed** → Use task management API to query detailed error information

---