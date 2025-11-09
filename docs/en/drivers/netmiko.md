# Netmiko Driver

## Overview

Netmiko driver is based on [Device Operation API](../api/device-api.md), providing SSH-based network device operation functions, supporting mainstream vendor devices such as Cisco, Juniper, Arista, Huawei, etc.

> **Important Note**: This document focuses on Netmiko driver-specific parameters and usage. For general API endpoints (`POST /device/execute`), request format, response format, etc., please refer to [Device Operation API](../api/device-api.md).

## Driver Features

- **Connection Method**: SSH/Telnet
- **Use Cases**: Universal SSH connection, supports most network devices
- **Recommended Queue Strategy**: `pinned` (device-bound queue, supports long connection reuse)
- **Advantages**: Strong universality, supports wide range of device types, long connection reuse improves performance

## Quick Reference

### Key Parameters

**connection_args (Connection Parameters)**:
- `device_type` (required): Device type, such as `cisco_ios`, `juniper_junos`, etc.
- `host` (required): Device IP address
- `username`, `password` (required): Authentication information
- `secret`: Privileged mode password (enable password)
- `keepalive` (default 180 seconds): SSH connection keepalive time, used for long connection reuse
- `port` (default 22): SSH port

**Request**
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

#### Basic Query - FIFO Queue

**Request**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 180
  }
}
```

#### Basic Query - Pinned Queue

**Request**
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
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

#### Slow Device Optimization

**Request**
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
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

#### Advanced Query - With driver_args

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 60,
    "keepalive": 30
  },
  "command": "show running-config",
  "driver_args": {
    "read_timeout": 60,
    "delay_factor": 2,
    "max_loops": 1000,
    "auto_find_prompt": true,
    "strip_prompt": true,
    "strip_command": true,
    "normalize": true,
    "cmd_verify": false
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

#### Query - With TextFSM Parsing

**Request**
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
  "options": {
    "parsing": {
      "name": "textfsm",
      "template": "cisco_ios_show_ip_interface_brief.textfsm"
    },
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

#### Query - With Webhook Callback

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "show version",
  "driver_args": {
    "read_timeout": 45,
    "strip_prompt": true,
    "normalize": true
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300,
    "webhook": {
      "url": "http://127.0.0.1:8888/webhook",
      "method": "POST",
      "headers": {
        "Content-Type": "application/json"
      },
      "timeout": 30
    }
  }
}
```

### 2. Multiple Command Queries

#### Multiple Commands - Basic Combination

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": [
    "show version",
    "show ip interface brief",
    "show interfaces status"
  ],
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

#### Multiple Commands - With driver_args Optimization

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 90,
    "keepalive": 60
  },
  "command": [
    "show version",
    "show ip interface brief",
    "show vlan brief",
    "show spanning-tree summary",
    "show mac address-table count",
    "show processes cpu",
    "show memory statistics"
  ],
  "driver_args": {
    "read_timeout": 45,
    "delay_factor": 1.5,
    "auto_find_prompt": true,
    "strip_prompt": true,
    "strip_command": true,
    "normalize": true,
    "cmd_verify": true
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

#### Multiple Commands - Network Diagnostics Combination

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": [
    "show ip route summary",
    "show ip arp",
    "show cdp neighbors detail",
    "show lldp neighbors detail",
    "show interface counters errors",
    "show logging | include ERROR|WARN"
  ],
  "driver_args": {
    "read_timeout": 60,
    "delay_factor": 2,
    "strip_prompt": true,
    "normalize": true
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 450
  }
}
```

#### Multiple Commands - Security Audit Combination

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": [
    "show running-config | include aaa|login|enable|service",
    "show users",
    "show privilege",
    "show access-lists",
    "show ip ssh",
    "show snmp community",
    "show logging"
  ],
  "driver_args": {
    "read_timeout": 60,
    "delay_factor": 2,
    "strip_prompt": true,
    "strip_command": true,
    "normalize": true
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600,
    "webhook": {
      "url": "https://security-audit.company.com/device-scan",
      "method": "POST",
      "headers": {
        "Authorization": "Bearer {{security_token}}"
      }
    }
  }
}
```

## Configuration Operations

### 1. Single Configuration Push

#### Basic Configuration - Single Command

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password"
  },
  "config": "hostname NetPulse-SW01",
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

