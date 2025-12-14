# Changelog

## [0.3.0] - 2025-12-14

### Added 

- **凭据插件架构**: 新增可扩展的凭据插件系统，支持从外部凭据管理系统动态获取设备认证信息
  - 插件化设计，支持多种凭据提供器
  - 自动解析凭据并注入到连接参数中
  - 支持在 API 请求中通过 `credential` 字段引用凭据，避免在请求中传递明文密码
- **Vault KV 凭据插件**: 集成 HashiCorp Vault KV v2 引擎，实现安全的凭据管理
  - 支持从 Vault KV v2 读取设备凭据（用户名、密码等）
  - 支持 Token 和 AppRole 两种认证方式
  - 支持路径白名单（`allowed_paths`）限制访问范围，提升安全性
  - 支持命名空间（namespace）隔离
  - 支持凭据缓存（`cache_ttl`）提升性能，减少 Vault API 调用
  - 支持自定义字段映射（`field_mapping`），灵活适配不同的 Vault 数据结构
  - 支持版本化密钥读取
  - 完整的单元测试覆盖
- 支持在任意命令之前执行 template rendering，在命令执行之后进行 template parsing
- 添加单元测试、端到端测试、CI/CD 集成
- **增强 Webhook 上报数据**: Webhook 通知现在包含完整的任务上下文信息
  - 设备信息（host, device_type）用于任务追踪
  - 驱动信息用于识别执行方法
  - 命令/配置信息用于追踪执行的操作
  - 状态字段（success/failed）用于快速识别
  - 改进多命令结果的格式化，提供更易读的输出
  - 支持嵌套字典结果格式（如 paramiko 驱动）

### Changed

- **重大 API 重构**: 统一 API 和 CLI 体验，简化使用方式
  - **统一设备操作接口** `/device/exec`: 自动识别操作类型（查询/配置），无需区分不同端点
    - 包含 `command` 字段时自动识别为查询操作
    - 包含 `config` 字段时自动识别为配置操作
    - 根据驱动类型自动选择队列策略（可手动指定）
  - **统一模板接口**: `/template/render` 和 `/template/parse` 支持自动识别引擎/解析器
  - **简化请求模型**: 统一请求/响应格式，减少 API 复杂度
  - **CLI 集成**: 将独立的 `netpulse-client` 包集成到主项目，统一开发体验
  - 重构后的 API 设计提升了扩展性和可维护性
- 优化 Docker 镜像构建流程，减小镜像体积
- 升级 TTP 模板解析器到 0.10.0

### Fixed

- 修复批量任务中缺失的失败回调
- 修复序列化错误
- 修复验证相关的 bug
- 修复测试配置读取问题
- 修复 Postman collection：将测试响应字段从 `connection_time` 更新为 `latency`
- 修复多个测试用例中的 bug

### Documentation

- 新增凭据配置指南文档（中英文），详细介绍 Vault KV 凭据插件的配置和使用方法
- 更新 API 文档，补充凭据相关字段说明
- 修复 Postman collection 示例
- 修复文档中的选项说明

## [0.2.0] - 2025-11-09

### Added

- **Paramiko 驱动**: 新增 Paramiko 驱动，支持 Linux 服务器管理
  - 支持多种认证方式（密码、密钥文件、密钥内容）
  - 支持 SFTP 文件传输（上传/下载/断点续传）
  - 支持 SSH 代理/跳板机连接
  - 支持 sudo 权限执行和 PTY 模式

## [0.1.0] - 2025-7-04

### Added

- 初始版本发布
- 支持 Netmiko、NAPALM、PyEAPI 驱动
- 支持长连接技术、分布式架构、插件系统
- 支持模板引擎（Jinja2、TextFSM、TTP）和 Webhook 通知

