# API 概览

## 简介

NetPulse 提供统一的API接口来管理各种网络设备。本文档介绍NetPulse支持的所有API接口及其基本用法。

## 基础信息

### API 端点
- **基础URL**: `http://localhost:9000`
- **API版本**: v0.2
- **认证方式**: API Key (X-API-KEY Header)

### 认证
所有API请求都需要API Key认证，支持以下三种方式：

1. **Header方式**（推荐）：
   ```
   X-API-KEY: your-api-key-here
   ```

2. **Query参数方式**：
   ```
   ?X-API-KEY=your-api-key-here
   ```

3. **Cookie方式**：
   ```
   X-API-KEY=your-api-key-here
   ```

### 响应格式
所有API响应都采用统一的JSON格式：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

**响应码说明**：
- `code: 200` - 请求成功
- `code: -1` - 请求失败（错误详情在 `message` 和 `data` 中）

## 完整API端点列表

NetPulse 提供以下API端点，所有端点都需要API Key认证。

> **⭐推荐**：优先使用 `/device/execute` 统一接口，它自动识别操作类型，使用更简单。

| HTTP方法 | 端点路径 | 功能说明 | 详细文档 |
|---------|---------|---------|---------|
| **设备操作** | | | |
| `POST` | `/device/execute` | 设备操作（查询/配置）⭐推荐 | [设备操作 API](./device-api.md) |
| `POST` | `/device/bulk` | 批量设备操作 | [设备操作 API](./device-api.md) |
| `POST` | `/device/test-connection` | 设备连接测试 | [设备操作 API](./device-api.md) |
| **模板操作** | | | |
| `POST` | `/template/render` | 模板渲染（自动识别引擎） | [模板操作 API](./template-api.md) |
| `POST` | `/template/render/{name}` | 使用指定引擎渲染 | [模板操作 API](./template-api.md) |
| `POST` | `/template/parse` | 模板解析（自动识别解析器） | [模板操作 API](./template-api.md) |
| `POST` | `/template/parse/{name}` | 使用指定解析器解析 | [模板操作 API](./template-api.md) |
| **任务管理** | | | |
| `GET` | `/job` | 查询任务状态和结果 | [任务管理 API](./job-api.md) |
| `DELETE` | `/job` | 取消任务 | [任务管理 API](./job-api.md) |
| `GET` | `/worker` | 查询Worker状态 | [任务管理 API](./job-api.md) |
| `DELETE` | `/worker` | 删除Worker | [任务管理 API](./job-api.md) |
| `GET` | `/health` | 系统健康检查 | [任务管理 API](./job-api.md) |

## API 分类

### 1. 设备操作 API
设备操作 API 提供设备查询、配置和连接测试功能，支持所有驱动类型。

**主要端点**：
- `POST /device/execute` - 统一设备操作（自动识别查询/配置）
- `POST /device/bulk` - 批量设备操作
- `POST /device/test-connection` - 设备连接测试

**支持的驱动**：
- Netmiko (SSH) - 通用SSH连接
- NAPALM (跨厂商) - 标准化接口
- PyEAPI (Arista专用) - HTTP/HTTPS API
- Paramiko (SSH) - Linux服务器管理

详细说明请参考：[设备操作 API](./device-api.md)

### 2. 模板操作 API
提供配置模板渲染和命令输出解析功能。

**主要端点**：
- `POST /template/render` - 模板渲染
- `POST /template/parse` - 输出解析

**支持的引擎**：
- Jinja2 - 配置模板渲染
- TextFSM - 命令输出解析
- TTP - 配置解析

详细说明请参考：[模板操作 API](./template-api.md)

### 3. 任务管理 API
提供任务状态查询、任务取消和Worker管理功能。

**主要端点**：
- `GET /job` - 查询任务状态
- `DELETE /job` - 取消任务
- `GET /worker` - 查询Worker状态
- `DELETE /worker` - 删除Worker
- `GET /health` - 系统健康检查

详细说明请参考：[任务管理 API](./job-api.md)

## 支持的驱动类型

