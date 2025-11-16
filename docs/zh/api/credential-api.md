# Vault 凭据管理 API

## 概述

Vault 凭据管理 API (`/credential/vault/*`) 提供对 HashiCorp Vault 的完整 CRUD 操作，用于安全地存储和管理网络设备的用户名和密码。

!!! tip "为什么使用 Vault？"
    - **安全性**：密码不直接暴露在 API 请求中
    - **集中管理**：统一管理所有设备凭据
    - **版本控制**：支持凭据版本历史和回滚
    - **元数据管理**：支持标签、描述等元数据
    - **权限控制**：通过 Vault 的权限策略控制访问

## API 端点

### POST /credential/vault/test

测试 Vault 连接状态。

**请求示例**：

```bash
curl -X POST "http://localhost:9000/credential/vault/test" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**响应示例**：

```json
{
  "code": 200,
  "message": "Vault connection successful",
  "data": {
    "success": true,
    "vault_version": "1.15.0",
    "sealed": false,
    "standby": false
  }
}
```

### POST /credential/vault/create

创建或更新 Vault 中的凭据。

**请求参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 凭据在 Vault 中的路径（如：`sites/hq/admin`） |
| `username` | string | ✅ | 用户名 |
| `password` | string | ✅ | 密码 |
| `username_key` | string | ❌ | 用户名字段名（默认：`username`） |
| `password_key` | string | ❌ | 密码字段名（默认：`password`） |
| `metadata` | object | ❌ | 自定义元数据（用于标签、描述等） |

**请求示例**：

```bash
curl -X POST "http://localhost:9000/credential/vault/create" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin",
    "username": "admin",
    "password": "admin123",
    "username_key": "username",
    "password_key": "password",
    "metadata": {
      "description": "HQ site admin credentials",
      "site": "hq",
      "role": "admin"
    }
  }'
```

**响应示例**：

```json
{
  "code": 200,
  "message": "Credential created/updated successfully",
  "data": {
    "success": true,
    "path": "sites/hq/admin",
    "message": "Credential created/updated successfully"
  }
}
```

!!! note "路径格式说明"
    - 路径不需要包含 `secret/data/` 前缀，系统会自动添加
    - 支持层级结构，如：`sites/hq/admin`、`devices/core/backup`
    - 路径区分大小写

### POST /credential/vault/read

读取 Vault 中的凭据（默认不显示密码）。

**请求参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 凭据路径 |
| `show_password` | boolean | ❌ | 是否显示密码（默认：`false`） |

**请求示例**：

```bash
curl -X POST "http://localhost:9000/credential/vault/read" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin",
    "show_password": false
  }'
```

**响应示例**（`show_password: false`）：

```json
{
  "code": 200,
  "message": "Credential read successfully",
  "data": {
    "path": "sites/hq/admin",
    "username": "admin",
    "password": "***"
  }
}
```

**响应示例**（`show_password: true`）：

```json
{
  "code": 200,
  "message": "Credential read successfully",
  "data": {
    "path": "sites/hq/admin",
    "username": "admin",
    "password": "admin123"
  }
}
```

### POST /credential/vault/delete

删除 Vault 中的凭据。

**请求参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 凭据路径 |

**请求示例**：

```bash
curl -X POST "http://localhost:9000/credential/vault/delete" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin"
  }'
```

**响应示例**：

```json
{
  "code": 200,
  "message": "Credential deleted successfully",
  "data": {
    "success": true,
    "path": "sites/hq/admin"
  }
}
```

### POST /credential/vault/list

列出 Vault 中的凭据路径。

**请求参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path_prefix` | string | ❌ | 路径前缀过滤（如：`sites/hq`） |
| `recursive` | boolean | ❌ | 是否递归列出（默认：`false`） |

**请求示例**：

```bash
curl -X POST "http://localhost:9000/credential/vault/list" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path_prefix": "sites",
    "recursive": true
  }'
```

**响应示例**：

```json
{
  "code": 200,
  "message": "Credentials listed successfully",
  "data": {
    "paths": [
      "sites/hq/admin",
      "sites/hq/readonly",
      "sites/branch1/admin",
      "sites/branch2/readonly"
    ],
    "count": 4
  }
}
```

### POST /credential/vault/metadata

获取凭据元数据（版本信息、创建时间、更新时间、自定义元数据）。

!!! info "Vault 原生 API"
    此 API 使用 Vault 原生的 metadata API (`GET /v1/{mount}/metadata/{path}`)，返回完整的元数据信息。

**请求参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `path` | string | ✅ | 凭据路径 |

**请求示例**：

```bash
curl -X POST "http://localhost:9000/credential/vault/metadata" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin"
  }'
```

**响应示例**：

```json
{
  "code": 200,
  "message": "Metadata retrieved successfully",
  "data": {
    "path": "sites/hq/admin",
    "current_version": 2,
    "created_time": "2024-01-15T08:30:15.123456789Z",
    "updated_time": "2024-01-20T10:45:30.987654321Z",
    "custom_metadata": {
      "description": "HQ site admin credentials",
      "site": "hq",
      "role": "admin"
    },
    "versions": {
      "1": {
        "created_time": "2024-01-15T08:30:15.123456789Z",
        "deletion_time": ""
      },
      "2": {
        "created_time": "2024-01-20T10:45:30.987654321Z",
        "deletion_time": ""
      }
    }
  }
}
```

