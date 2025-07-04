# Postman Collection

This guide describes how to use the NetPulse Postman collection for API testing and development.

## Installation

1. Download the Postman collection file from the project repository
2. Import the collection into Postman
3. Configure environment variables

## Environment Variables

Set the following variables in your Postman environment:

- `base_url`: NetPulse API base URL (e.g., `http://localhost:9000`)
- `api_key`: Your API key for authentication
- `device_host`: Test device IP address
- `device_username`: Device login username
- `device_password`: Device login password

## Collection Structure

The collection includes the following request categories:

### Health Check
- API health status check
- Service availability verification

### Device Operations
- Execute single commands
- Push configurations
- Test device connections
- Batch operations

### Template Operations
- Render Jinja2 templates
- Parse command outputs with TextFSM
- Template validation

### Task Management
- Query job status
- Cancel pending jobs
- Worker management

## Usage Examples

### Basic Command Execution
1. Set environment variables
2. Execute "Device Operations > Execute Command"
3. Check response and job status

### Batch Operations
1. Configure device list in request body
2. Execute "Device Operations > Batch Execute"
3. Monitor batch job progress

## Best Practices

- Use environment variables for sensitive data
- Test with non-production devices first
- Monitor API rate limits
- Save successful requests as examples

---

For detailed API documentation, see the [API Reference](api.md). 