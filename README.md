# NetPulse

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://hub.docker.com)
[![Python](https://img.shields.io/badge/Python-3.12+-green?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Agent-Ready](https://img.shields.io/badge/Agent--Ready-informational.svg)](ai-docs/llms.txt)

NetPulse is a high-performance, distributed **Connectivity Gateway** designed for large-scale infrastructure interaction. It provides a standardized API-first approach to manage **Network Switches**, **Firewalls**, and **Linux Servers**, specialized for the rigorous demands of **Large-Scale AI Infrastructure** management.

Rather than a complex orchestration engine, NetPulse focuses on being the most reliable "Connectivity Layer"—delivering rock-solid interaction even in massive-scale environments like GPU clusters and high-performance RDMA networks.

## 🛠 Core Engineering Strengths

*   **Multi-Vendor Network Interaction**: Standardized CLI/API control for Cisco, Huawei, Arista, Juniper, and more, leveraging battle-tested drivers (Netmiko, NAPALM, PyEAPI).
*   **High-Resiliency Connectivity**: Beyond traditional SSH, NetPulse implements deep self-healing probes and persistent session pooling ("Pinned Workers") to ensure zero-drop interaction.
*   **Linux Infrastructure Management**: Native Paramiko integration for server-side operations, supporting sudo handling, SFTP, and persistent detached background tasks.
*   **AI Infrastructure Optimized**: Engineered to manage the backbone of AI clusters, where managing thousands of RDMA network nodes and GPU servers requires extreme stability and performance.
*   **Distributed Scalability**: A Controller-Worker architecture that scales horizontally across geo-locations, coordinated via a Redis-backed state machine.
*   **Agent-Ready Context**: Optimized for AI integration, providing structured JSON outputs and specialized context docs for LLM-driven automation.

## 🏗 System Architecture

NetPulse is designed as a lightweight interaction layer. It offloads command execution to a distributed fleet of Workers, ensuring the central API remains responsive while maintaining thousands of concurrent sessions.

- **Pinned Sessions**: Reuses existing connections to eliminate SSH handshake overhead.
- **Failover Logic**: Automatically detects and restores stalled sessions without interrupting higher-level logic.

## 📥 Quick Start

### One-Click Deployment

NetPulse is designed to be deployed quickly in Docker environments:

```bash
# Clone the repository
git clone https://github.com/scitix/netpulse.git
cd netpulse

# One-click deployment using the provided script
bash ./scripts/docker_auto_deploy.sh
```

### Essential Manual Setup
If you prefer manual configuration:
1. Generate env: `bash ./scripts/setup_env.sh generate`
2. Update `.env` with your `NETPULSE_REDIS__PASSWORD` and `NETPULSE_SERVER__API_KEY`.
3. Start: `docker compose up -d`

## 🔌 API Interaction Examples

### A. Network Switch Management (Netmiko)
Execute commands on a switch and retrieve structured data:

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

### B. Linux Server Management (Paramiko)
Execute background maintenance tasks with detached tracking:

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