# Webhook 系统

NetPulse 支持通过网络钩子（Webhooks）将任务执行结果通知到外部系统，便于集成监控系统、自动化工作流或支持 HTTP 的服务。

## 调用流程

任务执行和 Webhook 调用的流程如下：

```mermaid
sequenceDiagram
    participant Controller as Controller
    participant Redis as Redis Job Queue
    participant Worker as Worker
    participant Hook as WebHook Caller
    participant External as External Service

    Controller->>Redis: Schedule and Enqueue Job
    Redis-->>Worker: Job Assigned
    Worker->>Worker: Execute Job
    
    alt 任务成功
        Worker->>Redis: Store Result (成功)
        Worker->>Hook: 触发成功回调
        Hook->>Hook: 从 job.kwargs 获取 req
        Hook->>Hook: 实例化 Webhook Caller
        Hook-->>External: HTTP Request (包含任务结果)
        External-->>Hook: Response
    else 任务失败
        Worker->>Redis: Store Result (失败)
        Worker->>Hook: 触发失败回调
        Hook->>Hook: 处理异常信息
        Hook-->>External: HTTP Request (包含错误信息)
        External-->>Hook: Response
    end
    
    Note over Hook: Webhook 调用失败不影响任务结果<br/>仅记录警告日志
```

### 调用时机

Webhook 在以下时机被调用：

1. **任务成功完成**：Worker 执行完任务后，通过 RQ 的 `on_success` 回调触发
2. **任务执行失败**：Worker 捕获异常后，通过 RQ 的 `on_failure` 回调触发

### 实现机制

Webhook 调用通过 RQ 的回调机制实现：

```python
# 在任务入队时设置回调
job = queue.enqueue(
    func,
    on_success=rpc_webhook_callback,  # 成功回调
    on_failure=rpc_webhook_callback,  # 失败回调
    **kwargs
)

# 回调函数从 job.kwargs 中获取请求信息
def rpc_webhook_callback(*args):
    job = args[0]
    req = job.kwargs.get("req")  # 获取原始请求
    webhook = req.webhook
    
    # 实例化并调用 Webhook
    caller = webhooks[webhook.name](webhook)
    caller.call(req=req, job=job, result=result)
```

## Webhook 配置

### 基本配置

```json
{
  "name": "basic",
  "url": "http://monitor.example.com/callback",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-token"
  }
}
```

### 配置选项

| 字段     | 类型    | 描述                         | 默认值 |
|----------|---------|-------------------------------------|---------|
| name     | string  | WebHook 调用类型 ("basic")       | "basic" |
| url      | string  | Webhook 端点 URL                | 必填    |
| method   | string  | HTTP 方法 (GET/POST/PUT/DELETE)   | "POST"  |
| headers  | object  | 自定义 HTTP 头                 | null    |
| cookies  | object  | 自定义 cookies                  | null    |
| auth     | array   | 基本认证 [用户名, 密码]     | null    |
| timeout  | number  | 请求超时时间（秒）          | 5.0     |

## 示例

1. 请求时设置 Webhook
   
    使用 `webhook` 字段在任务请求中附加 Webhook 配置：

    ```json
    {
      "driver": "netmiko",
      "connection_args": {
        "device_type": "cisco_ios",
        "host": "192.168.1.1",
        "username": "admin",
        "password": "pwd123"
      },
      "command": "show version",
      "webhook": {
        "name": "basic",
        "url": "http://monitor.example.com/callback",
        "method": "POST",
        "headers": {
          "Content-Type": "application/json"
        },
        "timeout": 5.0
      }
    }
    ```

2. 在外部服务中处理 Webhook 消息

    默认的 Basic Webhook 会将任务执行结果发送到指定的 URL。Webhook 请求体包含以下信息：

    **成功任务的回调示例**：
    ```json
    {
      "id": "job-uuid-here",
      "result": "Interface GigabitEthernet1/0/1\n description Core Link"
    }
    ```

    **失败任务的回调示例**：
    ```json
    {
      "id": "job-uuid-here",
      "result": "Connection timeout: Unable to connect to device"
    }
    ```

    !!! note "结果格式"
        Webhook 中的 `result` 字段是字符串格式，包含任务执行的原始结果或错误信息。

## 注意事项

1. **超时限制**
    - 最小值：0.5 秒
    - 最大值：120.0 秒
    - 默认值：5.0 秒

2. **HTTP 方法**
    - 支持：GET, POST, PUT, DELETE, PATCH
    - 默认：POST

3. **错误处理**
    - 请求失败时会输出警告日志，但不会影响任务执行结果
    - 请求失败时不会重试（避免阻塞 Worker）
    - Webhook 异常不会导致任务失败
    - 建议在外部服务端实现幂等性和重试机制

!!! warning "Webhook 可靠性"
    Webhook 调用是"尽力而为"的，不保证一定成功。如果需要可靠的通知机制，建议：
    - 在外部服务端实现幂等性处理
    - 使用消息队列（如 RabbitMQ、Kafka）作为中间层
    - 定期轮询任务状态作为备用方案

## 自定义 Webhook 开发

NetPulse 内置的 Basic Webhook 可以满足大部分需求，但如果需要更复杂的逻辑，可以通过实现 `BaseWebHookCaller` 类来创建自定义 Webhook。

1. 在 `netpulse/plugins/webhooks/` 中创建新目录
2. 继承 `BaseWebHookCaller` 类并实现所需方法
  ```python
  class CustomWebHookCaller:
    webhook_name: str = "custom"

    def call(self, req: Any, job: rq.job.Job, result: Any, **kwargs):
    # ...

    # 具体方法请参考 BaseWebHookCaller 类
  ```
3. 在 `__init__.py` 中注册 Webhook
  ```python
  __all__ = [CustomWebHookCaller]
  ```

关于插件系统的详细介绍，请参考[插件系统](./plugin-system.md)。