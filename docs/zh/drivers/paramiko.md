# Paramiko 驱动

## 概述

Paramiko 驱动用于管理Linux服务器（Ubuntu、CentOS、Debian等），通过SSH协议执行命令、传输文件、管理配置等操作。

> **注意**：本文档专注于Paramiko驱动的参数和用法。通用API端点（`POST /device/execute`）、请求格式、响应格式等，参考：[设备操作 API](../api/device-api.md)

## 驱动特点

- **连接方式**: SSH协议
- **适用场景**: Linux服务器管理
- **推荐队列策略**: `fifo`（短连接，适合长时间运行任务）
- **核心功能**: 命令执行、文件传输、sudo权限管理、SSH代理/跳板机

## command 与 config 的区别

对于Linux服务器，`command` 和 `config` 都可以执行任何Linux命令，区别在于**功能支持**：

| 功能 | `command` | `config` |
|------|----------|---------|
| 执行命令 | ✅ 可以执行任何Linux命令 | ✅ 可以执行任何Linux命令 |
| 自动sudo | ❌ 不支持（需在命令中手动添加 `sudo`） | ✅ 支持（通过 `driver_args.sudo: true` 自动添加 `sudo -S`） |
| 自动输入sudo密码 | ❌ 不支持 | ✅ 支持（通过 `driver_args.sudo_password`） |
| 文件传输 | ✅ 支持（通过 `driver_args.file_transfer`） | ❌ 不支持 |

**使用建议**：
- **需要文件传输**：使用 `command` + `driver_args.file_transfer`
- **需要自动sudo处理**：使用 `config` + `driver_args.sudo: true`
- **普通命令执行**：两者都可以，根据是否需要上述功能选择

## 快速参考

### 必选参数

**connection_args（连接参数）**：
- `host`（**必需**）：服务器IP地址或域名
- `username`（**必需**）：SSH登录用户名
- 认证方式（**至少选一种**）：
  - `password`：密码认证
  - `key_filename`：私钥文件路径
  - `pkey`：私钥内容（PEM格式字符串）

**操作参数**（**二选一**）：
- `command`：执行命令（字符串或数组）
- `config`：执行配置命令（字符串或数组）

### 常用可选参数

**connection_args**：
- `port`：SSH端口（默认22）
- `timeout`：连接超时时间（默认30秒）
- `host_key_policy`：主机密钥验证策略（默认"auto_add"）

**driver_args**：
- `timeout`：命令执行超时时间（秒）
- `sudo`：是否自动添加sudo（仅config支持）
- `sudo_password`：sudo密码（仅config支持）
- `file_transfer`：文件传输操作（仅command支持）

## 使用示例（从简单到复杂）

### 示例1：最简单的命令执行（密码认证）

执行单个命令，查看系统信息。

**必选字段**：
- `driver`：驱动名称
- `connection_args.host`：服务器地址
- `connection_args.username`：SSH用户名
- `connection_args.password`：SSH密码
- `command`：要执行的命令

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

**说明**：
- 使用密码认证，最简单的方式
- 默认使用SSH端口22
- 默认连接超时30秒
- 默认主机密钥策略为"auto_add"（自动接受）

---

### 示例1a：使用Vault凭据执行命令

使用 Vault 中存储的凭据执行命令，避免在请求中直接传递密码。

**必选字段**：
- `connection_args.credential_ref`：Vault 凭据路径（替代 username/password）

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

**说明**：
- 使用 `credential_ref` 引用 Vault 中存储的凭据
- 系统会自动从 Vault 读取用户名和密码
- 更安全，避免在请求中暴露密码
- 详见 [Vault 凭据管理 API](../api/credential-api.md)

---

### 示例2：执行多个命令

一次执行多个命令，批量获取系统信息。

**必选字段**：同示例1

**可选字段**：
- `driver_args.timeout`：命令执行超时时间

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

**说明**：
- `command` 可以是字符串（单命令）或数组（多命令）
- 设置 `timeout` 避免长时间运行的命令超时

---

### 示例3：使用密钥文件认证

使用SSH私钥文件进行认证，适合生产环境。

**必选字段**：
- `connection_args.key_filename`：私钥文件路径（替代password）

**可选字段**：
- `connection_args.passphrase`：私钥密码（如果密钥已加密）

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

**说明**：
- 使用密钥文件认证，更安全
- 如果私钥文件已加密，需要提供 `passphrase`
- 适合本地开发环境，需要确保密钥文件路径可访问

