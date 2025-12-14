# 设备操作 API

## 概述

设备操作 API (`/device/*`) 是 NetPulse 的核心接口，提供以下功能：

- **操作识别** - 根据请求参数自动识别操作类型（查询/配置）
- **统一接口** - 支持所有已实现的驱动和设备类型
- **简化使用** - 通过统一接口减少API调用复杂度
- **基础功能** - 支持设备操作、连接测试和批量操作

## API 端点

### POST /device/exec

统一的设备操作端点，根据请求参数识别操作类型。

**功能说明**:
- **查询操作** - 当请求包含 `command` 字段时
- **配置操作** - 当请求包含 `config` 字段时
- **队列选择** - 根据驱动类型自动选择队列策略（可手动指定）

**请求示例**:

```bash
curl -X POST "http://localhost:9000/device/exec" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "admin123"
    },
    "command": "show version"
  }'
```

**配置操作示例**:

```bash
curl -X POST "http://localhost:9000/device/exec" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "admin123"
    },
    "config": "interface GigabitEthernet0/1\n description Test Interface"
  }'
```

### POST /device/bulk

批量设备操作端点，支持对多个设备执行相同操作。

**请求示例**:

```bash
curl -X POST "http://localhost:9000/device/bulk" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "devices": [
      {
        "host": "192.168.1.1",
        "username": "admin",
        "password": "admin123"
      },
      {
        "host": "192.168.1.2",
        "username": "admin",
        "password": "admin123"
      }
    ],
    "connection_args": {
      "device_type": "cisco_ios",
      "timeout": 30
    },
    "command": "show version"
  }'
```

### POST /device/test

测试设备连接状态，用于验证设备连接和认证的可用性。支持Netmiko、NAPALM、PyEAPI和Paramiko等不同驱动类型。

**请求示例**:

```bash
curl -X POST "http://localhost:9000/device/test" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "admin123"
    }
  }'
```

**响应示例**:

```json
{
  "code": 200,
  "message": "Connection test completed",
  "data": {
    "success": true,
    "connection_time": 2.5,
    "error_message": null,
    "device_info": {
      "prompt": "Router#",
      "device_type": "cisco_ios",
      "host": "192.168.1.1"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## 快速开始

### 场景1：简单查询（最常用）

**需求**：查询设备版本信息

```python
import requests

response = requests.post(
    "http://localhost:9000/device/exec",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin123"
        },
        "command": "show version"
    }
)

job_id = response.json()["data"]["id"]
print(f"任务ID: {job_id}")
```

**说明**：只需提供连接参数和命令，其他参数使用默认值。

### 场景2：配置推送（需要保存）

**需求**：配置接口并保存

```python
response = requests.post(
    "http://localhost:9000/device/exec",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin123"
        },
        "config": [
            "interface GigabitEthernet0/1",
            " description Test",
            " no shutdown"
        ],
        "driver_args": {
            "save": True,              # 保存配置
            "exit_config_mode": True   # 退出配置模式
        }
    }
)
```

**说明**：配置操作建议设置 `save: true` 以保存配置。

### 场景3：慢速设备优化

**需求**：操作响应慢的设备，需要增加超时时间

```python
response = requests.post(
    "http://localhost:9000/device/exec",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "username": "admin",
            "password": "admin123",
            "timeout": 60              # 连接超时增加到60秒
        },
        "command": "show running-config",
        "driver_args": {
            "read_timeout": 120,       # 读取超时120秒
            "delay_factor": 3          # 延迟因子3（慢速设备）
        },
        "ttl": 600                     # 任务超时600秒
    }
)
```

**说明**：慢速设备需要增加各种超时参数。

## 参数详解

### connection_args（连接参数）

所有操作必需，用于建立设备连接。

**必需参数**：
| 参数 | 类型 | 描述 | 示例 |
|------|------|------|------|
| device_type | string | 设备类型 | `cisco_ios`, `juniper_junos`, `arista_eos` |
| host | string | 设备IP地址 | `192.168.1.1` |
| username | string | 登录用户名 | `admin` |
| password | string | 登录密码 | `password123` |

**可选参数**：
| 参数 | 类型 | 默认值 | 使用场景 |
|------|------|--------|----------|
| port | integer | 22 | 非标准SSH端口 |
| timeout | integer | 30 | 连接超时时间（秒），慢速网络可增大 |
| secret | string | - | 特权模式密码（enable密码） |
| enable_mode | boolean | true | 配置操作是否进入特权模式 |

> **提示**：不同驱动的 `connection_args` 可能有额外参数，详见各驱动文档。

### driver_args（驱动参数）

驱动特定参数，根据驱动类型和操作类型不同。**大多数场景无需指定**，使用默认值即可。

**何时需要指定**：
- 慢速设备：增加 `read_timeout`、`delay_factor`
- 配置操作：设置 `save`、`exit_config_mode`
- 特殊需求：参考各驱动文档

**各驱动常用参数**：

**Netmiko**（SSH设备）：
```json
{
  "read_timeout": 60,        // 读取超时（慢速设备）
  "delay_factor": 2,         // 延迟因子（慢速设备）
  "save": true,              // 配置操作后保存
  "exit_config_mode": true   // 配置操作后退出配置模式
}
```

**NAPALM**（跨厂商）：
```json
{
  "optional_args": {
    "secret": "enable_password"  // 特权模式密码
  }
}
```

**PyEAPI**（Arista专用）：
```json
{
  "transport": "https",      // 传输协议
  "port": 443,               // API端口
  "verify": false            // SSL验证
}
```

> **详细参数说明**：请参考各驱动文档（[Netmiko](../drivers/netmiko.md)、[NAPALM](../drivers/napalm.md)、[PyEAPI](../drivers/pyeapi.md)、[Paramiko](../drivers/paramiko.md)）

### options

全局选项，控制任务执行行为。全局选项直接写在请求体根级别。

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| queue_strategy | string | 自动选择 | 队列策略：`pinned`（SSH长连接，连接复用）或 `fifo`（HTTP短连接）。Netmiko/NAPALM默认`pinned`，PyEAPI默认`fifo` |
| ttl | integer | 300（批量600） | 任务超时时间（秒）。单设备操作默认300秒，批量操作默认600秒 |
| parsing | object | null | 输出解析配置（TextFSM/TTP等） |
| rendering | object | null | 模板渲染配置（Jinja2等） |
| webhook | object | null | Webhook回调配置 |

**队列策略选择建议**：
- **`pinned`**：适合SSH/Telnet长连接（Netmiko、NAPALM），支持连接复用，提升性能
- **`fifo`**：适合HTTP/HTTPS无状态连接（PyEAPI），每次新建连接

## 响应模型

### SubmitJobResponse

任务提交响应（单设备操作）。

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "job_123456",
    "status": "queued",
    "queue": "pinned_192.168.1.1"
  }
}
```

