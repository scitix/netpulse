# NetPulse REST API Complete Reference Manual

> Target Audience: Developers or AI Agents using non-Python languages like Go, Java, Rust to call the REST API directly.
> All endpoints require API Key authentication (except for `/storage/fetch`).

---

## 1. Authentication (Authentication)

| Method | Format |
| :--- | :--- |
| **Header (Recommended)** | `X-API-KEY: <key>` |
| **Query** | `?api_key=<key>` |
| **Cookie** | `api_key=<key>` |

---

## 2. Core Concepts (Core Concepts)

### 2.1 Interaction Modes

**Mode A: Standard Asynchronous Jobs** (Network devices / Short-term Linux)
```
POST /device/bulk  → Returns job_id
GET  /jobs/{id}    → Poll until status="finished", retrieve result from result.retval
```

**Mode B: Linux Detached Tasks** (Long-running processes, `paramiko` driver only)
```
POST /device/bulk (detach:true) → Returns task_id
GET  /detached-tasks/{task_id}  → Real-time log polling or wait for webhook push
```

### 2.2 Queue Strategy (`queue_strategy`)

| Value | Description |
| :--- | :--- |
| `fifo` | New connection, executed by any idle Worker |
| `pinned` | **Reuse connection**, fixed-binding to the same Worker (Optimal performance) |

> `netmiko` driver defaults to `pinned`; `detach:true` forces `pinned`; others default to `fifo`.
> When using `pinned`, if `keepalive` is not set, it is **automatically set to 60 seconds**.

---

## 3. Full Endpoint List

### 3.1 Device Operations (Device)

#### `POST /device/exec` — Single Device Execution
Execute on a single device. Supports two request formats:

**Format A: JSON**
```
Content-Type: application/json
Body: <ExecutionRequest>
```

**Format B: Multipart (Including file upload)**
```
Content-Type: multipart/form-data
file:    <binary file>
request: <ExecutionRequest JSON string>
```

Returns: `JobInResponse`

---

#### `POST /device/bulk` — Batch Device Execution (Most Common)
Batch operation on multiple devices. Each device can independently override command/config.

**Request Body `BulkExecutionRequest` (Inherits from ExecutionRequest, adds `devices` field):**

```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "username": "admin",
    "password": "admin"
  },
  "command": ["show version"],
  "devices": [
    { "host": "192.168.1.1" },
    { "host": "192.168.1.2", "command": ["show ip int brief"] }
  ]
}
```

Returns: `BatchSubmitJobResponse`
```json
{
  "succeeded": [{ "id": "abc123", "status": "queued", "queue": "fifo" }],
  "failed":    [{ "host": "192.168.1.3", "reason": "No worker capacity" }]
}
```

---

#### `POST /device/test` — Connection Test
Test connectivity with the device, **returns synchronously**, does not go through the task queue.

```json
{
  "driver": "paramiko",
  "connection_args": { "host": "10.0.0.1", "username": "root", "password": "pass" }
}
```

Returns `ConnectionTestResponse`:
```json
{
  "success": true,
  "latency": 0.045,
  "error": null,
  "result": { "driver": "paramiko", "host": "10.0.0.1" },
  "timestamp": "2024-01-01T10:00:00+08:00"
}
```

---

