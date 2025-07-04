# 错误代码说明

本文档详细说明了 NetPulse API 中所有可能的错误代码，包括 HTTP 状态码、业务错误代码、错误处理方法和示例。

## 📋 错误代码总览

### 错误分类
- **HTTP状态码**: 标准HTTP响应状态码
- **业务错误代码**: NetPulse特定的业务错误代码
- **设备错误代码**: 网络设备相关的错误代码
- **系统错误代码**: 系统内部错误代码

## 🌐 HTTP状态码

### 成功状态码
| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| `200` | OK | 请求成功，返回数据 |
| `201` | Created | 资源创建成功 |
| `204` | No Content | 请求成功，无返回内容 |

### 客户端错误状态码
| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| `400` | Bad Request | 请求参数错误 |
| `401` | Unauthorized | 认证失败 |
| `403` | Forbidden | 权限不足 |
| `404` | Not Found | 资源不存在 |
| `405` | Method Not Allowed | 请求方法不允许 |
| `409` | Conflict | 资源冲突 |
| `422` | Unprocessable Entity | 请求格式正确但语义错误 |
| `429` | Too Many Requests | 请求频率超限 |

### 服务器错误状态码
| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| `500` | Internal Server Error | 服务器内部错误 |
| `502` | Bad Gateway | 网关错误 |
| `503` | Service Unavailable | 服务不可用 |
| `504` | Gateway Timeout | 网关超时 |

## 🔧 业务错误代码

### 认证和授权错误
| 错误代码 | 说明 | HTTP状态码 | 解决方案 |
|----------|------|------------|----------|
| `unauthorized` | API密钥无效或过期 | 401 | 检查API密钥是否正确 |
| `invalid_token` | 令牌格式错误 | 401 | 检查令牌格式 |
| `token_expired` | 令牌已过期 | 401 | 重新获取令牌 |
| `insufficient_permissions` | 权限不足 | 403 | 联系管理员提升权限 |
| `access_denied` | 访问被拒绝 | 403 | 检查访问权限 |

### 请求参数错误
| 错误代码 | 说明 | HTTP状态码 | 解决方案 |
|----------|------|------------|----------|
| `invalid_parameters` | 请求参数错误 | 400 | 检查请求参数格式 |
| `missing_required_field` | 缺少必需字段 | 400 | 补充必需字段 |
| `invalid_field_format` | 字段格式错误 | 400 | 修正字段格式 |
| `field_too_long` | 字段长度超限 | 400 | 缩短字段长度 |
| `invalid_enum_value` | 枚举值无效 | 400 | 使用有效的枚举值 |

### 设备相关错误
| 错误代码 | 说明 | HTTP状态码 | 解决方案 |
|----------|------|------------|----------|
| `device_not_found` | 设备不存在 | 404 | 检查设备ID是否正确 |
| `device_offline` | 设备离线 | 503 | 检查设备连接状态 |
| `connection_failed` | 设备连接失败 | 500 | 检查网络连接和设备配置 |
| `authentication_failed` | 设备认证失败 | 401 | 检查设备用户名密码 |
| `command_not_supported` | 命令不支持 | 400 | 检查设备类型和命令兼容性 |
| `privilege_level_required` | 需要特权级别 | 403 | 提供enable密码 |

### 命令执行错误
| 错误代码 | 说明 | HTTP状态码 | 解决方案 |
|----------|------|------------|----------|
| `command_failed` | 命令执行失败 | 400 | 检查命令语法 |
| `command_timeout` | 命令执行超时 | 408 | 增加超时时间或简化命令 |
| `invalid_command` | 无效命令 | 400 | 检查命令格式 |
| `command_rejected` | 命令被拒绝 | 400 | 检查命令权限 |
| `syntax_error` | 语法错误 | 400 | 修正命令语法 |

### 系统错误
| 错误代码 | 说明 | HTTP状态码 | 解决方案 |
|----------|------|------------|----------|
| `internal_error` | 系统内部错误 | 500 | 查看系统日志 |
| `database_error` | 数据库错误 | 500 | 检查数据库连接 |
| `redis_error` | Redis错误 | 500 | 检查Redis连接 |
| `worker_unavailable` | Worker不可用 | 503 | 检查Worker服务状态 |
| `service_unavailable` | 服务不可用 | 503 | 检查服务状态 |

