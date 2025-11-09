# NetPulse Webhook Test Server

A simple HTTP server for testing and debugging NetPulse webhook functionality.

## Overview

This tool provides a lightweight HTTP server that can receive and display webhook messages from NetPulse. It's designed to help developers test webhook configurations and debug webhook-related issues.

## Features

- **Webhook Reception**: Receives POST requests at `/webhook` endpoint
- **Message Storage**: Stores received webhook messages in memory with size limits
- **Detailed Logging**: Provides comprehensive logging of webhook requests
- **Status Monitoring**: Offers endpoints to check server status and view messages
- **Error Parsing**: Intelligently parses and displays NetPulse error messages
- **JSON Formatting**: Pretty-prints JSON responses for better readability
- **Message Filtering**: Filter messages by job ID, time range, and success status
- **Pagination**: Support for paginated message retrieval
- **Statistics**: Track success/failure rates and message counts
- **Export**: Export messages in JSON or CSV format
- **Auto Cleanup**: Automatic cleanup of old messages based on retention policy
- **CORS Support**: Configurable CORS for frontend access
- **Health Check**: Standard health check endpoint for monitoring

## Installation

### Prerequisites

- Python 3.12+
- NetPulse project dependencies

### Setup

Dependencies are already defined in the `api` group of `[project.optional-dependencies]` in `pyproject.toml`.

**Method 1: If virtual environment has pip (Recommended)**

```bash
# Activate virtual environment
source .venv/bin/activate

# Install API dependencies (including FastAPI and Uvicorn)
pip install -e ".[api]"
```

**Method 2: If virtual environment doesn't have pip (using system pip)**

Use system pip to install directly to the virtual environment, referencing versions defined in `pyproject.toml`:

```bash
# From project root directory, install dependencies needed for webhook server
python3 -m pip install --target .venv/lib/python3.12/site-packages \
    "fastapi~=0.115.12" \
    "uvicorn~=0.34.0"
```

> **Note**: Version numbers come from the `api` group in `[project.optional-dependencies]` of `pyproject.toml`. If you need to install all API dependencies (including gunicorn, uvloop, etc.), check the file for the complete list.

## Usage

### Starting the Server

From the project root directory:

```bash
python tools/webhook/webhook_server.py
```

Or from the webhook directory:

```bash
cd tools/webhook
python webhook_server.py
```

The server will start on `http://localhost:8888` by default.

#### Command Line Arguments

You can specify IP address and port using command line arguments:

```bash
# Specify host and port
python tools/webhook/webhook_server.py --host 127.0.0.1 --port 9999

# Specify only port
python tools/webhook/webhook_server.py --port 9999

# Specify only host
python tools/webhook/webhook_server.py --host 192.168.1.100

# Other options
python tools/webhook/webhook_server.py --host 0.0.0.0 --port 8888 --max-messages 20000 --retention-hours 48 --no-cors
```

Available command line arguments:
- `--host`: Server host address (default: 0.0.0.0)
- `--port`: Server port (default: 8888)
- `--max-messages`: Maximum messages to store (default: 10000)
- `--retention-hours`: Message retention time in hours (default: 24)
- `--no-cors`: Disable CORS (default: enabled)

#### Environment Variables

You can also configure the server using environment variables (with `WEBHOOK_` prefix):
- `WEBHOOK_SERVER_PORT`: Server port (default: 8888)
- `WEBHOOK_SERVER_HOST`: Server host (default: 0.0.0.0)
- `WEBHOOK_MAX_MESSAGES`: Maximum messages to store (default: 10000)
- `WEBHOOK_RETENTION_HOURS`: Message retention time in hours (default: 24)
- `WEBHOOK_ENABLE_CORS`: Enable CORS (default: true)

> **Note**: Command line arguments take precedence over environment variables.

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server information and available endpoints |
| `/health` | GET | Health check endpoint |
| `/webhook` | POST | Receive webhook messages from NetPulse |
| `/webhook/status` | GET | Check server status and message count |
| `/webhook/messages` | GET | View messages with filtering & pagination |
| `/webhook/stats` | GET | Get detailed statistics |
| `/webhook/export` | GET | Export messages (JSON/CSV format) |
| `/webhook/clear` | DELETE | Clear all stored messages |

### Testing with NetPulse

