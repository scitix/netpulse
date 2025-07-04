# 环境变量参考

本文档详细说明了 NetPulse 系统中所有可用的环境变量，包括其用途、格式、默认值和示例。

## 📋 环境变量总览

### 按功能分类
- **基础配置**: 系统基础设置
- **数据库配置**: 数据库连接和连接池设置
- **Redis配置**: Redis缓存和消息队列设置
- **API服务配置**: API服务运行参数
- **Worker配置**: Worker服务运行参数
- **设备连接配置**: 网络设备连接参数
- **安全配置**: 安全相关设置
- **日志配置**: 日志记录设置
- **模板配置**: 模板引擎设置
- **Webhook配置**: Webhook通知设置

## 🌐 基础配置

### API_KEY
**用途**: API访问密钥，用于API认证
**类型**: string
**默认值**: 自动生成
**示例**: 
```bash
export API_KEY="np_sk_1234567890abcdef"
```

### DEBUG
**用途**: 调试模式开关
**类型**: boolean
**默认值**: false
**示例**:
```bash
export DEBUG=true
```

### LOG_LEVEL
**用途**: 日志记录级别
**类型**: string
**默认值**: INFO
**可选值**: DEBUG, INFO, WARNING, ERROR, CRITICAL
**示例**:
```bash
export LOG_LEVEL=DEBUG
```

### TZ
**用途**: 系统时区设置
**类型**: string
**默认值**: Asia/Shanghai
**示例**:
```bash
export TZ=Asia/Shanghai
export TZ=UTC
export TZ=America/New_York
```

## 🗄️ 数据库配置

### DATABASE_URL
**用途**: 数据库连接URL
**类型**: string
**默认值**: sqlite:///netpulse.db
**格式**: `driver://user:password@host:port/database`
**示例**:
```bash
# SQLite
export DATABASE_URL="sqlite:///netpulse.db"

# PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost:5432/netpulse"

# MySQL
export DATABASE_URL="mysql://user:password@localhost:3306/netpulse"
```

### DB_POOL_SIZE
**用途**: 数据库连接池大小
**类型**: integer
**默认值**: 10
**示例**:
```bash
export DB_POOL_SIZE=20
```

### DB_MAX_OVERFLOW
**用途**: 数据库连接池溢出大小
**类型**: integer
**默认值**: 20
**示例**:
```bash
export DB_MAX_OVERFLOW=30
```

### DB_ECHO
**用途**: 是否显示SQL语句
**类型**: boolean
**默认值**: false
**示例**:
```bash
export DB_ECHO=true
```

## 🔴 Redis配置

### REDIS_URL
**用途**: Redis连接URL
**类型**: string
**默认值**: redis://localhost:6379
**格式**: `redis://[password@]host[:port][/db]`
**示例**:
```bash
# 本地Redis
export REDIS_URL="redis://localhost:6379"

# 带密码的Redis
export REDIS_URL="redis://password@localhost:6379"

# 指定数据库
export REDIS_URL="redis://localhost:6379/1"

# 带密码和数据库
export REDIS_URL="redis://password@localhost:6379/1"
```

### REDIS_DB
**用途**: Redis数据库编号
**类型**: integer
**默认值**: 0
**示例**:
```bash
export REDIS_DB=1
```

### REDIS_PASSWORD
**用途**: Redis密码
**类型**: string
**默认值**: null
**示例**:
```bash
export REDIS_PASSWORD="your_redis_password"
```

### REDIS_POOL_SIZE
**用途**: Redis连接池大小
**类型**: integer
**默认值**: 10
**示例**:
```bash
export REDIS_POOL_SIZE=20
```

## 🚀 API服务配置

### API_HOST
**用途**: API服务监听地址
**类型**: string
**默认值**: 0.0.0.0
**示例**:
```bash
export API_HOST="0.0.0.0"
export API_HOST="127.0.0.1"
```

### API_PORT
**用途**: API服务监听端口
**类型**: integer
**默认值**: 9000
**示例**:
```bash
export API_PORT=9000
```

