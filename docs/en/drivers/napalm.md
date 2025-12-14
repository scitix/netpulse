# NAPALM Driver

## Overview

NAPALM driver is based on [Device Operation API](../api/device-api.md), providing cross-vendor standardized network device operation functions, supporting mainstream vendor devices such as Cisco, Juniper, Arista, HP, etc.

> **Important Note**: This document focuses on NAPALM driver-specific parameters and usage. For general API endpoints (`POST /device/exec`), request format, response format, etc., please refer to [Device Operation API](../api/device-api.md).

## Driver Features

- **Connection Method**: SSH/HTTP/HTTPS
- **Use Cases**: Cross-vendor environments, need unified configuration management
- **Recommended Queue Strategy**: `fifo` (First-In-First-Out queue)
- **Advantages**: Standardized interface, supports configuration merge, replace, rollback

## Query Operations

### 1. Basic Data Collection

#### Device Facts Collection

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "eos",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "get_facts",
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### Multi-Method Combination Query

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 60,
    "optional_args": {
      "port": 22,
      "secret": "enable_password"
    }
  },
  "command": [
    "get_facts",
    "get_interfaces",
    "get_interfaces_ip",
    "get_arp_table",
    "get_mac_address_table"
  ],
  "driver_args": {
    "encoding": "text"
  },
  "queue_strategy": "fifo",
  "ttl": 600
}
```

#### Routing Information Query

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "iosxr",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "optional_args": {
      "port": 22,
      "secret": "enable_password"
    }
  },
  "command": [
    "get_route_to",
    "get_bgp_neighbors",
    "get_bgp_neighbors_detail"
  ],
  "driver_args": {
    "destination": "8.8.8.8",
    "protocol": "ipv4"
  },
  "queue_strategy": "fifo",
  "ttl": 450
}
```

### 2. Interface Information Query

#### Interface Status Query

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "get_interfaces",
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### Interface IP Information Query

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "eos",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "get_interfaces_ip",
  "queue_strategy": "fifo",
  "ttl": 300
}
```

### 3. Network Protocol Query

#### BGP Neighbor Query

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "get_bgp_neighbors",
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### OSPF Neighbor Query

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "get_ospf_neighbors",
  "queue_strategy": "fifo",
  "ttl": 300
}
```

## Configuration Operations

### 1. Basic Configuration Push

#### Single Command Configuration

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "optional_args": {
      "secret": "enable_password"
    }
  },
  "config": "hostname NAPALM-Test-Device",
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### Interface Configuration - With driver_args

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "optional_args": {
      "secret": "enable_password"
    }
  },
  "config": [
    "interface GigabitEthernet0/1",
    "description NAPALM Configured Interface",
    "ip address 192.168.100.1 255.255.255.0",
    "no shutdown"
  ],
  "driver_args": {
    "message": "NAPALM interface configuration",
    "revert_in": 60
  },
  "queue_strategy": "fifo",
  "ttl": 600
}
```

### 2. Configuration Replace Operations

#### Configuration Push - Using Template

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "junos",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "config": {
    "snmp": {
      "community": "napalm_ro",
      "location": "Datacenter-01",
      "contact": "netops@company.com"
    },
    "ntp": {
      "servers": ["8.8.8.8", "8.8.4.4"]
    }
  },
  "driver_args": {
    "message": "NAPALM configuration",
    "revert_in": 120
  },
  "rendering": {
    "name": "jinja2",
    "template": "snmp community {{ snmp.community }} authorization read-only\nsnmp location {{ snmp.location }}\nsnmp contact {{ snmp.contact }}\n{% for server in ntp.servers %}ntp server {{ server }}\n{% endfor %}"
  },
  "queue_strategy": "fifo",
  "ttl": 600
}
```

#### Configuration Merge - Incremental Configuration (Default Mode)

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "eos",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "config": [
    "interface Ethernet1",
    "description Management Interface",
    "ip address 192.168.1.1/24",
    "no shutdown"
  ],
  "driver_args": {
    "message": "NAPALM merge configuration",
    "revert_in": 60
  },
  "queue_strategy": "fifo",
  "ttl": 600
}
```

### 3. Advanced Configuration Operations

#### Configuration Rollback

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "optional_args": {
      "secret": "enable_password"
    }
  },
  "command": "rollback",
  "driver_args": {
    "message": "Rollback to previous configuration"
  },
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### Configuration Compare

**Request**
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "ios",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password"
  },
  "command": "compare_config",
  "queue_strategy": "fifo",
  "ttl": 300
}
```

## Usage Examples

### cURL Examples

```bash
# Basic device facts collection
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "napalm",
    "connection_args": {
      "device_type": "ios",
      "hostname": "192.168.1.1",
      "username": "admin",
      "password": "password"
    },
    "command": "get_facts"
  }' \
  http://localhost:9000/device/exec

# Multi-method combination query
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "napalm",
    "connection_args": {
      "device_type": "ios",
      "hostname": "192.168.1.1",
      "username": "admin",
      "password": "password"
    },
    "command": [
      "get_facts",
      "get_interfaces",
      "get_interfaces_ip"
    ]
  }' \
  http://localhost:9000/device/exec

# Configuration push
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "napalm",
    "connection_args": {
      "device_type": "ios",
      "hostname": "192.168.1.1",
      "username": "admin",
      "password": "password"
    },
    "config": "hostname NAPALM-Device",
    "driver_args": {
      "message": "NAPALM configuration"
    }
  }' \
  http://localhost:9000/device/exec
```

### Python Examples

