# NAPALM 驱动

## 概述

NAPALM 驱动基于[设备操作 API](../api/device-api.md)，提供跨厂商标准化的网络设备操作功能，支持Cisco、Juniper、Arista、HP等主流厂商设备。

> **重要提示**：本文档专注于NAPALM驱动的特定参数和用法。通用API端点（`POST /device/execute`）、请求格式、响应格式等请参考[设备操作 API](../api/device-api.md)。

## 驱动特点

- **连接方式**: SSH/HTTP/HTTPS
- **适用场景**: 跨厂商环境，需要统一配置管理
- **推荐队列策略**: `fifo`（先进先出队列）
- **优势**: 标准化接口，支持配置合并、替换、回滚

## 查询操作

### 1. 基础数据收集

#### 设备事实收集

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### 多方法组合查询

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

#### 路由信息查询

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 450
  }
}
```

### 2. 接口信息查询

#### 接口状态查询

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### 接口IP信息查询

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

### 3. 网络协议查询

#### BGP邻居查询

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### OSPF邻居查询

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

## 配置操作

### 1. 基础配置推送

#### 单命令配置

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### 接口配置 - 带driver_args

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

### 2. 配置替换操作

#### 配置推送 - 使用模板

**请求**
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
  "options": {
    "rendering": {
      "name": "jinja2",
      "template": "snmp community {{ snmp.community }} authorization read-only\nsnmp location {{ snmp.location }}\nsnmp contact {{ snmp.contact }}\n{% for server in ntp.servers %}ntp server {{ server }}\n{% endfor %}"
    },
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

#### 配置合并 - 增量配置（默认模式）

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

### 3. 高级配置操作

#### 配置回滚

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

#### 配置比较

**请求**
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
  "options": {
    "queue_strategy": "fifo",
    "ttl": 300
  }
}
```

## 使用示例

### cURL 示例

```bash
# 基础设备事实收集
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
  http://localhost:9000/device/execute

# 多方法组合查询
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
  http://localhost:9000/device/execute

# 配置推送
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
  http://localhost:9000/device/execute
```

