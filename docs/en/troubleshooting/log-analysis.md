# Log Analysis Guide

This guide provides comprehensive information on analyzing NetPulse logs for troubleshooting and monitoring.

## Log Structure

### Log Format
NetPulse uses structured logging with the following format:
```
[TIMESTAMP] [LEVEL] [COMPONENT] [MESSAGE] [CONTEXT]
```

Example:
```
2024-01-01 12:00:00,123 INFO  [API] Request received {"method": "POST", "path": "/api/v1/execute", "device": "192.168.1.1"}
2024-01-01 12:00:00,456 DEBUG [WORKER] Connecting to device {"host": "192.168.1.1", "driver": "cisco_ios"}
2024-01-01 12:00:01,789 INFO  [WORKER] Command executed successfully {"device": "192.168.1.1", "command": "show version", "duration": 1.2}
```

### Log Levels
| Level | Description | Use Case |
|-------|-------------|----------|
| DEBUG | Detailed debugging information | Development and troubleshooting |
| INFO | General information messages | Normal operation tracking |
| WARNING | Warning messages | Potential issues |
| ERROR | Error messages | Failures and exceptions |
| CRITICAL | Critical system failures | System-wide issues |

## Log Components

### API Logs
API logs track HTTP requests and responses:
```
2024-01-01 12:00:00,123 INFO  [API] Request received {"method": "POST", "path": "/api/v1/execute", "ip": "10.0.0.1", "user_agent": "curl/7.68.0"}
2024-01-01 12:00:00,456 INFO  [API] Request processed {"status": 200, "duration": 0.5, "job_id": "job_123456"}
2024-01-01 12:00:00,789 ERROR [API] Authentication failed {"ip": "10.0.0.2", "api_key": "invalid_key"}
```

### Worker Logs
Worker logs track job execution:
```
2024-01-01 12:00:01,000 INFO  [WORKER] Job started {"job_id": "job_123456", "device": "192.168.1.1", "command": "show version"}
2024-01-01 12:00:01,200 DEBUG [WORKER] Connecting to device {"host": "192.168.1.1", "port": 22, "driver": "cisco_ios"}
2024-01-01 12:00:02,500 INFO  [WORKER] Command executed {"device": "192.168.1.1", "command": "show version", "duration": 1.3}
2024-01-01 12:00:02,600 INFO  [WORKER] Job completed {"job_id": "job_123456", "status": "success", "total_duration": 1.6}
```

### Connection Logs
Connection logs track device connectivity:
```
2024-01-01 12:00:01,200 DEBUG [CONNECTION] Establishing connection {"host": "192.168.1.1", "port": 22, "timeout": 30}
2024-01-01 12:00:01,800 INFO  [CONNECTION] Connection established {"host": "192.168.1.1", "connection_id": "conn_789"}
2024-01-01 12:00:02,000 DEBUG [CONNECTION] Authenticating {"host": "192.168.1.1", "username": "admin"}
2024-01-01 12:00:02,200 INFO  [CONNECTION] Authentication successful {"host": "192.168.1.1", "method": "password"}
```

### Error Logs
Error logs capture failures and exceptions:
```
2024-01-01 12:00:05,000 ERROR [WORKER] Connection failed {"host": "192.168.1.1", "error": "Connection timeout", "error_code": "NP-CONN-001"}
2024-01-01 12:00:05,100 ERROR [WORKER] Job failed {"job_id": "job_123456", "error": "Device unreachable", "retry_count": 3}
2024-01-01 12:00:05,200 ERROR [API] Internal server error {"path": "/api/v1/execute", "error": "Redis connection failed", "traceback": "..."}
```

## Log Analysis Techniques

### Basic Log Analysis
```bash
# View recent logs
tail -f /var/log/netpulse/netpulse.log

# Search for specific patterns
grep "ERROR" /var/log/netpulse/netpulse.log
grep "192.168.1.1" /var/log/netpulse/netpulse.log
grep "job_123456" /var/log/netpulse/netpulse.log

# Count log entries by level
grep -c "INFO" /var/log/netpulse/netpulse.log
grep -c "ERROR" /var/log/netpulse/netpulse.log
```

