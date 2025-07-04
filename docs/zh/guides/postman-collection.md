# Postman Collection

## 快速开始

Postman 是常用的 API 测试与调试工具，NetPulse 提供官方 Postman 集合，帮助用户快速体验和验证 API。

## 📦 获取官方集合

- 下载地址：[NetPulse Postman Collection](https://netpulse.readthedocs.io/assets/netpulse.postman_collection.json)
- 或在项目 `docs-draft/assets/` 目录下查找 `netpulse.postman_collection.json`

## 🚀 导入集合

1. 打开 Postman，点击左上角 `Import` 按钮
2. 选择 `File`，上传 `netpulse.postman_collection.json`
3. 导入后可在左侧看到 NetPulse API 的所有接口

## 🔑 配置环境变量

建议在 Postman 中配置如下环境变量：
- `base_url`：API 基础地址（如 `http://localhost:9000`）
- `api_key`：API 认证密钥

## 📝 常用用例

- 设备管理：添加、删除、查询设备
- 命令执行：单命令、批量命令、并发命令
- 配置管理：获取/保存/备份配置
- 日志与监控：查询操作日志、健康检查

## ⚙️ 自动化测试建议

- 利用 Postman 的 `Tests` 脚本自动校验响应内容
- 可批量运行集合，实现回归测试
- 支持环境切换（开发/测试/生产）

## 💡 最佳实践

- 导入集合后，先配置好环境变量，避免每次手动填写
- 可将常用请求保存为个人模板，便于团队协作
- 利用 Postman Monitor 实现定时自动化 API 检查

---

<div align="center">

**用 Postman 快速体验和验证 NetPulse API！**

</div> 