### API_WORKERS
**用途**: API工作进程数
**类型**: integer
**默认值**: 4
**示例**:
```bash
export API_WORKERS=8
```

### API_TIMEOUT
**用途**: API请求超时时间(秒)
**类型**: integer
**默认值**: 30
**示例**:
```bash
export API_TIMEOUT=60
```

### API_CORS_ORIGINS
**用途**: CORS允许的源
**类型**: string
**默认值**: *
**示例**:
```bash
export API_CORS_ORIGINS="*"
export API_CORS_ORIGINS="http://localhost:3000,https://example.com"
```

## ⚙️ Worker配置

### WORKER_HOST
**用途**: Worker服务监听地址
**类型**: string
**默认值**: 0.0.0.0
**示例**:
```bash
export WORKER_HOST="0.0.0.0"
```

### WORKER_PORT
**用途**: Worker服务监听端口
**类型**: integer
**默认值**: 9001
**示例**:
```bash
export WORKER_PORT=9001
```

### WORKER_POOL_SIZE
**用途**: Worker连接池大小
**类型**: integer
**默认值**: 20
**示例**:
```bash
export WORKER_POOL_SIZE=50
```

### WORKER_TIMEOUT
**用途**: Worker操作超时时间(秒)
**类型**: integer
**默认值**: 30
**示例**:
```bash
export WORKER_TIMEOUT=60
```

### WORKER_MAX_CONCURRENT
**用途**: Worker最大并发任务数
**类型**: integer
**默认值**: 100
**示例**:
```bash
export WORKER_MAX_CONCURRENT=200
```

## 🔌 设备连接配置

### DEFAULT_SSH_PORT
**用途**: 默认SSH端口
**类型**: integer
**默认值**: 22
**示例**:
```bash
export DEFAULT_SSH_PORT=22
```

### DEFAULT_TELNET_PORT
**用途**: 默认Telnet端口
**类型**: integer
**默认值**: 23
**示例**:
```bash
export DEFAULT_TELNET_PORT=23
```

### CONNECTION_TIMEOUT
**用途**: 连接超时时间(秒)
**类型**: integer
**默认值**: 30
**示例**:
```bash
export CONNECTION_TIMEOUT=60
```

### COMMAND_TIMEOUT
**用途**: 命令执行超时时间(秒)
**类型**: integer
**默认值**: 30
**示例**:
```bash
export COMMAND_TIMEOUT=60
```

### KEEPALIVE_INTERVAL
**用途**: 连接保活间隔(秒)
**类型**: integer
**默认值**: 60
**示例**:
```bash
export KEEPALIVE_INTERVAL=30
```

### MAX_CONNECTIONS_PER_DEVICE
**用途**: 每个设备最大连接数
**类型**: integer
**默认值**: 5
**示例**:
```bash
export MAX_CONNECTIONS_PER_DEVICE=10
```

## 🔒 安全配置

### SSL_ENABLED
**用途**: 启用SSL/TLS
**类型**: boolean
**默认值**: false
**示例**:
```bash
export SSL_ENABLED=true
```

### SSL_CERT_FILE
**用途**: SSL证书文件路径
**类型**: string
**默认值**: null
**示例**:
```bash
export SSL_CERT_FILE="/etc/ssl/certs/netpulse.crt"
```

### SSL_KEY_FILE
**用途**: SSL私钥文件路径
**类型**: string
**默认值**: null
**示例**:
```bash
export SSL_KEY_FILE="/etc/ssl/private/netpulse.key"
```

### API_KEY_ROTATION_DAYS
**用途**: API密钥轮换天数
**类型**: integer
**默认值**: 90
**示例**:
```bash
export API_KEY_ROTATION_DAYS=30
```

### RATE_LIMIT_ENABLED
**用途**: 启用速率限制
**类型**: boolean
**默认值**: true
**示例**:
```bash
export RATE_LIMIT_ENABLED=true
```

### RATE_LIMIT_REQUESTS
**用途**: 速率限制请求数
**类型**: integer
**默认值**: 1000
**示例**:
```bash
export RATE_LIMIT_REQUESTS=2000
```

