# Error Codes Reference

This document provides a comprehensive reference for all NetPulse error codes and their meanings.

## Error Code Format

NetPulse uses a structured error code format:
```
NP-[CATEGORY]-[CODE]
```

- **NP**: NetPulse prefix
- **CATEGORY**: Error category (2-3 letters)
- **CODE**: Specific error code (3-4 digits)

## Error Categories

### Authentication Errors (AUTH)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-AUTH-001 | Invalid API key | API key is missing or incorrect | Verify API key in configuration |
| NP-AUTH-002 | API key expired | API key has expired | Generate new API key |
| NP-AUTH-003 | Insufficient permissions | User lacks required permissions | Check user permissions |
| NP-AUTH-004 | Rate limit exceeded | Too many requests | Implement rate limiting |

### Connection Errors (CONN)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-CONN-001 | Connection timeout | Device not responding | Check device connectivity |
| NP-CONN-002 | Authentication failed | Invalid credentials | Verify device credentials |
| NP-CONN-003 | Connection refused | Device refused connection | Check device SSH/Telnet settings |
| NP-CONN-004 | Host unreachable | Network connectivity issue | Check network connectivity |
| NP-CONN-005 | SSH key authentication failed | SSH key not accepted | Verify SSH key configuration |
| NP-CONN-006 | Connection pool exhausted | Too many concurrent connections | Increase connection pool size |

### Command Execution Errors (CMD)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-CMD-001 | Command timeout | Command execution timed out | Increase command timeout |
| NP-CMD-002 | Command failed | Command returned error | Check command syntax |
| NP-CMD-003 | Invalid command | Command not recognized | Verify command for device type |
| NP-CMD-004 | Permission denied | Insufficient privileges | Check user permissions on device |
| NP-CMD-005 | Command not supported | Command not supported by driver | Use alternative command |

### Template Errors (TMPL)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-TMPL-001 | Template not found | Template file missing | Check template path |
| NP-TMPL-002 | Template syntax error | Invalid template syntax | Fix template syntax |
| NP-TMPL-003 | Template rendering failed | Error during rendering | Check template variables |
| NP-TMPL-004 | Template variable missing | Required variable not provided | Provide missing variables |
| NP-TMPL-005 | Template parsing failed | TextFSM/TTP parsing error | Check template format |

### Job Errors (JOB)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-JOB-001 | Job not found | Job ID does not exist | Verify job ID |
| NP-JOB-002 | Job already cancelled | Job was previously cancelled | Check job status |
| NP-JOB-003 | Job execution failed | Job failed during execution | Check job logs |
| NP-JOB-004 | Job timeout | Job exceeded timeout limit | Increase job timeout |
| NP-JOB-005 | Job queue full | Job queue is at capacity | Wait or increase queue size |

### Configuration Errors (CFG)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-CFG-001 | Configuration file not found | Config file missing | Create configuration file |
| NP-CFG-002 | Invalid configuration | Configuration syntax error | Fix configuration syntax |
| NP-CFG-003 | Missing required parameter | Required config parameter missing | Add missing parameter |
| NP-CFG-004 | Invalid parameter value | Parameter value is invalid | Correct parameter value |
| NP-CFG-005 | Configuration validation failed | Configuration failed validation | Check configuration format |

### Driver Errors (DRV)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-DRV-001 | Driver not found | Device driver not available | Install or configure driver |
| NP-DRV-002 | Driver initialization failed | Driver failed to initialize | Check driver configuration |
| NP-DRV-003 | Driver not supported | Device type not supported | Use compatible driver |
| NP-DRV-004 | Driver version mismatch | Driver version incompatible | Update driver version |
| NP-DRV-005 | Driver dependency missing | Required dependency not installed | Install missing dependency |

### System Errors (SYS)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-SYS-001 | Internal server error | Unexpected system error | Check system logs |
| NP-SYS-002 | Database connection failed | Database not accessible | Check database connectivity |
| NP-SYS-003 | Redis connection failed | Redis not accessible | Check Redis connectivity |
| NP-SYS-004 | Memory allocation failed | Insufficient memory | Increase system memory |
| NP-SYS-005 | File system error | File system operation failed | Check file system permissions |

### Validation Errors (VAL)

| Code | Description | Cause | Solution |
|------|-------------|--------|----------|
| NP-VAL-001 | Invalid request format | Request format is invalid | Check request format |
| NP-VAL-002 | Missing required field | Required field not provided | Provide missing field |
| NP-VAL-003 | Invalid field value | Field value is invalid | Correct field value |
| NP-VAL-004 | Field value out of range | Value exceeds allowed range | Use valid range |
| NP-VAL-005 | Invalid data type | Data type is incorrect | Use correct data type |

