# Netmiko Driver

## Overview

Netmiko is the SSH/Telnet driver behind the [Device Operation API](../api/device-api.md). It targets common network vendors (Cisco, Juniper, Arista, Huawei, etc.).

> This page focuses on Netmiko-specific parameters. For the unified endpoints (`POST /device/exec`, payload shape, responses), see [Device Operation API](../api/device-api.md).

## Highlights
- Transport: SSH/Telnet
- Use cases: general SSH access across vendors
- Recommended queue: `pinned` (device-bound, connection reuse)
- Strengths: broad device support, long-lived session reuse for performance

## Quick reference

### Key parameters

`connection_args`:
- `device_type` (required): e.g., `cisco_ios`, `juniper_junos`
- `host` (required)
- `username`, `password` (required)
- `secret`: enable password
- `keepalive` (default 180s): keepalive for long-lived sessions
- `port` (default 22)

Basic request:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "show version"
}
```

### Query examples

**FIFO queue**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "show ip interface brief",
  "queue_strategy": "fifo",
  "ttl": 180
}
```

**Pinned queue**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "show interfaces status",
  "queue_strategy": "pinned",
  "ttl": 300
}
```

**Slow device tuning**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 120,
    "global_delay_factor": 3
  },
  "command": "show running-config",
  "driver_args": {
    "read_timeout": 120,
    "delay_factor": 4,
    "max_loops": 1000,
    "auto_find_prompt": true,
    "strip_prompt": true,
    "cmd_verify": false
  },
  "queue_strategy": "pinned",
  "ttl": 600
}
```

**Query with TextFSM parsing**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "show ip interface brief",
  "driver_args": {
    "read_timeout": 30,
    "strip_prompt": true,
    "strip_command": true,
    "normalize": true
  },
  "parsing": {
    "name": "textfsm",
    "template": "cisco_ios_show_ip_interface_brief.textfsm"
  },
  "queue_strategy": "pinned",
  "ttl": 300
}
```

## Configuration pushes

**Basic config push**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "enable_mode": true
  },
  "config": [
    "interface GigabitEthernet0/1",
    "description Test",
    "no shutdown"
  ],
  "driver_args": {
    "save": true,
    "exit_config_mode": true,
    "strip_command": false,
    "strip_prompt": false
  },
  "queue_strategy": "pinned",
  "ttl": 600
}
```

**Rollback example**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "enable_mode": true
  },
  "config": [
    "rollback running-config last 1"
  ],
  "driver_args": {
    "save": true,
    "cmd_verify": false
  },
  "queue_strategy": "pinned",
  "ttl": 600
}
```

## Driver arguments (common)

```json
{
  "read_timeout": 60,
  "delay_factor": 2,
  "max_loops": 1000,
  "auto_find_prompt": true,
  "strip_prompt": true,
  "strip_command": true,
  "normalize": true,
  "cmd_verify": false,
  "save": true,
  "exit_config_mode": true,
  "enter_config_mode": true
}
```

## Best practices
- Prefer `queue_strategy: pinned` for repeated SSH access to reuse sessions.
- Increase `timeout`, `read_timeout`, and `delay_factor` for slow devices.
- Use TextFSM parsing for structured outputs.
- Always set `save: true` when you expect config persistence.
- For high-volume tasks, batch hosts and monitor job TTLs to avoid long locks.
