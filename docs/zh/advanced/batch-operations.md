# 批量操作指南

NetPulse 支持批量操作，便于统一管理多台网络设备。

## 功能概述

- 多设备同命令/配置批量下发
- 单设备多命令/配置下发
- 支持部分并发、超时等参数

## 批量操作API

### 1. 多设备同命令批量下发

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "devices": [
      {"host": "192.168.1.1", "username": "admin", "password": "pass"},
      {"host": "192.168.1.2", "username": "admin", "password": "pass"}
    ],
    "connection_args": {"device_type": "cisco_ios"},
    "command": "show version"
  }' \
  http://localhost:9000/device/bulk
```

### 2. 单设备多命令批量下发

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {"host": "192.168.1.1", "username": "admin", "password": "pass", "device_type": "cisco_ios"},
    "command": ["show version", "show interfaces"]
  }' \
  http://localhost:9000/device/execute
```

### 3. 多设备同配置批量下发

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "devices": [
      {"host": "192.168.1.1", "username": "admin", "password": "pass"},
      {"host": "192.168.1.2", "username": "admin", "password": "pass"}
    ],
    "connection_args": {"device_type": "cisco_ios"},
    "config": ["interface Loopback0", "ip address 1.1.1.1 255.255.255.255"]
  }' \
  http://localhost:9000/device/bulk
```

## 支持的参数
- driver: 设备驱动（如 netmiko、napalm、pyeapi）
- devices: 设备列表（多设备批量必填）
- connection_args: 连接参数模板
- command/config: 命令或配置，二选一
- options: 可选参数（如ttl、queue_strategy等，详见API文档）

## 注意事项
- 不支持"多命令多设备矩阵"批量（即每台设备下发不同命令/配置）。
- 并发、重试、进度监控等仅支持部分参数，详见API文档。
- 复杂分组、worker分配、详细进度推送等为建议/规划功能，当前未实现。

## 性能建议（建议/规划）
- 合理设置并发数和超时时间，避免设备压力过大。
- 建议分批处理大规模设备，监控系统资源。
- 可结合模板系统批量生成配置。

## 最佳实践
- 按设备类型/地理位置分组批量操作。
- 命令/配置下发前建议先小范围验证。
- 记录批量操作日志，便于追溯。

---

如需详细参数说明，请参考 API 文档或联系开发者。 