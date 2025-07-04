# 模板系统使用指南

NetPulse 支持 Jinja2、TextFSM、TTP 等模板格式，帮助用户快速解析和处理网络设备输出。

## 支持的模板格式
- Jinja2：通用模板引擎，支持变量替换和逻辑控制
- TextFSM：专为网络设备输出解析设计
- TTP：基于YAML的模板解析器

## 应用场景
- 设备配置生成
- 命令输出解析
- 报表生成

## Jinja2 模板

### 基础用法
```jinja2
hostname: {{ device.hostname }}
interface: {{ interface.name }}
```

### API 调用示例
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "interface {{ name }}",
    "variables": {
      "name": "GigabitEthernet0/1"
    },
    "engine": "jinja2"
  }' \
  http://localhost:9000/templates/render
```

## TextFSM 模板

### 语法规则
```textfsm
Value HOSTNAME (\S+)
Value VERSION ([\d.]+)

Start
  ^.*Version ${VERSION}.* -> Continue
  ^.*${HOSTNAME}# -> Record
```

### API 调用示例
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "Value HOSTNAME (\\S+)\\nValue VERSION ([\\d.]+)\\n\\nStart\\n  ^.*Version ${VERSION}.* -> Continue\\n  ^.*${HOSTNAME}# -> Record",
    "data": "Router uptime is 2 weeks, 3 days\nVersion 17.03.01\nRouter#",
    "engine": "textfsm"
  }' \
  http://localhost:9000/templates/parse
```

## TTP 模板

### YAML格式
```yaml
---
template: |
  {{ hostname }} uptime is {{ uptime }}
  Version {{ version }}

vars:
  hostname: "Router"
  uptime: "2 weeks, 3 days"
  version: "17.03.01"
```

---

如需详细参数说明，请参考 API 文档或联系开发者。 