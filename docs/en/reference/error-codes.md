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
| `403` | Forbidden | API key invalid or missing |
| `404` | Not Found | Resource not found (e.g., template engine not found) |
| `500` | Internal Server Error | Server internal error |

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
- Other Python exception types

## Debugging

- `docker compose logs controller` — server-side errors
- `GET /job?id=<id>` — check job `result.error` for device-level failures
- `POST /device/test` — validate connection before running jobs
- Check `code` field first — HTTP 200 with `code: -1` means a business error