### 速率限制错误
| 错误代码 | 说明 | HTTP状态码 | 解决方案 |
|----------|------|------------|----------|
| `rate_limit_exceeded` | 请求频率超限 | 429 | 降低请求频率 |
| `quota_exceeded` | 配额超限 | 429 | 联系管理员增加配额 |
| `too_many_connections` | 连接数超限 | 429 | 减少并发连接 |

## 📊 错误响应格式

### 标准错误响应
```json
{
  "success": false,
  "error": "error_code",
  "message": "错误描述",
  "details": {
    "field": "具体字段",
    "value": "错误值",
    "expected": "期望值"
  },
  "timestamp": "2024-01-01T12:00:00+08:00",
  "request_id": "req_1234567890"
}
```

### 详细错误响应
```json
{
  "success": false,
  "error": "validation_error",
  "message": "请求参数验证失败",
  "details": {
    "errors": [
      {
        "field": "hostname",
        "message": "主机名不能为空",
        "code": "missing_required_field"
      },
      {
        "field": "port",
        "message": "端口号必须在1-65535之间",
        "code": "invalid_field_format",
        "value": 70000
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00+08:00",
  "request_id": "req_1234567890"
}
```

## 🔍 错误处理示例

### Python错误处理
```python
import requests
from typing import Dict, Any

class NetPulseError(Exception):
    """NetPulse API异常"""
    def __init__(self, error_code: str, message: str, status_code: int, details: Dict = None):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

def handle_api_response(response: requests.Response) -> Dict[str, Any]:
    """处理API响应"""
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_data = {}
        try:
            error_data = response.json()
        except:
            pass
        
        error_code = error_data.get('error', 'unknown_error')
        message = error_data.get('message', str(e))
        details = error_data.get('details', {})
        
        raise NetPulseError(error_code, message, response.status_code, details)

def api_call(url: str, headers: Dict, data: Dict = None) -> Dict[str, Any]:
    """API调用示例"""
    try:
        if data:
            response = requests.post(url, headers=headers, json=data)
        else:
            response = requests.get(url, headers=headers)
        
        return handle_api_response(response)
    except NetPulseError as e:
        # 处理特定错误
        if e.error_code == 'rate_limit_exceeded':
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"请求频率超限，{retry_after}秒后重试")
            time.sleep(retry_after)
            return api_call(url, headers, data)
        elif e.error_code == 'device_not_found':
            print(f"设备不存在: {e.details.get('device_id')}")
        elif e.error_code == 'connection_failed':
            print(f"设备连接失败: {e.details.get('hostname')}")
        else:
            print(f"API错误: {e.message}")
        raise e
    except Exception as e:
        print(f"未知错误: {e}")
        raise e
```

### JavaScript错误处理
```javascript
class NetPulseError extends Error {
    constructor(errorCode, message, statusCode, details = {}) {
        super(message);
        this.name = 'NetPulseError';
        this.errorCode = errorCode;
        this.statusCode = statusCode;
        this.details = details;
    }
}

async function handleApiResponse(response) {
    if (response.ok) {
        return await response.json();
    }
    
    let errorData = {};
    try {
        errorData = await response.json();
    } catch (e) {
        // 无法解析JSON响应
    }
    
    const errorCode = errorData.error || 'unknown_error';
    const message = errorData.message || response.statusText;
    const details = errorData.details || {};
    
    throw new NetPulseError(errorCode, message, response.status, details);
}

async function apiCall(url, headers, data = null) {
    try {
        const options = {
            method: data ? 'POST' : 'GET',
            headers: headers
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        return await handleApiResponse(response);
    } catch (error) {
        if (error instanceof NetPulseError) {
            // 处理特定错误
            switch (error.errorCode) {
                case 'rate_limit_exceeded':
                    const retryAfter = response.headers.get('Retry-After') || 60;
                    console.log(`请求频率超限，${retryAfter}秒后重试`);
                    await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
                    return apiCall(url, headers, data);
                case 'device_not_found':
                    console.log(`设备不存在: ${error.details.device_id}`);
                    break;
                case 'connection_failed':
                    console.log(`设备连接失败: ${error.details.hostname}`);
                    break;
                default:
                    console.log(`API错误: ${error.message}`);
            }
        } else {
            console.log(`未知错误: ${error.message}`);
        }
        throw error;
    }
}
```