### Advanced Log Analysis
```bash
# Analyze error patterns
awk '/ERROR/ {print $5}' /var/log/netpulse/netpulse.log | sort | uniq -c | sort -nr

# Find slow operations
grep "duration" /var/log/netpulse/netpulse.log | awk -F'"duration": ' '{print $2}' | awk -F',' '{print $1}' | sort -n

# Analyze connection failures
grep "Connection failed" /var/log/netpulse/netpulse.log | awk -F'"host": "' '{print $2}' | awk -F'"' '{print $1}' | sort | uniq -c
```

### Log Analysis with jq
For JSON-formatted logs:
```bash
# Extract error messages
cat netpulse.log | jq -r 'select(.level == "ERROR") | .message'

# Count errors by device
cat netpulse.log | jq -r 'select(.level == "ERROR") | .context.device' | sort | uniq -c

# Find slow operations
cat netpulse.log | jq -r 'select(.context.duration > 5) | "\(.timestamp) \(.context.device) \(.context.duration)"'
```

## Common Log Patterns

### Connection Issues
```
# Connection timeout
2024-01-01 12:00:05,000 ERROR [WORKER] Connection failed {"host": "192.168.1.1", "error": "Connection timeout", "error_code": "NP-CONN-001"}

# Authentication failure
2024-01-01 12:00:05,100 ERROR [WORKER] Authentication failed {"host": "192.168.1.1", "error": "Invalid credentials", "error_code": "NP-CONN-002"}

# Host unreachable
2024-01-01 12:00:05,200 ERROR [WORKER] Connection failed {"host": "192.168.1.1", "error": "Host unreachable", "error_code": "NP-CONN-004"}
```

### Performance Issues
```
# Slow command execution
2024-01-01 12:00:10,000 WARNING [WORKER] Slow command execution {"device": "192.168.1.1", "command": "show tech-support", "duration": 45.2}

# High memory usage
2024-01-01 12:00:15,000 WARNING [SYSTEM] High memory usage {"memory_percent": 85.5, "available_mb": 512}

# Connection pool exhaustion
2024-01-01 12:00:20,000 ERROR [WORKER] Connection pool exhausted {"host": "192.168.1.1", "active_connections": 10, "max_connections": 10}
```

### API Issues
```
# Rate limiting
2024-01-01 12:00:25,000 WARNING [API] Rate limit exceeded {"ip": "10.0.0.1", "requests_per_minute": 120, "limit": 100}

# Invalid API key
2024-01-01 12:00:30,000 ERROR [API] Invalid API key {"ip": "10.0.0.2", "api_key": "invalid_key"}

# Request validation failure
2024-01-01 12:00:35,000 ERROR [API] Request validation failed {"path": "/api/v1/execute", "error": "Missing required field: device"}
```

## Log Analysis Tools

### Built-in Tools
```bash
# Log rotation check
logrotate -d /etc/logrotate.d/netpulse

# Disk usage analysis
du -h /var/log/netpulse/

# Log file statistics
wc -l /var/log/netpulse/netpulse.log
```

### Third-party Tools

#### ELK Stack (Elasticsearch, Logstash, Kibana)
```yaml
# Logstash configuration
input {
  file {
    path => "/var/log/netpulse/netpulse.log"
    start_position => "beginning"
  }
}

filter {
  grok {
    match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} \[%{WORD:component}\] %{GREEDYDATA:message}" }
  }
  
  if [message] =~ /^{.*}$/ {
    json {
      source => "message"
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "netpulse-logs-%{+YYYY.MM.dd}"
  }
}
```

#### Grafana Loki
```yaml
# Promtail configuration
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: netpulse
    static_configs:
      - targets:
          - localhost
        labels:
          job: netpulse
          __path__: /var/log/netpulse/netpulse.log
```

## Troubleshooting Scenarios

