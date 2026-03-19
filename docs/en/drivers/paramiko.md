# Paramiko Driver

Paramiko manages Linux servers via SSH, supporting command execution, file transfer, sudo, and proxy/jump-host connections.

> This page covers Paramiko-specific parameters. For endpoint shapes and response format, see [Device Operation API](../api/device-api.md).

## At a Glance

- **Protocol**: SSH
- **Supported targets**: Linux servers (Ubuntu, CentOS, Debian, etc.)
- **Recommended queue**: `fifo`
- **Unique features**: File transfer, sudo automation, SSH jump-host proxy, script execution, interactive expect

## `command` vs `config`

Both execute Linux commands. The differences:

| Feature | `command` | `config` |
|---------|----------|---------|
| Execute commands | ✅ | ✅ |
| Auto sudo | ✅ via `driver_args.sudo: true` | ✅ via `driver_args.sudo: true` |
| `stop_on_error` | ❌ | ✅ (stops on first failed command) |
| Script execution | ✅ via `driver_args.script_content` | ❌ |
| Expect/interactive | ✅ via `driver_args.expect_map` | ❌ |

File transfer uses a **top-level `file_transfer` field** (not `command` or `config`):
```json
{"file_transfer": {"operation": "upload", "remote_path": "/remote/path"}}
```

## Examples

### Password authentication
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

### Multiple commands
```json
{
  "driver": "paramiko",
  "connection_args": {"host": "192.168.1.100", "username": "admin", "password": "your_password"},
  "command": ["uname -a", "df -h", "free -m", "uptime"],
  "driver_args": {"timeout": 30.0}
}
```

### Key file authentication
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

### Key content authentication (recommended for containers)
```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.100",
    "username": "admin",
    "pkey": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
  },
  "command": "free -m"
}
```

### sudo
```json
{
  "driver": "paramiko",
  "connection_args": {"host": "192.168.1.100", "username": "admin", "password": "your_password"},
  "config": ["echo 'server.example.com' > /etc/hostname", "systemctl restart hostname"],
  "driver_args": {"sudo": true, "sudo_password": "your_sudo_password", "stop_on_error": true}
}
```

`sudo` also works with `command` mode. `stop_on_error` is `config`-only.

### File upload
```json
{
  "driver": "paramiko",
  "connection_args": {"host": "192.168.1.100", "username": "admin", "password": "your_password"},
  "file_transfer": {
    "operation": "upload",
    "local_path": "/local/file.txt",
    "remote_path": "/remote/file.txt",
    "resume": false,
    "chunk_size": 32768
  }
}
```

`local_path` is on the NetPulse server; `remote_path` is on the target server.

### File download
```json
{
  "driver": "paramiko",
  "connection_args": {"host": "192.168.1.100", "username": "admin", "password": "your_password"},
  "file_transfer": {
    "operation": "download",
    "local_path": "/local/file.txt",
    "remote_path": "/remote/file.txt",
    "resume": true
  }
}
```

### SSH proxy / jump host
```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "192.168.1.200",
    "username": "admin",
    "password": "your_password",
    "proxy_host": "192.168.1.100",
    "proxy_username": "admin",
    "proxy_password": "your_proxy_password"
  },
  "command": "uname -a"
}
```

### Environment variables
```json
{
  "driver": "paramiko",
  "connection_args": {"host": "192.168.1.100", "username": "admin", "password": "your_password"},
  "command": "echo $CUSTOM_VAR",
  "driver_args": {
    "environment": {"CUSTOM_VAR": "custom_value", "PATH": "/usr/local/bin:/usr/bin:/bin"}
  }
}
```

### PTY (pseudo terminal)
```json
{
  "driver": "paramiko",
  "connection_args": {"host": "192.168.1.100", "username": "admin", "password": "your_password"},
  "command": "sudo -S some-interactive-command",
  "driver_args": {"get_pty": true, "timeout": 30.0}
}
```

When `sudo: true` + `sudo_password` is set, PTY is enabled automatically.

