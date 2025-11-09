# Changelog

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

