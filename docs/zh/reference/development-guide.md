# 开发指南

本文档介绍如何搭建 NetPulse 开发环境。

## 环境要求

- Python 3.12+
- Redis 6.0+
- Git
- Docker 20.10+ 和 Docker Compose 2.0+（可选）

## 快速开始

1. **克隆项目**
```bash
git clone git@github.com:scitix/netpulse.git
cd netpulse
```

2. **安装 uv**（如果尚未安装）
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **安装依赖**
```bash
# 安装开发依赖
uv sync --extra dev

# 或安装完整环境
uv sync --extra api --extra tool --extra dev
```

4. **启动 Redis**
```bash
docker compose -f docker-compose.yaml up -d redis
```

5. **验证环境**
```bash
# 检查 Redis 连接
uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis 连接成功' if r.ping() else 'Redis 连接失败')"
```

## 开发工作流

### 基本流程

1. **创建功能分支**
```bash
git checkout -b feature/your-feature-name
```

2. **编写代码**
- 遵循 PEP 8 代码风格
- 添加类型注解和文档字符串
- 编写适当的注释

3. **代码检查和格式化**
```bash
uv run ruff check --fix netpulse/
```

4. **提交代码**
```bash
git add .
git commit -m "feat: add new feature"
```

5. **创建 Pull Request**

### 代码规范

**工具配置**
- **格式化、检查**: Ruff
- **文档**: mkdocs-material

**提交信息规范**

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>[optional scope]: <description>
```

类型包括：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

## 项目结构

```
netpulse/
├── netpulse/                 # 核心代码
│   ├── cli/                 # CLI 工具
│   ├── models/              # 数据模型
│   ├── plugins/             # 插件系统
│   │   ├── drivers/         # 设备驱动
│   │   ├── schedulers/      # 调度器
│   │   ├── templates/       # 模板
│   │   └── webhooks/        # Webhook
│   ├── routes/              # API 路由
│   ├── services/            # 业务逻辑
│   ├── server/              # 服务器
│   ├── utils/               # 工具函数
│   ├── worker/              # 工作进程
│   └── controller.py        # 控制器
├── docs/                    # 文档
├── docker/                  # Docker 配置
├── docker-compose.yaml      # 生产环境配置
└── docker-compose.dev.yaml  # 开发环境配置
```

## 插件开发

NetPulse 采用插件化架构，支持自定义驱动、调度器、模板和 Webhook。

### 驱动插件
在 `netpulse/plugins/drivers/` 目录下创建新的驱动模块。

### 调度器插件
在 `netpulse/plugins/schedulers/` 目录下创建新的调度器模块。

### 模板插件
在 `netpulse/plugins/templates/` 目录下创建新的模板模块。

### Webhook 插件
在 `netpulse/plugins/webhooks/` 目录下创建新的 Webhook 模块。

## 调试

### 日志配置
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 使用调试器
```python
import pdb; pdb.set_trace()
```

### Docker 开发

**启动完整环境**
```bash
docker compose up -d
```

**开发环境**
```bash
docker compose -f docker-compose.dev.yaml up -d
```

## 常见问题

**Q: 如何添加新的设备驱动？**
A: 参考现有的驱动实现，在 `netpulse/plugins/drivers/` 目录下创建新的驱动模块。

**Q: 如何调试 API 请求？**
A: 使用 FastAPI 的自动文档功能，访问 `http://localhost:9000/docs`。

**Q: 如何添加新的开发依赖？**
A: 使用 `uv add --extra dev package-name` 命令。

## 获取帮助

- **GitHub Issues**: 报告问题和请求功能
- **文档**: 查看相关文档
