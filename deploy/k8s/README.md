# NetPulse Kubernetes 生产级 HA 部署指南

本目录包含 NetPulse 在 Kubernetes 环境下的生产级部署资源清单。
该方案已实现 **自动化高可用部署**，深度集成了 **Redis Operator 主从复制** 和 **Vault Raft 3节点高可用集群**，并实现了 **Vault API 零人工干预自动解封**、**持久化 100GiB 共享存储** 与 **大规模并发内存调优**。

---

## 🚀 核心架构与特性

- **Redis 集群**: 基于 `redis-operator` (OPSTree) 实现 1主2从高可用复制架构，自动化无缝故障转移，凭据由 Secret 自动注入。
- **Vault 集群**: 原生 Raft 后端 3 节点 HA 选主架构，支持零中断切换。
- **自动化密码学管控**: 全新重构的 `vault-init` 任务实现：
  1. 自动化集群初始化
  2. 自动化将 Unseal Key 落盘到 K8s 内部 Secret (`vault-unseal-key`)
  3. 全节点（新启/重启）免人工干预自动化集群解封 (Idempotent 幂等操作)
  4. 自动化注入统一的业务访问 Token (`1Jj1OB3RRsXLygXPzTwMn6KG`)

---

## 📦 标准化部署流程 (经过充分实盘验证)

部署必须**严格按照以下顺序进行**，以保证基础中间件的服务发现、凭据提取及初始化按正确依赖关系启动。

### [Step 1] 环境初始化与核心凭据下发
首先创建业务专用命名空间和包含系统运行必要密码的 Secret（Redis 强依赖该 Secret 注入配置）：
```bash
kubectl create namespace netpulse
kubectl apply -f deploy/k8s/00-secrets-deploy.yaml
```

### [Step 2] 部署支撑存储基石与 Redis HA 集群
部署 OPSTree Redis Operator 及通过 CRD 创建高可用 Redis：
```bash
# 1. (仅首次) 如果集群尚未安装 OPSTree Redis Operator，需先安装：
# helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
# helm upgrade --install redis-operator ot-helm/redis-operator --namespace redis-operator --create-namespace

# 2. 部署业务数据共享持久卷 (100Gi), Redis 配置文件及 Redis 集群实例
kubectl apply -f deploy/k8s/01-netpulse-storage.yaml \
              -f deploy/k8s/02-redis-operator.yaml \
              -f deploy/k8s/03-redis-cluster.yaml 
```
> **注意**: 部署后需等待几分钟，直到 `netpulse-redis-0`, `1`, `2` 完成持久卷绑定、镜像拉取（`quay.io/opstree/redis:v7.0.12`）并运行。

### [Step 3] 部署企业级高安全凭据中心 (Vault HA)
发起 3 节点的 Vault 集群，内部使用基于 Headless Service 的 Raft 内部通信：
```bash
kubectl apply -f deploy/k8s/04-vault.yaml

# 必须等待 Vault 的 3 个 Pod 都能被 K8s 创建出来后再进入 wait 阶段：
sleep 10
kubectl wait --for=condition=ready pod/vault-0 pod/vault-1 pod/vault-2 -n netpulse --timeout=180s
```

### [Step 4] 凭据中枢自动初始化及全局解封
跑一次自动化任务。该任务能够自动发现当前状态、进行 Init 选主，把 Unseal Key 保存到 K8s Secret，并对整个集群挨个实施 Unseal 解封：
```bash
# 执行自动化配置任务
kubectl apply -f deploy/k8s/05-vault-init.yaml

# 验证控制台日志（预期输出：Vault HA cluster is fully operational!）
kubectl wait --for=condition=complete job/vault-init -n netpulse --timeout=120s
kubectl logs job/vault-init -n netpulse
```
> 💡 **断电恢复特性**: 由于该任务具备完全幂等性。如果日后整个 K8s 物理集群关机重启，导致 Vault 节点集体进入 `Sealed` (锁定) 状态，你只需**重新 apply 执行一次该任务**（`kubectl delete job vault-init -n netpulse && kubectl apply -f deploy/k8s/05-vault-init.yaml`），它就能自动从 Secret 读取密钥并帮所有节点无痛解封。

