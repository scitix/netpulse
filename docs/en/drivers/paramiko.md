# Paramiko Driver

## Overview

The Paramiko driver is used to manage Linux servers (Ubuntu, CentOS, Debian, etc.) through SSH protocol, supporting command execution, file transfer, configuration management, and other operations.

> **Note**: This document focuses on Paramiko driver parameters and usage. For general API endpoints (`POST /device/execute`), request format, response format, etc., see [Device Operation API](../api/device-api.md).

## Driver Features

- **Connection Method**: SSH protocol
- **Use Cases**: Linux server management
- **Recommended Queue Strategy**: `fifo` (short connection, suitable for long-running tasks)
- **Core Features**: Command execution, file transfer, sudo privilege management, SSH proxy/jump host

## Difference Between command and config

For Linux servers, both `command` and `config` can execute any Linux command. The difference lies in **feature support**:

| Feature | `command` | `config` |
|---------|----------|---------|
| Execute commands | ✅ Can execute any Linux command | ✅ Can execute any Linux command |
| Auto sudo | ❌ Not supported (need to manually add `sudo` in command) | ✅ Supported (automatically adds `sudo -S` via `driver_args.sudo: true`) |
| Auto input sudo password | ❌ Not supported | ✅ Supported (via `driver_args.sudo_password`) |
| File transfer | ✅ Supported (via `driver_args.file_transfer`) | ❌ Not supported |

**Usage Recommendations**:
- **Need file transfer**: Use `command` + `driver_args.file_transfer`
- **Need auto sudo handling**: Use `config` + `driver_args.sudo: true`
- **Normal command execution**: Both work, choose based on whether you need the above features

## Quick Reference

### Required Parameters

**connection_args (Connection Parameters)**:
- `host` (**Required**): Server IP address or domain name
- `username` (**Required**): SSH login username
- Authentication method (**At least one required**):
  - `password`: Password authentication
  - `key_filename`: Private key file path
  - `pkey`: Private key content (PEM format string)

**Operation Parameters** (**Choose one**):
- `command`: Execute command (string or array)
- `config`: Execute configuration command (string or array)

### Common Optional Parameters

**connection_args**:
- `port`: SSH port (default 22)
- `timeout`: Connection timeout (default 30 seconds)
- `host_key_policy`: Host key verification policy (default "auto_add")

**driver_args**:
- `timeout`: Command execution timeout (seconds)
- `sudo`: Whether to auto-add sudo (only config supports)
- `sudo_password`: Sudo password (only config supports)
- `file_transfer`: File transfer operation (only command supports)

## Usage Examples (From Simple to Complex)

### Example 1: Simplest Command Execution (Password Authentication)

Execute a single command to view system information.

**Required Fields**:
- `driver`: Driver name
- `connection_args.host`: Server address
- `connection_args.username`: SSH username
- `connection_args.password`: SSH password
- `command`: Command to execute

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "command": "uname -a"
}
```

**Notes**:
- Uses password authentication, the simplest method
- Default SSH port 22
- Default connection timeout 30 seconds
- Default host key policy is "auto_add" (auto accept)

---

### Example 1a: Execute Command Using Vault Credentials

Execute commands using credentials stored in Vault, avoiding directly passing passwords in requests.

**Required Fields**:
- `connection_args.credential_ref`: Vault credential path (replaces username/password)

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "credential_ref": "servers/prod/admin"
  },
  "command": "uname -a"
}
```

**Notes**:
- Use `credential_ref` to reference credentials stored in Vault
- System will automatically read username and password from Vault
- More secure, avoids exposing passwords in requests
- See: [Vault Credential Management API](../api/credential-api.md)

---

### Example 2: Execute Multiple Commands

Execute multiple commands at once to batch collect system information.

**Required Fields**: Same as Example 1

