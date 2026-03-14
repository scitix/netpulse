# NetPulse Deployment

This directory contains all deployment assets for NetPulse.
Choose the method that best fits your environment.

---

## Directory Structure

```
deploy/
├── k8s/          # Raw Kubernetes YAML manifests (kubectl apply)
│   ├── scripts/  # Helper shell scripts for secrets and image distribution
│   └── README.md # Detailed step-by-step guide
└── charts/       # Helm Chart (recommended for production)
    └── netpulse/ # NetPulse Helm Chart
```

---

## Option A — Helm (Recommended)

The Helm Chart automates the full deployment: secrets, Redis, Vault, and NetPulse workers.

### Prerequisites

- Kubernetes cluster (1.24+)
- Helm 3.x
- `kubectl` configured to reach the cluster

### Quick Start

**Step 1. Fetch dependencies**

```bash
helm dependency update ./deploy/charts/netpulse
```

**Step 2. Install**

```bash
helm install netpulse ./deploy/charts/netpulse \
  --namespace netpulse \
  --create-namespace \
  --set secrets.redisPassword=<YOUR_REDIS_PASSWORD> \
  --set secrets.apiKey=<YOUR_API_KEY> \
  --set secrets.vaultToken=<YOUR_VAULT_TOKEN>
```

> ⚠️ **Never pass real credentials via `--set` in CI logs.** Use a Kubernetes Secret or
> a `values.override.yaml` file (excluded from git) instead:
>
> ```bash
> helm install netpulse ./deploy/charts/netpulse \
>   --namespace netpulse \
>   --create-namespace \
>   -f values.override.yaml
> ```

**Step 3. Verify**

```bash
# Check all pods are ready
kubectl get pods -n netpulse

# Check Vault initialization log
kubectl logs -f job/netpulse-vault-init -n netpulse
```

### Common Operations

| Command | Action |
|---|---|
| `helm upgrade netpulse ./deploy/charts/netpulse -n netpulse` | Apply config changes |
| `helm rollback netpulse -n netpulse` | Roll back to previous release |
| `helm uninstall netpulse -n netpulse` | Remove all resources |
| `helm list -n netpulse` | Show installed releases |

### Key values.yaml Options

| Parameter | Default | Description |
|---|---|---|
| `replicaCount.controller` | `3` | Number of API controller replicas |
| `replicaCount.nodeWorker` | `18` | Number of SSH node-worker replicas |
| `replicaCount.fifoWorker` | `12` | Number of FIFO-worker replicas |
| `persistence.size` | `100Gi` | Shared storage size |
| `ingress.host` | `netpulse.example.com` | Ingress domain |
| `images.controller.tag` | `0.4.1` | Image version to deploy |
| `config.logLevel` | `INFO` | Application log level |

---

## Option B — Raw Kubernetes YAML

For users who prefer plain `kubectl apply` without Helm.

See **[deploy/k8s/README.md](./k8s/README.md)** for the full step-by-step guide.

### Quick summary

```bash
kubectl create namespace netpulse

# Step 1: Secrets
bash deploy/k8s/scripts/k8s_setup_secrets.sh auto

# Step 2: Storage + Redis
kubectl apply -f deploy/k8s/01-netpulse-storage.yaml \
              -f deploy/k8s/02-redis-operator.yaml \
              -f deploy/k8s/03-redis-cluster.yaml

# Step 3: Vault
kubectl apply -f deploy/k8s/04-vault.yaml
sleep 10
kubectl wait --for=condition=ready pod/vault-0 pod/vault-1 pod/vault-2 -n netpulse --timeout=180s

# Step 4: Vault init
kubectl apply -f deploy/k8s/05-vault-init.yaml
kubectl wait --for=condition=complete job/vault-init -n netpulse --timeout=120s

# Step 5: NetPulse
kubectl apply -f deploy/k8s/06-netpulse-core.yaml \
              -f deploy/k8s/07-ingress.yaml \
              -f deploy/k8s/08-nodeport.yaml
```

---

## Security Notes

| File | Status | Notes |
|---|---|---|
| `deploy/k8s/00-secrets.yaml` | ✅ Safe to commit | Contains **placeholders only** |
| `deploy/k8s/00-secrets-deploy.yaml` | 🚫 Git-ignored | Auto-generated with real credentials |
| `deploy/charts/netpulse/values.yaml` | ✅ Safe to commit | Contains **placeholders only** |
| `deploy/charts/netpulse/charts/` | 🚫 Git-ignored | Third-party packages, fetch via `helm dependency update` |

---

## Image Distribution (Air-Gapped / On-Premise)

If your Kubernetes nodes cannot pull images from the internet, use the distribution script:

```bash
# Initial deploy (includes all base images: Redis, Vault, kubectl)
bash deploy/k8s/scripts/distribute_images.sh init --restart

# Code update only (faster, only pushes NetPulse app images)
bash deploy/k8s/scripts/distribute_images.sh update --restart
```

This script builds images locally → exports to tar → distributes to all cluster nodes via SSH → triggers a rolling restart.
