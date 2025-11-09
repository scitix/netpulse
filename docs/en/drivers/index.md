# Driver Selection Guide

NetPulse adopts a plugin-based driver architecture, supporting rapid extension of new device drivers. Through a unified API interface, new drivers can be easily integrated to support more device types.

## Quick Comparison

| Driver | Connection Method | Recommended Scenario | Core Advantage |
|--------|------------------|---------------------|----------------|
| **Netmiko** | SSH/Telnet | **Most scenarios (recommended)** | Supports a wide range of device types, long connection reuse improves performance |
| **NAPALM** | SSH/HTTP/HTTPS | Need configuration merge/rollback | Supports configuration merge, replace, rollback |
| **PyEAPI** | HTTP/HTTPS | Arista EOS devices | Native API, excellent performance, JSON structured data |

## Driver Description

NetPulse is based on a plugin-based driver architecture that can quickly extend new device drivers. Currently supports the following drivers:

### Netmiko (Recommended)

**Default choice for most scenarios**. Executes commands via SSH connection, supports Cisco, Juniper, and most network devices. Long connection reuse can improve performance in frequent operation scenarios.

- Supported Devices: Cisco, Juniper, HP and other SSH devices
- Recommended Queue Strategy: Pinned (long connection reuse)
- Use Cases: Query, configuration push and other regular operations

**Key Parameters**:
- `connection_args.device_type` (required)`: Device type, such as `cisco_ios`, `juniper_junos`, etc.
- `connection_args.keepalive` (default 180 seconds)`: SSH connection keepalive time for long connection reuse
- `connection_args.secret`: Privileged mode password (enable password)
- `driver_args.read_timeout` (default 10 seconds)`: Read timeout time
- `driver_args.delay_factor`: Delay factor for slow devices
- `driver_args.strip_prompt` (default true)`: Remove prompt from output
- `driver_args.cmd_verify` (default true)`: Command verification

📖 [View Netmiko Detailed Documentation](./netmiko.md)

### NAPALM

**Use only when advanced configuration management features are needed**. Provides advanced features such as configuration merge, replace, and rollback.

- Supported Devices: Cisco, Juniper and other multi-vendor devices
- Use Cases: Need configuration merge, replace, rollback, version control

**Key Parameters**:
- `connection_args.device_type` (required)`: Device type, such as `ios`, `junos`, `eos`, etc.
- `connection_args.hostname` (required)`: Device IP address (Note: NAPALM uses hostname instead of host)
- `connection_args.optional_args`: Optional parameter object, can include `port`, `secret`, `transport`, etc.
- `driver_args.encoding` (query, default "text")`: Encoding format
- `driver_args.message` (configuration)`: Configuration commit message
- `driver_args.revert_in` (configuration)`: Configuration confirmation time (seconds) for automatic rollback

📖 [View NAPALM Detailed Documentation](./napalm.md)

### PyEAPI

**Recommended choice when managing Arista devices**. Uses Arista native HTTP API with excellent performance.

- Supported Devices: Arista EOS specific
- Use Cases: All operations on Arista devices

**Key Parameters**:
- `connection_args.host` (required)`: Device IP address
- `connection_args.transport` (default https)`: Transport protocol, supports `http`/`https`
- `connection_args.port`: API port number (HTTP default 80, HTTPS default 443)
- `connection_args.timeout` (default 60 seconds)`: Connection timeout time
- `driver_args`: Supports arbitrary parameters, will be passed to pyeapi's enable/config methods

📖 [View PyEAPI Detailed Documentation](./pyeapi.md)

## Selection Recommendations

| Scenario | Recommended Driver |
|----------|-------------------|
| Arista devices | **PyEAPI (preferred)** |
| Cisco/Juniper/Other SSH devices | **Netmiko (recommended)** |
| Need configuration merge/rollback | NAPALM |

## Quick Decision

```
Arista device? → PyEAPI
Need configuration merge/rollback? → NAPALM
Other scenarios → Netmiko (recommended)
```