**Optional Fields**:
- `driver_args.timeout`: Command execution timeout

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "command": [
    "uname -a",
    "df -h",
    "free -m",
    "uptime"
  ],
  "driver_args": {
    "timeout": 30.0
  }
}
```

**Notes**:
- `command` can be a string (single command) or array (multiple commands)
- Set `timeout` to avoid long-running commands timing out

---

### Example 3: Using Key File Authentication

Use SSH private key file for authentication, suitable for production environments.

**Required Fields**:
- `connection_args.key_filename`: Private key file path (replaces password)

**Optional Fields**:
- `connection_args.passphrase`: Private key password (if key is encrypted)

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "key_filename": "/path/to/private_key",
    "passphrase": "your_key_passphrase"
  },
  "command": "df -h"
}
```

**Notes**:
- Using key file authentication is more secure
- If the private key file is encrypted, provide `passphrase`
- Suitable for local development environments, ensure key file path is accessible

---

### Example 4: Using Key Content Authentication (Recommended for Container Environments)

Use private key content (PEM format string) for authentication, suitable for container environments.

**Required Fields**:
- `connection_args.pkey`: Private key content (replaces password or key_filename)

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "pkey": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----",
    "passphrase": "your_key_passphrase"
  },
  "command": "free -m"
}
```

**Notes**:
- **Recommended for container environments** to avoid mounting key files
- Private key content must be a complete PEM format string
- If the key is encrypted, provide `passphrase`

---

### Example 5: Using config to Execute Commands Requiring sudo

Use `config` to automatically handle sudo privileges without manually adding sudo to commands.

**Required Fields**:
- `config`: Command to execute (replaces command)

**Optional Fields**:
- `driver_args.sudo`: Whether to auto-add sudo
- `driver_args.sudo_password`: Sudo password

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "config": "ls /root",
  "driver_args": {
    "sudo": true,
    "sudo_password": "your_sudo_password"
  }
}
```

**Notes**:
- When using `config`, setting `sudo: true` automatically adds `sudo -S` before the command
- If sudo requires a password, providing `sudo_password` will automatically input it
- More convenient than manually adding `sudo` to commands

---

### Example 6: Execute Multiple Commands Requiring sudo

Batch execute commands requiring sudo privileges.

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "config": [
    "echo 'server.example.com' > /etc/hostname",
    "systemctl restart hostname",
    "chmod 644 /etc/hostname"
  ],
  "driver_args": {
    "sudo": true,
    "sudo_password": "your_sudo_password",
    "timeout": 60.0
  }
}
```

**Notes**:
- Multiple commands execute sequentially, each automatically gets sudo added
- Set reasonable `timeout` to avoid long-running operations timing out

---

### Example 7: File Upload

Upload local file to remote server.

**Required Fields**:
- `command`: Must be set to `["__FILE_TRANSFER__"]`
- `driver_args.file_transfer.operation`: Operation type ("upload")
- `driver_args.file_transfer.local_path`: Local file path
- `driver_args.file_transfer.remote_path`: Remote file path

**Optional Fields**:
- `driver_args.file_transfer.resume`: Whether to enable resume for interrupted transfers
- `driver_args.file_transfer.chunk_size`: Transfer chunk size (default 32768 bytes)
- `driver_args.file_transfer.timeout`: Transfer timeout

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "command": ["__FILE_TRANSFER__"],
  "driver_args": {
    "file_transfer": {
      "operation": "upload",
      "local_path": "/local/file.txt",
      "remote_path": "/remote/file.txt",
      "resume": false,
      "chunk_size": 32768
    }
  }
}
```

**Notes**:
- File transfer must use `command`, cannot use `config`
- `local_path` is the file path on the NetPulse server
- `remote_path` is the file path on the target server
- For large file transfers, enable `resume: true` to support resuming interrupted transfers

---

### Example 8: File Download

