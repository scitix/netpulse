# Glossary

This document defines main terms used in NetPulse system.

## Core Concepts

### API Key
Key used for authentication and authorization to access NetPulse API, passed through HTTP header `X-API-KEY`.

### Controller
Core component of NetPulse, provides RESTful API interface, responsible for receiving requests, validating API keys, dispatching tasks to queues.

### Worker
Process that executes specific network device operations, including:
- **Node Worker**: Node worker process, manages device connections
- **Fifo Worker**: FIFO queue worker process
- **Pinned Worker**: Device-bound worker process, supports connection reuse

### Queue
Data structure for storing pending tasks, supports two strategies:
- **FIFO Queue**: First-In-First-Out, suitable for one-time operations
- **Pinned Queue**: Device-bound, supports connection reuse

### Driver
Component for connecting and managing specific types of network devices:
- **Netmiko**: Universal SSH driver
- **NAPALM**: Cross-vendor standardized driver
- **PyEAPI**: Arista-specific driver

### Scheduler
Component for managing task scheduling, supports:
- `least_load`: Least load scheduling
- `load_weighted_random`: Load weighted random scheduling

### Plugin
Component for extending NetPulse functionality, including:
- Driver plugins: Support new device types
- Template plugins: Custom template engines
- Scheduler plugins: Custom task scheduling
- Webhook plugins: Event notifications

### Template
Template files for generating configuration or parsing output:
- **Jinja2**: Configuration template engine
- **TextFSM**: Text parsing template
- **TTP**: Configuration parsing template

### Long Connection
Maintains persistent connection with network devices, reduces connection establishment time, improves command execution efficiency.

### Job
Specific operation executed in NetPulse, contains task ID, status, parameters, results, and other information.

## Technical Terms

### Redis
In-memory database, used for task queues and state storage.

### RESTful API
API design conforming to REST architecture style, uses standard HTTP methods.

### SSH
Secure Shell protocol, used for remote connection to network devices.

### TTL
Time To Live for connections or cache, unit: seconds.

### Webhook
Event notification mechanism, sends notifications when tasks complete or status changes.

### Vault
HashiCorp Vault, a secrets management system used to securely store and manage network device credentials.

### credential_ref
Credential reference, used in device operations to reference credentials stored in Vault, avoiding directly passing passwords in requests.

### KV v2
Vault's Key-Value storage engine version 2, supports version control, metadata management, and soft delete functionality.

### unseal_key
Vault unseal key, used to unseal a Vault instance (Vault is sealed by default after startup).

### root_token
Vault root token, used for authentication and accessing Vault, has full control permissions.

### mount_point
Vault mount point, the mount path for KV v2 engine, default value is `secret`.
