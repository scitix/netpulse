#!/bin/bash

# NetPulse 0.4.3 镜像离线分发脚本 (支持初始化部署与代码更新)

set -e

# Get script dir and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$PROJECT_ROOT"

# --- 配置区 ---
VERSION="0.4.3"
# 自动获取当前 K8s 集群所有节点名称，确保新节点也能同步镜像
NODES=($(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'))

# NetPulse 业务镜像
APP_IMAGES=(
    "netpulse-controller"
    "netpulse-node-worker"
    "netpulse-fifo-worker"
    "netpulse-archiver-worker"
)

# K8s 基础依赖镜像 (仅初始化部署时需要拉取分发)
BASE_IMAGES=(
    "quay.io/opstree/redis:v7.0.12"
    "hashicorp/vault:1.21"
    "bitnami/kubectl:latest"
)

# 解析参数
MODE="update"
if [[ "$1" == "init" ]]; then
    MODE="init"
    shift
elif [[ "$1" == "update" ]]; then
    MODE="update"
    shift
fi

TAR_FILE="netpulse-images-$VERSION-$MODE.tar"

echo "================================================"
if [[ "$MODE" == "init" ]]; then
    echo "▶ 运行模式:【初始化部署】(将打包分发业务镜像 + 基础组件镜像)"
else
    echo "▶ 运行模式:【代码更新】(仅打包分发业务镜像)"
fi
echo "================================================"

echo "=== 步骤 1: 构建本地业务镜像 (Version: $VERSION) ==="
echo "执行路径: $(pwd)"

for img in "${APP_IMAGES[@]}"; do
    CORE_NAME="${img#netpulse-}"
    DOCKERFILE="docker/${CORE_NAME//-/_}.dockerfile"
    
    echo "正在构建: localhost/$img:$VERSION (使用 $DOCKERFILE)"
    docker build -t "localhost/$img:$VERSION" -f "$DOCKERFILE" .
done

# 如果是初始化模式，先拉取基础组件镜像
if [[ "$MODE" == "init" ]]; then
    echo "=== 步骤 1.5: 跨节点拉取基础组件镜像 ==="
    for base_img in "${BASE_IMAGES[@]}"; do
        echo "正在拉取基础镜像: $base_img"
        docker pull "$base_img" || echo "警告: 拉取 $base_img 失败，请检查网络"
    done
fi

echo "=== 步骤 2: 导出镜像到压缩包 ==="
FULL_IMAGE_TAGS=()

# 业务镜像添加到列表
for img in "${APP_IMAGES[@]}"; do
    FULL_IMAGE_TAGS+=("localhost/$img:$VERSION")
done

# 基础镜像添加到列表
if [[ "$MODE" == "init" ]]; then
    for base_img in "${BASE_IMAGES[@]}"; do
        FULL_IMAGE_TAGS+=("$base_img")
    done
fi

echo "正在生成 tar 包: $TAR_FILE"
docker save -o $TAR_FILE "${FULL_IMAGE_TAGS[@]}"
echo "镜像已导出至: $TAR_FILE ($(du -h $TAR_FILE | cut -f1))"

echo "=== 步骤 3: 分发镜像并加载至各节点 ==="
for node in "${NODES[@]}"; do
    echo "------------------------------------------------"
    echo "🚀 正在处理节点: $node"
    
    echo "  -> 传送镜像包..."
    scp $TAR_FILE root@$node:/tmp/$TAR_FILE
    
    echo "  -> 自动识别运行时并导入..."
    ssh root@$node "
        if command -v ctr >/dev/null 2>&1; then
            echo '检测到 Containerd，执行 ctr import...'
            ctr -n k8s.io images import /tmp/$TAR_FILE
        elif command -v docker >/dev/null 2>&1; then
            echo '检测到 Docker，执行 docker load...'
            docker load -i /tmp/$TAR_FILE
        else
            echo '错误: 未检测到 ctr 或 docker，无法导入镜像'
            exit 1
        fi
        rm -f /tmp/$TAR_FILE
    "
    
    echo "  ✅ 节点 $node 处理完成"
done

# 删除本地临时 tar 包
rm -f "$TAR_FILE"

echo "================================================"
echo "🎉 所有节点镜像同步完成！"

# --- 自动触发更新 (可选) ---
if [[ "$*" == *"--restart"* ]]; then
    echo "=== 步骤 4: 正在触发 K8s 滚动更新 ==="
    kubectl rollout restart deployment/netpulse-controller -n netpulse
    kubectl rollout restart deployment/netpulse-node-worker -n netpulse
    kubectl rollout restart deployment/netpulse-fifo-worker -n netpulse
    echo "等待更新完成..."
    kubectl rollout status deployment/netpulse-controller -n netpulse
    echo "✅ 系统已平滑更新至最新镜像版本。"
else
    echo "提示: 如需应用代码更新，请手动执行 'kubectl rollout restart deployment -n netpulse' 或在脚本后追加 --restart 参数。"
fi
