# Troubleshooting

This document provides troubleshooting methods and solutions for common issues, for reference.

## View Logs

### Docker Environment

```bash
# View all service logs
docker compose logs

# View specific service logs
docker compose logs controller
docker compose logs fifo-worker
docker compose logs node-worker

# Real-time log tracking
docker compose logs -f

# View recent logs
docker compose logs --tail=100 controller
```

### Log Format

```
[2025-07-20 01:10:38 +0800] [9] [INFO] [netpulse.api|routes.py:45] - API request received
```

Format description:
- `2025-07-20 01:10:38 +0800`: Timestamp and timezone
- `[9]`: Process ID
- `INFO`: Log level
- `[netpulse.api|routes.py:45]`: Module name|file name:line number
- `API request received`: Log message

### Log Levels

- **INFO**: Normal operation information
- **WARNING**: Warning information
- **ERROR**: Error information
- **DEBUG**: Debug information (detailed information)

### Quick Troubleshooting Commands

```bash
# View error logs
docker compose logs | grep ERROR

# View warning logs
docker compose logs | grep WARNING

# View startup related logs
docker compose logs | grep -E "(Starting|Started|ERROR|CRITICAL)"

# View device connection logs
docker compose logs node-worker | grep -E "(connect|connection|timeout|failed)"
```

## Common Issues

### Deployment Related Issues

#### Q1: Docker Container Startup Failure

**Problem Description**: Container fails to start or exits immediately.

**Troubleshooting Steps**:
```bash
# 1. Check Docker service
sudo systemctl status docker

# 2. Check port occupancy
sudo netstat -tlnp | grep :9000

# 3. View detailed logs
docker compose logs

# 4. Rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

**Common Causes**:
- Port is occupied
- Insufficient memory
- Configuration file error
- Docker service not started

#### Q2: API Key Issues

**Problem Description**: Unable to obtain or use API key.

**Troubleshooting Steps**:
```bash
# 1. View environment variables
cat .env | grep NETPULSE_SERVER__API_KEY

# 2. Find from logs
docker compose logs controller | grep "API Key"

# 3. Regenerate
docker compose down
rm .env
bash ./scripts/setup_env.sh generate
docker compose up -d
```

#### Q3: Redis Connection Failure

**Problem Description**: Worker cannot connect to Redis.

**Troubleshooting Steps**:
```bash
# 1. Check Redis container status
docker compose ps redis

# 2. View Redis logs
docker compose logs redis

# 3. Restart Redis
docker compose restart redis

# 4. Test connection
docker compose exec controller ping redis
```

### Connection Related Issues

#### Q4: Device Connection Timeout

**Problem Description**: Timeout when connecting to network devices.

**Possible Causes**:
- High network latency
- Heavy device load
- Firewall blocking
- Incorrect device type configuration

**Can Try**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "device_type": "cisco_ios",
    "timeout": 60,
    "read_timeout": 120
  }
}
```

#### Q5: SSH Authentication Failure

**Problem Description**: SSH connection authentication error.

**Troubleshooting Steps**:
```bash
# 1. Manually test connection
ssh admin@192.168.1.1

# 2. Check device type
# Ensure device_type is correct: cisco_ios, cisco_nxos, juniper_junos, arista_eos, etc.

# 3. Check if enable password is needed
{
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password",
    "device_type": "cisco_ios"
  }
}
```

#### Q6: Device Type Not Supported

**Supported Device Types**:
- **Cisco**: cisco_ios, cisco_nxos, cisco_ios_xr
- **Juniper**: juniper_junos
- **Arista**: arista_eos
- **Huawei**: huawei
- **HP**: hp_comware

### API Related Issues

#### Q7: API Request Returns 403 Error

**Problem Description**: API request returns authentication failure (HTTP 403).

**Troubleshooting Steps**:
```bash
# 1. Check API key
curl -H "X-API-KEY: YOUR_API_KEY" \
     http://localhost:9000/health

# 2. Verify key format
# Ensure key is correct, no extra spaces or newlines

# 3. Regenerate key
docker compose down
bash ./scripts/setup_env.sh generate
docker compose up -d
```

#### Q8: Task Execution Failure

**Problem Description**: Submitted task execution fails.

**Troubleshooting Steps**:
```bash
# 1. View task status
curl -H "X-API-KEY: YOUR_API_KEY" \
     http://localhost:9000/job?id=JOB_ID

# 2. View Worker logs
docker compose logs worker

# 3. Test device connection
curl -X POST \
  -H "X-API-KEY: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password",
      "device_type": "cisco_ios"
    }
  }' \
  http://localhost:9000/device/test
```

### Performance Related Issues

#### Q9: Slow Task Execution

**Possible Causes**:
- Insufficient Worker count
- Network latency
- Slow device response

**Can Try**:
- Appropriately increase `pinned_per_node`
- Use Pinned queue strategy
- Increase task timeout

#### Q10: High Memory Usage

**Can Try**:
```bash
# 1. Check memory usage
docker stats

# 2. Limit container memory (in docker-compose.yml)
services:
  controller:
    deploy:
      resources:
        limits:
          memory: 1G

# 3. Restart Worker
docker compose restart worker
```

### Configuration Related Issues

#### Q11: Environment Variable Configuration Error

**Troubleshooting Steps**:
```bash
# 1. Check environment variables
cat .env

# 2. Regenerate configuration
bash ./scripts/setup_env.sh generate

# 3. Verify configuration
docker compose config
```

#### Q12: Template Rendering Failure

**Troubleshooting Steps**:
```python
# Check template syntax
from jinja2 import Template

template = Template("""
interface {{ interface.name }}
 description {{ interface.description }}
""")

# Verify variables
variables = {
    'interface': {
        'name': 'GigabitEthernet0/1',
        'description': 'LAN Interface'
    }
}

result = template.render(**variables)
print(result)
```

## Problem Diagnosis Flow

Recommend troubleshooting in the following order:

1. **View Logs**: First view logs of related services
2. **Check Configuration**: Verify configuration files and environment variables
3. **Test Connection**: Test network and device connections
4. **Check Resources**: Check system resource usage
5. **Refer to Documentation**: View related documentation

## Get Help

If the above methods cannot solve the problem:

1. **View Detailed Logs**: `docker compose logs`
2. **Collect Error Information**: Record complete error messages and context
3. **Provide Environment Information**: Operating system, Docker version, configuration information, etc.
4. **Submit Issue**: Submit detailed problem report on GitHub
