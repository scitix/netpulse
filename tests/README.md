## 测试目录结构与运行指南

- `unit/`：核心逻辑单测（含 FastAPI 路由，标记为 `api`），使用 `config.test.yaml` 与 fakeredis。
- `e2e/`：端到端用例及 pytest 配置（自动/显式启用）。
- `data/`：测试配置（`config.test.yaml`、`config.e2e.yaml`）。
- `clab/`：ContainerLab 拓扑与说明。
- 根 `conftest.py`：设置默认测试配置与标记；`unit/conftest.py` 提供 fakeredis/配置加载夹具；`e2e/conftest.py` 负责 e2e 自动探测与环境切换。

### Pytest 开关与标记

- 运行单元+API 测试：`pytest` 或 `pytest -q`
- 端到端：默认在探测到 lab（ssh1/redis1/srl1 可达）时自动开启；可用 `pytest --e2e` 仅运行 e2e；`pytest --no-e2e` 禁用。
- 过滤标记：`pytest -m api`（仅路由层），`pytest -m e2e`（仅端到端），`pytest -m "not e2e"`（跳过端到端）。
- e2e 运行会加载 `tests/data/config.e2e.yaml`，关闭 fakeredis；用例使用 `@pytest.mark.e2e`。

### 端到端前置

- 拓扑文件：`tests/clab/e2e.clab.yaml`（参见 `clab/README.md`）。
- 前置服务：Redis、NetPulse API、RQ worker 与拓扑处于同一管理网可达。
- 默认节点：`ssh1` 172.20.20.21:2222（netpulse/netpulse，可用 `E2E_SSH_*` 覆盖）；`redis1` 172.20.20.30:6379（无密码，已在 `config.e2e.yaml`）；`srl1/srl2` 172.20.20.11/12（按镜像默认凭据或 `E2E_SRL_*` 覆盖）。
- 启停示例：
```bash
SRL_EULA_ACCEPT=true containerlab deploy -t tests/clab/e2e.clab.yaml
pytest --e2e -q -m e2e   # 强制跑端到端
containerlab destroy -t tests/clab/e2e.clab.yaml
```