Download file from remote server to local.

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "command": ["__FILE_TRANSFER__"],
  "driver_args": {
    "file_transfer": {
      "operation": "download",
      "local_path": "/local/file.txt",
      "remote_path": "/remote/file.txt",
      "resume": true,
      "chunk_size": 32768,
      "timeout": 300.0
    }
  }
}
```

**Notes**:
- Set `operation` to "download" for download
- For large file downloads, enable `resume: true`
- Set reasonable `timeout` to avoid large file transfer timeouts

---

### Example 9: Connect via SSH Proxy/Jump Host

Access internal network servers through a jump host.

**Required Fields**:
- `connection_args.proxy_host`: Proxy server address

**Optional Fields**:
- `connection_args.proxy_port`: Proxy server SSH port (default 22)
- `connection_args.proxy_username`: Proxy server username (can be omitted if same as target server)
- `connection_args.proxy_password`: Proxy server password
- `connection_args.proxy_key_filename`: Proxy server private key file path

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.200",
    "username": "admin",
    "password": "your_password",
    "proxy_host": "192.168.1.100",
    "proxy_username": "admin",
    "proxy_password": "your_proxy_password",
    "proxy_port": 22
  },
  "command": "uname -a"
}
```

**Notes**:
- First connect to proxy server, then connect to target server through proxy
- Proxy server and target server can use different authentication methods
- Suitable for accessing internal network servers or scenarios requiring jump hosts

---

### Example 10: Execute Command with Environment Variables

Set custom environment variables when executing commands.

**Optional Fields**:
- `driver_args.environment`: Environment variables dictionary

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "command": "echo $CUSTOM_VAR && echo $PATH",
  "driver_args": {
    "environment": {
      "CUSTOM_VAR": "custom_value",
      "PATH": "/usr/local/bin:/usr/bin:/bin"
    }
  }
}
```

**Notes**:
- Environment variables set via `environment` only take effect for this command execution
- Can override system environment variables (such as PATH)

---

### Example 11: Using PTY (Pseudo Terminal)

Use PTY for commands requiring interactive terminal.

**Optional Fields**:
- `driver_args.get_pty`: Whether to use pseudo terminal

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "password": "your_password"
  },
  "command": "sudo -S command",
  "driver_args": {
    "get_pty": true,
    "timeout": 30.0
  }
}
```

**Notes**:
- PTY is used for commands requiring interactive terminal
- When using `config` + `sudo: true`, if `sudo_password` is provided, PTY is automatically enabled

---

### Example 12: Complete Configuration Example (Production Environment)

Complete example including all common configurations.

```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "pkey": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
    "port": 22,
    "timeout": 30.0,
    "host_key_policy": "reject"
  },
  "config": [
    "systemctl restart nginx",
    "systemctl status nginx"
  ],
  "driver_args": {
    "sudo": true,
    "sudo_password": "your_sudo_password",
    "timeout": 60.0,
    "get_pty": false,
    "environment": {
      "LANG": "en_US.UTF-8"
    }
  },
  "options": {
    "queue_strategy": "fifo",
    "ttl": 600
  }
}
```

**Notes**:
- Uses key content authentication (suitable for container environments)
- Set `host_key_policy: "reject"` for better security (recommended for production)
- Uses `config` + `sudo` to automatically handle privileges
- Set reasonable timeout and TTL values

---

## Parameter Details

### connection_args (Connection Parameters)

Used to establish SSH connection to Linux server.

#### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `host` | string | Server address (IP or domain name) |
| `username` | string | SSH login username |

#### Authentication Parameters (At least one required)

| Parameter | Type | Description |
|-----------|------|-------------|
| `password` | string | Password authentication (simplest, suitable for testing) |
| `key_filename` | string | Private key file path (suitable for local environments) |
| `pkey` | string | Private key content (PEM format string, **recommended for container environments**) |

**Authentication Method Selection Recommendations**:
- **Development/Testing Environment**: Use `password` for quick testing
- **Local Production Environment**: Use `key_filename` for better security
- **Container Environment**: Use `pkey` to avoid mounting key files

#### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `port` | integer | 22 | SSH port |
| `timeout` | float | 30.0 | Connection timeout (seconds) |
| `passphrase` | string | - | Private key password (if key is encrypted) |
| `host_key_policy` | string | "auto_add" | Host key verification policy (see below) |
| `look_for_keys` | boolean | true | Whether to auto-discover keys in `~/.ssh/` directory |
| `allow_agent` | boolean | false | Whether to allow SSH agent |
| `compress` | boolean | false | Whether to enable compression |
| `banner_timeout` | float | - | Banner timeout (seconds) |
| `auth_timeout` | float | - | Authentication timeout (seconds) |

#### SSH Proxy/Jump Host Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `proxy_host` | string | - | Proxy server address (enables proxy when set) |
| `proxy_port` | integer | 22 | Proxy server SSH port |
| `proxy_username` | string | - | Proxy server username (can be omitted if same as target server) |
| `proxy_password` | string | - | Proxy server password |
| `proxy_key_filename` | string | - | Proxy server private key file path |
| `proxy_pkey` | string | - | Proxy server private key content (PEM format) |
| `proxy_passphrase` | string | - | Proxy server private key password |

#### host_key_policy Parameter Description

`host_key_policy` is used to control SSH connection host key verification policy to prevent man-in-the-middle attacks.

| Value | Description | Use Cases |
|-------|-------------|-----------|
| `"auto_add"` | Automatically accept unknown host keys | Development/testing environments, convenient for first connection |
| `"reject"` | Reject unknown hosts or mismatched keys | **Recommended for production**, most secure |
| `"warning"` | Warn about unknown hosts but still allow connection | Balance between security and convenience |

**Usage Recommendations**:
- **Development/Testing Environment**: Use `"auto_add"` for quick testing
- **Production Environment**: Use `"reject"` and pre-verify host keys via `ssh-keyscan`
- **Container Environment**: Since known_hosts cannot be persisted, usually use `"auto_add"` or `"warning"`

---

### driver_args (Driver Parameters)

Different parameters are used based on operation type (command or config).

#### command Operation Parameters (ParamikoSendCommandArgs)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | float | - | Command execution timeout (seconds), None means no timeout |
| `get_pty` | boolean | false | Whether to use pseudo-terminal (PTY) for interactive commands |
| `environment` | dict | - | Environment variables dictionary |
| `bufsize` | integer | -1 | Buffer size, -1 means use system default |
| `file_transfer` | object | - | File transfer operation (see below) |

#### config Operation Parameters (ParamikoSendConfigArgs)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | float | - | Configuration execution timeout (seconds) |
| `get_pty` | boolean | false | Whether to use pseudo-terminal |
| `sudo` | boolean | false | Whether to use sudo execution (automatically adds `sudo -S`) |
| `sudo_password` | string | - | Sudo password (if sudo is enabled and password is required) |
| `environment` | dict | - | Environment variables dictionary |

**sudo Usage Notes**:
- After setting `sudo: true`, the system automatically adds `sudo -S` before each command
- If sudo requires a password, providing `sudo_password` will automatically input it
- When using sudo, if `sudo_password` is provided, PTY is automatically enabled

#### File Transfer Parameters (ParamikoFileTransferOperation)

Only used in `command` operations, set via `driver_args.file_transfer`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `operation` | string | - | Operation type: `"upload"` (upload) or `"download"` (download) |
| `local_path` | string | - | Local file path (path on NetPulse server) |
| `remote_path` | string | - | Remote file path (path on target server) |
| `resume` | boolean | false | Whether to enable resume for interrupted transfers |
| `chunk_size` | integer | 32768 | Transfer chunk size (bytes, default 32KB) |
| `timeout` | float | - | Transfer timeout (seconds), None means no timeout |

**File Transfer Notes**:
- Must use `command` operation, cannot use `config`
- `command` must be set to `["__FILE_TRANSFER__"]`
- For large file transfers, enable `resume: true` to support resuming interrupted transfers
- Adjust `chunk_size` based on network conditions (default 32KB)

