# 配置参数参考

本文档详细说明了 NetPulse 的所有配置参数，包括环境变量、配置文件选项和运行时参数。

## 🌐 环境变量配置

### 基础配置
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `API_KEY` | string | 自动生成 | API访问密钥 |
| `DEBUG` | boolean | false | 调试模式开关 |
| `LOG_LEVEL` | string | INFO | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `TZ` | string | Asia/Shanghai | 系统时区设置 |

### 数据库配置
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | string | sqlite:///netpulse.db | 数据库连接URL |
| `DB_POOL_SIZE` | integer | 10 | 数据库连接池大小 |
| `DB_MAX_OVERFLOW` | integer | 20 | 数据库连接池溢出大小 |

### Redis配置
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `REDIS_URL` | string | redis://localhost:6379 | Redis连接URL |
| `REDIS_DB` | integer | 0 | Redis数据库编号 |
| `REDIS_PASSWORD` | string | - | Redis密码 |

### API服务配置
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `API_HOST` | string | 0.0.0.0 | API服务监听地址 |
| `API_PORT` | integer | 9000 | API服务监听端口 |
| `API_WORKERS` | integer | 4 | API工作进程数 |
| `API_TIMEOUT` | integer | 30 | API请求超时时间(秒) |

### Worker配置
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `WORKER_HOST` | string | 0.0.0.0 | Worker服务监听地址 |
| `WORKER_PORT` | integer | 9001 | Worker服务监听端口 |
| `WORKER_POOL_SIZE` | integer | 20 | Worker连接池大小 |
| `WORKER_TIMEOUT` | integer | 30 | Worker操作超时时间(秒) |

### 设备连接配置
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DEFAULT_SSH_PORT` | integer | 22 | 默认SSH端口 |
| `DEFAULT_TELNET_PORT` | integer | 23 | 默认Telnet端口 |
| `CONNECTION_TIMEOUT` | integer | 30 | 连接超时时间(秒) |
| `COMMAND_TIMEOUT` | integer | 30 | 命令执行超时时间(秒) |
| `KEEPALIVE_INTERVAL` | integer | 60 | 连接保活间隔(秒) |

### 安全配置
| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SSL_ENABLED` | boolean | false | 启用SSL/TLS |
| `SSL_CERT_FILE` | string | - | SSL证书文件路径 |
| `SSL_KEY_FILE` | string | - | SSL私钥文件路径 |
| `CORS_ORIGINS` | string | * | CORS允许的源 |

## 📁 配置文件结构

### 主配置文件 (config.yaml)
```yaml
# NetPulse 主配置文件
api:
  host: 0.0.0.0
  port: 9000
  workers: 4
  timeout: 30
  cors_origins: "*"

database:
  url: sqlite:///netpulse.db
  pool_size: 10
  max_overflow: 20

redis:
  url: redis://localhost:6379
  db: 0
  password: null

worker:
  host: 0.0.0.0
  port: 9001
  pool_size: 20
  timeout: 30

logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/netpulse.log
  max_size: 100MB
  backup_count: 5

security:
  ssl_enabled: false
  ssl_cert_file: null
  ssl_key_file: null
  api_key_rotation_days: 90

devices:
  default_ssh_port: 22
  default_telnet_port: 23
  connection_timeout: 30
  command_timeout: 30
  keepalive_interval: 60
  max_connections_per_device: 5

templates:
  jinja2_enabled: true
  textfsm_enabled: true
  ttp_enabled: true
  template_path: templates/

webhooks:
  enabled: true
  timeout: 10
  retry_count: 3
  retry_delay: 5
```

### 设备配置文件 (devices.yaml)
```yaml
# 设备配置文件
devices:
  - hostname: 192.168.1.1
    username: admin
    password: password123
    device_type: cisco_ios
    port: 22
    timeout: 30
    enable_password: enable123
    description: "核心路由器"
    
  - hostname: 192.168.1.2
    username: admin
    password: password123
    device_type: cisco_nxos
    port: 22
    timeout: 30
    description: "接入交换机"
```

## 🔧 配置示例

### 开发环境配置
```bash
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG
API_PORT=9000
WORKER_PORT=9001
DATABASE_URL=sqlite:///dev_netpulse.db
REDIS_URL=redis://localhost:6379/1
```

### 生产环境配置
```bash
# .env.production
DEBUG=false
LOG_LEVEL=INFO
API_PORT=9000
WORKER_PORT=9001
DATABASE_URL=postgresql://user:pass@localhost/netpulse
REDIS_URL=redis://localhost:6379/0
SSL_ENABLED=true
SSL_CERT_FILE=/etc/ssl/certs/netpulse.crt
SSL_KEY_FILE=/etc/ssl/private/netpulse.key
```