### 3.2 Job Management (Jobs)

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/jobs` | Get job list (Supports filtering) |
| `GET` | `/jobs/{id}` | Get single job status and results |
| `DELETE` | `/jobs/{id}` | Cancel a specific queued job |
| `DELETE` | `/jobs` | Batch cancel all queued jobs in a specific queue |

**`GET /jobs` Query Parameters:**

| Parameter | Description |
| :--- | :--- |
| `queue` | Filter by queue name |
| `status` | Filter by status: `queued` / `started` / `finished` / `failed` |
| `node` | Filter by Worker Node name |
| `host` | Filter by device IP (Auto-resolves to corresponding queue) |

**`JobInResponse` Response Structure:**
```json
{
  "id": "job-abc123",
  "status": "finished",
  "queue": "fifo",
  "worker": "worker@server1",
  "created_at": "2024-01-01T10:00:00+08:00",
  "started_at":  "2024-01-01T10:00:01+08:00",
  "ended_at":    "2024-01-01T10:00:02+08:00",
  "duration":    1.35,
  "queue_time":  0.05,
  "task_id":     null,
  "device_name": "192.168.1.1",
  "command":     ["show version"],
  "result": {
    "type": 1,
    "retval": [
      {
        "command":    "show version",
        "stdout":     "Cisco IOS ...",
        "stderr":     "",
        "exit_status": 0,
        "download_url": null,
        "parsed":     null,
        "metadata": {
          "host": "192.168.1.1",
          "duration_seconds": 1.2,
          "session_reused": true
        }
      }
    ],
    "error": null
  }
}
```

> `result.type`: `1`=Success, `2`=Failed, `3`=Stopped, `4`=Retried
> `result.retval`: `DriverExecutionResult` list, one per command

---

### 3.3 Worker Management

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/workers` | Get worker list |
| `DELETE` | `/workers/{name}` | Shutdown a specific Worker |
| `DELETE` | `/workers` | Batch shutdown all workers in a specific queue |

`GET /workers` supports the same filtering parameters as `GET /jobs` (`queue`/`node`/`host`).

### 3.4 System Statistics

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/system/stats` | Get aggregated system performance and connectivity stats |

Provides real-time visibility into active workers (pinned vs fifo), job success rates, and self-healing (Session recovery) events.

**Example Response**:
```json
{
  "status": "online",
  "workers": { "total": 5, "pinned": 4, "fifo": 1, "idle": 3, "busy": 2 },
  "self_healing": { "total_triggers": 12 },
  "uptime_seconds": 3600
}
```

---

### 3.5 Health Check

```
GET /health → { "status": "ok" }
```

---

### 3.6 Linux Detached Tasks (Detached Tasks)

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/detached-tasks` | List all detached tasks (Supports filtering by `?status=running/completed/launching`) |
| `GET` | `/detached-tasks/{task_id}` | Synchronously query task logs and status (Supports incremental reading via `?offset=<bytes>`) |
| `DELETE` | `/detached-tasks/{task_id}` | Terminate (Kill) detached task and cleanup remote files |
| `POST` | `/detached-tasks/discover` | Scan device to find disconnected detached tasks after restart |

**`GET /detached-tasks/{task_id}` Response:**
```json
{
  "task_id": "abc12345",
  "status": "running",
  "result": [
    {
      "command": "query",
      "stdout": "...incremental log output...",
      "stderr": "",
      "exit_status": 0,
      "metadata": {
        "task_id": "abc12345",
        "is_running": true,
        "pid": 12345,
        "next_offset": 2048,
        "completed": false
      }
    }
  ]
}
```

> **`next_offset`**: Pass `?offset=<next_offset>` in the next request to perform incremental reading and avoid duplicate logs.

---

### 3.7 Template Engine (Template)

#### `POST /template/render` — Jinja2 Rendering
Render template + variables into final context text. Can also be directly integrated into the `rendering` field of an execution request.

```json
{
  "name": "jinja2",
  "template": "hostname {{ name }}\ninterface {{ intf }}",
  "context": { "name": "router1", "intf": "Gi0/1" }
}
```

Returns the rendered string.

#### `POST /template/parse` — Structured Output Parsing
Parse command output into structured data (Supports `textfsm` / `ttp`).

```json
{
  "name": "textfsm",
  "template": "Value NAME (\\S+)\nValue VERSION (.+)\n\nStart\n  ^Cisco IOS.*Version ${VERSION}\n\n",
  "context": "Cisco IOS Software, Version 15.2..."
}
```

Returns a structured JSON array.

---

### 3.8 File Storage (Storage)

#### `GET /storage/fetch/{file_id}` — Download File (**No Auth Required**)
Used for downloading files pulled (SFTP download) from devices. `file_id` comes from `DriverExecutionResult.download_url`.
Files are **retained for 24 hours** on the server before automatic cleanup.

---

## 4. `ExecutionRequest` Full Field Reference 

