# Netmiko 驱动

## 概述

Netmiko 驱动基于[设备操作 API](../api/device-api.md)，提供基于SSH的网络设备操作功能，支持Cisco、Juniper、Arista、华为等主流厂商设备。

> **重要提示**：本文档专注于Netmiko驱动的特定参数和用法。通用API端点（`POST /device/execute`）、请求格式、响应格式等请参考[设备操作 API](../api/device-api.md)。

## 驱动特点

- **连接方式**: SSH/Telnet
- **适用场景**: 通用SSH连接，支持大多数网络设备
- **推荐队列策略**: `pinned`（设备绑定队列，支持长连接复用）
- **优势**: 通用性强，支持设备类型广泛，长连接复用提升性能

## 快速参考

### 关键参数

**connection_args（连接参数）**：
- `device_type`（必需）：设备类型，如 `cisco_ios`、`juniper_junos` 等
- `host`（必需）：设备IP地址
- `username`、`password`（必需）：认证信息
- `secret`：特权模式密码（enable密码）
- `keepalive`（默认180秒）：SSH连接保活时间，用于长连接复用
- `port`（默认22）：SSH端口

**请求**
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

#### 基础查询 - FIFO队列

**请求**
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

#### 基础查询 - Pinned队列

**请求**
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

#### 慢速设备优化

**请求**
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

#### 高级查询 - 带driver_args

**请求**
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

#### 查询 - 带TextFSM解析

**请求**
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

#### 查询 - 带Webhook回调

**请求**
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

### 2. 多命令查询

#### 多命令 - 基础组合

**请求**
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

#### 多命令 - 带driver_args优化

**请求**
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

#### 多命令 - 网络诊断组合

**请求**
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

#### 多命令 - 安全审计组合

**请求**
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

## 配置操作

### 1. 单配置推送

#### 基础配置 - 单命令

**请求**
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

#### 基础配置 - 带driver_args

**请求**
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

### 2. 多配置推送

#### 接口配置 - 基础

**请求**
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

#### 批量接口配置 - 带driver_args

**请求**
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

#### 高级配置推送

**请求**
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

#### 系统配置 - 完整设置

**请求**
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

#### 安全配置 - ACL和认证

**请求**
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

## 使用示例

### cURL 示例

```bash
# 基础查询
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

# 多命令查询
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

# 配置推送
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

### Python 示例

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
        """执行单命令查询"""
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
        
        # 添加可选参数
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
        """执行多命令查询"""
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
        
        # 添加可选参数
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
        """推送配置"""
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
        
        # 添加可选参数
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

# 使用示例
client = NetmikoClient("http://localhost:9000", "your-api-key-here")

# 基础查询
result = client.execute_command(
    "192.168.1.1", "admin", "password", "show version"
)
print(f"查询结果: {result}")

# 多命令查询
commands = ["show version", "show ip interface brief", "show interfaces status"]
result = client.execute_commands(
    "192.168.1.1", "admin", "password", commands
)
print(f"多命令查询结果: {result}")

# 配置推送
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
print(f"配置推送结果: {result}")
```

## Netmiko驱动特定参数

> **注意**：通用连接参数（host、username、password等）请参考[设备操作 API](../api/device-api.md)中的参数说明。本节只说明Netmiko驱动特有的参数。

### connection_args 特定参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| device_type | string | - | 设备类型（必需），支持：cisco_ios, cisco_nxos, juniper_junos, arista_eos, huawei, hp_comware等 |
| secret | string | - | 特权模式密码（enable密码） |
| keepalive | integer | 180 | SSH连接保活时间（秒），用于长连接复用 |
| global_delay_factor | float | 1 | 全局延迟因子，用于慢速设备 |
| fast_cli | boolean | false | 快速CLI模式，跳过某些验证 |
| verbose | boolean | false | 详细输出模式 |

### driver_args 特定参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| read_timeout | float | 10.0 | 读取超时时间（秒） |
| delay_factor | float | 1 | 延迟因子，用于慢速设备 |
| max_loops | integer | 500 | 最大循环次数，等待命令输出 |
| auto_find_prompt | boolean | true | 自动查找设备提示符 |
| strip_prompt | boolean | true | 去除输出中的提示符 |
| strip_command | boolean | true | 去除输出中的命令 |
| normalize | boolean | true | 标准化输出（去除多余空格等） |
| cmd_verify | boolean | true | 命令验证，检查命令是否正确执行 |
| exit_config_mode | boolean | true | 配置操作后自动退出配置模式 |
| enter_config_mode | boolean | true | 配置操作前自动进入配置模式 |
| error_pattern | string | - | 错误模式正则表达式，用于检测命令执行错误 |
| config_mode_command | string | - | 配置模式命令（如：configure terminal） |
| terminator | string | "#" | 配置模式终止符 |

> **注意**：`options` 参数是全局选项，所有驱动通用。详细说明请参考[设备操作 API](../api/device-api.md)。

**Netmiko推荐配置**：
- `queue_strategy`: 推荐使用 `"pinned"`，支持连接复用，提高性能
- `ttl`: 根据操作复杂度设置，查询操作建议300秒，配置操作建议600秒

## 支持的设备类型

### Cisco 设备
- `cisco_ios`: Cisco IOS
- `cisco_nxos`: Cisco NX-OS
- `cisco_xe`: Cisco IOS XE
- `cisco_xr`: Cisco IOS XR

### Juniper 设备
- `juniper_junos`: Juniper Junos
- `juniper_screenos`: Juniper ScreenOS

### Arista 设备
- `arista_eos`: Arista EOS

### 其他厂商
- `huawei`: 华为设备
- `hp_comware`: HP Comware
- `hp_procurve`: HP ProCurve
- `f5_tmsh`: F5 BIG-IP
- `paloalto_panos`: Palo Alto PAN-OS

## Netmiko驱动最佳实践

### 1. 查询操作
- 使用pinned队列提高效率（支持连接复用）
- 合理设置超时时间（read_timeout）
- 使用driver_args优化性能（delay_factor, strip_prompt等）

### 2. 配置操作
- 启用命令验证（cmd_verify: true）
- 设置错误模式检测（error_pattern）
- 使用webhook回调获取结果

### 3. 慢速设备优化
- 增加delay_factor（如：2-4）
- 增加read_timeout
- 使用global_delay_factor

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

3. **命令执行失败**
   - 检查设备类型
   - 验证命令语法
   - 查看错误日志

### 调试命令

```bash
# 测试SSH连接
ssh admin@192.168.1.1

# 查看连接日志
tail -f /var/log/netpulse.log

# 检查设备类型
ssh admin@192.168.1.1 "show version"
```

## 相关文档

- [设备操作 API](../api/device-api.md) - 设备操作核心接口
- [驱动选择](./index.md) - 了解其他驱动 