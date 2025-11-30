# 凭据配置指南（Vault KV）

本文介绍如何启用 `vault_kv` 凭据提供器，将 Netpulse 与 Vault 对接，并在 API 请求中使用。

## 工作机制
- 仅当 `credential.enabled=true` 且请求里的 `credential.name` 与配置的提供器名称一致时才会解析凭据。
- 设备路由从 `netpulse.plugins.credentials` 加载 provider，用全局配置 + `CredentialRef` 实例化，将密文写入 `connection_args`，并清空请求中的 `credential`。
- `vault_kv` 通过 `hvac` 读取 Vault KV v2，校验 `allowed_paths`，支持 namespace，按 `cache_ttl` 缓存，默认映射 `username/password` 字段。

## 应用配置
`config/config.yaml`（默认关闭）：
```yaml
credential:
  enabled: false
  name: vault_kv
  # addr: http://vault:8200
  # namespace: ""
  # allowed_paths: ["kv/netpulse"]
  # cache_ttl: 30
  # verify: true       # 或 CA 证书路径
  # token: ${NETPULSE_VAULT_TOKEN}
  # role_id: ${NETPULSE_VAULT_ROLE_ID}
  # secret_id: ${NETPULSE_VAULT_SECRET_ID}
```

## 环境变量
- `NETPULSE_CREDENTIAL__ENABLED`：设为 `true` 启用。
- `NETPULSE_CREDENTIAL__NAME`：设置为 `vault_kv`。
- `NETPULSE_CREDENTIAL__ADDR`：如 `http://vault:8200`。
- `NETPULSE_CREDENTIAL__ALLOWED_PATHS`：逗号分隔前缀（如 `kv/netpulse`）。
- `NETPULSE_CREDENTIAL__VERIFY`：`true`/`false` 或 CA 路径。
- `NETPULSE_CREDENTIAL__CACHE_TTL`：缓存秒数，`0` 关闭缓存。
- 认证方式二选一：`NETPULSE_VAULT_TOKEN`，或 `NETPULSE_VAULT_ROLE_ID` + `NETPULSE_VAULT_SECRET_ID`。

## 请求示例
```json
{
  "driver": "netmiko",
  "credential": {
    "name": "vault_kv",
    "ref": "netpulse/device-a",
    "mount": "kv",
    "field_mapping": {"username": "username", "password": "password"}
  },
  "connection_args": {"device_type": "cisco_ios", "host": "10.0.0.1"},
  "command": "show version"
}
```
- `ref`：密文路径（不含 mount 前缀）。
- `mount`：KV v2 挂载点，默认 `secret`，示例用 `kv`。
- `field_mapping`：将 Vault 字段映射到 `connection_args`。
- `version`：可选版本号（KV v2）。

## 使用 Docker Compose 本地测试
- `docker-compose.yaml` 与 `docker-compose.dev.yaml` 内置 `vault` 服务（dev 模式），监听 `http://localhost:8200`，使用 `.env` 中的 `NETPULSE_VAULT_TOKEN` 作为 root token。
- 启动示例：`docker-compose up -d vault redis controller` 或 `docker-compose -f docker-compose.dev.yaml up -d vault`。
- dev 模式不持久化，重启后需要重新写入策略与密文。

## Vault 侧操作
1. 启用 KV v2（如未启用）：`vault secrets enable -path=kv kv-v2`
2. 创建最小权限策略（如 `kv/netpulse/*`）：
   ```hcl
   path "kv/data/netpulse/*" { capabilities = ["read"] }
   ```
   载入：`vault policy write netpulse-read policy.hcl`
3. 发放凭据：
   - Token：`vault token create -policy=netpulse-read -display-name=netpulse`
   - AppRole：`vault auth enable approle`（一次性），然后
     ```
     vault write auth/approle/role/netpulse policies="netpulse-read"
     vault read auth/approle/role/netpulse/role-id
     vault write -f auth/approle/role/netpulse/secret-id
     ```
4. 写入设备密文（默认映射）：
   ```bash
   vault kv put kv/netpulse/device-a username=admin password=Pa55w0rd!
   ```

## 排错与最佳实践
- 401/permission denied：检查 token/AppRole 策略与 `allowed_paths`。
- Missing fields：确认 Vault 字段与 `field_mapping` 一致。
- TLS 问题：设置 `NETPULSE_CREDENTIAL__VERIFY` 为 `true/false` 或 CA 路径。
- 优先 AppRole，限制 `allowed_paths`，为 `cache_ttl` 设置合适值以平衡频率与新鲜度。
