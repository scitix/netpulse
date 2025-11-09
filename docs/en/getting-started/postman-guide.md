# Postman Usage Guide

!!! info "Why Choose Postman?"
    Postman is the best way to experience NetPulse API! No need to write code, quickly test and experience all API functions through a graphical interface.

## Get Collection

- **Local File**: `@NetPulse.postman_collection.json` in the project root directory (i.e., `postman/NetPulse.postman_collection.json`)

## Import Collection

1. Open [Postman](https://www.postman.com)
2. Click `Import` → `File`, select `postman/NetPulse.postman_collection.json` in the project root directory
3. After import, NetPulse API folder will be displayed on the left

## Configure Environment Variables

Create environment `NetPulse Local` and configure the following variables:

| Variable Name | Initial Value | Description |
|---------------|---------------|-------------|
| `base_url` | `http://localhost:9000` | API server address |
| `api_key` | `np_90fbd8685671a2c0b...` | API authentication key |

!!! tip "Get API Key"
    After starting the service, the API Key is displayed in the console output, or check the `.env` file.

## Quick Experience

1. **Health Check**: Execute `System Health > Health Check`
2. **Connection Test**: Execute test requests under `Device Connection Testing`
3. **Command Execution**: Use `Netmiko Driver` to execute device commands
4. **Batch Operations**: Experience concurrent processing of `Batch Operations`

## Function Modules

- **System Health**: System health check
- **Job Management**: Job management
- **Worker Management**: Worker process management
- **Device Connection Testing**: Device connection testing
- **Netmiko Driver**: Netmiko driver operations
- **NAPALM Driver**: NAPALM driver operations
- **PyEAPI Driver**: PyEAPI driver operations
- **Batch Operations**: Batch operations
- **Template Operations**: Template operations

---