```python
import requests
import json

class NapalmClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def get_facts(self, host, username, password, device_type="ios"):
        """Get device facts information"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "command": "get_facts",
            "queue_strategy": "fifo",
            "ttl": 300
        }
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_interfaces(self, host, username, password, device_type="ios"):
        """Get interface information"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "command": "get_interfaces",
            "queue_strategy": "fifo",
            "ttl": 300
        }
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_bgp_neighbors(self, host, username, password, device_type="ios"):
        """Get BGP neighbor information"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "command": "get_bgp_neighbors",
            "queue_strategy": "fifo",
            "ttl": 300
        }
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def push_config(self, host, username, password, config, device_type="ios", **kwargs):
        """Push configuration"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "config": config,
            "queue_strategy": "fifo",
            "ttl": 600
        }
        
        # Add driver_args
        if "driver_args" in kwargs:
            payload["driver_args"] = kwargs["driver_args"]
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def multi_method_query(self, host, username, password, methods, device_type="ios"):
        """Multi-method combination query"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "command": methods,
            "driver_args": {
                "encoding": "text"
            },
            "queue_strategy": "fifo",
            "ttl": 600
        }
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()

# Usage example
client = NapalmClient("http://localhost:9000", "your-api-key-here")

# Get device facts
facts = client.get_facts("192.168.1.1", "admin", "password")
print(f"Device facts: {facts}")

# Get interface information
interfaces = client.get_interfaces("192.168.1.1", "admin", "password")
print(f"Interface information: {interfaces}")

# Get BGP neighbors
bgp_neighbors = client.get_bgp_neighbors("192.168.1.1", "admin", "password")
print(f"BGP neighbors: {bgp_neighbors}")

# Multi-method query
methods = ["get_facts", "get_interfaces", "get_interfaces_ip", "get_arp_table"]
result = client.multi_method_query("192.168.1.1", "admin", "password", methods)
print(f"Multi-method query result: {result}")

# Configuration push
config = "hostname NAPALM-Device"
result = client.push_config(
    "192.168.1.1", "admin", "password", config,
    driver_args={
        "message": "NAPALM configuration",
        "revert_in": 60
    }
)
print(f"Configuration push result: {result}")
```

## NAPALM Driver-Specific Parameters

> **Note**: For general connection parameters (hostname, username, password, etc.), please refer to parameter descriptions in [Device Operation API](../api/device-api.md). This section only describes NAPALM driver-specific parameters.

### connection_args Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| device_type | string | - | Device type (required), supports: ios, iosxr, junos, eos, nxos |
| hostname | string | - | Device IP address (NAPALM uses hostname instead of host) |
| optional_args | object | {} | Optional parameters object, can include: port, secret, transport, etc. |

**optional_args Common Parameters**:
- `port`: SSH port number
- `secret`: enable password
- `transport`: transport protocol (ssh/http/https)

### driver_args Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| encoding | string | "text" | Encoding format (only for query operations, CLI commands) |
| message | string | - | Configuration commit message (only for configuration operations, passed to commit_config) |
| revert_in | integer | - | Configuration confirmation time (seconds), used for automatic rollback (only for configuration operations, passed to commit_config) |

> **Note**: `options` parameter is a global option, common to all drivers. For detailed description, please refer to [Device Operation API](../api/device-api.md).

**NAPALM Recommended Configuration**:
- `queue_strategy`: Recommended to use `"fifo"`, suitable for HTTP/SSH short connections
- `ttl`: Set based on operation complexity, query operations recommend 300 seconds, configuration operations recommend 600 seconds

### Supported Device Types

| Device Type | Vendor | Description |
|-------------|--------|-------------|
| ios | Cisco | Cisco IOS |
| iosxr | Cisco | Cisco IOS XR |
| junos | Juniper | Juniper Junos |
| eos | Arista | Arista EOS |
| nxos | Cisco | Cisco NX-OS |

### Supported Methods

| Method | Description | Return Value |
|--------|-------------|--------------|
| get_facts | Get device facts | Device basic information |
| get_interfaces | Get interface information | Interface status and configuration |
| get_interfaces_ip | Get interface IP information | Interface IP addresses |
| get_arp_table | Get ARP table | ARP entries |
| get_mac_address_table | Get MAC address table | MAC address entries |
| get_route_to | Get routing information | Routing table |
| get_bgp_neighbors | Get BGP neighbors | BGP neighbor information |
| get_bgp_neighbors_detail | Get BGP neighbor details | Detailed BGP information |
| get_ospf_neighbors | Get OSPF neighbors | OSPF neighbor information |
| get_lldp_neighbors | Get LLDP neighbors | LLDP neighbor information |
| get_lldp_neighbors_detail | Get LLDP neighbor details | Detailed LLDP information |
| get_environment | Get environment information | Temperature, power, etc. |
| get_config | Get configuration | Device configuration |
| compare_config | Compare configuration | Configuration differences |
| rollback | Configuration rollback | Rollback result |

## NAPALM Driver Best Practices

### 1. Query Operations
- Use fifo queue strategy
- Set timeout appropriately
- Use multi-method combination queries (e.g.: get_facts, get_interfaces, get_interfaces_ip)

### 2. Configuration Operations
- Enable confirmation mechanism (set revert_in parameter)
- Set commit message (message parameter)
- Use template rendering to generate configuration
- NAPALM configuration operations default to merge mode (incremental configuration)

### 3. Configuration Management
- Configuration operations default to merge mode (incremental configuration)
- Use rollback function for configuration rollback (rollback as command call)

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

3. **Method Not Supported**
   - Check device type
   - Verify method support
   - View error logs

### Debug Commands

```bash
# Test network connectivity
ping 192.168.1.1

# Test SSH connection
ssh admin@192.168.1.1

# View connection logs
tail -f /var/log/netpulse.log
```

## Related Documentation

- [Device Operation API](../api/device-api.md) - Core device operation interfaces
- [Driver Selection](./index.md) - Learn about other drivers