This is the core request body for all execution APIs (used by both `/device/exec` and `/device/bulk`).

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `driver` | string | **Required** | `netmiko`, `paramiko`, `napalm`, `pyeapi` |
| `connection_args` | object | **Required** | Connection parameters, varies by driver |
| `credential` | object | null | Vault credential reference, overrides password in `connection_args` when provided |
| `command` | string/list | null | Commands to execute (Exclusive with `config`) |
| `config` | string/list/dict | null | Configuration to apply (Exclusive with `command`) |
| `file_transfer` | object | null | SFTP file transfer configuration |
| `driver_args` | object | null | Driver behavior parameters (See Section 5) |
| `rendering` | object | null | Jinja2 rendering configuration, used when `command`/`config` is a template |
| `parsing` | object | null | Structured output parsing configuration |
| `webhook` | object | null | Callback configuration after task completion |
| `detach` | bool | false | Whether to run in background (Paramiko only) |
| `push_interval` | int(sec) | null | Interval for incremental log pushes to Webhook, requires `detach:true` |
| `queue_strategy` | string | Auto | `fifo` or `pinned` |
| `ttl` | int(sec) | 300/600 | Max time a task can wait in the queue |
| `execution_timeout` | int(sec) | System Default | Max execution time for the task (File transfer defaults to 3600) |
| `result_ttl` | int(sec) | System Default | Retention duration for results in Redis (up to 7 days) |
| `staged_file_id` | string | null | Internal field, automatically filled during Multipart upload |

---

## 5. Driver Details

### 5.1 Paramiko Driver (Linux Servers)

#### `connection_args` (ParamikoConnectionArgs)

| Field | Default | Description |
| :--- | :--- | :--- |
| `host` | **Required** | Server IP/Domain |
| `username` | **Required** | SSH Username |
| `password` | null | Password authentication |
| `key_filename` | null | Private key file path |
| `pkey` | null | Raw private key content (PEM string, avoids file path dependency) |
| `passphrase` | null | Passphrase for the private key |
| `port` | `22` | SSH Port |
| `timeout` | `30.0` | Connection timeout (seconds) |
| `keepalive` | null | Set seconds (e.g., `60`) to enable persistent connection reuse |
| `host_key_policy` | `auto_add` | `auto_add` / `reject` / `warning` |
| `look_for_keys` | `true` | Automatically search for keys in `~/.ssh/` |
| `allow_agent` | `false` | Allow SSH Agent |
| `compress` | `false` | Enable SSH compression |
| `proxy_host` | null | Jump Host address |
| `proxy_port` | `22` | Jump Host port |
| `proxy_username` | null | Jump Host username |
| `proxy_password` | null | Jump Host password |
| `proxy_key_filename` | null | Jump Host private key path |
| `proxy_pkey` | null | Jump Host raw private key content (PEM) |

#### `driver_args` — Command Execution (ParamikoSendCommandArgs)

| Field | Default | Description |
| :--- | :--- | :--- |
| `timeout` | null | Single command timeout (null = never timeout) |
| `get_pty` | `false` | Request a TTY (Required for interactive commands like `top`) |
| `environment` | null | Environment variable dictionary `{"KEY": "val"}` |
| `working_directory` | null | Directory for command execution |
| `expect_map` | null | Automatic interactive response mapping `{"[Y/n]": "y"}` |
| `sudo` | `false` | Whether to execute with sudo |
| `sudo_password` | null | Sudo password |
| `script_content` | null | Script body (pass content directly without uploading file) |
| `script_interpreter` | `bash` | Script interpreter: `bash`, `sh`, `python`, etc. |

#### `driver_args` — Configuration Apply (ParamikoSendConfigArgs)

| Field | Default | Description |
| :--- | :--- | :--- |
| `sudo` | `false` | Whether to use sudo |
| `sudo_password` | null | Sudo password |
| `stop_on_error` | `true` | Whether to stop subsequent lines after a failure |
| `environment` | null | Environment variables |
| `get_pty` | `false` | Request a TTY |

---

### 5.2 Netmiko Driver (Network Device CLI)

#### `connection_args`

| Field | Default | Description |
| :--- | :--- | :--- |
| `device_type` | **Required** | Device type, e.g., `cisco_ios`, `huawei`, `cisco_xe` |
| `host` | **Required** | Device IP |
| `username` | **Required** | Username |
| `password` | null | Password |
| `secret` | null | Enable mode password |
| `port` | `22` | Port |
| `keepalive` | null | Same as Paramiko, enables persistent connections |