### RATE_LIMIT_WINDOW
**用途**: 速率限制时间窗口(秒)
**类型**: integer
**默认值**: 60
**示例**:
```bash
export RATE_LIMIT_WINDOW=300
```

## 📝 日志配置

### LOG_FILE
**用途**: 日志文件路径
**类型**: string
**默认值**: logs/netpulse.log
**示例**:
```bash
export LOG_FILE="/var/log/netpulse/netpulse.log"
```

### LOG_FORMAT
**用途**: 日志格式
**类型**: string
**默认值**: %(asctime)s - %(name)s - %(levelname)s - %(message)s
**示例**:
```bash
export LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### LOG_MAX_SIZE
**用途**: 日志文件最大大小
**类型**: string
**默认值**: 100MB
**示例**:
```bash
export LOG_MAX_SIZE="500MB"
```

### LOG_BACKUP_COUNT
**用途**: 日志备份文件数量
**类型**: integer
**默认值**: 5
**示例**:
```bash
export LOG_BACKUP_COUNT=10
```

## 📄 模板配置

### TEMPLATE_PATH
**用途**: 模板文件路径
**类型**: string
**默认值**: templates/
**示例**:
```bash
export TEMPLATE_PATH="/opt/netpulse/templates/"
```

### JINJA2_ENABLED
**用途**: 启用Jinja2模板引擎
**类型**: boolean
**默认值**: true
**示例**:
```bash
export JINJA2_ENABLED=true
```

### TEXTFSM_ENABLED
**用途**: 启用TextFSM模板引擎
**类型**: boolean
**默认值**: true
**示例**:
```bash
export TEXTFSM_ENABLED=true
```

### TTP_ENABLED
**用途**: 启用TTP模板引擎
**类型**: boolean
**默认值**: true
**示例**:
```bash
export TTP_ENABLED=true
```

## 🔔 Webhook配置

### WEBHOOK_ENABLED
**用途**: 启用Webhook通知
**类型**: boolean
**默认值**: true
**示例**:
```bash
export WEBHOOK_ENABLED=true
```

### WEBHOOK_TIMEOUT
**用途**: Webhook请求超时时间(秒)
**类型**: integer
**默认值**: 10
**示例**:
```bash
export WEBHOOK_TIMEOUT=30
```

### WEBHOOK_RETRY_COUNT
**用途**: Webhook重试次数
**类型**: integer
**默认值**: 3
**示例**:
```bash
export WEBHOOK_RETRY_COUNT=5
```

### WEBHOOK_RETRY_DELAY
**用途**: Webhook重试延迟(秒)
**类型**: integer
**默认值**: 5
**示例**:
```bash
export WEBHOOK_RETRY_DELAY=10
```

## 🔧 环境变量管理

### 1. 环境变量文件
```bash
# .env 文件示例
API_KEY=np_sk_1234567890abcdef
DEBUG=false
LOG_LEVEL=INFO
TZ=Asia/Shanghai

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/netpulse
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Redis配置
REDIS_URL=redis://localhost:6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password

# API服务配置
API_HOST=0.0.0.0
API_PORT=9000
API_WORKERS=8
API_TIMEOUT=60

# Worker配置
WORKER_HOST=0.0.0.0
WORKER_PORT=9001
WORKER_POOL_SIZE=50
WORKER_TIMEOUT=60

# 设备连接配置
CONNECTION_TIMEOUT=60
COMMAND_TIMEOUT=60
KEEPALIVE_INTERVAL=30
MAX_CONNECTIONS_PER_DEVICE=10

# 安全配置
SSL_ENABLED=true
SSL_CERT_FILE=/etc/ssl/certs/netpulse.crt
SSL_KEY_FILE=/etc/ssl/private/netpulse.key
API_KEY_ROTATION_DAYS=30

# 日志配置
LOG_FILE=/var/log/netpulse/netpulse.log
LOG_MAX_SIZE=500MB
LOG_BACKUP_COUNT=10

# 模板配置
TEMPLATE_PATH=/opt/netpulse/templates/