### Production example
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
  "config": ["systemctl restart nginx", "systemctl status nginx"],
  "driver_args": {
    "sudo": true,
    "sudo_password": "your_sudo_password",
    "timeout": 60.0,
    "environment": {"LANG": "en_US.UTF-8"}
  },
  "queue_strategy": "fifo",
  "ttl": 600
}
```

## Parameters

### connection_args

**Required:**

| Parameter | Description |
|-----------|-------------|
| `host` | Server IP or hostname |
| `username` | SSH username |
| `password` / `key_filename` / `pkey` | Authentication (at least one required) |

**Authentication options:**

| Method | Parameter | Best for |
|--------|-----------|----------|
| Password | `password` | Dev/testing |
| Key file | `key_filename` | Local production |
| Key content | `pkey` (PEM string) | Container environments |

**Optional:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `port` | 22 | SSH port |
| `timeout` | 30.0 | Connection timeout (seconds) |
| `passphrase` | | Private key passphrase |
| `host_key_policy` | `"auto_add"` | `"auto_add"` / `"reject"` / `"warning"` |
| `look_for_keys` | true | Auto-discover keys in `~/.ssh/` |
| `allow_agent` | false | Allow SSH agent |
| `compress` | false | Enable compression |
| `banner_timeout` | | Banner timeout (seconds) |
| `auth_timeout` | | Auth timeout (seconds) |
| `keepalive` | | Keepalive interval (seconds); enables persistent connection mode when set |

**Proxy/jump-host:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `proxy_host` | | Jump host address (enables proxy when set) |
| `proxy_port` | 22 | Jump host SSH port |
| `proxy_username` | | Jump host username |
| `proxy_password` | | Jump host password |
| `proxy_key_filename` | | Jump host key file |
| `proxy_pkey` | | Jump host key content (PEM) |
| `proxy_passphrase` | | Jump host key passphrase |

**`host_key_policy` values:**

| Value | Description |
|-------|-------------|
| `"auto_add"` | Accept unknown keys (dev/test) |
| `"reject"` | Reject unknown/mismatched keys (production) |
| `"warning"` | Warn but allow |

### driver_args — `command` operations

| Parameter | Default | Description |
|-----------|---------|-------------|
| `timeout` | None | Command timeout (seconds); None = no timeout |
| `get_pty` | false | Use pseudo-terminal |
| `environment` | | Environment variables dict |
| `sudo` | false | Prepend `sudo -S` to command |
| `sudo_password` | | Sudo password (auto-input when set) |
| `bufsize` | -1 | Buffer size (-1 = system default) |
| `script_content` | | Script content to execute via stdin (alternative to `command`) |
| `script_interpreter` | `"bash"` | Interpreter for `script_content` (bash, sh, python, etc.) |
| `working_directory` | | Working directory for execution |
| `expect_map` | | Dict of expected prompts → responses (e.g. `{"[Y/n]": "y"}`) |

### driver_args — `config` operations

| Parameter | Default | Description |
|-----------|---------|-------------|
| `timeout` | None | Execution timeout (seconds) |
| `get_pty` | false | Use pseudo-terminal |
| `sudo` | false | Prepend `sudo -S` to each command |
| `sudo_password` | | Sudo password (auto-input when set) |
| `environment` | | Environment variables dict |
| `stop_on_error` | true | Stop on first failed command |

### file_transfer field (top-level)

Set at the top level of the request (not inside `driver_args`). Supported by Paramiko and Netmiko.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `operation` | | `"upload"` or `"download"` |
| `remote_path` | | File path on target server |
| `local_path` | | File path on NetPulse server |
| `resume` | false | Resume interrupted transfers |
| `chunk_size` | 32768 | Transfer chunk size (bytes) |
| `overwrite` | true | Overwrite if destination exists |
| `recursive` | false | Transfer directory recursively |
| `sync_mode` | `"full"` | `"full"` always transfers; `"hash"` skips if MD5 matches |
| `verify_file` | true | Verify integrity after transfer |
| `chmod` | | Set permissions after upload (e.g. `"0755"`) |

**Supported key types:** RSA ✅, ED25519 ✅, DSA ❌ (deprecated)
