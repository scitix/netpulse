# NetPulse Webhook Test Server

A simple HTTP server for testing and debugging NetPulse webhook functionality.

## Overview

This tool provides a lightweight HTTP server that can receive and display webhook messages from NetPulse. It's designed to help developers test webhook configurations and debug webhook-related issues.

## Features

- **Webhook Reception**: Receives POST requests at `/webhook` endpoint
- **Message Storage**: Stores received webhook messages in memory
- **Detailed Logging**: Provides comprehensive logging of webhook requests
- **Status Monitoring**: Offers endpoints to check server status and view messages
- **Error Parsing**: Intelligently parses and displays NetPulse error messages
- **JSON Formatting**: Pretty-prints JSON responses for better readability

## Installation

### Prerequisites

- Python 3.8+
- FastAPI
- Uvicorn

### Setup

1. Navigate to the webhook test server directory:
   ```bash
   cd tools/webhook
   ```

2. Install dependencies:
   ```bash
   pip install fastapi uvicorn
   ```

## Usage

### Starting the Server

```bash
python test_server.py
```

The server will start on `http://localhost:8888`

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server information and available endpoints |
| `/webhook` | POST | Receive webhook messages from NetPulse |
| `/webhook/status` | GET | Check server status and message count |
| `/webhook/messages` | GET | View all received webhook messages |
| `/webhook/clear` | DELETE | Clear all stored messages |

### Testing with NetPulse

1. Start the webhook test server:
   ```bash
   python test_server.py
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
- **Memory Management**: Automatically manages message storage

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