---

### 5.3 NAPALM Driver (Standardized Network Management)

`driver: "napalm"`, `connection_args.device_type` uses NAPALM platform names like `ios`, `eos`.

- `command`: Retrieve standardized Facts such as interface/routing/BGP.
- `config`: Supports Replace / Merge / Rollback configuration transactions.

---

### 5.4 PyEAPI Driver (Arista EOS)

`driver: "pyeapi"`, uses JSON-RPC, ideal for stable interaction with Arista EOS.

---

## 6. File Transfer (`FileTransferModel`)

Applicable for Paramiko and Netmiko drivers, configured via the `file_transfer` field:

| Field | Default | Description |
| :--- | :--- | :--- |
| `operation` | **Required** | `upload` or `download` |
| `remote_path` | **Required** | Absolute path for remote file/directory |
| `local_path` | null | Local path (automatically staged if not filled during download) |
| `overwrite` | `true` | Whether to overwrite if target exists |
| `resume` | `false` | Whether to resume interrupted transfer |
| `recursive` | `false` | Whether to transfer directory recursively |
| `sync_mode` | `full` | `full` = always transfer / `hash` = transfer as needed after MD5 check |
| `verify_file` | `true` | Verify file integrity after transfer |
| `chunk_size` | `32768` | Transfer chunk size (bytes, default 32 KB) |
| `chmod` | null | Set permissions after transfer, e.g., `"0755"` |
| `execute_after_upload` | `false` | Whether to execute `execute_command` immediately after upload |
| `execute_command` | null | Command to execute after upload |
| `cleanup_after_exec` | `true` | Whether to delete remote file after successful execution |

**Download Result Retrieval Workflow:**
1. Submit download request, receive `job_id`.
2. Poll `GET /jobs/{id}` until `finished`.
3. Get download link from `result.retval[0].download_url`.
4. Directly `GET <download_url>` to download the file stream (No Auth, valid for 24h).

---

## 7. Webhook Callback (`WebHook`)

**Request Fields:**

| Field | Default | Description |
| :--- | :--- | :--- |
| `name` | `basic` | Webhook invoker name (currently only `basic`) |
| `url` | **Required** | Callback URL |
| `method` | `POST` | HTTP method: `GET/POST/PUT/PATCH/DELETE` |
| `headers` | null | Custom headers, e.g., `{"Authorization": "Bearer ..."}` |
| `cookies` | null | Cookies sent with the request |
| `auth` | null | HTTP Basic Auth, format: `["username", "password"]` |
| `timeout` | `5.0` | Request timeout (seconds), range 0.5~120 |

**NetPulse Pushed Payload Format:**
```json
{
  "id":     "job-abc123 or task_id (for detach tasks)",
  "status": "success or failed",
  "result": "Formatted output text or error message",
  "device": { "host": "192.168.1.1", "device_type": "cisco_ios" },
  "driver": "netmiko",
  "command": "show version"
}
```

**How Detached Task Real-time Pushing Works:**
1. Set `detach:true`, `push_interval: 30` (sec), and `webhook.url` in the request.
2. The NetPulse background Supervisor scans running tasks every `push_interval` seconds.
3. Reads new logs (delta) and triggers the Webhook push.
4. When the task finishes, Webhook `status` is `success` and `result` contains final output.

---

## 8. Credentials & Vault (`credential`)

Reference external credentials via the `credential` field to avoid transmitting plain-text passwords:

```json
{
  "driver": "paramiko",
  "connection_args": { "host": "10.0.0.1" },
  "credential": {
    "name": "vault_kv",
    "ref": "netpulse/server-a",
    "mount": "kv",
    "field_mapping": { "username": "user", "password": "pass" }
  }
}
```

NetPulse automatically pulls the credential from Vault, injects it into `connection_args`, and subsequently scrubs the `credential` field.

---

## 9. Template Rendering & Parsing (Integration with execution request)

### 9.1 Jinja2 Rendering (`rendering` field)
Inline rendering within the execution request, where `command` or `config` can be a Jinja2 template:

