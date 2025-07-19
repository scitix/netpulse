# NetPulse Documentation Center

Welcome to the NetPulse Documentation Center! NetPulse is a distributed RESTful API server designed for network device management, providing a unified multi-vendor network device management interface.

![NetPulse Project Value Proposition](assets/images/architecture/project-value-proposition-en.svg)

## Core Features

- **RESTful API**: Simple and efficient asynchronous API supporting multi-vendor network devices
- **AI Agent Support**: Intelligent network operations supporting AI Agents and MCP clients
- **Multi-protocol Support**: Telnet, SSH, HTTP(S), and other connection protocols
- **High Performance**: Persistent SSH connections with keepalive mechanism
- **Distributed Architecture**: Scalable multi-master design with high availability
- **Extensibility**: Plugin system supporting drivers, templates, schedulers, and webhooks
- **Template Engine**: Support for Jinja2, TextFSM, and TTP template formats

## Quick Start

### One-click Deployment
```bash
git clone <repository-url>
cd netpulse
bash ./scripts/docker_auto_deploy.sh
```

### Manual Setup
```bash
# Generate environment configuration
bash ./scripts/setup_env.sh generate

# Start services
docker compose up -d

# Test API
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:9000/health
```

## System Architecture

![NetPulse Core Workflow](assets/images/architecture/workflow-overview-en.svg)

## Documentation Navigation

### New User Guide
- **[Quick Start](getting-started/quick-start.md)** - Get started in 5 minutes
- **[First API Call](getting-started/first-steps.md)** - Learn basic API usage
- **[Deployment Guide](getting-started/deployment.md)** - Production environment deployment

### User Guides
- **[API Reference](guides/api.md)** - Complete API documentation
- **[CLI Tools](guides/cli.md)** - Command-line tool usage
- **[Configuration Management](guides/configuration.md)** - System configuration details
- **[SDK Guide](guides/sdk-guide.md)** - SDK usage instructions
- **[Postman Collection](guides/postman-collection.md)** - API testing tools

### Advanced Features
- **[Batch Operations](advanced/batch-operations.md)** - Large-scale device management
- **[Template System](advanced/templates.md)** - Template engine usage
- **[Webhook Configuration](advanced/webhooks.md)** - Webhook setup
- **[Performance Tuning](advanced/performance-tuning.md)** - Performance optimization guide

### System Architecture
- **[Architecture Overview](architecture/overview.md)** - Overall system design
- **[Architecture Design](architecture/architecture.md)** - Detailed architecture explanation
- **[Long Connection Technology](architecture/long-connection.md)** - Connection technology details
- **[Task Schedulers](architecture/schedulers.md)** - Scheduler mechanism
- **[Driver System](architecture/drivers.md)** - Device driver details
- **[Template System](architecture/templates.md)** - Template system architecture
- **[Webhook System](architecture/webhooks.md)** - Webhook architecture
- **[Plugin System](architecture/plugins.md)** - Plugin extension mechanism

### Reference Documentation
- **[Configuration Parameters](reference/configuration.md)** - Complete configuration options
- **[Environment Variables](reference/environment-variables.md)** - Environment variable descriptions
- **[Error Codes](reference/error-codes.md)** - Error handling guide
- **[Best Practices](reference/best-practices.md)** - Usage recommendations

### Troubleshooting
- **[Log Analysis](troubleshooting/log-analysis.md)** - Log interpretation

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/netpulse/LICENSE) file for details.

--- 