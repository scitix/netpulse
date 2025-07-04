# NetPulse 文档中心

欢迎来到 NetPulse 文档中心！NetPulse 是一个专为网络设备管理设计的分布式 RESTful API 服务器，提供统一的多厂商网络设备管理接口。

![NetPulse 项目价值定位](assets/images/architecture/project-value-proposition.svg)

## 核心特性

- **RESTful API**: 简洁高效的异步API，支持多厂商网络设备
- **AI Agent 支持**: 智能网络操作，支持AI Agent和MCP客户端
- **多协议支持**: Telnet、SSH、HTTP(S)等多种连接协议
- **高性能**: 持久化SSH连接，支持keepalive机制
- **分布式架构**: 可扩展的多主设计，高可用性
- **可扩展性**: 插件系统支持驱动、模板、调度器和Webhook
- **模板引擎**: 支持Jinja2、TextFSM、TTP模板格式

## 快速开始

### 一键部署
```bash
git clone <repository-url>
cd netpulse
bash ./scripts/docker_deploy.sh
```

### 手动设置
```bash
# 生成环境配置
bash ./scripts/check_env.sh generate

# 启动服务
docker compose up -d

# 测试API
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:9000/health
```

## 系统架构

![NetPulse 核心工作流程](assets/images/architecture/workflow-overview.svg)

## 文档导航

### 新用户指南
- **[快速开始](getting-started/quick-start.md)** - 5分钟快速上手
- **[第一个API调用](getting-started/first-steps.md)** - 学习基础API使用
- **[部署指南](getting-started/deployment.md)** - 生产环境部署

### 使用指南
- **[API参考](guides/api.md)** - 完整的API文档
- **[CLI工具](guides/cli.md)** - 命令行工具使用
- **[配置管理](guides/configuration.md)** - 系统配置详解
- **[SDK指南](guides/sdk-guide.md)** - SDK使用说明
- **[Postman集合](guides/postman-collection.md)** - API测试工具

### 高级功能
- **[批量操作](advanced/batch-operations.md)** - 大规模设备管理
- **[模板系统](advanced/templates.md)** - 模板引擎使用
- **[Webhook配置](advanced/webhooks.md)** - Webhook设置
- **[性能调优](advanced/performance-tuning.md)** - 性能优化指南

### 系统架构
- **[架构概览](architecture/overview.md)** - 系统整体设计
- **[架构设计](architecture/architecture.md)** - 详细架构说明
- **[长连接技术](architecture/long-connection.md)** - 连接技术详解
- **[任务调度器](architecture/schedulers.md)** - 调度器机制
- **[驱动系统](architecture/drivers.md)** - 设备驱动详解
- **[模板系统](architecture/templates.md)** - 模板系统架构
- **[Webhook系统](architecture/webhooks.md)** - Webhook架构
- **[插件系统](architecture/plugins.md)** - 插件扩展机制

### 参考文档
- **[配置参数](reference/configuration.md)** - 完整配置选项
- **[环境变量](reference/environment-variables.md)** - 环境变量说明
- **[错误代码](reference/error-codes.md)** - 错误处理指南
- **[最佳实践](reference/best-practices.md)** - 使用建议

### 故障排除
- **[日志分析](troubleshooting/log-analysis.md)** - 日志解读


## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](https://github.com/netpulse/LICENSE) 文件。

---