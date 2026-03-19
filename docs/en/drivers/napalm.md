# NAPALM Driver

NAPALM provides cross-vendor standardized device management with support for configuration merge, replace, and rollback.

> This page covers NAPALM-specific parameters. For endpoint shapes and response format, see [Device Operation API](../api/device-api.md).

## At a Glance

- **Protocol**: SSH/HTTP/HTTPS
- **Supported vendors**: Cisco IOS/IOS-XR/NX-OS, Juniper JunOS, Arista EOS
- **Recommended queue**: `fifo`
- **Unique features**: `get_*` collection methods, config merge/replace/rollback, `revert_in` auto-rollback

!!! warning "Key difference: `hostname` not `host`"
    NAPALM uses `hostname` for the device IP, not `host`.

## Query Operations

Use NAPALM's `get_*` methods as the `command` value:

```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "get_facts",
  "queue_strategy": "fifo"
}
```

Multiple methods in one request:
```json
{
  "command": ["get_facts", "get_interfaces", "get_interfaces_ip", "get_arp_table"]
}
```

**Available methods:**

| Method | Returns |
|--------|---------|
| `get_facts` | Hostname, vendor, model, OS version |
| `get_interfaces` | Interface status and config |
| `get_interfaces_ip` | Interface IP addresses |
| `get_arp_table` | ARP entries |
| `get_mac_address_table` | MAC address entries |
| `get_route_to` | Routing info (needs `driver_args.destination`) |
| `get_bgp_neighbors` | BGP neighbor info |
| `get_bgp_neighbors_detail` | Detailed BGP info |
| `get_ospf_neighbors` | OSPF neighbor info |
| `get_lldp_neighbors` | LLDP neighbor info |
| `get_environment` | Temperature, power, fans |
| `get_config` | Device running/startup config |
| `compare_config` | Show pending config diff |
| `rollback` | Roll back to previous config |

## Configuration Operations

NAPALM configurations are merge mode by default (incremental). Use `driver_args.revert_in` for safe changes:

```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "optional_args": {"secret": "enable_password"}
  },
  "config": [
    "interface GigabitEthernet0/1",
    "description Uplink",
    "no shutdown"
  ],
  "driver_args": {
    "message": "Add uplink description",
    "revert_in": 60
  },
  "queue_strategy": "fifo"
}
```

Configuration rollback:
```json
{
  "driver": "napalm",
  "connection_args": {"device_type": "ios", "hostname": "192.168.1.1", "username": "admin", "password": "password"},
  "command": "rollback",
  "queue_strategy": "fifo"
}
```

## Parameters

### connection_args

| Parameter | Required | Description |
|-----------|----------|-------------|
| `device_type` | Yes | `ios`, `iosxr`, `junos`, `eos`, `nxos` |
| `hostname` | Yes | Device IP (note: `hostname` not `host`) |
| `username` | Yes | |
| `password` | Yes | |
| `timeout` | No | Connection timeout in seconds |
| `optional_args` | No | Object: `port`, `secret` (enable password), `transport` |

### driver_args

| Parameter | Operations | Description |
|-----------|-----------|-------------|
| `encoding` | Query | Output encoding (`"text"` default) |
| `message` | Config | Commit message |
| `revert_in` | Config | Auto-rollback timeout in seconds (commit confirmation window) |
| `destination` | `get_route_to` | Target IP for route lookup |

## Best Practices

- Use `fifo` queue — NAPALM connections are not persistent
- Always set `revert_in` on production config changes
- Use `compare_config` before committing to verify diff
- For multi-vendor queries, batch `get_*` methods in a single request
