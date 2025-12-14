# Credential Guide (Vault KV)

This guide shows how to enable the `vault_kv` credential provider, wire it to Vault, and use it in API requests.

## How it works
- Credential resolution runs only when `credential.enabled=true` and the request `credential.name` matches the configured provider name.
- The device route loads the provider from `netpulse.plugins.credentials`, instantiates it with global config + `CredentialRef`, then writes secrets into `connection_args` and removes the `credential` field before dispatching.
- `vault_kv` reads from Vault KV v2 via `hvac`, enforces `allowed_paths`, supports optional namespaces, caches secrets by `cache_ttl`, and defaults to mapping `username/password` fields.

## Application configuration
`config/config.yaml` (disabled by default):
```yaml
credential:
  enabled: false
  name: vault_kv
  # addr: http://vault:8200
  # namespace: ""
  # allowed_paths: ["kv/netpulse"]
  # cache_ttl: 30
  # verify: true       # or CA bundle path
  # token: ${NETPULSE_VAULT_TOKEN}
  # role_id: ${NETPULSE_VAULT_ROLE_ID}
  # secret_id: ${NETPULSE_VAULT_SECRET_ID}
```

## Environment variables
- `NETPULSE_CREDENTIAL__ENABLED` — set to `true` to enable.
- `NETPULSE_CREDENTIAL__NAME` — must be `vault_kv`.
- `NETPULSE_CREDENTIAL__ADDR` — e.g., `http://vault:8200`.
- `NETPULSE_CREDENTIAL__ALLOWED_PATHS` — comma-separated prefixes (`kv/netpulse`).
- `NETPULSE_CREDENTIAL__VERIFY` — `true`/`false` or CA path.
- `NETPULSE_CREDENTIAL__CACHE_TTL` — seconds; `0` disables cache.
- Auth (choose one): `NETPULSE_VAULT_TOKEN` or `NETPULSE_VAULT_ROLE_ID` + `NETPULSE_VAULT_SECRET_ID`.

## Request example
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
- `ref`: secret path (without mount prefix).
- `mount`: KV v2 mount point (default `secret`; example uses `kv`).
- `field_mapping`: map Vault fields to `connection_args`.
- `version`: optional secret version (KV v2).

## Local testing with Docker Compose
- Both `docker-compose.yaml` and `docker-compose.dev.yaml` include a `vault` service (dev mode) listening on `http://localhost:8200`, using `.env` `NETPULSE_VAULT_TOKEN` as the root token.
- Start a test stack: `docker-compose up -d vault redis controller` (or `docker-compose -f docker-compose.dev.yaml up -d vault`).
- Dev mode is non-persistent; write secrets and policies after each start.

## Vault setup steps
1. Enable KV v2 (if needed): `vault secrets enable -path=kv kv-v2`
2. Create a least-privilege policy (example `kv/netpulse/*`):
   ```hcl
   path "kv/data/netpulse/*" { capabilities = ["read"] }
   ```
   Apply: `vault policy write netpulse-read policy.hcl`
3. Issue credentials:
   - Token: `vault token create -policy=netpulse-read -display-name=netpulse`
   - AppRole: `vault auth enable approle` (once), then
     ```
     vault write auth/approle/role/netpulse policies="netpulse-read"
     vault read auth/approle/role/netpulse/role-id
     vault write -f auth/approle/role/netpulse/secret-id
     ```
4. Write device secrets (default mapping):
   ```bash
   vault kv put kv/netpulse/device-a username=admin password=Pa55w0rd!
   ```

## Troubleshooting and best practices
- 401/permission denied: check token/AppRole policy and `allowed_paths`.
- Missing fields: ensure Vault keys match `field_mapping`.
- TLS issues: set `NETPULSE_CREDENTIAL__VERIFY` to `true/false` or a CA path.
- Prefer AppRole over long-lived tokens; restrict `allowed_paths`; set a sensible `cache_ttl` to balance load vs. freshness.