### [Step 5] 部署 NetPulse 业务控制面与数据面
只有当 Vault 和 Redis 全部呈就绪状态后，才可以下发业务应用和反向代理网络：
```bash
# 包括 Controller, FIFO-Worker, Node-Worker, Ingress 路由及 NodePort 暴露
kubectl apply -f deploy/k8s/06-netpulse-core.yaml \
              -f deploy/k8s/07-ingress.yaml \
              -f deploy/k8s/08-nodeport.yaml

### [Step 6] (可选) 部署企业级 MongoDB 审计存储 (MongoDB Operator)
如果你需要启用 0.4.3 版本新增的审计归档与 MongoDB 增强功能：
```bash
# 1. 安装 MongoDB Community Operator (仅首次)
helm repo add mongodb https://mongodb.github.io/helm-charts
helm install community-operator mongodb/community-operator --namespace mongodb --create-namespace

# 2. 部署 3 节点高可用 MongoDB 副本集
kubectl apply -f deploy/k8s/09-mongodb.yaml

# 3. 开启业务审计状态
kubectl patch configmap netpulse-config -n netpulse --type merge -p '{"data":{"NETPULSE_MONGODB__ENABLED":"true"}}'
kubectl rollout restart deployment/netpulse-archiver-worker -n netpulse
```
```

---

## 🛠 日常运维与持续集成 (CI/CD)

### 1. 核心链路自动化更新
当修改了 Python 代码并希望快速热更到 K8s 集群中时，只需执行部署分发脚本：
```bash
# 自动执行：构建镜像 -> 打包导出 -> 分发到各节点 -> 在 K8s 中滚动重启
bash deploy/k8s/scripts/distribute_images.sh --restart
```
> *`--restart` 参数触发 K8s 滚动重载，全程保证前端网关 0 停机访问。*

### 2. 集群状态巡检命令
- **全栈概览**：`kubectl get pods,pvc,ingress,redisreplication -n netpulse`
- **监控应用日志**：`kubectl logs -f deployment/netpulse-controller -n netpulse`
- **查看 Vault 选主状态**：
  ```bash
  kubectl exec vault-0 -n netpulse -- sh -c "VAULT_TOKEN=1Jj1OB3RRsXLygXPzTwMn6KG vault operator raft list-peers"
  ```

### 3. 系统凭据与令牌管理 (Credential & Token Management)

系统涉及三类核心凭据，请根据使用场景选择正确的令牌：

| 凭据名称 | 作用范围 | 权限等级 | 获取命令 |
| :--- | :--- | :--- | :--- |
| **Vault Initial Root Token** | **Vault 管理**：登录 UI、管理策略、手动调试 Vault 核心 | **最高 (Supreme)** | `kubectl get secret vault-unseal-key -n netpulse -o jsonpath='{.data.root-token}' \| base64 -d && echo` |
| **Vault Operational Token** | **业务访问**：用于 NetPulse 程序内部读写 KV 密钥 | **高 (Root级/隔离)** | `kubectl get secret netpulse-secrets -n netpulse -o jsonpath='{.data.vault-token}' \| base64 -d && echo` |
| **NetPulse API Key** | **SDK/客户端**：用于在请求 API 时通过 `X-API-KEY` 进行头部鉴权 | **应用级 (App)** | `kubectl get secret netpulse-secrets -n netpulse -o jsonpath='{.data.api-key}' \| base64 -d && echo` |

#### 🔑 运维备忘录：
- **解封密钥 (Unseal Key)**：用于 Vault 集群崩溃或重启后的手动/自动解锁，存储在 K8s Secret 中：
  `kubectl get secret vault-unseal-key -n netpulse -o jsonpath='{.data.unseal-key}' | base64 -d && echo`
- **Redis 密码**：
  `kubectl get secret netpulse-secrets -n netpulse -o jsonpath='{.data.password}' | base64 -d && echo`

---
