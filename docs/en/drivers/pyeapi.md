# PyEAPI Driver

## Overview

PyEAPI driver is based on [Device Operation API](../api/device-api.md), providing dedicated operation functions for Arista devices, implementing device query and configuration management through HTTP/HTTPS API.

> **Important Note**: This document focuses on PyEAPI driver-specific parameters and usage. For general API endpoints (`POST /device/execute`), request format, response format, etc., please refer to [Device Operation API](../api/device-api.md).

## Driver Features

- **Connection Method**: HTTP/HTTPS API
- **Use Cases**: Arista EOS devices only
- **Recommended Queue Strategy**: `fifo` (HTTP stateless connection)
- **Advantages**: Native API support, excellent performance, supports JSON format structured data

## Query Operations

### 1. Basic eAPI Query

#### Basic Query - JSON Format

**Request**
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
    "encoding": "json",
    "format": "json"
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### Multiple Command JSON Query

**Request**
```json
{
  "driver": "pyeapi",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "transport": "https",
    "port": 443,
    "timeout": 60
  },
  "command": [
    "show version",
    "show interfaces status",
    "show ip interface brief",
    "show vlan brief",
    "show mac address-table"
  ],
  "driver_args": {
    "encoding": "json",
    "format": "json",
    "timestamps": true
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

#### Advanced eAPI Query - With Parsing

**Request**
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
  "command": "show interfaces ethernet status",
  "driver_args": {
    "encoding": "json",
    "format": "json",
    "expand": true,
    "detail": true
  },
  "options": {
    "parsing": {
      "name": "json",
      "path": "interfaceStatuses"
    },
    "queue_strategy": "fifo",
    "ttl": 300,
    "webhook": {
      "url": "https://monitoring.company.com/arista-interfaces",
      "method": "POST",
      "headers": {
        "Authorization": "Bearer {{api_token}}"
      }
    }
  }
}
```

### 2. Interface Information Query

#### Interface Status Query