### BatchSubmitJobResponse

批量任务提交响应。

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "succeeded": [
      {
        "id": "job_123456",
        "status": "queued",
        "queue": "pinned_192.168.1.1",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "failed": [
      "192.168.1.3",
      "192.168.1.5"
    ]
  }
}
```

**说明**：
- `succeeded`：成功提交的任务列表（`JobInResponse` 对象）
- `failed`：失败设备的host列表（字符串数组）

### ConnectionTestResponse

连接测试响应。

```json
{
  "code": 200,
  "message": "Connection test completed",
  "data": {
    "success": true,
    "connection_time": 2.5,
    "error_message": null,
    "device_info": {
      "prompt": "Router#",
      "device_type": "cisco_ios",
      "host": "192.168.1.1"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

## 批量操作

批量设备操作支持对多个设备执行相同操作，适用于大规模网络运维场景。

### 批量查询操作

```python
# 批量查询设备状态
response = requests.post(
    "http://localhost:9000/device/bulk",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "devices": [
            {"host": "192.168.1.1", "username": "admin", "password": "admin123"},
            {"host": "192.168.1.2", "username": "admin", "password": "admin123"},
            {"host": "192.168.1.3", "username": "admin", "password": "admin123"}
        ],
        "connection_args": {
            "device_type": "cisco_ios",
            "timeout": 30
        },
        "command": "show interfaces status"
    }
)

result = response.json()
data = result['data']
print(f"成功: {len(data['succeeded']) if data['succeeded'] else 0}")
print(f"失败: {len(data['failed']) if data['failed'] else 0}")

# 处理失败设备
if data.get('failed'):
    print(f"失败设备: {data['failed']}")
```

### 混合厂商批量操作

```python
# 混合厂商设备批量查询
response = requests.post(
    "http://localhost:9000/device/bulk",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "devices": [
            {"host": "192.168.1.1", "device_type": "cisco_ios"},
            {"host": "192.168.1.2", "device_type": "cisco_nxos"},
            {"host": "192.168.1.3", "device_type": "juniper_junos"}
        ],
        "connection_args": {
            "username": "admin",
            "password": "admin123",
            "timeout": 60
        },
        "command": "show version"
    }
)
```

### 批量配置操作

```python
# 批量推送配置
response = requests.post(
    "http://localhost:9000/device/bulk",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "driver": "netmiko",
        "devices": [
            {"host": "192.168.1.1"},
            {"host": "192.168.1.2"},
            {"host": "192.168.1.3"}
        ],
        "connection_args": {
            "device_type": "cisco_ios",
            "username": "admin",
            "password": "admin123",
            "secret": "enable_password"
        },
        "config": [
            "interface range GigabitEthernet0/1-10",
            "description User Ports",
            "switchport mode access",
            "switchport access vlan 200",
            "no shutdown"
        ],
        "driver_args": {
            "exit_config_mode": True,
            "enter_config_mode": True,
            "cmd_verify": True
        },
        "queue_strategy": "pinned",
        "ttl": 600
    }
)
```

### 批量操作响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "succeeded": [
      {
        "id": "job_123456",
        "status": "queued",
        "queue": "pinned_192.168.1.1"
      }
    ],
    "failed": [
      "192.168.1.3"
    ]
  }
}
```

**说明**：
- `succeeded`：成功提交的任务对象列表，每个对象包含任务ID、状态等信息
- `failed`：失败设备的host地址列表（字符串数组），失败原因需要查询任务状态获取

### 批量操作最佳实践

1. **设备分组策略**：按厂商或地理位置分组，批次大小建议10-50台设备
2. **错误处理**：实现重试机制，记录详细错误信息
3. **性能优化**：使用设备绑定队列，并行处理多个设备
4. **监控告警**：实时监控操作状态，设置失败率告警

## 设备连接测试

### 支持的驱动类型

#### Netmiko (SSH)

**基础连接测试**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 30
  }
}
```

