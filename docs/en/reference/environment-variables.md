# Environment Variables Reference

This document details all available environment variables in the NetPulse system, including their purpose, format, default values, and examples.

## 📋 Overview of Environment Variables

### By Function
- **Basic Configuration**: Basic system settings
- **Database Configuration**: Database connection and pool settings
- **Redis Configuration**: Redis cache and message queue settings
- **API Service Configuration**: API service runtime parameters
- **Worker Configuration**: Worker service runtime parameters
- **Device Connection Configuration**: Network device connection parameters
- **Security Configuration**: Security-related settings
- **Logging Configuration**: Logging settings
- **Template Configuration**: Template engine settings
- **Webhook Configuration**: Webhook notification settings

## 🌐 Basic Configuration

### API_KEY
**Purpose**: API access key for API authentication
**Type**: string
**Default**: Auto-generated
**Example**:
```bash
export API_KEY="np_sk_1234567890abcdef"
```

### DEBUG
**Purpose**: Debug mode switch
**Type**: boolean
**Default**: false
**Example**:
```bash
export DEBUG=true
```

### LOG_LEVEL
**Purpose**: Logging level
**Type**: string
**Default**: INFO
**Options**: DEBUG, INFO, WARNING, ERROR, CRITICAL
**Example**:
```bash
export LOG_LEVEL=DEBUG
```

### TZ
**Purpose**: System timezone setting
**Type**: string
**Default**: Asia/Shanghai
**Example**:
```bash
export TZ=Asia/Shanghai
export TZ=UTC
export TZ=America/New_York
```

## 🗄️ Database Configuration

### DATABASE_URL
**Purpose**: Database connection URL
**Type**: string
**Default**: sqlite:///netpulse.db
**Format**: `driver://user:password@host:port/database`
**Example**:
```bash
# SQLite
export DATABASE_URL="sqlite:///netpulse.db"

# PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost:5432/netpulse"

# MySQL
export DATABASE_URL="mysql://user:password@localhost:3306/netpulse"
```

### DB_POOL_SIZE
**Purpose**: Database connection pool size
**Type**: integer
**Default**: 10
**Example**:
```bash
export DB_POOL_SIZE=20
```

### DB_MAX_OVERFLOW
**Purpose**: Database connection pool overflow size
**Type**: integer
**Default**: 20
**Example**:
```bash
export DB_MAX_OVERFLOW=30
```

### DB_ECHO
**Purpose**: Show SQL statements
**Type**: boolean
**Default**: false
**Example**:
```bash
export DB_ECHO=true
```

## 🔴 Redis Configuration

### REDIS_URL
**Purpose**: Redis connection URL
**Type**: string
**Default**: redis://localhost:6379
**Format**: `redis://[password@]host[:port][/db]`
**Example**:
```bash
# Local Redis
export REDIS_URL="redis://localhost:6379"

# With password
export REDIS_URL="redis://password@localhost:6379"

# Specify database
export REDIS_URL="redis://localhost:6379/1"

# With password and database
export REDIS_URL="redis://password@localhost:6379/1"
```

### REDIS_DB
**Purpose**: Redis database number
**Type**: integer
**Default**: 0
**Example**:
```bash
export REDIS_DB=1
```

### REDIS_PASSWORD
**Purpose**: Redis password
**Type**: string
**Default**: null
**Example**:
```bash
export REDIS_PASSWORD="your_redis_password"
```

### REDIS_POOL_SIZE
**Purpose**: Redis connection pool size
**Type**: integer
**Default**: 10
**Example**:
```bash
export REDIS_POOL_SIZE=20
```

## 🚀 API Service Configuration

### API_HOST
**Purpose**: API service listen address
**Type**: string
**Default**: 0.0.0.0
**Example**:
```bash
export API_HOST="0.0.0.0"
export API_HOST="127.0.0.1"
```

### API_PORT
**Purpose**: API service listen port
**Type**: integer
**Default**: 9000
**Example**:
```bash
export API_PORT=9000
```

### API_WORKERS
**Purpose**: Number of API worker processes
**Type**: integer
**Default**: 4
**Example**:
```bash
export API_WORKERS=8
```

### API_TIMEOUT
**Purpose**: API request timeout (seconds)
**Type**: integer
**Default**: 30
**Example**:
```bash
export API_TIMEOUT=60
```

### API_CORS_ORIGINS
**Purpose**: Allowed CORS origins
**Type**: string
**Default**: *
**Example**:
```bash
export API_CORS_ORIGINS="*"
```

// ... 其余内容请继续补全，如需全部内容请告知 ... 