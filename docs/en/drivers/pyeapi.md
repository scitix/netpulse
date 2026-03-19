# PyEAPI Driver

PyEAPI connects to Arista EOS devices via HTTP/HTTPS (not SSH), providing JSON-native structured output.

> This page covers PyEAPI-specific parameters. For endpoint shapes and response format, see [Device Operation API](../api/device-api.md).

## At a Glance

- **Protocol**: HTTP/HTTPS API
- **Supported vendors**: Arista EOS only
- **Recommended queue**: `fifo` (HTTP stateless)
- **Unique features**: JSON-native output, `driver_args` pass-through to pyeapi library

## Query Operations

```json
{
  "driver": "pyeapi",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "transport": "https",
    "port": 443
  },
  "command": "show version",
  "driver_args": {
    "encoding": "json"
  },
  "queue_strategy": "fifo"
}
```

Multiple commands in one request:
```json
{
  "command": ["show version", "show interfaces status", "show vlan brief", "show ip bgp summary"],
  "driver_args": {"encoding": "json", "timestamps": true}
}
```

## Configuration Operations

```json
{
  "driver": "pyeapi",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "transport": "https",
    "port": 443
  },
  "config": [
    "vlan 100",
    "name DATA_VLAN",
    "interface range Ethernet1-10",
    "switchport mode access",
    "switchport access vlan 100"
  ],
  "driver_args": {
    "autoComplete": true,
    "expandAliases": true
  },
  "queue_strategy": "fifo"
}
```

With Jinja2 template rendering:
```json
{
  "config": {"local_asn": 65001, "router_id": "1.1.1.1"},
  "driver_args": {"autoComplete": true},
  "rendering": {
    "name": "jinja2",
    "template": "router bgp {{ local_asn }}\n router-id {{ router_id }}"
  }
}
```

## Parameters

### connection_args

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `host` | Yes | | Device IP |
| `username` | Yes | | |
| `password` | Yes | | |
| `transport` | No | `https` | `http` or `https` |
| `port` | No | 443 | API port (HTTP default: 80) |
| `timeout` | No | 60 | Connection timeout in seconds |
| `key_file` | No | | SSL key file path |
| `cert_file` | No | | SSL certificate file path |
| `ca_file` | No | | CA certificate file path |

### driver_args

All `driver_args` are passed directly to pyeapi's `enable()` (query) or `config()` (config) methods. Common parameters:

| Parameter | Operations | Description |
|-----------|-----------|-------------|
| `encoding` | Query | Output encoding (default: `"text"`) |
| `timestamps` | Query | Include timestamps in output |
| `expand` | Query | Expand abbreviated output |
| `autoComplete` | Config | Enable EOS auto-complete |
| `expandAliases` | Config | Expand command aliases |

For the full parameter list, see the [pyeapi documentation](https://github.com/arista-eosplus/pyeapi).

## Best Practices

- Use `encoding: "json"` — PyEAPI's main advantage is structured JSON output
- Batch multiple `show` commands in one request to minimize round trips
- HTTP is stateless — always use `fifo` queue
