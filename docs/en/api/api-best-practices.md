# API Best Practices

Guidelines to run NetPulse APIs safely and efficiently.

## Auth & security
- Store API keys in env vars; never hardcode.
- Rotate keys regularly; scope access narrowly.
- Use HTTPS in production.

```bash
export NETPULSE_API_KEY="your-api-key"
curl -H "X-API-KEY: $NETPULSE_API_KEY" http://localhost:9000/health
```

Standard headers:
```bash
curl -X POST \
  -H "X-API-KEY: $NETPULSE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"key": "value"}' \
  http://localhost:9000/api/endpoint
```

## Connection & queues

### Queue strategy
- **fifo** – stateless, good default for HTTP-style drivers.
- **pinned** – device-bound worker, reuses SSH/Telnet sessions; best for frequent ops on the same device.

```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "device_type": "cisco_ios"
  },
  "queue_strategy": "pinned",
  "ttl": 300
}
```

### Timeout tuning (slow devices)
```json
{
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "device_type": "cisco_ios",
    "timeout": 30
  },
  "driver_args": {
    "read_timeout": 60,
    "delay_factor": 2
  }
}
```

## Bulk operations

- Group devices by vendor/site; batch size 10–50.
- Add retries with exponential backoff.
- Track failures separately for later remediation.

```python
def execute_with_retry(devices, command, max_retries=3):
    results, failed = [], []
    for dev in devices:
        for attempt in range(max_retries):
            try:
                results.append(run_command(dev, command))
                break
            except Exception as exc:
                if attempt == max_retries - 1:
                    failed.append({"device": dev, "error": str(exc)})
```

## Templates

Jinja2 example:
```jinja2
{% for intf in interfaces %}
interface {{ intf.name }}
 description {{ intf.description }}
 ip address {{ intf.ip }} {{ intf.mask }}
 no shutdown
{% endfor %}
```

Validate variables before rendering:
```python
def validate(vars_):
    required = ["interfaces", "hostname"]
    missing = [k for k in required if k not in vars_]
    if missing:
        raise ValueError(f"Missing: {missing}")
```

## Error handling

- Poll `/job` or use webhooks; treat `code=-1` as a business failure even if HTTP 200.
- Log request payloads minus secrets for reproducibility.
- For connection errors, retry with higher `timeout`/`delay_factor`; for auth errors, fail fast.

## Performance tips

- Prefer `/device/exec` unified endpoint.
- Let the platform choose `queue_strategy` unless you need to force behavior.
- Use pinned queues for repetitive SSH operations to reuse sessions.
- Keep TTL reasonable (e.g., 300–600s) to free worker resources.
