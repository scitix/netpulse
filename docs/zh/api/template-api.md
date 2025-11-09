# 模板操作 API

## 概述

模板操作 API 提供配置模板渲染和命令输出解析功能，支持多种模板引擎和解析器。

## API 端点

### POST /template/render

渲染配置模板。

**功能说明**:
- 支持多种模板引擎 (Jinja2, Mako, etc.)
- 支持变量替换和条件逻辑
- 支持模板文件引用

**请求示例**:

```bash
curl -X POST "http://localhost:9000/template/render" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "jinja2",
    "template": "interface {{ interface_name }}\n description {{ description }}",
    "context": {
      "interface_name": "GigabitEthernet0/1",
      "description": "Test Interface"
    }
  }'
```

**请求模型**:

```json
{
  "name": "jinja2|mako|string",
  "template": "interface {{ interface_name }}\n description {{ description }}",
  "context": {
    "interface_name": "GigabitEthernet0/1",
    "description": "Test Interface"
  }
}
```

### POST /template/render/{name}

使用指定模板引擎渲染。

**请求示例**:

```bash
curl -X POST "http://localhost:9000/template/render/jinja2" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "interface {{ interface_name }}\n description {{ description }}",
    "context": {
      "interface_name": "GigabitEthernet0/1",
      "description": "Test Interface"
    }
  }'
```

### POST /template/parse

解析命令输出。

**功能说明**:
- 支持多种解析器 (TextFSM, TTP, etc.)
- 支持结构化数据提取
- 支持自定义解析模板

**请求示例**:

```bash
curl -X POST "http://localhost:9000/template/parse" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "textfsm",
    "template": "file:///templates/show_version.textfsm",
    "context": "Cisco IOS Software, Version 15.2(4)S7..."
  }'
```

**请求模型**:

```json
{
  "name": "textfsm|ttp|regex",
  "template": "file:///templates/show_version.textfsm",
  "context": "Cisco IOS Software, Version 15.2(4)S7..."
}
```

### POST /template/parse/{name}

使用指定解析器解析。

**请求示例**:

```bash
curl -X POST "http://localhost:9000/template/parse/textfsm" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "file:///templates/show_version.textfsm",
    "context": "Cisco IOS Software, Version 15.2(4)S7..."
  }'
```

## 响应模型

### BaseResponse

模板操作响应。

```json
{
  "code": 200,
  "message": "success",
  "data": "interface GigabitEthernet0/1\n description Test Interface"
}
```

### 解析响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "version": "15.2(4)S7",
      "hostname": "Router1",
      "uptime": "2 weeks, 3 days, 4 hours, 30 minutes"
    }
  ]
}
```

## 支持的模板引擎

### Jinja2

最常用的模板引擎，语法简洁强大。

**模板示例**:

```jinja2
interface {{ interface_name }}
 description {{ description }}
{% if ip_address %}
 ip address {{ ip_address }} {{ subnet_mask }}
{% endif %}
{% if vlan %}
 switchport access vlan {{ vlan }}
{% endif %}
 no shutdown
```

**使用示例**:

```python
import requests

# 渲染Jinja2模板
response = requests.post(
    "http://localhost:9000/template/render/jinja2",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "template": "interface {{ interface_name }}\n description {{ description }}",
        "context": {
            "interface_name": "GigabitEthernet0/1",
            "description": "Test Interface"
        }
    }
)

rendered_config = response.json()["data"]
print(rendered_config)
```

### Mako

高性能模板引擎，适合复杂模板。

**模板示例**:

```mako
interface ${interface_name}
 description ${description}
% if ip_address:
 ip address ${ip_address} ${subnet_mask}
% endif
 no shutdown
```

### String Template

简单字符串替换，适合基础场景。

**模板示例**:

```
interface {interface_name}
 description {description}
 ip address {ip_address} {subnet_mask}
 no shutdown
```

## 支持的解析器

### TextFSM

Cisco开发的文本解析器，适合网络设备输出。

**模板示例**:

```
Value VERSION ([\d.()]+)
Value HOSTNAME (\S+)
Value UPTIME (.+)

Start
  ^Cisco IOS Software, Version ${VERSION} -> Continue
  ^.*uptime is ${UPTIME} -> Continue
  ^${HOSTNAME}# -> Record
```

**使用示例**:

```python
# 解析show version输出
response = requests.post(
    "http://localhost:9000/template/parse/textfsm",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "template": "file:///templates/show_version.textfsm",
        "context": """
Cisco IOS Software, Version 15.2(4)S7
Router1 uptime is 2 weeks, 3 days, 4 hours, 30 minutes
Router1#
        """
    }
)

