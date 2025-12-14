### netpulse E2E ContainerLab 拓扑

- 拓扑文件：`tests/clab/e2e.clab.yaml`
- 设备：
- `srl1`、`srl2`：`ghcr.io/nokia/srlinux`，管理地址 `172.20.20.11`、`172.20.20.12`。
  默认用户名/密码需根据 SR Linux 版本调整（`admin`/`NokiaSrl1!`），可用 `E2E_SRL_*` 覆盖。
- `ssh1`：`lscr.io/linuxserver/openssh-server:latest`，管理地址 `172.20.20.21`，
  用户名/密码 `netpulse/netpulse`（可通过 env 覆盖），监听端口 **2222**（`E2E_SSH_*`）。
- `redis1`：`redis:7-alpine`，管理地址 `172.20.20.30`，无密码，已关闭 protected-mode，绑定 0.0.0.0（`E2E_REDIS_*` 可覆盖）。
- 管理网络：`netpulse-e2e`，前缀 `172.20.20.0/24`。容器的管理口可直接从宿主访问，无需端口映射。
- e2e 设置集中在 `tests/e2e/settings.py` 的 `LabConfig` 中，默认按上述拓扑与凭据，可用 `E2E_*` 变量覆盖（SSH/SRL/Redis/API）。
- 启动示例：
  ```bash
  SRL_EULA_ACCEPT=true containerlab deploy -t tests/clab/e2e.clab.yaml
  # 收尾
  containerlab destroy -t tests/clab/e2e.clab.yaml
  # 如遇残留网络导致部署失败，可手动清理：
  docker network rm netpulse-e2e 2>/dev/null || true
  ```
- 如果需要自定义启动配置（如修改 SRL 登录凭据或开启额外服务），可在拓扑文件中为节点添加 `startup-config` 指向本目录下的配置文件。
