# 错误代码

本文档说明 NetPulse API 的错误响应格式和常见错误情况。

## 响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

### 错误响应

NetPulse 使用统一的错误响应格式：

```json
{
  "code": -1,
  "message": "错误描述",
  "data": "错误详情或数据"
}
```

**说明**：
- `code: 200` 表示请求成功
- `code: -1` 表示请求失败
- `message` 包含错误描述
- `data` 包含错误详情（可能是字符串或对象）

## HTTP 状态码

NetPulse API 使用标准 HTTP 状态码：

| 状态码 | 说明 | 常见场景 |
|--------|------|----------|
| `200` | OK | 请求成功 |
| `201` | Created | 任务创建成功 |
| `400` | Bad Request | 请求参数错误、验证失败 |
| `403` | Forbidden | API 密钥无效或缺失 |
| `404` | Not Found | 资源不存在（如模板引擎未找到） |
| `500` | Internal Server Error | 服务器内部错误 |

## 常见错误情况

### 1. API 密钥错误

**HTTP 状态码**: `403`

**响应示例**:
```json
{
  "code": -1,
  "message": "Invalid or missing API key."
}
```

**解决方案**:
- 检查请求头中是否包含 `X-API-KEY`
- 验证 API 密钥是否正确
- 确认 API 密钥与配置文件中的 `server.api_key` 一致

### 2. 请求参数验证错误

**HTTP 状态码**: `400`

**响应示例**:
```json
{
  "code": -1,
  "message": "Validation Error",
  "data": [
    {
      "type": "missing",
      "loc": ["body", "driver"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

**解决方案**:
- 检查请求体是否包含所有必需字段
- 验证字段类型和格式是否正确
- 参考 API 文档确认参数要求

### 3. 值错误

**HTTP 状态码**: `400`

**响应示例**:
```json
{
  "code": -1,
  "message": "Value Error",
  "data": "具体错误信息"
}
```

**常见原因**:
- 驱动名称不存在
- 模板引擎或解析器未找到
- 配置参数值不合法

### 4. 服务器内部错误

**HTTP 状态码**: `500`

**响应示例**:
```json
{
  "code": -1,
  "message": "Internal Server Error",
  "data": "错误堆栈信息"
}
```

**解决方案**:
- 查看服务器日志获取详细错误信息
- 检查系统资源（内存、CPU、网络）
- 验证 Redis 连接是否正常

## 任务执行错误

任务执行失败时，错误信息包含在任务结果中：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": "job_id",
    "status": "failed",
    "result": {
      "type": 2,
      "error": {
        "type": "ConnectionError",
        "message": "连接超时"
      }
    }
  }
}
```

**错误类型**:
- `ConnectionError`: 设备连接失败
- `TimeoutError`: 操作超时
- `AuthenticationError`: 设备认证失败
- 其他 Python 异常类型

## 错误处理示例

### Python 示例

```python
import requests

def call_api(url, api_key, data=None):
    headers = {"X-API-KEY": api_key}
    
    try:
        if data:
            response = requests.post(url, headers=headers, json=data)
        else:
            response = requests.get(url, headers=headers)
        
        result = response.json()
        
        # 检查业务错误码
        if result.get("code") == -1:
            print(f"API 错误: {result.get('message')}")
            print(f"错误详情: {result.get('data')}")
            return None
        
        return result.get("data")
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("API 密钥错误，请检查配置")
        elif e.response.status_code == 400:
            print("请求参数错误")
        else:
            print(f"HTTP 错误: {e.response.status_code}")
        return None
```

### 检查任务状态

```python
def check_job_status(job_id, api_key):
    url = f"http://localhost:9000/job?id={job_id}"
    headers = {"X-API-KEY": api_key}
    
    response = requests.get(url, headers=headers)
    result = response.json()
    
    if result.get("code") == 200:
        job = result.get("data", [])[0]
        
        if job.get("status") == "failed":
            error = job.get("result", {}).get("error", {})
            print(f"任务失败: {error.get('type')} - {error.get('message')}")
            return False
        
        return True
    
    return False
```

## 调试建议

1. **查看日志**: 使用 `docker compose logs` 查看详细错误信息
2. **验证配置**: 确认配置文件和环境变量设置正确
3. **测试连接**: 使用 `/device/test-connection` 端点测试设备连接
4. **检查网络**: 确认网络连接和设备可达性