### Scenario 1: High Error Rate
```bash
# Identify error patterns
grep "ERROR" /var/log/netpulse/netpulse.log | tail -100

# Check error distribution
grep "ERROR" /var/log/netpulse/netpulse.log | awk '{print $5}' | sort | uniq -c | sort -nr

# Find affected devices
grep "ERROR" /var/log/netpulse/netpulse.log | grep -o '"host": "[^"]*"' | sort | uniq -c
```

### Scenario 2: Performance Degradation
```bash
# Find slow operations
grep "duration" /var/log/netpulse/netpulse.log | awk -F'"duration": ' '{print $2}' | awk -F',' '{print $1}' | sort -n | tail -20

# Check memory usage patterns
grep "memory" /var/log/netpulse/netpulse.log | tail -50

# Analyze connection pool usage
grep "connection" /var/log/netpulse/netpulse.log | grep -i "pool\|exhausted" | tail -20
```

### Scenario 3: Connection Issues
```bash
# Check connection failures
grep "Connection failed" /var/log/netpulse/netpulse.log | tail -50

# Analyze authentication issues
grep "Authentication" /var/log/netpulse/netpulse.log | grep -i "failed\|error" | tail -20

# Check timeout patterns
grep "timeout" /var/log/netpulse/netpulse.log | tail -30
```

## Log Monitoring and Alerting

### Prometheus Metrics from Logs
```python
# Log-based metrics
from prometheus_client import Counter, Histogram

# Error counters
error_counter = Counter(
    'netpulse_errors_total',
    'Total number of errors',
    ['error_type', 'component']
)

# Duration histogram
duration_histogram = Histogram(
    'netpulse_operation_duration_seconds',
    'Operation duration in seconds',
    ['operation', 'device']
)

# Connection metrics
connection_counter = Counter(
    'netpulse_connections_total',
    'Total number of connections',
    ['host', 'status']
)
```

### Alerting Rules
```yaml
# Prometheus alerting rules
groups:
  - name: netpulse_logs
    rules:
      - alert: HighErrorRate
        expr: rate(netpulse_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected in NetPulse logs"
          
      - alert: SlowOperations
        expr: histogram_quantile(0.95, rate(netpulse_operation_duration_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow operations detected in NetPulse"
          
      - alert: ConnectionFailures
        expr: rate(netpulse_connections_total{status="failed"}[5m]) > 0.05
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "High connection failure rate"
```

## Log Retention and Cleanup

### Log Rotation Configuration
```bash
# /etc/logrotate.d/netpulse
/var/log/netpulse/netpulse.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 netpulse netpulse
    postrotate
        systemctl reload netpulse
    endscript
}
```

### Automated Cleanup
```bash
#!/bin/bash
# cleanup-logs.sh

LOG_DIR="/var/log/netpulse"
RETENTION_DAYS=30

# Remove old log files
find $LOG_DIR -name "*.log.*" -type f -mtime +$RETENTION_DAYS -delete

# Compress large log files
find $LOG_DIR -name "*.log" -type f -size +100M -exec gzip {} \;

# Clean up empty log files
find $LOG_DIR -name "*.log" -type f -empty -delete

echo "Log cleanup completed"
```

## Best Practices

### Log Analysis Best Practices
1. **Use structured logging** for easier parsing
2. **Include correlation IDs** for request tracing
3. **Implement log aggregation** for centralized analysis
4. **Set up automated alerting** for critical issues
5. **Regular log review** to identify patterns

### Performance Considerations
1. **Use appropriate log levels** to avoid log flooding
2. **Implement log sampling** for high-volume operations
3. **Monitor log file sizes** and implement rotation
4. **Use asynchronous logging** to avoid performance impact

### Security Considerations
1. **Sanitize sensitive data** in logs
2. **Implement log access controls**
3. **Use secure log transmission** for remote logging
4. **Audit log access** and modifications

---

For more troubleshooting information, see:
- [Performance Tuning](../advanced/performance-tuning.md)