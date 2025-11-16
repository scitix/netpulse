# Vault Credential Management API

## Overview

The Vault Credential Management API (`/credential/vault/*`) provides complete CRUD operations for HashiCorp Vault, used to securely store and manage usernames and passwords for network devices.

!!! tip "Why Use Vault?"
    - **Security**: Passwords are not directly exposed in API requests
    - **Centralized Management**: Unified management of all device credentials
    - **Version Control**: Supports credential version history and rollback
    - **Metadata Management**: Supports tags, descriptions, and other metadata
    - **Access Control**: Controls access through Vault's permission policies

## API Endpoints

### POST /credential/vault/test

Test Vault connection status.

**Request Example**:

```bash
curl -X POST "http://localhost:9000/credential/vault/test" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response Example**:

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

Create or update credentials in Vault.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | ✅ | Credential path in Vault (e.g., `sites/hq/admin`) |
| `username` | string | ✅ | Username |
| `password` | string | ✅ | Password |
| `username_key` | string | ❌ | Username field name (default: `username`) |
| `password_key` | string | ❌ | Password field name (default: `password`) |
| `metadata` | object | ❌ | Custom metadata (for tags, descriptions, etc.) |

**Request Example**:

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

**Response Example**:

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

!!! note "Path Format"
    - Paths do not need to include the `secret/data/` prefix, the system will add it automatically
    - Supports hierarchical structure, e.g., `sites/hq/admin`, `devices/core/backup`
    - Paths are case-sensitive

### POST /credential/vault/read

Read credentials from Vault (password hidden by default).

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | ✅ | Credential path |
| `show_password` | boolean | ❌ | Whether to show password (default: `false`) |

**Request Example**:

```bash
curl -X POST "http://localhost:9000/credential/vault/read" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin",
    "show_password": false
  }'
```

**Response Example** (`show_password: false`):

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

**Response Example** (`show_password: true`):

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

Delete credentials from Vault.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | ✅ | Credential path |

**Request Example**:

```bash
curl -X POST "http://localhost:9000/credential/vault/delete" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin"
  }'
```

**Response Example**:

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

List credential paths in Vault.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path_prefix` | string | ❌ | Path prefix filter (e.g., `sites/hq`) |
| `recursive` | boolean | ❌ | Whether to list recursively (default: `false`) |

**Request Example**:

```bash
curl -X POST "http://localhost:9000/credential/vault/list" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path_prefix": "sites",
    "recursive": true
  }'
```

**Response Example**:

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

Get credential metadata (version information, creation time, update time, custom metadata).

!!! info "Vault Native API"
    This API uses Vault's native metadata API (`GET /v1/{mount}/metadata/{path}`), returning complete metadata information.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | ✅ | Credential path |

**Request Example**:

```bash
curl -X POST "http://localhost:9000/credential/vault/metadata" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "sites/hq/admin"
  }'
```

**Response Example**:

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

!!! tip "Metadata Usage"
    - **Lifecycle Management**: Track credential change history through version information
    - **Tag Management**: Implement tag classification through custom metadata
    - **Audit Trail**: Record operation history through creation/update times

### POST /credential/vault/batch-read

Batch read credentials (application-level encapsulation, suitable for batch operation scenarios).

!!! note "Application-Level Encapsulation"
    This API is an application-level encapsulation that internally loops through individual read APIs. While it reduces client API calls, Vault still receives multiple calls.

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `paths` | array | ✅ | List of credential paths (1-100) |
| `show_password` | boolean | ❌ | Whether to show password (default: `false`) |

**Request Example**:

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

**Response Example**:

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

## Using Vault Credentials in Device Operations

In device operation APIs, you can use the `credential_ref` parameter to reference credentials stored in Vault, without needing to directly pass usernames and passwords in requests.

### Supported Formats

`credential_ref` supports three formats:

1. **String Format** (simplest):
   ```json
   {
     "credential_ref": "sites/hq/admin"
   }
   ```

2. **Dictionary Format**:
   ```json
   {
     "credential_ref": {
       "path": "sites/hq/admin"
     }
   }
   ```

3. **Full Format**:
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

### Usage Examples

**Using Vault Credentials for Device Operations**:

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

**Using Vault Credentials in Batch Operations**:

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

!!! tip "credential_ref Priority"
    - If both `credential_ref` and `username`/`password` are provided, `credential_ref` takes priority
    - The system will read credentials from Vault and inject them into `connection_args`
    - Credentials are cached to avoid repeated reads

## Path Naming Recommendations

For easier management, it's recommended to use hierarchical path structures:

```
sites/{site_name}/{role}          # Site credentials
devices/{device_type}/{purpose}    # Device type credentials
environments/{env}/{role}          # Environment credentials
```

**Examples**:
- `sites/hq/admin` - HQ site admin credentials
- `sites/hq/readonly` - HQ site read-only credentials
- `devices/core/backup` - Core device backup credentials
- `environments/prod/admin` - Production environment admin credentials

## Error Handling

### Common Errors

| HTTP Status | Error Code | Description | Solution |
|------------|------------|-------------|----------|
| 403 | - | Access denied | Check Vault token permissions |
| 404 | - | Credential not found | Check if path is correct |
| 503 | - | Vault service unavailable | Check Vault service status |
| 500 | - | Internal server error | Check logs for issues |

### Error Response Example

```json
{
  "code": -1,
  "message": "Access denied to path 'sites/hq/admin'",
  "data": null
}
```

## Best Practices

### 1. Credential Management

- **Use Hierarchical Paths**: Organize credentials by site, environment, role
- **Add Metadata**: Use the `metadata` field to add descriptions, tags, etc.
- **Regular Rotation**: Regularly update passwords and create new versions

### 2. Security Recommendations

- **Least Privilege**: Create different Vault tokens with different permissions for different applications
- **Password Hiding**: Passwords are hidden by default, only use `show_password: true` when necessary
- **Audit Logging**: Track credential change history through metadata API

### 3. Performance Optimization

- **Batch Reading**: Use `batch-read` API to reduce API call count
- **Credential Caching**: System automatically caches credentials to avoid repeated reads
- **Path Planning**: Reasonably plan path structure for easier batch operations

## Related Documentation

- [Device Operation API](./device-api.md) - Using `credential_ref` in device operations
- [API Examples](./api-examples.md) - Complete usage examples
- [Configuration Guide](../reference/configuration-guide.md) - Vault configuration methods