---

### 示例4：使用密钥内容认证（推荐容器环境）

使用私钥内容（PEM格式字符串）进行认证，适合容器环境。

**必选字段**：
- `connection_args.pkey`：私钥内容（替代password或key_filename）

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

**说明**：
- **推荐在容器环境中使用**，避免需要挂载密钥文件
- 私钥内容必须是完整的PEM格式字符串
- 如果私钥已加密，需要提供 `passphrase`

---

### 示例5：使用config执行需要sudo的命令

使用 `config` 自动处理sudo权限，无需在命令中手动添加sudo。

**必选字段**：
- `config`：要执行的命令（替代command）

**可选字段**：
- `driver_args.sudo`：是否自动添加sudo
- `driver_args.sudo_password`：sudo密码

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

**说明**：
- 使用 `config` 时，设置 `sudo: true` 会自动在命令前添加 `sudo -S`
- 如果sudo需要密码，提供 `sudo_password` 会自动输入
- 比手动在命令中添加 `sudo` 更方便

---

### 示例6：执行多个需要sudo的命令

批量执行需要sudo权限的命令。

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

**说明**：
- 多个命令会依次执行，每个命令都会自动添加sudo
- 设置合理的 `timeout` 避免长时间运行超时

---

### 示例7：文件上传

上传本地文件到远程服务器。

**必选字段**：
- `command`：必须设置为 `["__FILE_TRANSFER__"]`
- `driver_args.file_transfer.operation`：操作类型（"upload"）
- `driver_args.file_transfer.local_path`：本地文件路径
- `driver_args.file_transfer.remote_path`：远程文件路径

**可选字段**：
- `driver_args.file_transfer.resume`：是否启用断点续传
- `driver_args.file_transfer.chunk_size`：传输块大小（默认32768字节）
- `driver_args.file_transfer.timeout`：传输超时时间

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

**说明**：
- 文件传输必须使用 `command`，不能使用 `config`
- `local_path` 是NetPulse服务器上的文件路径
- `remote_path` 是目标服务器上的文件路径
- 大文件传输建议启用 `resume: true` 支持断点续传

---

### 示例8：文件下载

从远程服务器下载文件到本地。

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

**说明**：
- `operation` 设置为 "download" 表示下载
- 大文件下载建议启用 `resume: true`
- 设置合理的 `timeout` 避免大文件传输超时

---

### 示例9：通过SSH代理/跳板机连接

通过跳板机访问内网服务器。

**必选字段**：
- `connection_args.proxy_host`：代理服务器地址

**可选字段**：
- `connection_args.proxy_port`：代理服务器SSH端口（默认22）
- `connection_args.proxy_username`：代理服务器用户名（如果与目标服务器相同可省略）
- `connection_args.proxy_password`：代理服务器密码
- `connection_args.proxy_key_filename`：代理服务器私钥文件路径

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

**说明**：
- 先连接到代理服务器，再通过代理连接到目标服务器
- 代理服务器和目标服务器的认证方式可以不同
- 适合访问内网服务器或需要通过跳板机的场景

---

### 示例10：设置环境变量执行命令

在执行命令时设置自定义环境变量。

**可选字段**：
- `driver_args.environment`：环境变量字典

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

**说明**：
- 通过 `environment` 设置的环境变量只在本次命令执行时生效
- 可以覆盖系统环境变量（如PATH）

---

### 示例11：使用PTY（伪终端）

对于需要交互式终端的命令，使用PTY。

**可选字段**：
- `driver_args.get_pty`：是否使用伪终端

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

**说明**：
- PTY用于需要交互式终端的命令
- 使用 `config` + `sudo: true` 时，如果提供了 `sudo_password`，会自动启用PTY

---

### 示例12：完整配置示例（生产环境）

包含所有常用配置的完整示例。

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

**说明**：
- 使用密钥内容认证（适合容器环境）
- 设置 `host_key_policy: "reject"` 提高安全性（生产环境推荐）
- 使用 `config` + `sudo` 自动处理权限
- 设置合理的超时时间和TTL

---

## 参数详细说明

### connection_args（连接参数）

用于建立SSH连接到Linux服务器。

#### 必选参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `host` | string | 服务器地址（IP或域名） |
| `username` | string | SSH登录用户名 |

#### 认证参数（至少选一种）

