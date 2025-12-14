# PyEAPI 驱动

## 概述

PyEAPI 驱动基于[设备操作 API](../api/device-api.md)，提供Arista设备的专用操作功能，通过HTTP/HTTPS API实现设备查询和配置管理。

> **重要提示**：本文档专注于PyEAPI驱动的特定参数和用法。通用API端点（`POST /device/exec`）、请求格式、响应格式等请参考[设备操作 API](../api/device-api.md)。

## 驱动特点

- **连接方式**: HTTP/HTTPS API
- **适用场景**: Arista EOS设备专用
- **推荐队列策略**: `fifo`（HTTP无状态连接）
- **优势**: 原生API支持，性能优异，支持JSON格式结构化数据

## 查询操作

### 1. 基础eAPI查询

#### 基础查询 - JSON格式

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### 多命令JSON查询

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 600
}
```

#### 高级eAPI查询 - 带解析

**请求**
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
```

### 2. 接口信息查询

#### 接口状态查询

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### 接口详细信息查询

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

### 3. VLAN信息查询

#### VLAN概览查询

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### VLAN详细信息查询

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

### 4. 路由信息查询

#### BGP邻居查询

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### 路由表查询

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

## 配置操作

### 1. 基础配置推送

#### 单命令配置

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 300
}
```

#### VLAN批量配置

**请求**
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
  "queue_strategy": "fifo",
  "ttl": 600
}
```

### 2. 高级配置操作

#### BGP配置 - 模板渲染

**请求**
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
  "rendering": {
    "name": "jinja2",
    "template": "router bgp {{ local_asn }}\n router-id {{ router_id }}\n{% for neighbor in neighbors %}\n neighbor {{ neighbor.ip }} remote-as {{ neighbor.asn }}\n neighbor {{ neighbor.ip }} description {{ neighbor.description }}\n{% endfor %}"
  },
  "queue_strategy": "fifo",
  "ttl": 600
}
```

#### 接口配置 - 结构化数据

**请求**
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
  "rendering": {
    "name": "jinja2",
    "template": "{% for intf in interfaces %}\ninterface {{ intf.name }}\n description {{ intf.description }}\n switchport mode {{ intf.mode }}\n switchport access vlan {{ intf.vlan }}\n{% endfor %}"
  },
  "queue_strategy": "fifo",
  "ttl": 600
}
```

## 使用示例

### cURL 示例

```bash
# 基础查询
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
  http://localhost:9000/device/exec

# 多命令查询
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
  http://localhost:9000/device/exec

# 配置推送
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
  http://localhost:9000/device/exec
```

