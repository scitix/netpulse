# Error Codes

This document explains NetPulse API error response format and common error situations.

## Response Format

### Success Response

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // Specific data
  }
}
```

### Error Response

NetPulse uses unified error response format:

```json
{
  "code": -1,
  "message": "Error description",
  "data": "Error details or data"
}
```

**Description**:
- `code: 200` indicates request success
- `code: -1` indicates request failure
- `message` contains error description
- `data` contains error details (may be string or object)

## HTTP Status Codes

NetPulse API uses standard HTTP status codes:

| Status Code | Description | Common Scenarios |
|-------------|-------------|------------------|
| `200` | OK | Request successful |
| `201` | Created | Task created successfully |
| `400` | Bad Request | Request parameter error, validation failed |
| `403` | Forbidden | API key invalid or missing, Vault credential access denied |
| `404` | Not Found | Resource not found (e.g., template engine not found, Vault credential not found) |
| `500` | Internal Server Error | Server internal error |
| `503` | Service Unavailable | Vault service unavailable |

## Common Error Situations

### 1. API Key Error

**HTTP Status Code**: `403`

**Response Example**:
```json
{
  "code": -1,
  "message": "Invalid or missing API key."
}
```

**Solution**:
- Check if request header contains `X-API-KEY`
- Verify API key is correct
- Confirm API key matches `server.api_key` in configuration file

### 2. Request Parameter Validation Error

**HTTP Status Code**: `400`

**Response Example**:
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

**Solution**:
- Check if request body contains all required fields
- Verify field types and formats are correct
- Refer to API documentation to confirm parameter requirements

### 3. Value Error

**HTTP Status Code**: `400`

**Response Example**:
```json
{
  "code": -1,
  "message": "Value Error",
  "data": "Specific error information"
}
```

**Common Causes**:
- Driver name doesn't exist
- Template engine or parser not found
- Configuration parameter values are invalid

### 4. Internal Server Error

**HTTP Status Code**: `500`

**Response Example**:
```json
{
  "code": -1,
  "message": "Internal Server Error",
  "data": "Error stack information"
}
```

**Solution**:
- View server logs for detailed error information
- Check system resources (memory, CPU, network)
- Verify Redis connection is normal

## Task Execution Errors

When task execution fails, error information is included in task result:

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
        "message": "Connection timeout"
      }
    }
  }
}
```

**Error Types**:
- `ConnectionError`: Device connection failed
- `TimeoutError`: Operation timeout
- `AuthenticationError`: Device authentication failed
- `CredentialError`: Vault credential error (credential not found, access denied, etc.)
- `VaultConnectionError`: Vault service connection failed
- Other Python exception types

## Error Handling Examples

### Python Example

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
        
        # Check business error code
        if result.get("code") == -1:
            print(f"API Error: {result.get('message')}")
            print(f"Error Details: {result.get('data')}")
            return None
        
        return result.get("data")
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print("API key error or Vault credential access denied, please check configuration")
        elif e.response.status_code == 400:
            print("Request parameter error")
        elif e.response.status_code == 404:
            print("Resource not found (may be Vault credential path does not exist)")
        elif e.response.status_code == 503:
            print("Vault service unavailable, please check Vault service status")
        else:
            print(f"HTTP Error: {e.response.status_code}")
        return None
```

### Check Job Status

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
            print(f"Task Failed: {error.get('type')} - {error.get('message')}")
            return False
        
        return True
    
    return False
```

## Debugging Recommendations

1. **View Logs**: Use `docker compose logs` to view detailed error information
2. **Verify Configuration**: Confirm configuration file and environment variable settings are correct
3. **Test Connection**: Use `/device/test-connection` endpoint to test device connection
4. **Check Network**: Confirm network connection and device reachability