| 参数 | 类型 | 说明 |
|------|------|------|
| `password` | string | 密码认证（最简单，适合测试） |
| `key_filename` | string | 私钥文件路径（适合本地环境） |
| `pkey` | string | 私钥内容（PEM格式字符串，**推荐容器环境**） |

**认证方式选择建议**：
- **开发/测试环境**：使用 `password` 方便快速测试
- **本地生产环境**：使用 `key_filename` 更安全
- **容器环境**：使用 `pkey` 避免需要挂载密钥文件

#### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port` | integer | 22 | SSH端口 |
| `timeout` | float | 30.0 | 连接超时时间（秒） |
| `passphrase` | string | - | 私钥密码（如果密钥已加密） |
| `host_key_policy` | string | "auto_add" | 主机密钥验证策略（见下方说明） |
| `look_for_keys` | boolean | true | 是否自动查找 `~/.ssh/` 目录中的密钥 |
| `allow_agent` | boolean | false | 是否允许SSH代理 |
| `compress` | boolean | false | 是否启用压缩 |
| `banner_timeout` | float | - | Banner超时时间（秒） |
| `auth_timeout` | float | - | 认证超时时间（秒） |

#### SSH代理/跳板机参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `proxy_host` | string | - | 代理服务器地址（设置后启用代理） |
| `proxy_port` | integer | 22 | 代理服务器SSH端口 |
| `proxy_username` | string | - | 代理服务器用户名（如果与目标服务器相同可省略） |
| `proxy_password` | string | - | 代理服务器密码 |
| `proxy_key_filename` | string | - | 代理服务器私钥文件路径 |
| `proxy_pkey` | string | - | 代理服务器私钥内容（PEM格式） |
| `proxy_passphrase` | string | - | 代理服务器私钥密码 |

#### host_key_policy 参数说明

`host_key_policy` 用于控制SSH连接时对服务器主机密钥的验证策略，防止中间人攻击。

| 值 | 说明 | 适用场景 |
|----|------|---------|
| `"auto_add"` | 自动接受未知主机的密钥 | 开发/测试环境，首次连接方便 |
| `"reject"` | 拒绝连接未知主机或密钥不匹配的主机 | **生产环境推荐**，最安全 |
| `"warning"` | 对未知主机发出警告但仍允许连接 | 平衡安全性和便利性 |

**使用建议**：
- **开发/测试环境**：使用 `"auto_add"` 方便快速测试
- **生产环境**：使用 `"reject"` 并预先通过 `ssh-keyscan` 验证主机密钥
- **容器环境**：由于无法持久化known_hosts，通常使用 `"auto_add"` 或 `"warning"`

---

### driver_args（驱动参数）

根据操作类型（command或config）使用不同的参数。

#### command 操作参数（ParamikoSendCommandArgs）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `timeout` | float | - | 命令执行超时时间（秒），None表示无超时 |
| `get_pty` | boolean | false | 是否使用伪终端（PTY），用于交互式命令 |
| `environment` | dict | - | 环境变量字典 |
| `bufsize` | integer | -1 | 缓冲区大小，-1表示使用系统默认值 |
| `file_transfer` | object | - | 文件传输操作（见下方说明） |

#### config 操作参数（ParamikoSendConfigArgs）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `timeout` | float | - | 配置执行超时时间（秒） |
| `get_pty` | boolean | false | 是否使用伪终端 |
| `sudo` | boolean | false | 是否使用sudo执行（自动添加 `sudo -S`） |
| `sudo_password` | string | - | sudo密码（如果sudo已启用且需要密码） |
| `environment` | dict | - | 环境变量字典 |

**sudo使用说明**：
- 设置 `sudo: true` 后，系统会自动在每个命令前添加 `sudo -S`
- 如果sudo需要密码，提供 `sudo_password` 会自动输入
- 使用sudo时，如果提供了 `sudo_password`，会自动启用PTY

#### 文件传输参数（ParamikoFileTransferOperation）

仅在 `command` 操作中使用，通过 `driver_args.file_transfer` 设置。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `operation` | string | - | 操作类型：`"upload"`（上传）或 `"download"`（下载） |
| `local_path` | string | - | 本地文件路径（NetPulse服务器上的路径） |
| `remote_path` | string | - | 远程文件路径（目标服务器上的路径） |
| `resume` | boolean | false | 是否启用断点续传 |
| `chunk_size` | integer | 32768 | 传输块大小（字节，默认32KB） |
| `timeout` | float | - | 传输超时时间（秒），None表示无超时 |

