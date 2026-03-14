# NetPulse

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://hub.docker.com)
[![Python](https://img.shields.io/badge/Python-3.12+-green?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Agent-Ready](https://img.shields.io/badge/Agent--Ready-informational.svg)](ai-docs/llms.txt)

**NetPulse** is a high-performance **Infrastructure Connectivity API** that bridges the gap between legacy human-oriented SSH/CLI and modern machine-oriented programmable environments. 

It is designed to transform traditional network switches and Linux servers into **AI-programmable assets**, providing the essential connectivity layer for managing massive-scale infrastructure like **AI GPU Clusters** and **RDMA Networks**.

## 🎯 Positioning: The SSH-to-API Bridge

Traditional infrastructure management relies heavily on manual SSH sessions and CLI strings. NetPulse abstracts these complexities into a standardized RESTful API, acting as the reliable "actuator" for:
- **AI Agents**: Enabling LLMs to orchestrate physical hardware with high fidelity.
- **Automation Frameworks**: Providing a stable, persistent connectivity foundation for NetOps and SysOps.
- **Large-Scale Clusters**: Managing high-density AI infrastructure where connection stability is non-negotiable.

## 🛠 Core Engineering Capabilities

*   **SSH-to-API Abstraction**: Effortlessly converts complex CLI interactions from multi-vendor network devices (Cisco, Huawei, Arista, etc.) and Linux servers into clean, structured JSON data.
*   **Infrastructure-as-an-API**: Unified interaction logic across disparate hardware platforms, eliminating vendor-specific SSH management overhead.
*   **High-Resiliency Persistent Sessions**: Implements "Pinned Workers" to reuse connections across requests, ensuring zero-drop interaction and ultra-low latency.
*   **Linux Infrastructure Mastery**: Deep integration for server-side operations, including sudo handling, SFTP file management, and persistent detached background tasks.
*   **Self-Healing Resilience**: Built-in automated probes and health checks to maintain session integrity and recover connectivity without human intervention.
*   **AI-Native Context**: Optimized for LLM integration with specialized context documentation (`ai-docs/`) and standardized result modeling.

## 🏗 System Architecture

NetPulse utilizes a distributed **Controller-Worker** model. The Controller provides the standardized API entry point, while a scalable fleet of Workers maintains thousands of persistent sessions, managed and coordinated via a Redis-backed state machine.

## 📥 Quick Start

### One-Click Deployment

NetPulse provides a streamlined deployment experience for Docker environments:

```bash
# Clone the repository
git clone https://github.com/scitix/netpulse.git
cd netpulse

# Launch the automated deployment script
bash ./scripts/docker_auto_deploy.sh
```

### Manual Configuration
1. Generate environment config: `bash ./scripts/setup_env.sh generate`
2. Update `.env` with your `NETPULSE_REDIS__PASSWORD` and `NETPULSE_SERVER__API_KEY`.
3. Start the stack: `docker compose up -d`

## 🔌 API Interaction Examples

### A. Network Switch Interface (SSH-to-API)
Connect to a network switch and retrieve structured status data:

```bash
curl -X POST http://localhost:9000/device/exec \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "10.0.0.1",
      "username": "admin",
      "password": "pass"
    },
    "command": ["show ip interface brief"],
    "parsing": {"name": "textfsm"}
  }'
```

### B. Linux Infrastructure Task (Background)
Execute long-running maintenance with asynchronous log tracking:

```bash
curl -X POST http://localhost:9000/device/exec \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "driver": "paramiko",
    "connection_args": {"host": "10.0.0.100", "username": "root"},
    "command": ["yum update -y"],
    "detach": true,
    "webhook": {"url": "https://callback.your-app.com/notify"}
  }'
```

## 📖 AI & Developer Resources

* 🤖 **[Agent Guide (llms.txt)](llms.txt)** - Essential context for LLM integration.
* 🔌 **[API Manual](ai-docs/API_REFERENCE.md)** - Cleaned and optimized for AI parsing.
* 🏗️ **[Documentation](https://netpulse.readthedocs.io/)** - Full architecture and deployment guides.
* 🐛 **[Issues](https://github.com/scitix/netpulse/issues)** - Bug reports and feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors

* **Locus Li** – Creator & Maintainer
* **Yongkun Li** – Lead Developer