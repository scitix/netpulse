# 术语表

本文档定义了 NetPulse 系统中使用的主要术语。

## 核心概念

### API Key
用于认证和授权访问 NetPulse API 的密钥，通过 HTTP 头 `X-API-KEY` 传递。

### Controller
NetPulse 的核心组件，提供 RESTful API 接口，负责接收请求、验证 API 密钥、分发任务到队列。

### Worker
执行具体网络设备操作的进程，包括：
- **Node Worker**: 节点工作进程，管理设备连接
- **Fifo Worker**: FIFO 队列工作进程
- **Pinned Worker**: 设备绑定工作进程，支持连接复用

### Queue
存储待执行任务的数据结构，支持两种策略：
- **FIFO 队列**: 先进先出，适合一次性操作
- **Pinned 队列**: 设备绑定，支持连接复用

### Driver
用于连接和管理特定类型网络设备的组件：
- **Netmiko**: 通用 SSH 驱动
- **NAPALM**: 跨厂商标准化驱动
- **PyEAPI**: Arista 专用驱动

### Scheduler
管理任务调度的组件，支持：
- `least_load`: 最少负载调度
- `load_weighted_random`: 负载加权随机调度

### Plugin
扩展 NetPulse 功能的组件，包括：
- 驱动插件：支持新的设备类型
- 模板插件：自定义模板引擎
- 调度器插件：自定义任务调度
- Webhook 插件：事件通知

### Template
用于生成配置或解析输出的模板文件：
- **Jinja2**: 配置模板引擎
- **TextFSM**: 文本解析模板
- **TTP**: 配置解析模板

### Long Connection
保持与网络设备的持久连接，减少连接建立时间，提高命令执行效率。

### Job
在 NetPulse 中执行的具体操作，包含任务ID、状态、参数、结果等信息。

## 技术术语

### Redis
内存数据库，用于任务队列和状态存储。

### RESTful API
符合 REST 架构风格的 API 设计，使用标准 HTTP 方法。

### SSH
安全外壳协议，用于远程连接网络设备。

### TTL
连接或缓存的生存时间，单位：秒。

### Webhook
事件通知机制，当任务完成或状态变化时发送通知。
