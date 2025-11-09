# 故障排查

本文档提供一些常见问题的排查方法和解决方案，供参考。

## 查看日志

### Docker 环境

```bash
# 查看所有服务日志
docker compose logs

# 查看特定服务日志
docker compose logs controller
docker compose logs fifo-worker
docker compose logs node-worker

# 实时跟踪日志
docker compose logs -f

# 查看最近的日志
docker compose logs --tail=100 controller
```

### 日志格式

```
[2025-07-20 01:10:38 +0800] [9] [INFO] [netpulse.api|routes.py:45] - API request received
```

格式说明：
- `2025-07-20 01:10:38 +0800`: 时间戳和时区
- `[9]`: 进程ID
- `INFO`: 日志级别
- `[netpulse.api|routes.py:45]`: 模块名|文件名:行号
- `API request received`: 日志消息

### 日志级别

- **INFO**: 正常运行信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **DEBUG**: 调试信息（详细信息）

### 快速排查命令

```bash
# 查看错误日志
docker compose logs | grep ERROR

# 查看警告日志
docker compose logs | grep WARNING

# 查看启动相关日志
docker compose logs | grep -E "(Starting|Started|ERROR|CRITICAL)"

# 查看设备连接日志
docker compose logs node-worker | grep -E "(connect|connection|timeout|failed)"
```

## 常见问题

### 部署相关问题

#### Q1: Docker 容器启动失败

**问题描述**: 容器启动失败或立即退出。

**排查步骤**:
```bash
# 1. 检查 Docker 服务
sudo systemctl status docker

# 2. 检查端口占用
sudo netstat -tlnp | grep :9000

# 3. 查看详细日志
docker compose logs

# 4. 重新构建
docker compose down
docker compose build --no-cache
docker compose up -d
```

**常见原因**:
- 端口被占用
- 内存不足
- 配置文件错误
- Docker 服务未启动

#### Q2: API 密钥问题

**问题描述**: 无法获取或使用 API 密钥。

**排查步骤**:
```bash
# 1. 查看环境变量
cat .env | grep NETPULSE_SERVER__API_KEY

# 2. 从日志中查找
docker compose logs controller | grep "API Key"

# 3. 重新生成
docker compose down
rm .env
bash ./scripts/setup_env.sh generate
docker compose up -d
```

#### Q3: Redis 连接失败

**问题描述**: Worker 无法连接到 Redis。

**排查步骤**:
```bash
# 1. 检查 Redis 容器状态
docker compose ps redis

# 2. 查看 Redis 日志
docker compose logs redis

# 3. 重启 Redis
docker compose restart redis

# 4. 测试连接
docker compose exec controller ping redis
```

### 连接相关问题

#### Q4: 设备连接超时

**问题描述**: 连接网络设备时超时。

**可能原因**:
- 网络延迟高
- 设备负载重
- 防火墙阻止
- 设备类型配置错误

**可尝试**:
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "device_type": "cisco_ios",
    "timeout": 60,
    "read_timeout": 120
  }
}
```

#### Q5: SSH 认证失败

**问题描述**: SSH 连接认证错误。

**排查步骤**:
```bash
# 1. 手动测试连接
ssh admin@192.168.1.1

# 2. 检查设备类型
# 确保 device_type 正确：cisco_ios, cisco_nxos, juniper_junos, arista_eos 等

# 3. 检查是否需要 enable 密码
{
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password",
    "secret": "enable_password",
    "device_type": "cisco_ios"
  }
}
```

#### Q6: 设备类型不支持

**支持的设备类型**:
- **Cisco**: cisco_ios, cisco_nxos, cisco_ios_xr
- **Juniper**: juniper_junos
- **Arista**: arista_eos
- **华为**: huawei
- **HP**: hp_comware

### API 相关问题

#### Q7: API 请求返回 403 错误

**问题描述**: API 请求返回认证失败（HTTP 403）。

**排查步骤**:
```bash
# 1. 检查 API 密钥
curl -H "X-API-KEY: YOUR_API_KEY" \
     http://localhost:9000/health

# 2. 验证密钥格式
# 确保密钥正确，无多余空格或换行

# 3. 重新生成密钥
docker compose down
bash ./scripts/setup_env.sh generate
docker compose up -d
```

#### Q8: 任务执行失败

**问题描述**: 提交的任务执行失败。

**排查步骤**:
```bash
# 1. 查看任务状态
curl -H "X-API-KEY: YOUR_API_KEY" \
     http://localhost:9000/job?id=JOB_ID

# 2. 查看 Worker 日志
docker compose logs worker

# 3. 测试设备连接
curl -X POST \
  -H "X-API-KEY: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "password",
      "device_type": "cisco_ios"
    }
  }' \
  http://localhost:9000/device/test-connection
```

### 性能相关问题

#### Q9: 任务执行缓慢

**可能原因**:
- Worker 数量不足
- 网络延迟
- 设备响应慢

**可尝试**:
- 适当增加 `pinned_per_node`
- 使用 Pinned 队列策略
- 增加任务超时时间

#### Q10: 内存使用过高

**可尝试**:
```bash
# 1. 检查内存使用
docker stats

# 2. 限制容器内存（在 docker-compose.yml 中）
services:
  controller:
    deploy:
      resources:
        limits:
          memory: 1G

# 3. 重启 Worker
docker compose restart worker
```

### 配置相关问题

#### Q11: 环境变量配置错误

**排查步骤**:
```bash
# 1. 检查环境变量
cat .env

# 2. 重新生成配置
bash ./scripts/setup_env.sh generate

# 3. 验证配置
docker compose config
```

#### Q12: 模板渲染失败

**排查步骤**:
```python
# 检查模板语法
from jinja2 import Template

template = Template("""
interface {{ interface.name }}
 description {{ interface.description }}
""")

# 验证变量
variables = {
    'interface': {
        'name': 'GigabitEthernet0/1',
        'description': 'LAN Interface'
    }
}

result = template.render(**variables)
print(result)
```

## 问题诊断流程

建议按以下顺序排查：

1. **查看日志**: 首先查看相关服务的日志
2. **检查配置**: 验证配置文件和环境变量
3. **测试连接**: 测试网络和设备连接
4. **检查资源**: 检查系统资源使用情况
5. **参考文档**: 查看相关文档

## 获取帮助

如果以上方法无法解决问题：

1. **查看详细日志**: `docker compose logs`
2. **收集错误信息**: 记录完整的错误消息和上下文
3. **提供环境信息**: 操作系统、Docker 版本、配置信息等
4. **提交 Issue**: 在 GitHub 上提交详细的问题报告
