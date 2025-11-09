# 驱动选择指南

NetPulse 采用插件化的驱动架构，支持快速扩展新的设备驱动。通过统一的API接口，可以轻松接入新的驱动来支持更多设备类型。

## 快速对比

| 驱动 | 连接方式 | 推荐场景 | 核心优势 |
|------|---------|---------|---------|
| **Netmiko** | SSH/Telnet | **大多数场景（推荐）** | 支持设备类型较广泛，长连接复用可提升性能 |
| **NAPALM** | SSH/HTTP/HTTPS | 需要配置合并/回滚 | 支持配置合并、替换、回滚 |
| **PyEAPI** | HTTP/HTTPS | Arista EOS设备 | 原生API，性能较好，JSON结构化数据 |

## 驱动说明

NetPulse 基于插件化的驱动架构，可以快速扩展新的设备驱动。当前支持以下驱动：

### Netmiko（推荐）

**大多数场景的默认选择**。通过SSH连接执行命令，支持Cisco、Juniper等大多数网络设备。长连接复用可在频繁操作场景下提升性能。

- 支持设备：Cisco、Juniper、HP等SSH设备
- 推荐队列策略：Pinned（长连接复用）
- 适用场景：查询、配置推送等常规操作

**关键参数**：
- `connection_args.device_type`（必需）：设备类型，如 `cisco_ios`、`juniper_junos` 等
- `connection_args.keepalive`（默认180秒）：SSH连接保活时间，用于长连接复用
- `connection_args.secret`：特权模式密码（enable密码）
- `driver_args.read_timeout`（默认10秒）：读取超时时间
- `driver_args.delay_factor`：延迟因子，用于慢速设备
- `driver_args.strip_prompt`（默认true）：去除输出中的提示符
- `driver_args.cmd_verify`（默认true）：命令验证

📖 [查看 Netmiko 详细文档](./netmiko.md)

### NAPALM

**仅在需要高级配置管理功能时使用**。提供配置合并、替换、回滚等高级功能。

- 支持设备：Cisco、Juniper等多厂商设备
- 适用场景：需要配置合并、替换、回滚、版本控制

**关键参数**：
- `connection_args.device_type`（必需）：设备类型，如 `ios`、`junos`、`eos` 等
- `connection_args.hostname`（必需）：设备IP地址（注意：NAPALM使用hostname而非host）
- `connection_args.optional_args`：可选参数对象，可包含 `port`、`secret`、`transport` 等
- `driver_args.encoding`（查询，默认"text"）：编码格式
- `driver_args.message`（配置）：配置提交消息
- `driver_args.revert_in`（配置）：配置确认时间（秒），用于自动回滚

📖 [查看 NAPALM 详细文档](./napalm.md)

### PyEAPI

**管理Arista设备时的推荐选择**。使用Arista原生HTTP API，性能较好。

- 支持设备：Arista EOS专用
- 适用场景：Arista设备的所有操作

**关键参数**：
- `connection_args.host`（必需）：设备IP地址
- `connection_args.transport`（默认https）：传输协议，支持 `http`/`https`
- `connection_args.port`：API端口号（HTTP默认80，HTTPS默认443）
- `connection_args.timeout`（默认60秒）：连接超时时间
- `driver_args`：支持任意参数，会传递给pyeapi的enable/config方法

📖 [查看 PyEAPI 详细文档](./pyeapi.md)

## 选择建议

| 场景 | 推荐驱动 |
|------|---------|
| Arista设备 | **PyEAPI（首选）** |
| Cisco/Juniper/其他SSH设备 | **Netmiko（推荐）** |
| 需要配置合并/回滚 | NAPALM |

## 快速决策

```
Arista设备？ → PyEAPI
需要配置合并/回滚？ → NAPALM
其他场景 → Netmiko（推荐）
```