## Error Response Format

### Standard Error Response
```json
{
  "error": {
    "code": "NP-CONN-001",
    "message": "Connection timeout",
    "details": "Device 192.168.1.1 did not respond within 30 seconds",
    "timestamp": "2024-01-01T12:00:00Z",
    "job_id": "job_123456",
    "trace_id": "trace_789012"
  }
}
```

### Batch Error Response
```json
{
  "errors": [
    {
      "device": "192.168.1.1",
      "error": {
        "code": "NP-CONN-001",
        "message": "Connection timeout",
        "details": "Device did not respond within 30 seconds"
      }
    },
    {
      "device": "192.168.1.2",
      "error": {
        "code": "NP-AUTH-002",
        "message": "Authentication failed",
        "details": "Invalid username or password"
      }
    }
  ]
}
```

## Error Handling Best Practices

### Client-side Error Handling
```python
import requests
from netpulse_sdk import NetPulseClient

client = NetPulseClient(api_key="your-api-key")

try:
    result = client.execute_command("192.168.1.1", "show version")
except NetPulseError as e:
    if e.code == "NP-CONN-001":
        print("Connection timeout - device may be unreachable")
    elif e.code == "NP-AUTH-002":
        print("Authentication failed - check credentials")
    else:
        print(f"Error: {e.message}")
```

### Retry Logic
```python
import time
from netpulse_sdk import NetPulseClient, NetPulseError

def execute_with_retry(client, device, command, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.execute_command(device, command)
        except NetPulseError as e:
            if e.code in ["NP-CONN-001", "NP-CONN-004"]:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            raise e
```

### Error Logging
```python
import logging
from netpulse_sdk import NetPulseError

logger = logging.getLogger(__name__)

try:
    result = client.execute_command("192.168.1.1", "show version")
except NetPulseError as e:
    logger.error(
        f"Command execution failed: {e.code} - {e.message}",
        extra={
            "error_code": e.code,
            "device": "192.168.1.1",
            "command": "show version",
            "trace_id": e.trace_id
        }
    )
```

## Common Error Scenarios

### Scenario 1: Device Connection Issues
```python
# Common connection errors and solutions
error_solutions = {
    "NP-CONN-001": "Check device connectivity and increase timeout",
    "NP-CONN-002": "Verify device credentials",
    "NP-CONN-003": "Check SSH/Telnet service on device",
    "NP-CONN-004": "Verify network connectivity to device"
}
```

### Scenario 2: Authentication Problems
```python
# Authentication troubleshooting
def handle_auth_error(error_code):
    if error_code == "NP-AUTH-001":
        return "Check API key configuration"
    elif error_code == "NP-AUTH-002":
        return "Generate new API key"
    elif error_code == "NP-AUTH-003":
        return "Contact administrator for permissions"
    else:
        return "Unknown authentication error"
```

### Scenario 3: Command Execution Failures
```python
# Command execution troubleshooting
def handle_command_error(error_code, device_type):
    if error_code == "NP-CMD-001":
        return "Increase command timeout"
    elif error_code == "NP-CMD-003":
        return f"Check command syntax for {device_type}"
    elif error_code == "NP-CMD-004":
        return "Check user privileges on device"
    else:
        return "Unknown command error"
```

## Error Monitoring

### Prometheus Metrics
```python
# Error rate metrics
netpulse_errors_total = Counter(
    'netpulse_errors_total',
    'Total number of errors',
    ['error_code', 'category']
)

# Error rate by device
netpulse_device_errors_total = Counter(
    'netpulse_device_errors_total',
    'Total number of device errors',
    ['device', 'error_code']
)
```

### Alerting Rules
```yaml
# Prometheus alerting rules
groups:
  - name: netpulse_errors
    rules:
      - alert: HighErrorRate
        expr: rate(netpulse_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          
      - alert: ConnectionFailures
        expr: rate(netpulse_errors_total{category="CONN"}[5m]) > 0.05
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High connection failure rate"
```

## Troubleshooting Guide

### Step 1: Identify Error Category
1. Check error code prefix
2. Refer to category-specific documentation
3. Review error message and details

### Step 2: Check Common Causes
1. Verify configuration
2. Check network connectivity
3. Validate credentials
4. Review system resources

### Step 3: Apply Solutions
1. Follow error-specific solutions
2. Implement retry logic if appropriate
3. Monitor error patterns
4. Contact support if needed

For more information, see:
- [Log Analysis](../troubleshooting/log-analysis.md)
- [Performance Tuning](../advanced/performance-tuning.md) 