**文件传输说明**：
- 必须使用 `command` 操作，不能使用 `config`
- `command` 必须设置为 `["__FILE_TRANSFER__"]`
- 大文件传输建议启用 `resume: true` 支持断点续传
- 根据网络情况调整 `chunk_size`（默认32KB）

---

### options（全局选项）

所有驱动通用的全局选项。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `queue_strategy` | string | "fifo" | 队列策略（Paramiko默认使用fifo） |
| `ttl` | integer | - | 任务结果保存时间（秒） |

**Paramiko推荐配置**：
- `queue_strategy`: 使用 `"fifo"`（默认），适合长时间运行任务
- `ttl`: 根据操作复杂度设置，查询操作建议300秒，配置操作建议600秒

---

## 支持的密钥格式

- ✅ **RSA**: 支持RSA密钥
- ✅ **ED25519**: 支持ED25519密钥
- ❌ **DSA**: 不支持DSA密钥（已弃用）

---

## 最佳实践

### 1. 认证方式选择

- **生产环境**：推荐使用密钥认证（`pkey` 或 `key_filename`），并设置 `host_key_policy: "reject"` 确保安全性
- **开发/测试环境**：可以使用密码认证，设置 `host_key_policy: "auto_add"` 方便快速测试
- **容器环境**：使用 `pkey`（密钥内容）避免需要挂载密钥文件

### 2. 连接管理

- **超时设置**：根据任务复杂度合理设置 `timeout`，避免任务被过早终止
- **代理连接**：通过跳板机访问内网服务器时使用 `proxy_host` 参数
- **队列策略**：Paramiko使用FIFO策略（短连接），适合长时间运行任务

### 3. 命令执行

- **sudo操作**：需要sudo权限时使用 `config` + `sudo: true`，比手动添加sudo更方便
- **环境变量**：通过 `environment` 参数设置命令执行环境
- **交互式命令**：需要交互时设置 `get_pty: true`

### 4. 文件传输

- **大文件传输**：启用 `resume: true` 支持断点续传
- **传输速度**：根据网络情况调整 `chunk_size`（默认32KB）
- **超时控制**：大文件传输时设置合理的 `timeout` 值

### 5. 错误处理

- **连接失败**：检查网络连接、SSH服务状态、认证信息
- **命令执行失败**：查看 `exit_status` 和 `error` 字段获取详细错误信息
- **文件传输失败**：检查文件路径、权限、磁盘空间

---

## 适用场景

✅ **推荐使用**：
- 系统监控和巡检
- 配置管理和下发
- 软件部署和更新
- 故障排查和修复
- 批量服务器管理
- 文件传输和同步

⚠️ **注意事项**：
- 长时间运行任务使用 FIFO 策略（短连接）
- 交互式命令建议使用非交互式替代方案（如 `rm -f` 替代 `rm -i`）
- 生产环境建议使用密钥认证和严格的主机密钥验证

---

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接和服务器可达性
   - 调整 `timeout` 参数
   - 验证SSH服务是否正常运行

2. **认证失败**
   - 验证用户名和密码
   - 检查密钥文件路径和格式
   - 确认密钥权限（建议600）
   - 验证密钥是否需要密码（`passphrase`）

3. **主机密钥验证失败**
   - 开发环境：使用 `host_key_policy: "auto_add"`
   - 生产环境：使用 `host_key_policy: "reject"` 并预先验证主机密钥

4. **命令执行失败**
   - 查看 `exit_status` 和 `error` 字段
   - 检查命令语法和权限
   - 验证环境变量设置

5. **文件传输失败**
   - 检查文件路径和权限
   - 验证磁盘空间
   - 确认网络连接稳定性
   - 大文件传输启用断点续传

### 调试命令

```bash
# 测试SSH连接
ssh admin@192.168.1.100

# 测试密钥认证
ssh -i /path/to/key admin@192.168.1.100

# 测试代理连接
ssh -J proxy_user@proxy_host admin@target_host

# 查看连接日志
tail -f /var/log/netpulse.log
```

---

## 相关文档

- [设备操作 API](../api/device-api.md) - 设备操作核心接口
- [驱动选择](./index.md) - 了解其他驱动
- [API示例](../api/api-examples.md) - 更多使用示例