# Webhook配置
WEBHOOK_ENABLED=true
WEBHOOK_TIMEOUT=30
WEBHOOK_RETRY_COUNT=5
WEBHOOK_RETRY_DELAY=10
```

### 2. 环境变量验证脚本
```bash
#!/bin/bash
# validate_env.sh

echo "验证环境变量配置..."

# 检查必需的环境变量
required_vars=(
    "API_KEY"
    "DATABASE_URL"
    "REDIS_URL"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo "✓ 所有必需的环境变量都已设置"
else
    echo "✗ 缺少以下环境变量:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

# 验证数据库URL格式
if [[ $DATABASE_URL == sqlite://* ]]; then
    echo "✓ 使用SQLite数据库"
elif [[ $DATABASE_URL == postgresql://* ]]; then
    echo "✓ 使用PostgreSQL数据库"
elif [[ $DATABASE_URL == mysql://* ]]; then
    echo "✓ 使用MySQL数据库"
else
    echo "✗ 不支持的数据库URL格式: $DATABASE_URL"
    exit 1
fi

# 验证Redis URL格式
if [[ $REDIS_URL == redis://* ]]; then
    echo "✓ Redis URL格式正确"
else
    echo "✗ Redis URL格式错误: $REDIS_URL"
    exit 1
fi

echo "环境变量验证完成"
```

### 3. 环境变量加载
```python
# load_env.py
import os
from dotenv import load_dotenv

def load_environment():
    """加载环境变量"""
    # 加载.env文件
    load_dotenv()
    
    # 验证必需的环境变量
    required_vars = [
        'API_KEY',
        'DATABASE_URL',
        'REDIS_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")
    
    return {
        'api_key': os.getenv('API_KEY'),
        'database_url': os.getenv('DATABASE_URL'),
        'redis_url': os.getenv('REDIS_URL'),
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'timezone': os.getenv('TZ', 'Asia/Shanghai')
    }

if __name__ == "__main__":
    try:
        config = load_environment()
        print("环境变量加载成功")
        print(f"API Key: {config['api_key'][:10]}...")
        print(f"数据库: {config['database_url']}")
        print(f"Redis: {config['redis_url']}")
    except ValueError as e:
        print(f"环境变量加载失败: {e}")
        exit(1)
```

## 📊 环境变量最佳实践

### 1. 环境分离
```bash
# 开发环境
.env.development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///dev_netpulse.db

# 生产环境
.env.production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@localhost/netpulse
SSL_ENABLED=true
```

### 2. 敏感信息管理
```bash
# 使用密钥管理服务
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id db-password --query SecretString --output text)
export API_KEY=$(aws secretsmanager get-secret-value --secret-id api-key --query SecretString --output text)

# 或使用环境变量文件（不提交到版本控制）
echo "DB_PASSWORD=secure_password" >> .env.local
echo "API_KEY=your_api_key" >> .env.local
```

### 3. 配置验证
```bash
# 启动前验证配置
./validate_env.sh

# 或在代码中验证
python -c "from load_env import load_environment; load_environment(); print('配置验证通过')"
```

### 4. 配置文档化
```bash
# 创建配置文档
cat > CONFIG.md << EOF
# 环境变量配置说明

## 必需配置
- API_KEY: API访问密钥
- DATABASE_URL: 数据库连接URL
- REDIS_URL: Redis连接URL

## 可选配置
- DEBUG: 调试模式
- LOG_LEVEL: 日志级别
- TZ: 时区设置

## 示例
\`\`\`bash
export API_KEY="np_sk_1234567890abcdef"
export DATABASE_URL="postgresql://user:pass@localhost/netpulse"
export REDIS_URL="redis://localhost:6379"
\`\`\`
EOF
```

## 📚 相关文档

- [配置参数参考](./configuration.md)
- [部署指南](../getting-started/deployment.md)
- [日志分析](../troubleshooting/log-analysis.md)
- [最佳实践](../reference/best-practices.md)

---

<div align="center">

**环境变量配置正确，系统运行稳定！**

[配置参数 →](./configuration.md) | [部署指南 →](../getting-started/deployment.md)

</div> 