### Bash错误处理
```bash
#!/bin/bash

# API调用函数
api_call() {
    local url="$1"
    local api_key="$2"
    local data="$3"
    
    # 设置请求头
    local headers=(
        "Authorization: Bearer $api_key"
        "Content-Type: application/json"
    )
    
    # 发送请求
    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" \
            -H "${headers[0]}" \
            -H "${headers[1]}" \
            -d "$data" \
            "$url")
    else
        response=$(curl -s -w "\n%{http_code}" \
            -H "${headers[0]}" \
            "$url")
    fi
    
    # 分离响应体和状态码
    local body=$(echo "$response" | head -n -1)
    local status_code=$(echo "$response" | tail -n 1)
    
    # 检查状态码
    if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 300 ]; then
        echo "$body"
        return 0
    else
        # 解析错误信息
        local error_code=$(echo "$body" | jq -r '.error // "unknown_error"')
        local message=$(echo "$body" | jq -r '.message // "Unknown error"')
        
        echo "错误: $message (代码: $error_code, 状态: $status_code)" >&2
        
        # 处理特定错误
        case $error_code in
            "rate_limit_exceeded")
                local retry_after=$(echo "$body" | jq -r '.details.retry_after // 60')
                echo "请求频率超限，${retry_after}秒后重试..." >&2
                sleep "$retry_after"
                api_call "$url" "$api_key" "$data"
                ;;
            "device_not_found")
                echo "设备不存在" >&2
                ;;
            "connection_failed")
                echo "设备连接失败" >&2
                ;;
            *)
                echo "未知错误" >&2
                ;;
        esac
        
        return 1
    fi
}

# 使用示例
api_key="your_api_key"
url="http://localhost:9000/devices"

# 获取设备列表
result=$(api_call "$url" "$api_key")
if [ $? -eq 0 ]; then
    echo "设备列表: $result"
else
    echo "获取设备列表失败"
fi
```

## 🔧 错误调试

### 1. 启用调试模式
```bash
# 设置调试环境变量
export DEBUG=true
export LOG_LEVEL=DEBUG

# 查看详细错误信息
curl -v -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/devices
```

### 2. 查看错误日志
```bash
# 查看API服务日志
docker compose logs api

# 查看Worker服务日志
docker compose logs worker

# 查看系统日志
tail -f /var/log/netpulse/netpulse.log
```

### 3. 错误诊断工具
```python
#!/usr/bin/env python3
# error_diagnosis.py

import requests
import json
from typing import Dict, Any

def diagnose_error(url: str, api_key: str, data: Dict = None) -> Dict[str, Any]:
    """错误诊断工具"""
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        if data:
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            response = requests.get(url, headers=headers, timeout=30)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"响应体: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应体: {response.text}")
        
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_data if response.ok else response.text
        }
        
    except requests.exceptions.Timeout:
        print("请求超时")
        return {"error": "timeout"}
    except requests.exceptions.ConnectionError:
        print("连接错误")
        return {"error": "connection_error"}
    except Exception as e:
        print(f"未知错误: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    api_key = "your_api_key"
    url = "http://localhost:9000/devices"
    
    result = diagnose_error(url, api_key)
    print(f"诊断结果: {result}")
```

## 📚 常见错误解决方案

### 1. 认证错误
```bash
# 检查API密钥
echo $API_KEY

# 重新生成API密钥
docker compose exec api python -c "
from netpulse.core.auth import generate_api_key
print(generate_api_key())
"
```

### 2. 设备连接错误
```bash
# 测试设备连接
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "hostname": "192.168.1.1",
       "username": "admin",
       "password": "password123",
       "device_type": "cisco_ios"
     }' \
     http://localhost:9000/devices/test
```

### 3. 速率限制错误
```bash
# 检查当前配额
curl -I -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:9000/health

# 查看剩余配额
echo "X-RateLimit-Remaining: $(curl -s -H 'Authorization: Bearer YOUR_API_KEY' http://localhost:9000/health | grep -i 'x-ratelimit-remaining' | cut -d' ' -f2)"
```

## 📚 相关文档

- [API参考文档](../guides/api.md)
- [日志分析](../troubleshooting/log-analysis.md)
- [最佳实践](../reference/best-practices.md)

---

<div align="center">

**错误处理得当，系统稳定运行！**

[API参考 →](../guides/api.md) | [日志分析 →](../troubleshooting/log-analysis.md)

</div> 