**完整参数示例**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password",
    "port": 22,
    "timeout": 60,
    "keepalive": 30,
    "global_delay_factor": 2,
    "fast_cli": false,
    "verbose": true
  }
}
```

#### NAPALM (跨厂商)

**连接测试示例**:
```json
{
  "driver": "napalm",
  "connection_args": {
    "device_type": "eos",
    "hostname": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "timeout": 60,
    "optional_args": {
      "port": 22,
      "secret": "enable_password",
      "transport": "ssh"
    }
  }
}
```

**Cisco IOS 示例**:
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
  }
}
```

#### PyEAPI (Arista专用)

**连接测试示例**:
```json
{
  "driver": "pyeapi",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "transport": "https",
    "port": 443,
    "timeout": 30
  }
}
```

#### Paramiko (Linux服务器)

**基础连接测试**:
```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password",
    "port": 22,
    "timeout": 30.0
  }
}
```

**密钥认证示例**:
```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "key_filename": "/path/to/private_key",
    "passphrase": "your_key_passphrase",
    "port": 22
  }
}
```

### 连接参数说明

**Netmiko 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| device_type | string | - | 设备类型 (cisco_ios, cisco_nxos, juniper_junos, arista_eos) |
| host | string | - | 设备IP地址 |
| username | string | - | 用户名 |
| password | string | - | 密码 |
| secret | string | - | 特权模式密码 |
| port | integer | 22 | SSH端口 |
| timeout | integer | 20 | 连接超时时间 |
| keepalive | integer | 60 | 保活时间 |
| global_delay_factor | float | 1 | 全局延迟因子 |
| fast_cli | boolean | false | 快速CLI模式 |
| verbose | boolean | false | 详细输出 |

**NAPALM 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| device_type | string | - | 设备类型 (ios, iosxr, junos, eos, nxos) |
| hostname | string | - | 设备IP地址 |
| username | string | - | 用户名 |
| password | string | - | 密码 |
| timeout | integer | 60 | 连接超时时间 |
| optional_args | object | {} | 可选参数 |

**PyEAPI 参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| host | string | - | 设备IP地址 |
| username | string | - | 用户名 |
| password | string | - | 密码 |
| transport | string | https | 传输协议 (http/https) |
| port | integer | 443 | 端口号 |
| timeout | integer | 30 | 连接超时时间 |

### 常见错误

**连接超时**：
```json
{
  "code": 200,
  "message": "Connection test failed",
  "data": {
    "success": false,
    "error_message": "Connection timeout after 30 seconds"
  }
}
```

**认证失败**：
```json
{
  "code": 200,
  "message": "Connection test failed",
  "data": {
    "success": false,
    "error_message": "Authentication failed"
  }
}
```

> **提示**：连接测试是同步操作，立即返回结果，无需查询任务状态。

## 最佳实践

> **详细的最佳实践指南请参考**：[API最佳实践](./api-best-practices.md)

### 快速提示

- **驱动选择**: Netmiko（通用SSH）、NAPALM（跨厂商）、PyEAPI（Arista专用）、Paramiko（Linux服务器）
- **队列策略**: 通常无需指定，系统会根据驱动自动选择
- **错误处理**: 实现重试机制，记录详细错误信息
- **任务跟踪**: 使用 `/job` 接口查询任务状态，或使用webhook回调

## 注意事项

1. **认证必需**: 所有API请求都需要API Key认证（支持Query参数、Header或Cookie三种方式）
2. **异步处理**: 设备操作是异步的，需要查询任务状态获取结果（连接测试是同步的）
3. **连接参数**: 确保设备连接参数正确，特别是用户名和密码
4. **超时设置**: 根据网络环境调整连接超时时间，慢速设备需要增加超时参数
5. **队列管理**: 系统会自动选择队列策略，通常无需手动指定
6. **批量操作**: 建议批次大小控制在10-50台设备，避免系统过载

---

## 相关文档

- [API概览](./api-overview.md) - 了解所有API接口
- [驱动选择](../drivers/index.md) - 选择合适的驱动类型
- [API最佳实践](./api-best-practices.md) - 使用建议和优化技巧 