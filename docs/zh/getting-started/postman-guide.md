# Postman 使用指南

!!! info "为什么选择 Postman？"
    Postman 是体验 NetPulse API 的最佳方式！无需编写代码，通过图形界面即可快速测试和体验所有 API 功能。

## 获取集合

- **本地文件**：项目根目录下的 `@NetPulse.postman_collection.json`（即 `postman/NetPulse.postman_collection.json`）

## 导入集合

1. 打开 [Postman](https://www.postman.com)
2. 点击 `Import` → `File`，选择项目根目录下的 `postman/NetPulse.postman_collection.json`
3. 导入后左侧显示 NetPulse API 文件夹

## 配置环境变量

创建环境 `NetPulse Local`，配置以下变量：

| 变量名 | 初始值 | 说明 |
|--------|--------|------|
| `base_url` | `http://localhost:9000` | API 服务器地址 |
| `api_key` | `np_90fbd8685671a2c0b...` | API 认证密钥 |

!!! tip "获取 API Key"
    启动服务后，API Key 在控制台输出中显示，或查看 `.env` 文件。

## 快速体验

1. **健康检查**：执行 `System Health > Health Check`
2. **连接测试**：执行 `Device Connection Testing` 下的测试请求
3. **命令执行**：使用 `Netmiko Driver` 执行设备命令
4. **批量操作**：体验 `Batch Operations` 的并发处理

## 功能模块

- **System Health**：系统健康检查
- **Job Management**：任务管理
- **Worker Management**：工作进程管理
- **Device Connection Testing**：设备连接测试
- **Netmiko Driver**：Netmiko 驱动操作
- **NAPALM Driver**：NAPALM 驱动操作
- **PyEAPI Driver**：PyEAPI 驱动操作
- **Batch Operations**：批量操作
- **Template Operations**：模板操作