### Python 示例

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
        """执行单命令查询"""
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
            "queue_strategy": "fifo",
            "ttl": 300
        }
        
        # 添加可选参数
        if "driver_args" in kwargs:
            payload["driver_args"].update(kwargs["driver_args"])
        if "queue_strategy" in kwargs:
            payload["queue_strategy"] = kwargs["queue_strategy"]
        if "ttl" in kwargs:
            payload["ttl"] = kwargs["ttl"]
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def execute_commands(self, host, username, password, commands, **kwargs):
        """执行多命令查询"""
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
            "queue_strategy": "fifo",
            "ttl": 600
        }
        
        # 添加可选参数
        if "driver_args" in kwargs:
            payload["driver_args"].update(kwargs["driver_args"])
        if "queue_strategy" in kwargs:
            payload["queue_strategy"] = kwargs["queue_strategy"]
        if "ttl" in kwargs:
            payload["ttl"] = kwargs["ttl"]
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def push_config(self, host, username, password, config, **kwargs):
        """推送配置"""
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
            "queue_strategy": "fifo",
            "ttl": 600
        }
        
        # 添加可选参数
        if "driver_args" in kwargs:
            payload["driver_args"].update(kwargs["driver_args"])
        if "queue_strategy" in kwargs:
            payload["queue_strategy"] = kwargs["queue_strategy"]
        if "ttl" in kwargs:
            payload["ttl"] = kwargs["ttl"]
        
        response = requests.post(
            f"{self.base_url}/device/exec",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_version(self, host, username, password):
        """获取设备版本信息"""
        return self.execute_command(host, username, password, "show version")
    
    def get_interfaces(self, host, username, password):
        """获取接口信息"""
        return self.execute_command(host, username, password, "show interfaces status")
    
    def get_vlans(self, host, username, password):
        """获取VLAN信息"""
        return self.execute_command(host, username, password, "show vlan brief")
    
    def get_bgp_summary(self, host, username, password):
        """获取BGP摘要信息"""
        return self.execute_command(host, username, password, "show ip bgp summary")

# 使用示例
client = PyEapiClient("http://localhost:9000", "your-api-key-here")

# 获取设备版本
version = client.get_version("192.168.1.1", "admin", "password")
print(f"设备版本: {version}")

# 获取接口信息
interfaces = client.get_interfaces("192.168.1.1", "admin", "password")
print(f"接口信息: {interfaces}")

# 获取VLAN信息
vlans = client.get_vlans("192.168.1.1", "admin", "password")
print(f"VLAN信息: {vlans}")

# 多命令查询
commands = ["show version", "show interfaces status", "show vlan brief"]
result = client.execute_commands("192.168.1.1", "admin", "password", commands)
print(f"多命令查询结果: {result}")

# 配置推送
config = "hostname PyEAPI-Switch"
result = client.push_config("192.168.1.1", "admin", "password", config)
print(f"配置推送结果: {result}")
```

## PyEAPI驱动特定参数

> **注意**：通用连接参数（host、username、password等）请参考[设备操作 API](../api/device-api.md)中的参数说明。本节只说明PyEAPI驱动特有的参数。

### connection_args 特定参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| transport | string | https | 传输协议，支持：http/https |
| port | integer | 443 | API端口号（HTTP默认80，HTTPS默认443） |
| timeout | integer | 60 | 连接超时时间（秒） |
| key_file | string | - | SSL密钥文件路径 |
| cert_file | string | - | SSL证书文件路径 |
| ca_file | string | - | CA证书文件路径 |

### driver_args 特定参数

PyEAPI 驱动的 `driver_args` 支持任意参数（`extra="allow"`），所有参数会直接传递给 pyeapi 的 `enable()` 或 `config()` 方法。

> **重要提示**：`driver_args` 中的所有参数都会直接传递给底层 pyeapi 库。文档中示例使用的参数（如 `encoding`、`format`、`timestamps`、`expand`、`detail`、`autoComplete`、`expandAliases` 等）需要根据 pyeapi 库的实际支持情况使用。具体支持的参数请参考 [pyeapi 官方文档](https://github.com/arista-eosplus/pyeapi)。

**常用参数示例**（实际支持情况请参考 pyeapi 文档）：
- `encoding`: 编码格式（用于 enable 方法）
- `format`: 输出格式（用于 enable 方法，如 `json`）
- 其他参数请参考 [pyeapi 官方文档](https://github.com/arista-eosplus/pyeapi)

> **注意**：`queue_strategy` 和 `ttl` 等全局选项应直接放在请求的顶级字段中，所有驱动通用。详细说明请参考[设备操作 API](../api/device-api.md)。

**PyEAPI推荐配置**：
- `queue_strategy`: 推荐使用 `"fifo"`，HTTP无状态连接
- `ttl`: 根据操作复杂度设置，查询操作建议300秒，配置操作建议600秒

### 支持的命令

| 命令 | 说明 | 返回值 |
|------|------|--------|
| show version | 显示版本信息 | 设备版本和型号 |
| show interfaces status | 显示接口状态 | 接口状态信息 |
| show interfaces ethernet status | 显示以太网接口状态 | 以太网接口状态 |
| show interfaces ethernet detail | 显示以太网接口详情 | 详细接口信息 |
| show vlan brief | 显示VLAN概览 | VLAN列表 |
| show vlan detail | 显示VLAN详情 | 详细VLAN信息 |
| show ip interface brief | 显示IP接口概览 | IP接口信息 |
| show ip bgp summary | 显示BGP摘要 | BGP邻居信息 |
| show ip route | 显示路由表 | 路由信息 |
| show mac address-table | 显示MAC地址表 | MAC地址信息 |
| show lldp neighbors | 显示LLDP邻居 | LLDP邻居信息 |
| show system resources | 显示系统资源 | 系统资源信息 |

## PyEAPI驱动最佳实践

### 1. 查询操作
- 使用JSON格式输出（format: "json"）
- 启用时间戳记录（timestamps: true）
- 利用结构化数据优势，直接处理JSON结果

### 2. 配置操作
- 使用模板渲染生成配置
- 启用自动完成（autoComplete: true）
- 设置合理超时时间

### 3. 性能优化
- 使用批量操作提高效率
- 合理设置TTL
- HTTP无状态连接，适合fifo队列

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
   - 确认API访问权限

3. **命令不支持**
   - 检查命令语法
   - 验证设备支持
   - 查看错误日志

### 调试命令

```bash
# 测试HTTPS连接
curl -k https://192.168.1.1

# 测试API访问
curl -u admin:password https://192.168.1.1/command-api

# 查看连接日志
tail -f /var/log/netpulse.log
```

## 相关文档

- [设备操作 API](../api/device-api.md) - 设备操作核心接口
- [驱动选择](./index.md) - 了解其他驱动 