### Netmiko (SSH)
- **设备类型**: cisco_ios, cisco_nxos, juniper_junos, arista_eos, huawei, hp_comware 等。完整支持的设备类型列表请查看 [Netmiko 平台支持文档](https://github.com/ktbyers/netmiko/blob/develop/PLATFORMS.md)
- **连接方式**: SSH
- **特点**: 通用性强，支持大多数主流网络设备

### NAPALM (跨厂商)
- **设备类型**: ios, iosxr, junos, eos, nxos 等
- **连接方式**: SSH/API
- **特点**: 标准化接口，跨厂商兼容

### PyEAPI (Arista专用)
- **设备类型**: Arista EOS
- **连接方式**: HTTP/HTTPS API
- **特点**: 原生API支持，性能优异

### Paramiko (Linux服务器)
- **设备类型**: Linux服务器（Ubuntu、CentOS、Debian等）
- **连接方式**: SSH
- **特点**: 原生SSH，支持文件传输、代理连接、sudo等，可以用于端侧相关的自动化

## 队列策略

NetPulse 支持两种队列策略，系统会根据驱动类型自动选择合适的策略：

### 设备绑定队列 (pinned)
- **适用驱动**：Netmiko、NAPALM（SSH/Telnet长连接）
- **特点**：每个设备专用Worker，连接复用
- **优势**：减少连接建立开销，提升性能
- **使用场景**：频繁操作同一设备，需要保持连接状态

### FIFO队列 (fifo)
- **适用驱动**：PyEAPI（HTTP/HTTPS无状态连接）、Paramiko（Linux服务器）
- **特点**：先进先出，每次新建连接
- **优势**：简单高效，适合无状态操作
- **使用场景**：HTTP API调用、长时间运行任务，无需保持连接状态

> **提示**：如果不指定 `queue_strategy`，系统会根据驱动类型自动选择（Netmiko/NAPALM → `pinned`，PyEAPI/Paramiko → `fifo`）

## 核心参数快速参考

### 必需参数

**connection_args（连接参数）** - 所有操作必需：
```json
{
  "device_type": "cisco_ios",  // 设备类型
  "host": "192.168.1.1",      // 设备IP
  "username": "admin",         // 用户名
  "password": "password"        // 密码
}
```

**操作参数** - 二选一：
- `command`：查询操作（如 `"show version"`）
- `config`：配置操作（如 `["interface Gi0/1", "description Test"]`）

### 可选参数

**driver_args（驱动参数）** - 根据驱动类型不同，详见各驱动文档：
```json
{
  "read_timeout": 60,      // Netmiko专用
  "delay_factor": 2        // Netmiko专用
}
```

**options（全局选项）** - 控制任务行为：
```json
{
  "queue_strategy": "pinned",  // 队列策略（自动选择，通常无需指定）
  "ttl": 300,                  // 超时时间（秒）
  "parsing": {...},            // 输出解析（可选）
  "webhook": {...}             // 回调通知（可选）
}
```

> **快速上手**：大多数场景只需提供 `connection_args` 和 `command`/`config`，其他参数使用默认值即可。

## 错误处理

### 错误响应格式
所有错误响应都采用统一格式：
```json
{
  "code": -1,
  "message": "错误描述",
  "data": "具体错误信息或错误详情对象"
}
```

**HTTP状态码**：
- `200` - 请求成功
- `201` - 资源创建成功（任务提交）
- `400` - 请求参数错误
- `403` - 认证失败（API Key无效或缺失）
- `404` - 资源不存在
- `422` - 参数验证失败
- `500` - 服务器内部错误

> **注意**：即使HTTP状态码为200，如果业务逻辑失败，响应中的 `code` 字段仍为 `-1`。

## 快速上手建议

### 参数选择指南

1. **必需参数**：`connection_args` + `command`/`config` 即可开始使用
2. **队列策略**：通常无需指定，系统会根据驱动自动选择
3. **驱动参数**：大多数场景使用默认值，特殊需求再调整
4. **超时设置**：默认值已足够，慢速设备或批量操作再增加

### 常见场景

- **简单查询**：只需 `connection_args` + `command`
- **配置推送**：添加 `driver_args.save: true` 保存配置
- **慢速设备**：增加 `timeout`、`read_timeout`、`delay_factor`
- **批量操作**：使用 `/device/bulk` 接口，系统自动优化

> **详细指南**：查看 [API最佳实践](./api-best-practices.md) 了解更多优化技巧

## 快速开始

### 1. 检查系统健康
```bash
curl -H "X-API-KEY: your-key" http://localhost:9000/health
```

### 2. 测试设备连接
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-key" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password"
    }
  }' \
  http://localhost:9000/device/test-connection
```

### 3. 执行简单查询
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-API-KEY: your-key" \
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
```

## 下一步

- [设备操作 API](./device-api.md) - 设备操作核心接口
- [驱动选择](../drivers/index.md) - 选择合适的驱动
- [API最佳实践](./api-best-practices.md) - 使用建议和优化技巧 