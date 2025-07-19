# 快速开始

本指南将帮助您在5分钟内快速上手 NetPulse，体验其强大的网络设备管理能力。

## 学习目标

通过本指南，您将学会：
- 部署 NetPulse 服务
- 配置网络设备连接
- 执行第一个API调用
- 查看设备状态信息

## 前置要求

### 系统要求
- **操作系统**: Linux (推荐 Ubuntu 22.04+)
- **Docker**: 版本 20.10+ 
- **Docker Compose**: 版本 2.0+
- **CPU**: 不少于 8C
- **内存**: 不少于 16GB

**在设备连接数量增多或并发任务执行时，建议提升系统资源以确保稳定性。**

### 网络设备
- 支持 SSH 的网络设备（路由器、交换机等）
- 设备IP地址和登录凭据

## 步骤

### 步骤1: 获取代码

```bash
# 克隆项目仓库
git clone https://github.com/netpulse/netpulse.git
cd netpulse

# 检查项目结构
ls -la
```

### 步骤2: 环境配置

```bash
# 运行环境检查脚本
bash ./scripts/setup_env.sh

# 生成环境配置文件
bash ./scripts/setup_env.sh generate
```

这将创建 `.env` 文件，包含所有必要的配置参数。

### 步骤3: 启动服务

```bash
# 使用 Docker Compose 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

服务启动后，您将看到以下容器：
- `netpulse-controller`: API控制器 (端口 9000)
- `netpulse-node-worker`: 节点工作进程 (2个实例)
- `netpulse-fifo-worker`: FIFO工作进程
- `netpulse-redis`: Redis缓存

### 步骤4: 获取API密钥

```bash
# 查看生成的API密钥
cat .env | grep NETPULSE_SERVER__API_KEY

# 或者从日志中获取
docker compose logs controller | grep "API Key"
```

### 步骤5: 测试API连接

```bash
# 测试健康检查端点
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/health

# 预期响应
{
  "code": 0,
  "message": "success",
  "data": "ok"
}
```

### 步骤6: 测试设备连接

准备设备信息
```json
{
  "driver": "netmiko",
  "connection_args": {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "your_password",
    "device_type": "cisco_ios",
    "port": 22
  }
}
```

测试连接
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin", 
      "password": "your_password",
      "device_type": "cisco_ios",
      "port": 22
    }
  }' \
  http://localhost:9000/device/test-connection
```

### 步骤7: 执行第一个命令

```bash
# 获取设备信息
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "host": "192.168.1.1",
      "username": "admin",
      "password": "your_password",
      "device_type": "cisco_ios",
      "port": 22
    },
    "command": "show version"
  }' \
  http://localhost:9000/device/execute
```

### 恭喜！

您已成功完成 NetPulse 的快速开始！现在您可以：

- ✅ 部署并运行 NetPulse 服务
- ✅ 连接网络设备
- ✅ 执行网络命令
- ✅ 获取设备信息

## 下一步

### 深入学习
- **[第一个API调用](first-steps.md)** - 更多API使用示例
- **[API参考](../guides/api.md)** - 完整的API文档

### 高级功能
- **[批量操作](../advanced/batch-operations.md)** - 管理多台设备
- **[模板系统](../advanced/templates.md)** - 使用模板简化操作
- **[长连接技术](../architecture/long-connection.md)** - 了解核心技术
- **[性能调优](../advanced/performance-tuning.md)** - 优化系统性能

## 遇到问题？

如果遇到任何问题，请参考：
- **[日志分析](../troubleshooting/log-analysis.md)** - 日志解读和问题诊断
- **[GitHub Issues](https://github.com/netpulse/issues)** - 提交问题反馈

---

<div align="center">

**准备好开始您的网络自动化之旅了吗？**

[第一个API调用 →](first-steps.md)

</div> 