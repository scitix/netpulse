# NetPulse

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://hub.docker.com)
[![Python](https://img.shields.io/badge/Python-3.12+-green?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Agent-Ready](https://img.shields.io/badge/Agent--Ready-informational.svg)](ai-docs/llms.txt)

NetPulse is a high-performance, distributed infrastructure orchestration engine. It provides a unified, API-first approach to managing both **Network Devices** (Routers, Switches, Firewalls) and **Linux Servers** at scale.

By utilizing persistent connection pooling and a distributed worker architecture, NetPulse transforms legacy CLI-based infrastructure into a cloud-native, programmable ecosystem that is highly optimized for integration with **AI Agents** and modern automated workflows.

## 🚀 Key Features

*   **Unified Orchestration**: A single API logic to manage multi-vendor Network CLI (Cisco, Huawei, Arista, etc.) and Linux/Unix systems.
*   **High-Performance Persistent Sessions**: Uses "Pinned Workers" to maintain long-lived SSH/API connections, reducing execution latency from seconds to milliseconds.
*   **Distributed Architecture**: Cloud-native design with a Controller-Worker model. Scalable on Kubernetes/Docker with dynamic node discovery and Redis-backed task scheduling.
*   **Linux Detached Tasks**: Launch long-running maintenance jobs (e.g., system upgrades) that run independently on the remote host with incremental log streaming and automatic tracking.
*   **Agent-Ready Design**: Engineered for LLM integration. Provides comprehensive context (`llms.txt`, specialized AI docs) and structured JSON outputs for seamless Agentic control.
*   **Production Hardening**: Deep self-healing session monitoring, HashiCorp Vault integration for zero-leak credentials, and automated storage lifecycle management.

## 🏗 System Architecture

NetPulse utilizes a distributed architecture where a central **Controller** manages API requests and a fleet of **Workers** handle the heavy lifting of device/server interaction.

- **Pinned Sessions**: Connections are bound to specific workers to minimize handshake overhead.
- **Failover & Recovery**: Workers automatically detect stalled sessions and self-heal via internal probes.

## 🔌 Plugin System

*   **Infrastructure Drivers**: 
    - **Paramiko**: Advanced Linux management (Detached, Sudo, SFTP, Agent Forwarding).
    - **Netmiko**: Universal Network CLI support (Cisco, Huawei, Juniper, etc.).
    - **NAPALM**: Standardized state verification and configuration management.
    - **PyEAPI**: Arista EOS JSON-RPC optimization.

*   **Logic & Rendering**: 
    - **Templates**: Jinja2 configuration rendering.
    - **Parsers**: TextFSM and TTP for converting raw CLI output into structured JSON.
    - **Webhooks**: Event-driven callbacks for task completion and incremental logs.

## 📥 Quick Start

### Docker Quick Deploy

```bash
# Clone the repository
git clone https://github.com/scitix/netpulse.git
cd netpulse

# One-click deployment
docker compose up -d
```

### API Examples

#### A. Network Device Execution (Cisco)
Connect to a switch and retrieve structured interface data:

```bash
curl -X POST http://localhost:9000/device/exec \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "driver": "netmiko",
    "connection_args": {
      "device_type": "cisco_ios",
      "host": "192.168.1.1",
      "username": "admin",
      "password": "pass"
    },
    "command": ["show ip interface brief"],
    "parsing": {"name": "textfsm"}
  }'
```

#### B. Linux Detached Maintenance (Background)
Launch a system upgrade that continues running even if the API call finishes:

```bash
curl -X POST http://localhost:9000/device/exec \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "driver": "paramiko",
    "connection_args": {"host": "10.0.0.1", "username": "root"},
    "command": ["apt-get update && apt-get upgrade -y"],
    "detach": true,
    "webhook": {"url": "https://callback.your-app.com/jobs"}
  }'
```

## 📖 AI & Developer Resources

For humans and AI Agents, NetPulse provides optimized context for deep integration:

*   🤖 **[Agent Guide (llms.txt)](llms.txt)** - The primary source of truth for LLM context.
*   🔌 **[API Manual](ai-docs/API_REFERENCE.md)** - Simplified API reference optimized for AI parsing.
*   🏗️ **[Documentation](https://netpulse.readthedocs.io/)** - Full architecture and deployment guides.
*   🐛 **[Issues](https://github.com/scitix/netpulse/issues)** - Bug reports and feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors

* **Locus Li** – Creator & Maintainer
* **Yongkun Li** – Lead Developer

---

**NetPulse** - Empowering AI to orchestrate the world's infrastructure.