!!! tip "元数据用途"
    - **生命周期管理**：通过版本信息追踪凭据变更历史
    - **标签管理**：通过自定义元数据实现标签分类
    - **审计追踪**：通过创建/更新时间记录操作历史

### POST /credential/vault/batch-read

批量读取凭据（应用层封装，适用于批量操作场景）。

!!! note "应用层封装"
    此 API 是应用层封装，内部循环调用单个读取 API。虽然减少了客户端 API 调用次数，但 Vault 端仍为多次调用。

**请求参数**：

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `paths` | array | ✅ | 凭据路径列表（1-100个） |
| `show_password` | boolean | ❌ | 是否显示密码（默认：`false`） |

**请求示例**：

```bash
curl -X POST "http://localhost:9000/credential/vault/batch-read" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "paths": [
      "sites/hq/admin",
      "sites/branch1/admin",
      "devices/core/backup"
    ],
    "show_password": false
  }'
```

**响应示例**：

```json
{
  "code": 200,
  "message": "Batch read completed: 3 succeeded, 0 failed",
  "data": {
    "succeeded": [
      {
        "path": "sites/hq/admin",
        "username": "admin",
        "password": "***"
      },
      {
        "path": "sites/branch1/admin",
        "username": "admin",
        "password": "***"
      },
      {
        "path": "devices/core/backup",
        "username": "backup",
        "password": "***"
      }
    ],
    "failed": [],
    "total": 3,
    "success_count": 3,
    "failed_count": 0
  }
}
```

## 在设备操作中使用 Vault 凭据

在设备操作 API 中，可以使用 `credential_ref` 参数引用 Vault 中存储的凭据，而不需要在请求中直接传递用户名和密码。

### 支持的格式

`credential_ref` 支持三种格式：

1. **字符串格式**（最简单）：
   ```json
   {
     "credential_ref": "sites/hq/admin"
   }
   ```

2. **字典格式**：
   ```json
   {
     "credential_ref": {
       "path": "sites/hq/admin"
     }
   }
   ```

3. **完整格式**：
   ```json
   {
     "credential_ref": {
       "provider": "vault",
       "path": "sites/hq/admin",
       "username_key": "username",
       "password_key": "password"
     }
   }
   ```

### 使用示例

**使用 Vault 凭据执行设备操作**：

```bash
curl -X POST "http://localhost:9000/device/execute" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "credential_ref": "sites/hq/admin"
    },
    "command": "show version"
  }'
```

**批量操作中使用 Vault 凭据**：

```bash
curl -X POST "http://localhost:9000/device/bulk" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios"
    },
    "devices": [
      {
        "host": "192.168.1.1",
        "credential_ref": "sites/hq/admin"
      },
      {
        "host": "192.168.1.2",
        "credential_ref": "sites/branch1/admin"
      }
    ],
    "command": "show version"
  }'
```

!!! tip "credential_ref 优先级"
    - 如果同时提供了 `credential_ref` 和 `username`/`password`，`credential_ref` 优先
    - 系统会从 Vault 读取凭据并注入到 `connection_args` 中
    - 凭据会被缓存，避免重复读取

## 路径命名建议

为了便于管理，建议使用层级路径结构：

```
sites/{site_name}/{role}          # 站点凭据
devices/{device_type}/{purpose}    # 设备类型凭据
environments/{env}/{role}          # 环境凭据
```

**示例**：
- `sites/hq/admin` - HQ 站点管理员凭据
- `sites/hq/readonly` - HQ 站点只读凭据
- `devices/core/backup` - 核心设备备份凭据
- `environments/prod/admin` - 生产环境管理员凭据

## 错误处理

### 常见错误

| HTTP 状态码 | 错误码 | 说明 | 解决方案 |
|------------|--------|------|----------|
| 403 | - | 访问被拒绝 | 检查 Vault token 权限 |
| 404 | - | 凭据不存在 | 检查路径是否正确 |
| 503 | - | Vault 服务不可用 | 检查 Vault 服务状态 |
| 500 | - | 服务器内部错误 | 查看日志排查问题 |

### 错误响应示例

```json
{
  "code": -1,
  "message": "Access denied to path 'sites/hq/admin'",
  "data": null
}
```

## 最佳实践

### 1. 凭据管理

- **使用层级路径**：按站点、环境、角色组织凭据
- **添加元数据**：使用 `metadata` 字段添加描述、标签等信息
- **定期轮换**：定期更新密码并创建新版本

### 2. 安全建议

- **最小权限**：为不同应用创建不同权限的 Vault token
- **密码隐藏**：默认不显示密码，仅在必要时使用 `show_password: true`
- **审计日志**：通过元数据 API 追踪凭据变更历史

### 3. 性能优化

- **批量读取**：使用 `batch-read` API 减少 API 调用次数
- **凭据缓存**：系统会自动缓存凭据，避免重复读取
- **路径规划**：合理规划路径结构，便于批量操作

## 相关文档

- [设备操作 API](./device-api.md) - 在设备操作中使用 `credential_ref`
- [API 示例](./api-examples.md) - 完整使用示例
- [配置指南](../reference/configuration-guide.md) - Vault 配置方法


