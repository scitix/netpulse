# Quick Start

This guide will help you get started with NetPulse in 5 minutes and experience its powerful network device management capabilities.

## Learning Objectives

Through this guide, you will learn:
- Deploy NetPulse services
- Configure network device connections
- Execute your first API call
- View device status information

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 22.04+ recommended)
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **CPU**: At least 8 cores
- **Memory**: At least 16GB

**When the number of device connections increases or concurrent tasks are executed, it is recommended to increase system resources to ensure stability.**

### Network Devices
- Network devices supporting SSH (routers, switches, etc.)
- Device IP address and login credentials

## Step 1: Get the Code

```bash
# Clone the project repository
git clone https://github.com/netpulse/netpulse.git
cd netpulse

# Check project structure
ls -la
```

## Step 2: Environment Configuration

```bash
# Run environment check script
bash ./scripts/setup_env.sh

# Generate environment configuration file
bash ./scripts/setup_env.sh generate
```

This will create a `.env` file containing all necessary configuration parameters.

## Step 3: Start Services

```bash
# Start all services using Docker Compose
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

After services start, you will see the following containers:
- `netpulse-controller`: API controller (port 9000)
- `netpulse-node-worker`: Node worker processes (2 instances)
- `netpulse-fifo-worker`: FIFO worker process
- `netpulse-redis`: Redis cache

## Step 4: Get API Key

```bash
# View generated API key
cat .env | grep NETPULSE_SERVER__API_KEY

# Or get from logs
docker compose logs controller | grep "API Key"
```

## Step 5: Test API Connection

```bash
# Test health check endpoint
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/health

# Expected response
{
  "code": 0,
  "message": "success",
  "data": "ok"
}
```

## Step 6: Test Device Connection

### Prepare Device Information
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "your_password",
    "device_type": "cisco_ios",
    "port": 22
  }
}
```

### Test Connection
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin", 
      "password": "your_password",
      "device_type": "cisco_ios",
      "port": 22
    }
  }' \
  http://localhost:9000/device/test-connection
```

## Step 7: Execute First Command

```bash
# Get device information
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios",
      "port": 22
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute
```

## Congratulations!

You have successfully completed the NetPulse quick start! Now you can:

- ✅ Deploy and run NetPulse services
- ✅ Connect to network devices
- ✅ Execute network commands
- ✅ Get device information

## Next Steps

### Deep Learning
- **[First API Call](first-steps.md)** - More API usage examples
- **[API Reference](../guides/api.md)** - Complete API documentation

### Advanced Features
- **[Batch Operations](../advanced/batch-operations.md)** - Manage multiple devices
- **[Template System](../advanced/templates.md)** - Use templates to simplify operations
- **[Long Connection Technology](../architecture/long-connection.md)** - Understand core technology
- **[Performance Tuning](../advanced/performance-tuning.md)** - Optimize system performance

## Having Issues?

If you encounter any problems, please refer to:
- **[Log Analysis](../troubleshooting/log-analysis.md)** - Log interpretation and problem diagnosis
- **[GitHub Issues](https://github.com/netpulse/issues)** - Submit issue feedback

---

<div align="center">

**Ready to start your network automation journey?**

[First API Call →](first-steps.md)

</div> 