### Python 示例

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
        """获取设备事实信息"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "command": "get_facts",
            "options": {
                "queue_strategy": "fifo",
                "ttl": 300
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_interfaces(self, host, username, password, device_type="ios"):
        """获取接口信息"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "command": "get_interfaces",
            "options": {
                "queue_strategy": "fifo",
                "ttl": 300
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_bgp_neighbors(self, host, username, password, device_type="ios"):
        """获取BGP邻居信息"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "command": "get_bgp_neighbors",
            "options": {
                "queue_strategy": "fifo",
                "ttl": 300
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def push_config(self, host, username, password, config, device_type="ios", **kwargs):
        """推送配置"""
        payload = {
            "driver": "napalm",
            "connection_args": {
                "device_type": device_type,
                "hostname": host,
                "username": username,
                "password": password
            },
            "config": config,
            "options": {
                "queue_strategy": "fifo",
                "ttl": 600
            }
        }
        
        # 添加driver_args
        if "driver_args" in kwargs:
            payload["driver_args"] = kwargs["driver_args"]
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def multi_method_query(self, host, username, password, methods, device_type="ios"):
        """多方法组合查询"""
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
            "options": {
                "queue_strategy": "fifo",
                "ttl": 600
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            headers=self.headers,
            json=payload
        )
        return response.json()

# 使用示例
client = NapalmClient("http://localhost:9000", "your-api-key-here")

# 获取设备事实
facts = client.get_facts("192.168.1.1", "admin", "password")
print(f"设备事实: {facts}")

# 获取接口信息
interfaces = client.get_interfaces("192.168.1.1", "admin", "password")
print(f"接口信息: {interfaces}")

# 获取BGP邻居
bgp_neighbors = client.get_bgp_neighbors("192.168.1.1", "admin", "password")
print(f"BGP邻居: {bgp_neighbors}")

# 多方法查询
methods = ["get_facts", "get_interfaces", "get_interfaces_ip", "get_arp_table"]
result = client.multi_method_query("192.168.1.1", "admin", "password", methods)
print(f"多方法查询结果: {result}")

# 配置推送
config = "hostname NAPALM-Device"
    result = client.push_config(
    "192.168.1.1", "admin", "password", config,
    driver_args={
        "message": "NAPALM configuration",
        "revert_in": 60
    }
)
print(f"配置推送结果: {result}")
```

## NAPALM驱动特定参数

> **注意**：通用连接参数（hostname、username、password等）请参考[设备操作 API](../api/device-api.md)中的参数说明。本节只说明NAPALM驱动特有的参数。

### connection_args 特定参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| device_type | string | - | 设备类型（必需），支持：ios, iosxr, junos, eos, nxos |
| hostname | string | - | 设备IP地址（NAPALM使用hostname而非host） |
| optional_args | object | {} | 可选参数对象，可包含：port, secret, transport等 |

**optional_args 常用参数**：
- `port`: SSH端口号
- `secret`: enable密码
- `transport`: 传输协议（ssh/http/https）

### driver_args 特定参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| encoding | string | "text" | 编码格式（仅用于查询操作，CLI命令） |
| message | string | - | 配置提交消息（仅用于配置操作，传递给commit_config） |
| revert_in | integer | - | 配置确认时间（秒），用于自动回滚（仅用于配置操作，传递给commit_config） |

> **注意**：`options` 参数是全局选项，所有驱动通用。详细说明请参考[设备操作 API](../api/device-api.md)。

**NAPALM推荐配置**：
- `queue_strategy`: 推荐使用 `"fifo"`，适合HTTP/SSH短连接
- `ttl`: 根据操作复杂度设置，查询操作建议300秒，配置操作建议600秒

### 支持的设备类型

| 设备类型 | 厂商 | 说明 |
|----------|------|------|
| ios | Cisco | Cisco IOS |
| iosxr | Cisco | Cisco IOS XR |
| junos | Juniper | Juniper Junos |
| eos | Arista | Arista EOS |
| nxos | Cisco | Cisco NX-OS |

### 支持的方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| get_facts | 获取设备事实 | 设备基本信息 |
| get_interfaces | 获取接口信息 | 接口状态和配置 |
| get_interfaces_ip | 获取接口IP信息 | 接口IP地址 |
| get_arp_table | 获取ARP表 | ARP条目 |
| get_mac_address_table | 获取MAC地址表 | MAC地址条目 |
| get_route_to | 获取路由信息 | 路由表 |
| get_bgp_neighbors | 获取BGP邻居 | BGP邻居信息 |
| get_bgp_neighbors_detail | 获取BGP邻居详情 | 详细BGP信息 |
| get_ospf_neighbors | 获取OSPF邻居 | OSPF邻居信息 |
| get_lldp_neighbors | 获取LLDP邻居 | LLDP邻居信息 |
| get_lldp_neighbors_detail | 获取LLDP邻居详情 | 详细LLDP信息 |
| get_environment | 获取环境信息 | 温度、电源等 |
| get_config | 获取配置 | 设备配置 |
| compare_config | 比较配置 | 配置差异 |
| rollback | 配置回滚 | 回滚结果 |

## NAPALM驱动最佳实践

### 1. 查询操作
- 使用fifo队列策略
- 合理设置超时时间
- 使用多方法组合查询（如：get_facts, get_interfaces, get_interfaces_ip）

### 2. 配置操作
- 启用确认机制（设置revert_in参数）
- 设置提交消息（message参数）
- 使用模板渲染生成配置
- NAPALM配置操作默认使用merge模式（增量配置）

### 3. 配置管理
- 配置操作默认使用merge模式（增量配置）
- 利用rollback功能进行配置回滚（rollback作为命令调用）

> **详细的最佳实践请参考**：[API最佳实践](../api/api-best-practices.md)

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接
   - 调整超时时间
   - 验证设备可达性

2. **认证失败**
   - 验证用户名密码
   - 检查账户权限
   - 确认认证方式

3. **方法不支持**
   - 检查设备类型
   - 验证方法支持
   - 查看错误日志

### 调试命令

```bash
# 测试网络连通性
ping 192.168.1.1

# 测试SSH连接
ssh admin@192.168.1.1

# 查看连接日志
tail -f /var/log/netpulse.log
```

## 相关文档

- [设备操作 API](../api/device-api.md) - 设备操作核心接口
- [驱动选择](./index.md) - 了解其他驱动 