parsed_data = response.json()["data"]
print(parsed_data)
```

### TTP

Template Text Parser，支持多种格式。

**模板示例**:

```
interface {{ interface_name }}
 description {{ description }}
 ip address {{ ip_address }} {{ subnet_mask }}
 no shutdown
```

### Regex

正则表达式解析，适合简单场景。

**使用示例**:

```python
# 使用正则表达式解析
response = requests.post(
    "http://localhost:9000/template/parse/regex",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "template": r"Version (\d+\.\d+\([^)]+\))",
        "context": "Cisco IOS Software, Version 15.2(4)S7"
    }
)
```

## 模板文件管理

### 文件路径格式

支持多种文件路径格式：

- **绝对路径**: `/templates/interface.j2`
- **相对路径**: `templates/interface.j2`
- **文件协议**: `file:///templates/interface.j2`

### 模板目录结构

```
templates/
├── cisco/
│   ├── interface.j2
│   ├── vlan.j2
│   └── routing.j2
├── juniper/
│   ├── interface.j2
│   └── routing.j2
└── common/
    ├── show_version.textfsm
    └── show_interfaces.textfsm
```

## 使用示例

### 1. 配置模板渲染

```python
import requests

# 渲染接口配置模板
template_data = {
    "name": "jinja2",
    "template": """
interface {{ interface_name }}
 description {{ description }}
{% if ip_address %}
 ip address {{ ip_address }} {{ subnet_mask }}
{% endif %}
{% if vlan %}
 switchport access vlan {{ vlan }}
{% endif %}
 no shutdown
""",
    "context": {
        "interface_name": "GigabitEthernet0/1",
        "description": "Test Interface",
        "ip_address": "192.168.1.10",
        "subnet_mask": "255.255.255.0",
        "vlan": 100
    }
}

response = requests.post(
    "http://localhost:9000/template/render",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json=template_data
)

config = response.json()["data"]
print(config)
```

### 2. 命令输出解析

```python
# 解析show interfaces输出
parse_data = {
    "name": "textfsm",
    "template": "file:///templates/show_interfaces.textfsm",
    "context": """
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/1    192.168.1.1    YES NVRAM  up                    up
GigabitEthernet0/2    unassigned     YES unset  down                  down
"""
}

response = requests.post(
    "http://localhost:9000/template/parse",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json=parse_data
)

interfaces = response.json()["data"]
for interface in interfaces:
    print(f"Interface: {interface['interface']}, Status: {interface['status']}")
```

### 3. 批量配置生成

```python
# 批量生成接口配置
interfaces = [
    {"name": "GigabitEthernet0/1", "description": "LAN1", "ip": "192.168.1.1"},
    {"name": "GigabitEthernet0/2", "description": "LAN2", "ip": "192.168.2.1"},
    {"name": "GigabitEthernet0/3", "description": "WAN", "ip": "10.0.0.1"}
]

configs = []
for interface in interfaces:
    response = requests.post(
        "http://localhost:9000/template/render/jinja2",
        headers={
            "X-API-KEY": "your_key",
            "Content-Type": "application/json"
        },
        json={
            "template": """
interface {{ name }}
 description {{ description }}
 ip address {{ ip }} 255.255.255.0
 no shutdown
""",
            "context": interface
        }
    )
    configs.append(response.json()["data"])

# 合并所有配置
full_config = "\n".join(configs)
print(full_config)
```

## 最佳实践

### 1. 模板设计

- **模块化**: 将复杂模板拆分为多个小模板
- **可重用**: 设计通用的模板组件
- **参数化**: 使用变量而不是硬编码值

### 2. 错误处理

```python
try:
    response = requests.post(url, json=template_data)
    response.raise_for_status()
    result = response.json()["data"]
except requests.exceptions.RequestException as e:
    print(f"模板渲染失败: {e}")
except KeyError as e:
    print(f"响应格式错误: {e}")
```

### 3. 性能优化

- **缓存模板**: 避免重复加载相同模板
- **批量处理**: 一次处理多个模板
- **异步处理**: 对于大量模板使用异步处理

### 4. 安全考虑

- **输入验证**: 验证模板变量
- **路径限制**: 限制模板文件访问路径
- **权限控制**: 控制模板访问权限

## 注意事项

1. **模板语法**: 不同模板引擎语法不同
2. **文件路径**: 确保模板文件路径正确
3. **变量类型**: 注意变量类型匹配
4. **错误处理**: 处理模板渲染和解析错误
5. **性能影响**: 复杂模板可能影响性能

---

## 相关文档

- [API概览](./api-overview.md) - 了解所有API接口
- [设备操作 API](./device-api.md) - 设备操作核心接口 