**Request**
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
  "command": "show interfaces status",
  "driver_args": {
    "encoding": "json",
    "format": "json"
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### Interface Detail Information Query

**Request**
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
  "command": "show interfaces ethernet detail",
  "driver_args": {
    "encoding": "json",
    "format": "json",
    "expand": true
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

### 3. VLAN Information Query

#### VLAN Overview Query

**Request**
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
  "command": "show vlan brief",
  "driver_args": {
    "encoding": "json",
    "format": "json"
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### VLAN Detail Information Query

**Request**
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
  "command": "show vlan detail",
  "driver_args": {
    "encoding": "json",
    "format": "json",
    "expand": true
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

### 4. Routing Information Query

#### BGP Neighbor Query

**Request**
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
  "command": "show ip bgp summary",
  "driver_args": {
    "encoding": "json",
    "format": "json"
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### Routing Table Query

**Request**
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
  "command": "show ip route",
  "driver_args": {
    "encoding": "json",
    "format": "json"
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

## Configuration Operations

### 1. Basic Configuration Push

#### Single Command Configuration

**Request**
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
  "config": "hostname PyEAPI-Test-Switch",
  "driver_args": {
    "format": "text",
    "autoComplete": true
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### VLAN Batch Configuration

**Request**
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
    "vlan 200",
    "name VOICE_VLAN",
    "vlan 300",
    "name GUEST_VLAN",
    "interface range Ethernet1-10",
    "switchport mode access",
    "switchport access vlan 100"
  ],
  "driver_args": {
    "format": "text",
    "autoComplete": true,
    "expandAliases": true
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

### 2. Advanced Configuration Operations

#### BGP Configuration - Template Rendering

**Request**
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
  "config": {
    "local_asn": 65001,
    "router_id": "1.1.1.1",
    "neighbors": [
      {"ip": "10.1.1.2", "asn": 65002, "description": "Peer-1"},
      {"ip": "10.1.1.3", "asn": 65003, "description": "Peer-2"}
    ]
  },
  "driver_args": {
    "format": "text",
    "autoComplete": true
  },
  "options": {
    "rendering": {
      "name": "jinja2",
      "template": "router bgp {{ local_asn }}\n router-id {{ router_id }}\n{% for neighbor in neighbors %}\n neighbor {{ neighbor.ip }} remote-as {{ neighbor.asn }}\n neighbor {{ neighbor.ip }} description {{ neighbor.description }}\n{% endfor %}"
    },
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

#### Interface Configuration - Structured Data

**Request**
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
  "config": {
    "interfaces": [
      {
        "name": "Ethernet1",
        "description": "Server Connection",
        "mode": "access",
        "vlan": 100
      },
      {
        "name": "Ethernet2",
        "description": "IP Phone",
        "mode": "access",
        "vlan": 200
      }
    ]
  },
  "driver_args": {
    "format": "text",
    "autoComplete": true
  },
  "options": {
    "rendering": {
      "name": "jinja2",
      "template": "{% for intf in interfaces %}\ninterface {{ intf.name }}\n description {{ intf.description }}\n switchport mode {{ intf.mode }}\n switchport access vlan {{ intf.vlan }}\n{% endfor %}"
    },
    "queue_strategy": "fifo",
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
      "encoding": "json",
      "format": "json"
    }
  }' \
  http://localhost:9000/device/execute

# Multiple command query
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "pyeapi",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password",
      "transport": "https",
      "port": 443
    },
    "command": [
      "show version",
      "show interfaces status",
      "show vlan brief"
    ],
    "driver_args": {
      "encoding": "json",
      "format": "json"
    }
  }' \
  http://localhost:9000/device/execute

# Configuration push
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key-here" \
  -d '{
    "driver": "pyeapi",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password",
      "transport": "https",
      "port": 443
    },
    "config": "hostname PyEAPI-Switch",
    "driver_args": {
      "format": "text",
      "autoComplete": true
    }
  }' \
  http://localhost:9000/device/execute
```

### Python Examples

```python
import requests
import json

class PyEapiClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def execute_command(self, host, username, password, command, **kwargs):
        """Execute single command query"""
        payload = {
            "driver": "pyeapi",
            "connection_args": {
                "host": host,
                "username": username,
                "password": password,
                "transport": "https",
                "port": 443
            },
            "command": command,
            "driver_args": {
                "encoding": "json",
                "format": "json"
            },
            "options": {
                "queue_strategy": "fifo",
                "ttl": 300
            }
        }
        
        # Add optional parameters
        if "driver_args" in kwargs:
            payload["driver_args"].update(kwargs["driver_args"])
        if "options" in kwargs:
            payload["options"].update(kwargs["options"])
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def execute_commands(self, host, username, password, commands, **kwargs):
        """Execute multiple command query"""
        payload = {
            "driver": "pyeapi",
            "connection_args": {
                "host": host,
                "username": username,
                "password": password,
                "transport": "https",
                "port": 443
            },
            "command": commands,
            "driver_args": {
                "encoding": "json",
                "format": "json"
            },
            "options": {
                "queue_strategy": "fifo",
                "ttl": 600
            }
        }
        
        # Add optional parameters
        if "driver_args" in kwargs:
            payload["driver_args"].update(kwargs["driver_args"])
        if "options" in kwargs:
            payload["options"].update(kwargs["options"])
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def push_config(self, host, username, password, config, **kwargs):
        """Push configuration"""
        payload = {
            "driver": "pyeapi",
            "connection_args": {
                "host": host,
                "username": username,
                "password": password,
                "transport": "https",
                "port": 443
            },
            "config": config,
            "driver_args": {
                "format": "text",
                "autoComplete": True
            },
            "options": {
                "queue_strategy": "fifo",
                "ttl": 600
            }
        }
        
        # Add optional parameters
        if "driver_args" in kwargs:
            payload["driver_args"].update(kwargs["driver_args"])
        if "options" in kwargs:
            payload["options"].update(kwargs["options"])
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_version(self, host, username, password):
        """Get device version information"""
        return self.execute_command(host, username, password, "show version")
    
    def get_interfaces(self, host, username, password):
        """Get interface information"""
        return self.execute_command(host, username, password, "show interfaces status")
    
    def get_vlans(self, host, username, password):
        """Get VLAN information"""
        return self.execute_command(host, username, password, "show vlan brief")
    
    def get_bgp_summary(self, host, username, password):
        """Get BGP summary information"""
        return self.execute_command(host, username, password, "show ip bgp summary")

# Usage example
client = PyEapiClient("http://localhost:9000", "your-api-key-here")

# Get device version
version = client.get_version("192.168.1.1", "admin", "password")
print(f"Device version: {version}")

# Get interface information
interfaces = client.get_interfaces("192.168.1.1", "admin", "password")
print(f"Interface information: {interfaces}")

# Get VLAN information
vlans = client.get_vlans("192.168.1.1", "admin", "password")
print(f"VLAN information: {vlans}")

# Multiple command query
commands = ["show version", "show interfaces status", "show vlan brief"]
result = client.execute_commands("192.168.1.1", "admin", "password", commands)
print(f"Multiple command query result: {result}")

# Configuration push
config = "hostname PyEAPI-Switch"
result = client.push_config("192.168.1.1", "admin", "password", config)
print(f"Configuration push result: {result}")
```

## PyEAPI Driver-Specific Parameters

> **Note**: For general connection parameters (host, username, password, etc.), please refer to parameter descriptions in [Device Operation API](../api/device-api.md). This section only describes PyEAPI driver-specific parameters.

### connection_args Specific Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| transport | string | https | Transport protocol, supports: http/https |
| port | integer | 443 | API port number (HTTP default 80, HTTPS default 443) |
| timeout | integer | 60 | Connection timeout (seconds) |
| key_file | string | - | SSL key file path |
| cert_file | string | - | SSL certificate file path |
| ca_file | string | - | CA certificate file path |

### driver_args Specific Parameters

PyEAPI driver's `driver_args` supports arbitrary parameters (`extra="allow"`), all parameters are directly passed to pyeapi's `enable()` or `config()` methods.

> **Important Note**: All parameters in `driver_args` are directly passed to the underlying pyeapi library. Parameters used in documentation examples (such as `encoding`, `format`, `timestamps`, `expand`, `detail`, `autoComplete`, `expandAliases`, etc.) need to be used according to the actual support of the pyeapi library. For specific supported parameters, please refer to [pyeapi official documentation](https://github.com/arista-eosplus/pyeapi).

**Common Parameter Examples** (actual support please refer to pyeapi documentation):
- `encoding`: Encoding format (for enable method)
- `format`: Output format (for enable method, such as `json`)
- For other parameters, please refer to [pyeapi official documentation](https://github.com/arista-eosplus/pyeapi)

> **Note**: `options` parameter is a global option, common to all drivers. For detailed description, please refer to [Device Operation API](../api/device-api.md).

**PyEAPI Recommended Configuration**:
- `queue_strategy`: Recommended to use `"fifo"`, HTTP stateless connection
- `ttl`: Set based on operation complexity, query operations recommend 300 seconds, configuration operations recommend 600 seconds

### Supported Commands

| Command | Description | Return Value |
|---------|-------------|--------------|
| show version | Display version information | Device version and model |
| show interfaces status | Display interface status | Interface status information |
| show interfaces ethernet status | Display Ethernet interface status | Ethernet interface status |
| show interfaces ethernet detail | Display Ethernet interface details | Detailed interface information |
| show vlan brief | Display VLAN overview | VLAN list |
| show vlan detail | Display VLAN details | Detailed VLAN information |
| show ip interface brief | Display IP interface overview | IP interface information |
| show ip bgp summary | Display BGP summary | BGP neighbor information |
| show ip route | Display routing table | Routing information |
| show mac address-table | Display MAC address table | MAC address information |
| show lldp neighbors | Display LLDP neighbors | LLDP neighbor information |
| show system resources | Display system resources | System resource information |

## PyEAPI Driver Best Practices

### 1. Query Operations
- Use JSON format output (format: "json")
- Enable timestamp recording (timestamps: true)
- Leverage structured data advantages, directly process JSON results

### 2. Configuration Operations
- Use template rendering to generate configuration
- Enable auto-complete (autoComplete: true)
- Set reasonable timeout

### 3. Performance Optimization
- Use batch operations to improve efficiency
- Set TTL appropriately
- HTTP stateless connection, suitable for fifo queue

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
   - Confirm API access permissions

3. **Command Not Supported**
   - Check command syntax
   - Verify device support
   - View error logs

### Debug Commands

```bash
# Test HTTPS connection
curl -k https://192.168.1.1

# Test API access
curl -u admin:password https://192.168.1.1/command-api

# View connection logs
tail -f /var/log/netpulse.log
```

## Related Documentation

- [Device Operation API](../api/device-api.md) - Core device operation interfaces
- [Driver Selection](./index.md) - Learn about other drivers