### Docker环境配置
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    image: netpulse/api:latest
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=9000
      - DATABASE_URL=postgresql://netpulse:password@db/netpulse
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "9000:9000"
    depends_on:
      - db
      - redis
      
  worker:
    image: netpulse/worker:latest
    environment:
      - WORKER_HOST=0.0.0.0
      - WORKER_PORT=9001
      - DATABASE_URL=postgresql://netpulse:password@db/netpulse
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
```

## 📊 配置验证

### 配置检查脚本
```python
#!/usr/bin/env python3
# config_validator.py

import os
import yaml
from typing import Dict, Any

def validate_config(config: Dict[str, Any]) -> bool:
    """验证配置文件"""
    required_fields = [
        'api.host', 'api.port', 'database.url', 'redis.url'
    ]
    
    for field in required_fields:
        keys = field.split('.')
        value = config
        for key in keys:
            if key not in value:
                print(f"缺少必需配置: {field}")
                return False
            value = value[key]
    
    return True

def load_config(config_file: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

if __name__ == "__main__":
    config = load_config('config.yaml')
    if validate_config(config):
        print("配置验证通过")
    else:
        print("配置验证失败")
        exit(1)
```

### 环境变量检查
```bash
#!/bin/bash
# setup_env.sh

echo "检查环境变量配置..."

# 检查必需的环境变量
required_vars=("API_KEY" "DATABASE_URL" "REDIS_URL")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "错误: 缺少环境变量 $var"
        exit 1
    else
        echo "✓ $var 已设置"
    fi
done

echo "环境变量检查完成"
```

## 🔄 配置热重载

### 配置更新API
```python
# 配置更新示例
import requests

def update_config(config_data: dict):
    """更新运行时配置"""
    url = "http://localhost:9000/admin/config"
    headers = {"Authorization": "Bearer YOUR_API_KEY"}
    
    response = requests.put(url, json=config_data, headers=headers)
    return response.json()

# 更新日志级别
update_config({
    "logging": {
        "level": "DEBUG"
    }
})
```

### 配置监控
```python
# 配置监控示例
import time
import json

def monitor_config_changes():
    """监控配置变化"""
    last_config = None
    
    while True:
        try:
            with open('config.yaml', 'r') as f:
                current_config = yaml.safe_load(f)
            
            if last_config != current_config:
                print("检测到配置变化，重新加载...")
                # 重新加载配置
                reload_config(current_config)
                last_config = current_config
            
            time.sleep(30)  # 每30秒检查一次
            
        except Exception as e:
            print(f"配置监控错误: {e}")
```

## 📝 配置最佳实践

### 1. 环境分离
```bash
# 不同环境使用不同的配置文件
config/
├── development.yaml
├── staging.yaml
├── production.yaml
└── docker.yaml
```

### 2. 敏感信息管理
```bash
# 使用环境变量存储敏感信息
export DB_PASSWORD="secure_password"
export API_KEY="your_api_key"

# 在配置文件中引用
database:
  url: postgresql://user:${DB_PASSWORD}@localhost/netpulse
```

### 3. 配置版本控制
```yaml
# 在配置文件中添加版本信息
version: "1.0.0"
config_version: "2024-01-01"
api:
  host: 0.0.0.0
  port: 9000
```

### 4. 配置文档化
```yaml
# 添加配置说明
api:
  host: 0.0.0.0  # API服务监听地址
  port: 9000     # API服务监听端口
  workers: 4     # 工作进程数
  timeout: 30    # 请求超时时间(秒)
```

## 🚨 常见配置问题

### 1. 端口冲突
```bash
# 检查端口占用
netstat -tulpn | grep :9000

# 修改端口配置
API_PORT=9001
```

### 2. 数据库连接失败
```bash
# 检查数据库连接
python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://user:pass@localhost/netpulse')
    print('数据库连接成功')
except Exception as e:
    print(f'数据库连接失败: {e}')
"
```

### 3. Redis连接失败
```bash
# 检查Redis连接
redis-cli ping

# 测试Redis连接
python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print('Redis连接成功')
except Exception as e:
    print(f'Redis连接失败: {e}')
"
```

## 📚 相关文档

- [环境变量参考](./environment-variables.md)
- [部署指南](../getting-started/deployment.md)
- [日志分析](../troubleshooting/log-analysis.md)

---

<div align="center">

**配置正确，系统稳定运行！**

[环境变量 →](./environment-variables.md) | [部署指南 →](../getting-started/deployment.md)

</div> 