1. Start the webhook test server:
   ```bash
   python tools/webhook/webhook_server.py
   ```

2. Configure NetPulse to send webhooks to:
   ```
   http://localhost:8888/webhook
   ```

3. Execute a job in NetPulse that triggers a webhook

4. Check the server logs to see the received webhook data

### Example Webhook Configuration

In your NetPulse configuration, you can set up a webhook like this:

```yaml
webhooks:
  - name: "test-webhook"
    url: "http://localhost:8888/webhook"
    events: ["job.completed", "job.failed"]
    timeout: 30
```

## Log Output

The server provides detailed logging including:

- Request headers (with sensitive data masked)
- Request body parsing
- Job execution status (success/failure)
- Error details with proper formatting
- Response information

Example log output:
```
2024-01-15 10:30:45 - INFO - ================================================================================
2024-01-15 10:30:45 - INFO - NetPulse Webhook Request Details
2024-01-15 10:30:45 - INFO - ================================================================================
2024-01-15 10:30:45 - INFO - Received Time: 2024-01-15 10:30:45
2024-01-15 10:30:45 - INFO - Request Method: POST
2024-01-15 10:30:45 - INFO - Request URL: http://localhost:8888/webhook
2024-01-15 10:30:45 - INFO - Request Headers:
2024-01-15 10:30:45 - INFO -     content-type: application/json
2024-01-15 10:30:45 - INFO -     user-agent: NetPulse/1.0.0
2024-01-15 10:30:45 - INFO - Request Body Data:
2024-01-15 10:30:45 - INFO -     Job ID: job_12345
2024-01-15 10:30:45 - INFO -     Job Execution Successful
2024-01-15 10:30:45 - INFO -     Execution Result:
2024-01-15 10:30:45 - INFO -         [output]: show version
2024-01-15 10:30:45 - INFO -         [status]: completed
```

## API Response Format

### Webhook Handler Response

```json
{
  "status": "success",
  "message": "NetPulse webhook message received (#1)",
  "timestamp": "2024-01-15T10:30:45.123456",
  "job_id": "job_12345",
  "total_messages": 1
}
```

### Status Endpoint Response

```json
{
  "server_status": "running",
  "total_messages_received": 5,
  "latest_messages": [...],
  "server_time": "2024-01-15T10:30:45.123456"
}
```

## Error Handling

The server handles various error scenarios:

- **Invalid JSON**: Returns 400 Bad Request
- **Parsing Errors**: Logs raw data for debugging
- **Memory Management**: Automatically manages message storage with size limits
- **Auto Cleanup**: Periodically removes messages older than retention period

## Advanced Usage

### Filtering Messages

You can filter messages using query parameters:

```bash
# Filter by job ID
GET /webhook/messages?job_id=abc123

# Filter by success status
GET /webhook/messages?is_success=true

# Filter by time range
GET /webhook/messages?start_time=2024-01-01T00:00:00&end_time=2024-01-02T00:00:00

# Combine filters with pagination
GET /webhook/messages?is_success=false&limit=50&offset=0
```

### Exporting Messages

Export messages in different formats:

```bash
# Export as JSON
GET /webhook/export?format=json

# Export as CSV
GET /webhook/export?format=csv

# Export with filters
GET /webhook/export?format=csv&is_success=true&start_time=2024-01-01T00:00:00
```

### Viewing Statistics

Get detailed statistics about received webhooks:

```bash
GET /webhook/stats
```

Returns information about:
- Total messages received
- Success/failure counts
- Success rate
- Messages in memory vs total

## Development

### Adding New Features

1. The server is built with FastAPI for easy extension
2. Add new endpoints in the main application
3. Update logging functions as needed
4. Test with actual NetPulse webhook data

### Customization

You can modify the server behavior by:

- Changing the port (default: 8888)
- Adjusting log levels
- Adding authentication
- Implementing persistent storage
- Adding custom response formats

## Troubleshooting

### Common Issues

1. **Port Already in Use**: Change the port in the script or kill existing processes
2. **CORS Issues**: Add CORS middleware if testing from web browsers
3. **Memory Issues**: Clear messages periodically using the `/webhook/clear` endpoint

### Debug Mode

For detailed debugging, you can modify the logging level:

```python
logging.basicConfig(level=logging.DEBUG)
```

## License

This tool is part of the NetPulse project and follows the same MIT license. 