```json
{
  "driver": "netmiko",
  "connection_args": { "device_type": "cisco_ios", "host": "10.0.0.1", "username": "admin", "password": "pass" },
  "config": "interface {{ intf }}\n description {{ desc }}",
  "rendering": {
    "name": "jinja2",
    "context": { "intf": "Gi0/1", "desc": "Managed by NetPulse" }
  }
}
```

### 9.2 TextFSM/TTP Parsing (`parsing` field)
Automatically parse output after command execution, result stored in `DriverExecutionResult.parsed`:

```json
{
  "driver": "netmiko",
  "connection_args": { "device_type": "cisco_ios", "host": "10.0.0.1", "username": "admin", "password": "pass" },
  "command": ["show ip interface brief"],
  "parsing": {
    "name": "textfsm",
    "template": "Value INTF (\\S+)\nValue STATUS (\\S+)\n\nStart\n  ^${INTF}\\s+\\S+\\s+\\S+\\s+\\S+\\s+${STATUS} -> Record\n"
  }
}
```

---

## 10. Complete Examples

### Example A: Netmiko Batch Inspection + TextFSM Parsing
```json
{
  "driver": "netmiko",
  "connection_args": { "device_type": "cisco_ios", "username": "admin", "password": "pass" },
  "command": ["show version"],
  "parsing": { "name": "textfsm" },
  "webhook": { "url": "http://my-app/callback" },
  "devices": [
    { "host": "192.168.1.1" },
    { "host": "192.168.1.2" }
  ]
}
```

### Example B: Linux Background Upgrade Task + Webhook Real-time Push
```json
{
  "driver": "paramiko",
  "connection_args": { "host": "10.0.0.1", "username": "admin", "password": "pass", "keepalive": 60 },
  "command": ["yum update -y"],
  "detach": true,
  "push_interval": 30,
  "webhook": {
    "url": "http://my-go-app/webhook",
    "headers": { "Authorization": "Bearer my-token" }
  },
  "driver_args": { "sudo": true, "sudo_password": "pass" },
  "devices": [{ "host": "10.0.0.1" }]
}
```

### Example C: Upload Script and Execute in Background
```json
{
  "driver": "paramiko",
  "connection_args": { "host": "10.0.0.1", "username": "root", "password": "pass" },
  "file_transfer": {
    "operation": "upload",
    "remote_path": "/tmp/deploy.sh",
    "execute_after_upload": true,
    "execute_command": "bash /tmp/deploy.sh",
    "cleanup_after_exec": true,
    "chmod": "0755"
  },
  "detach": true,
  "push_interval": 60,
  "webhook": { "url": "http://my-go-app/webhook" },
  "devices": [{ "host": "10.0.0.1" }]
}
```
> When uploading a script, use **Multipart Mode** of `POST /device/exec`. Use the `file` field for the script and the `request` field for the JSON above.

### Example D: Download Device File and Get Link
```json
{
  "driver": "paramiko",
  "connection_args": { "host": "10.0.0.1", "username": "admin", "password": "pass" },
  "file_transfer": {
    "operation": "download",
    "remote_path": "/var/log/syslog",
    "sync_mode": "hash"
  },
  "devices": [{ "host": "10.0.0.1" }]
}
```
After polling `GET /jobs/{id}` successfully, get the link from `result.retval[0].download_url` (valid for 24h).

### Example E: Connect to Internal Linux Server via Jump Host
```json
{
  "driver": "paramiko",
  "connection_args": {
    "host": "Intranet_IP",
    "username": "admin",
    "password": "pass",
    "proxy_host": "Public_Jump_Host_IP",
    "proxy_username": "jump_user",
    "proxy_password": "jump_pass"
  },
  "command": ["uname -a"],
  "devices": [{ "host": "Intranet_IP" }]
}
```

### Example F: Inline Script Execution (No file upload needed)
```json
{
  "driver": "paramiko",
  "connection_args": { "host": "10.0.0.1", "username": "admin", "password": "pass" },
  "driver_args": {
    "script_content": "#!/bin/bash\nset -e\nhostname\ndf -h\nfree -m",
    "script_interpreter": "bash",
    "sudo": false
  },
  "devices": [{ "host": "10.0.0.1" }]
}
```
