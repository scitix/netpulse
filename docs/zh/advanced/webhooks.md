# Webhook 配置指南

NetPulse 支持 Webhook 功能，可在特定事件发生时自动向外部系统发送通知。

## 支持的事件类型

| 事件类型 | 触发条件 |
|----------|----------|
| device.connected | 设备连接成功 |
| device.disconnected | 设备连接断开 |
| command.executed | 命令执行完成 |
| command.failed | 命令执行失败 |
| config.changed | 配置变更 |
| system.alert | 系统告警 |

## 配置方式

### 1. 通过API配置
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "监控告警",
    "url": "https://your-webhook-url.com/webhook",
    "events": ["device.disconnected", "command.failed"],
    "headers": {
      "Authorization": "Bearer your-webhook-token"
    },
    "enabled": true
  }' \
  http://localhost:9000/webhooks
```

### 2. 配置文件方式
```yaml
webhooks:
  - name: "监控告警"
    url: "https://your-webhook-url.com/webhook"
    events:
      - device.disconnected
      - command.failed
    headers:
      Authorization: "Bearer your-webhook-token"
    enabled: true
    retry_count: 3
    timeout: 30
```

## 重试机制
- 支持设置 retry_count、timeout 等参数。
- 失败自动重试，最大重试次数可配置。

## 注意事项
- 建议生产环境使用 HTTPS。
- 复杂模板推送、签名校验等为建议/规划功能，当前未实现。

---

如需详细参数说明，请参考 API 文档或联系开发者。 