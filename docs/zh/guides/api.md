# RESTful API 指南

NetPulse 提供用于网络设备操作的 RESTful API。所有操作都是异步的，并通过 Redis Queue (RQ) 进行任务状态和结果的管理。

## API 概览

NetPulse 提供三大类别的 API：

- **设备操作 API** (命令执行和配置应用)
- **模板操作 API**（模板渲染和解析）
- **任务管理 API**（任务和 Worker 管理）

此外，NetPulse 针对大规模设备操作提供了 API 的批量形式（Batch API），参见下文。

## 认证

所有 API 请求都需要通过 API Key 进行认证。支持以下三种方式：

- **Query 参数**: `?X-API-KEY=your_api_key`
- **Header**: `X-API-KEY: your_api_key`
- **Cookie**: `X-API-KEY=your_api_key`

## 统一设备操作 API

### POST /device/execute

统一的设备操作端点，自动识别操作类型（查询或配置）。

**请求体**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123",
    "port": 22,
    "timeout": 30
  },
  "command": "show version",
  "driver_args": {
    "read_timeout": 30,
    "delay_factor": 2
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300,
    "parsing": {
      "name": "textfsm",
      "template": "file:///templates/show_version.textfsm"
    }
  }
}
```

**配置操作示例**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123"
  },
  "config": "interface GigabitEthernet0/1\n description Test Interface",
  "driver_args": {
    "save": true,
    "exit_config_mode": true
  },
  "options": {
    "queue_strategy": "pinned",
    "ttl": 300
  }
}
```

### POST /device/bulk

批量设备操作端点，支持对多个设备执行相同操作。

**请求体**:
```json
{
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
    "timeout": 30,
    "keepalive": 120
  },
  "command": "show version",
  "options": {
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

### POST /device/test-connection

测试设备连接状态。

**请求体**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123"
  }
}
```

## 传统 API 端点

### POST /pull/

执行命令并获取输出（向后兼容）。

**请求体**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123"
  },
  "command": "show version",
  "queue_strategy": "pinned"
}
```

### POST /push/

推送配置到设备（向后兼容）。

**请求体**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123"
  },
  "config": "interface GigabitEthernet0/1\n description Test",
  "enable_mode": true
}
```

### POST /pull/batch

批量执行命令（向后兼容）。

### POST /push/batch

批量推送配置（向后兼容）。

## 模板操作 API

### POST /template/render

渲染模板。

**请求体**:
```json
{
  "name": "jinja2",
  "template": "interface {{ interface_name }}\n description {{ description }}",
  "context": {
    "interface_name": "GigabitEthernet0/1",
    "description": "Test Interface"
  }
}
```

### POST /template/parse

解析命令输出。

**请求体**:
```json
{
  "name": "textfsm",
  "template": "file:///templates/show_version.textfsm",
  "context": "Cisco IOS Software, Version 15.2(4)S7..."
}
```

## 任务管理 API

### GET /job

获取任务列表。

**查询参数**:
- `id`: 获取指定ID的任务
- `queue`: 按队列名称过滤
- `status`: 按状态过滤
- `node`: 按节点名称过滤
- `host`: 按主机名称过滤

### DELETE /job

删除任务。

**查询参数**:
- `id`: 删除指定ID的任务
- `queue`: 按队列名称过滤
- `host`: 按主机名称过滤

### GET /worker

获取Worker列表。

**查询参数**:
- `queue`: 按队列名称过滤
- `node`: 按节点名称过滤
- `host`: 按主机名称过滤

### DELETE /worker

删除Worker。

**查询参数**:
- `name`: 删除指定名称的Worker
- `queue`: 按队列名称过滤
- `node`: 按节点名称过滤
- `host`: 按主机名称过滤

### GET /health

健康检查。

## 响应格式

所有 API 响应都遵循统一的格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

### 任务提交响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "job_123456",
    "status": "queued",
    "submitted_at": "2024-01-01T12:00:00+08:00"
  }
}
```

### 批量任务响应

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "succeeded": [
      {
        "id": "job_123456",
        "status": "queued",
        "submitted_at": "2024-01-01T12:00:00+08:00"
      }
    ],
    "failed": [
      "192.168.1.100: Connection failed"
    ]
  }
}
```

## 错误处理

API 使用标准的 HTTP 状态码：

- `200`: 成功
- `201`: 任务已创建
- `400`: 请求参数错误
- `403`: 认证失败
- `404`: 资源不存在
- `500`: 服务器内部错误

错误响应格式：

```json
{
  "code": -1,
  "message": "错误描述",
  "data": "详细错误信息"
}
```

## 工作流示例

### 1. 执行命令并解析结果

```bash
# 1. 提交任务
curl -X POST "http://localhost:9000/device/execute" \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "admin123"
    },
    "command": "show version",
    "options": {
      "parsing": {
        "name": "textfsm",
        "template": "file:///templates/show_version.textfsm"
      }
    }
  }'

# 2. 查询任务状态
curl -X GET "http://localhost:9000/job?id=job_123456" \
  -H "X-API-KEY: your_api_key"
```

### 2. 批量配置推送

```bash
# 1. 提交批量任务
curl -X POST "http://localhost:9000/device/bulk" \
  -H "X-API-KEY: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "devices": [
      {"host": "192.168.1.1", "username": "admin", "password": "admin123"},
      {"host": "192.168.1.2", "username": "admin", "password": "admin123"}
    ],
    "connection_args": {
      "device_type": "cisco_ios"
    },
    "config": "interface GigabitEthernet0/1\n description Test Interface"
  }'

# 2. 监控任务进度
curl -X GET "http://localhost:9000/job?queue=pinned" \
  -H "X-API-KEY: your_api_key"
```

## 向后兼容性

NetPulse 保持了与旧版本 API 的兼容性：

- `/pull/` 和 `/push/` 端点仍然可用
- `/pull/batch` 和 `/push/batch` 端点仍然可用
- 旧的请求格式仍然被支持

建议使用新的统一 API 端点 `/device/execute` 和 `/device/bulk` 以获得更好的性能和功能。

## API 参考