#### Basic Configuration - With driver_args

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password"
  },
  "config": "ip domain-name company.local",
  "driver_args": {
    "exit_config_mode": true,
    "enter_config_mode": true,
    "cmd_verify": true,
    "delay_factor": 1,
    "error_pattern": "% Invalid|% Error"
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

### 2. Multiple Configuration Push

#### Interface Configuration - Basic

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password"
  },
  "config": [
    "interface GigabitEthernet0/1",
    "description Server Connection",
    "switchport mode access",
    "switchport access vlan 100",
    "no shutdown"
  ],
  "driver_args": {
    "exit_config_mode": true,
    "enter_config_mode": true,
    "cmd_verify": true,
    "delay_factor": 1
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

#### Batch Interface Configuration - With driver_args

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password"
  },
  "config": [
    "interface range GigabitEthernet0/1-10",
    "description User Ports",
    "switchport mode access",
    "switchport access vlan 200",
    "spanning-tree portfast",
    "spanning-tree bpduguard enable",
    "no shutdown"
  ],
  "driver_args": {
    "exit_config_mode": true,
    "enter_config_mode": true,
    "cmd_verify": true,
    "delay_factor": 2,
    "read_timeout": 60,
    "error_pattern": "% Invalid|% Error|% Bad"
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

#### Advanced Configuration Push

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password"
  },
  "config": [
    "interface range GigabitEthernet0/1-10",
    "description Batch Configuration by NetPulse",
    "switchport mode access",
    "switchport access vlan 200",
    "spanning-tree portfast",
    "no shutdown"
  ],
  "driver_args": {
    "exit_config_mode": true,
    "config_mode_command": "configure terminal",
    "enter_config_mode": true,
    "cmd_verify": true,
    "delay_factor": 2,
    "read_timeout": 60,
    "error_pattern": "% Invalid|% Error|% Bad",
    "terminator": "#",
    "strip_prompt": false,
    "strip_command": false
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600,
    "webhook": {
      "url": "https://config-mgmt.company.com/callback",
      "method": "POST"
    }
  }
}
```

#### System Configuration - Complete Setup

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password"
  },
  "config": [
    "ntp server 8.8.8.8",
    "ntp server 8.8.4.4",
    "logging host 192.168.1.100",
    "logging trap informational",
    "snmp-server community public RO",
    "snmp-server location Datacenter-Rack01",
    "snmp-server contact admin@company.com",
    "ip domain-name company.local",
    "clock timezone EST -5",
    "service timestamps log datetime msec"
  ],
  "driver_args": {
    "exit_config_mode": true,
    "enter_config_mode": true,
    "cmd_verify": true,
    "delay_factor": 1,
    "read_timeout": 45,
    "error_pattern": "% Invalid|% Error",
    "strip_prompt": false,
    "strip_command": false
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600,
    "webhook": {
      "url": "https://config-mgmt.company.com/device-config",
      "method": "POST",
      "headers": {
        "Authorization": "Bearer {{config_token}}"
      }
    }
  }
}
```

#### Security Configuration - ACL and Authentication