---

### options (Global Options)

Global options common to all drivers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `queue_strategy` | string | "fifo" | Queue strategy (Paramiko defaults to fifo) |
| `ttl` | integer | - | Task result retention time (seconds) |

**Paramiko Recommended Configuration**:
- `queue_strategy`: Use `"fifo"` (default), suitable for long-running tasks
- `ttl`: Set based on operation complexity, query operations recommend 300 seconds, configuration operations recommend 600 seconds

---

## Supported Key Formats

- ✅ **RSA**: Supports RSA keys
- ✅ **ED25519**: Supports ED25519 keys
- ❌ **DSA**: Does not support DSA keys (deprecated)

---

## Best Practices

### 1. Authentication Method Selection

- **Production Environment**: Recommend using key authentication (`pkey` or `key_filename`) and set `host_key_policy: "reject"` for security
- **Development/Testing Environment**: Can use password authentication, set `host_key_policy: "auto_add"` for quick testing
- **Container Environment**: Use `pkey` (key content) to avoid mounting key files

### 2. Connection Management

- **Timeout Settings**: Set `timeout` reasonably based on task complexity to avoid premature termination
- **Proxy Connection**: Use `proxy_host` parameter when accessing internal network servers through jump hosts
- **Queue Strategy**: Paramiko uses FIFO strategy (short connection), suitable for long-running tasks

### 3. Command Execution

- **Sudo Operations**: Use `config` + `sudo: true` when sudo privileges are needed, more convenient than manually adding sudo
- **Environment Variables**: Set command execution environment via `environment` parameter
- **Interactive Commands**: Set `get_pty: true` when interaction is needed

### 4. File Transfer

- **Large File Transfer**: Enable `resume: true` to support resuming interrupted transfers
- **Transfer Speed**: Adjust `chunk_size` based on network conditions (default 32KB)
- **Timeout Control**: Set reasonable `timeout` value for large file transfers

### 5. Error Handling

- **Connection Failure**: Check network connection, SSH service status, authentication information
- **Command Execution Failure**: Check `exit_status` and `error` fields for detailed error information
- **File Transfer Failure**: Check file path, permissions, disk space

---

## Use Cases

✅ **Recommended For**:
- System monitoring and inspection
- Configuration management and deployment
- Software deployment and updates
- Troubleshooting and repair
- Batch server management
- File transfer and synchronization

⚠️ **Notes**:
- Use FIFO strategy (short connection) for long-running tasks
- Interactive commands recommend using non-interactive alternatives (e.g., `rm -f` instead of `rm -i`)
- Production environments recommend using key authentication and strict host key verification

---

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Check network connection and server reachability
   - Adjust `timeout` parameter
   - Verify SSH service is running normally

2. **Authentication Failure**
   - Verify username and password
   - Check key file path and format
   - Confirm key permissions (recommend 600)
   - Verify if key requires password (`passphrase`)

3. **Host Key Verification Failure**
   - Development environment: Use `host_key_policy: "auto_add"`
   - Production environment: Use `host_key_policy: "reject"` and pre-verify host keys

4. **Command Execution Failure**
   - Check `exit_status` and `error` fields
   - Check command syntax and permissions
   - Verify environment variable settings

5. **File Transfer Failure**
   - Check file path and permissions
   - Verify disk space
   - Confirm network connection stability
   - Enable resume for large file transfers

### Debug Commands

```bash
# Test SSH connection
ssh admin@192.168.1.100

# Test key authentication
ssh -i /path/to/key admin@192.168.1.100

# Test proxy connection
ssh -J proxy_user@proxy_host admin@target_host

# View connection logs
tail -f /var/log/netpulse.log
```

---

## Related Documents

- [Device Operation API](../api/device-api.md) - Device operation core interface
- [Driver Selection](./index.md) - Learn about other drivers
- [API Examples](../api/api-examples.md) - More usage examples