**Request**
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password"
  },
  "config": [
    "ip access-list extended MANAGEMENT_ACCESS",
    "permit tcp 192.168.1.0 0.0.0.255 any eq 22",
    "permit tcp 192.168.1.0 0.0.0.255 any eq 443",
    "permit icmp 192.168.1.0 0.0.0.255 any",
    "deny ip any any log",
    "exit",
    "line vty 0 4",
    "access-class MANAGEMENT_ACCESS in",
    "transport input ssh",
    "exit",
    "ip ssh version 2",
    "ip ssh time-out 60",
    "ip ssh authentication-retries 3"
  ],
  "driver_args": {
    "exit_config_mode": true,
    "enter_config_mode": true,
    "cmd_verify": true,
    "delay_factor": 2,
    "read_timeout": 60,
    "error_pattern": "% Invalid|% Error|% Incomplete"
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

## Usage Examples

### cURL Examples

```bash
# Basic query
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password"
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute

# Multiple command query
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password"
    },
    "command": [
      "show version",
      "show ip interface brief",
      "show interfaces status"
    ]
  }' \
  http://localhost:9000/device/execute

# Configuration push
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password",
      "secret": "enable_password"
    },
    "config": [
      "interface GigabitEthernet0/1",
      "description Server Connection",
      "switchport mode access",
      "switchport access vlan 100",
      "no shutdown"
    ]
  }' \
  http://localhost:9000/device/execute
```

### Python Examples

```python
import requests
import json

class NetmikoClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def execute_command(self, host, username, password, command, device_type="cisco_ios", **kwargs):
        """Execute single command query"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device_type,
                "host": host,
                "username": username,
                "password": password
            },
            "command": command
        }
        
        # Add optional parameters
        if "driver_args" in kwargs:
            payload["driver_args"] = kwargs["driver_args"]
        if "options" in kwargs:
            payload["options"] = kwargs["options"]
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def execute_commands(self, host, username, password, commands, device_type="cisco_ios", **kwargs):
        """Execute multiple command query"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device_type,
                "host": host,
                "username": username,
                "password": password
            },
            "command": commands
        }
        
        # Add optional parameters
        if "driver_args" in kwargs:
            payload["driver_args"] = kwargs["driver_args"]
        if "options" in kwargs:
            payload["options"] = kwargs["options"]
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def push_config(self, host, username, password, config, device_type="cisco_ios", **kwargs):
        """Push configuration"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device_type,
                "host": host,
                "username": username,
                "password": password
            },
            "config": config
        }
        
        # Add optional parameters
        if "driver_args" in kwargs:
            payload["driver_args"] = kwargs["driver_args"]
        if "options" in kwargs:
            payload["options"] = kwargs["options"]
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()

# Usage example
client = NetmikoClient("http://localhost:9000", "your-api-key-here")

# Basic query
result = client.execute_command(
    "192.168.1.1", "admin", "password", "show version"
)
print(f"Query result: {result}")

# Multiple command query
commands = ["show version", "show ip interface brief", "show interfaces status"]
result = client.execute_commands(
    "192.168.1.1", "admin", "password", commands
)
print(f"Multiple command query result: {result}")

# Configuration push
config = [
    "interface GigabitEthernet0/1",
    "description Server Connection",
    "switchport mode access",
    "switchport access vlan 100",
    "no shutdown"
]
result = client.push_config(
    "192.168.1.1", "admin", "password", config,
    driver_args={
        "exit_config_mode": True,
        "enter_config_mode": True,
        "cmd_verify": True
    }
)
print(f"Configuration push result: {result}")
```

## Netmiko Driver-Specific Parameters

> **Note**: For general connection parameters (host, username, password, etc.), please refer to parameter descriptions in [Device Operation API](../api/device-api.md). This section only describes Netmiko driver-specific parameters.

### connection_args Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| device_type | string | - | Device type (required), supports: cisco_ios, cisco_nxos, juniper_junos, arista_eos, huawei, hp_comware, etc. |
| secret | string | - | Privileged mode password (enable password) |
| keepalive | integer | 180 | SSH connection keepalive time (seconds), used for long connection reuse |
| global_delay_factor | float | 1 | Global delay factor, used for slow devices |
| fast_cli | boolean | false | Fast CLI mode, skip some validations |
| verbose | boolean | false | Verbose output mode |

### driver_args Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| read_timeout | float | 10.0 | Read timeout (seconds) |
| delay_factor | float | 1 | Delay factor, used for slow devices |
| max_loops | integer | 500 | Maximum loop count, wait for command output |
| auto_find_prompt | boolean | true | Automatically find device prompt |
| strip_prompt | boolean | true | Remove prompt from output |
| strip_command | boolean | true | Remove command from output |
| normalize | boolean | true | Normalize output (remove extra spaces, etc.) |
| cmd_verify | boolean | true | Command verification, check if command executed correctly |
| exit_config_mode | boolean | true | Automatically exit configuration mode after configuration operation |
| enter_config_mode | boolean | true | Automatically enter configuration mode before configuration operation |
| error_pattern | string | - | Error pattern regular expression, used to detect command execution errors |
| config_mode_command | string | - | Configuration mode command (e.g.: configure terminal) |
| terminator | string | "#" | Configuration mode terminator |

> **Note**: `options` parameter is a global option, common to all drivers. For detailed description, please refer to [Device Operation API](../api/device-api.md).

**Netmiko Recommended Configuration**:
- `queue_strategy`: Recommended to use `"pinned"`, supports connection reuse, improves performance
- `ttl`: Set based on operation complexity, query operations recommend 300 seconds, configuration operations recommend 600 seconds

## Supported Device Types

### Cisco Devices
- `cisco_ios`: Cisco IOS
- `cisco_nxos`: Cisco NX-OS
- `cisco_xe`: Cisco IOS XE
- `cisco_xr`: Cisco IOS XR

### Juniper Devices
- `juniper_junos`: Juniper Junos
- `juniper_screenos`: Juniper ScreenOS

### Arista Devices
- `arista_eos`: Arista EOS

### Other Vendors
- `huawei`: Huawei devices
- `hp_comware`: HP Comware
- `hp_procurve`: HP ProCurve
- `f5_tmsh`: F5 BIG-IP
- `paloalto_panos`: Palo Alto PAN-OS

## Netmiko Driver Best Practices

### 1. Query Operations
- Use pinned queue to improve efficiency (supports connection reuse)
- Set timeout appropriately (read_timeout)
- Use driver_args to optimize performance (delay_factor, strip_prompt, etc.)

### 2. Configuration Operations
- Enable command verification (cmd_verify: true)
- Set error pattern detection (error_pattern)
- Use webhook callback to get results

### 3. Slow Device Optimization
- Increase delay_factor (e.g.: 2-4)
- Increase read_timeout
- Use global_delay_factor

> **For detailed best practices, see**: [API Best Practices](../api/api-best-practices.md)

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check network connection
   - Adjust timeout
   - Verify device reachability

2. **Authentication Failed**
   - Verify username and password
   - Check account permissions
   - Confirm authentication method

3. **Command Execution Failed**
   - Check device type
   - Verify command syntax
   - View error logs

### Debug Commands

```bash
# Test SSH connection
ssh admin@192.168.1.1

# View connection logs
tail -f /var/log/netpulse.log

# Check device type
ssh admin@192.168.1.1 "show version"
```

## Related Documentation

- [Device Operation API](../api/device-api.md) - Core device operation interfaces
- [Driver Selection](./index.md) - Learn about other drivers
