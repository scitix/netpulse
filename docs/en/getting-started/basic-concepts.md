# NetPulse Basic Concepts

## Overview

NetPulse is a distributed RESTful API controller designed for network device management. It adopts a microservices architecture, based on SSH long connection technology, providing API services for network device management. Before starting to use it, understanding its core concepts and architectural components will help you use the system better.

!!! tip "NetPulse Features"
    - **Distributed Architecture**: Supports Docker and Kubernetes multi-node deployment, supports horizontal scaling
    - **Connection Reuse**: Reduces connection establishment overhead through persistent connections
    - **Asynchronous Processing**: Asynchronous processing mechanism based on task queues
    - **Multi-Driver Support**: Supports multiple network device drivers (Netmiko, NAPALM, PyEAPI, Paramiko, etc.)
    - **Basic Monitoring**: Provides task status query and Worker status monitoring

## Core Concepts Overview

Before diving deep, first understand the relationship between three core concepts:

```
Client → API Request → Controller → Task Queue → Worker → Network Device
         ↓           ↓            ↓         ↓
      Driver Selection  Task Dispatch  Queue Strategy  Connection Reuse
```

- **Driver**: How to connect to devices (Netmiko/NAPALM/PyEAPI/Paramiko)
- **Queue**: How to schedule tasks (FIFO/Pinned)
- **Job**: Asynchronous execution, need to query results

## Core Concepts

### 1. Driver System (Drivers)

NetPulse supports multiple network device drivers, each targeting different device types and connection methods. Choosing the right driver can improve operation efficiency and stability in specific scenarios.

#### Driver Comparison Table

| Driver Type | Connection Method | Performance | Compatibility | Recommended Scenario |
|-------------|-------------------|-------------|----------------|----------------------|
| **Netmiko** | SSH | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | General device management |
| **NAPALM** | SSH/API | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Multi-vendor standardization |
| **PyEAPI** | HTTP/HTTPS | ⭐⭐⭐⭐⭐ | ⭐⭐ | Arista-specific |
| **Paramiko** | SSH | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Linux server management |

#### Netmiko Driver

!!! success "Recommended for daily operations"
    Netmiko is a more universal driver, supporting a wide range of device types.

| Feature | Description |
|---------|-------------|
| **Purpose** | Universal SSH connection, supports most network devices |
| **Device Types** | cisco_ios, cisco_nxos, juniper_junos, arista_eos, huawei, hp_comware |
| **Characteristics** | Strong universality, good compatibility, low learning curve |
| **Use Cases** | Daily device management and configuration, mixed vendor environments |
| **Advantages** | Supports many device types, relatively complete documentation |
| **Disadvantages** | Relatively lower performance, depends on SSH connection |

#### NAPALM Driver

!!! info "Suitable for multi-vendor environments"
    NAPALM provides a unified interface, simplifying multi-vendor device management.

| Feature | Description |
|---------|-------------|
| **Purpose** | Cross-vendor standardized operations |
| **Device Types** | ios, iosxr, junos, eos, nxos |
| **Characteristics** | Provides unified interface, cross-vendor compatible |
| **Use Cases** | Standardized operations in multi-vendor environments |
| **Advantages** | Unified interface, supports configuration rollback |
| **Disadvantages** | Limited supported device types |

#### PyEAPI Driver

!!! warning "Only supports Arista devices"
    PyEAPI is Arista device's native API with good performance.

| Feature | Description |
|---------|-------------|
| **Purpose** | Arista device-specific operations |
| **Device Types** | Arista EOS |
| **Characteristics** | Native API support, excellent performance |
| **Use Cases** | High-performance operations for Arista devices |
| **Advantages** | Good performance for Arista devices, supports batch operations |
| **Disadvantages** | Only supports Arista devices |

#### Paramiko Driver

!!! info "For Linux server management"
    Paramiko is a driver for managing Linux servers, implemented based on native SSH protocol.

| Feature | Description |
|---------|-------------|
| **Purpose** | Linux server management (Ubuntu, CentOS, Debian, etc.) |
| **Device Types** | Linux servers |
| **Characteristics** | Supports command execution, file transfer, proxy connections, sudo, and other advanced features |
| **Use Cases** | System monitoring, configuration management, software deployment, file transfer |
| **Advantages** | Rich features, supports file transfer and sudo operations |
| **Disadvantages** | Only supports Linux servers, does not support network devices |

### 2. Queue Strategies (Queue Strategies)

NetPulse provides two queue strategies to optimize task execution. Choosing the right queue strategy can improve system performance and stability in specific scenarios.

#### Queue Strategy Comparison

| Strategy | Performance | Connection Reuse | Use Cases | Driver Recommendation |
|----------|-------------|------------------|-----------|----------------------|
| **FIFO** | ⭐⭐⭐ | ❌ | Stateless general tasks, long-running tasks, file transfer | **NAPALM** (recommended), **PyEAPI** (default + recommended), **Paramiko** (default + recommended) |
| **Pinned** | ⭐⭐⭐⭐⭐ | ✅ | SSH operations, frequent operations on same device | **Netmiko** (default + recommended), NAPALM (default, but FIFO recommended) |

!!! tip "Driver and Queue Strategy Selection"
    - **Netmiko**: Default and recommended to use **Pinned**, improves performance through connection reuse
    - **NAPALM**: Default uses Pinned, but **FIFO** is recommended (more suitable for configuration management scenarios)
    - **PyEAPI**: Default and recommended to use **FIFO** (HTTP/HTTPS stateless connection)
    - **Paramiko**: Default and recommended to use **FIFO** (suitable for Linux server management and file transfer)

#### FIFO Queue (fifo)

!!! note "Default strategy for PyEAPI and Paramiko drivers"
    FIFO queue is the default strategy for PyEAPI and Paramiko drivers, suitable for HTTP/HTTPS stateless connections and Linux server management.

- **Characteristics**: First-In-First-Out, creates new connection each time
- **Advantages**: Simple and efficient, suitable for stateless operations and long-running tasks
- **Use Cases**: HTTP/HTTPS API calls (e.g., PyEAPI), Linux server management (e.g., Paramiko), file transfer
- **Configuration**: `"queue_strategy": "fifo"`
- **Performance**: Suitable for stateless operations and long-running tasks, relatively large connection overhead

#### Device-Bound Queue (pinned)

!!! success "Default strategy for Netmiko/NAPALM drivers"
    Pinned queue is the default strategy for Netmiko and NAPALM drivers, reducing SSH connection establishment time overhead through connection reuse, which can improve operation efficiency in scenarios where the same device is frequently operated.

- **Characteristics**: Device-specific queue, connection reuse
- **Advantages**: Reduces connection establishment time, can improve efficiency in frequent operation scenarios
- **Use Cases**: Frequent operations on the same device, SSH-connected devices (Netmiko/NAPALM)
- **Configuration**: `"queue_strategy": "pinned"`
- **Performance**: Suitable for high-frequency operation scenarios, can reduce connection establishment overhead

!!! tip "Usage Recommendation"
    In scenarios where you need to frequently operate the same device, using Pinned queue strategy can reduce connection establishment overhead.

### 3. Job Management (Job Management)

NetPulse adopts an asynchronous task processing mechanism, supporting large-scale concurrent operations and task status tracking.

!!! warning "Important: Asynchronous Processing Mechanism"
    All device operations (`/device/exec`, `/device/bulk`) are asynchronous:
    - API immediately returns job ID and status (usually `queued`)
    - Need to query execution results through `/job?id=xxx` interface
    - Only `/device/test-connection` is synchronous, returns results immediately

#### Job Lifecycle

```
Submit Job → Queue Waiting → Executing → Execution Complete
                    ↓
              Execution Failed → Error Handling
```

**Detailed Process:**

1. **Submit**: Client submits job to queue, API immediately returns job ID
2. **Queue**: Job waits in Redis queue for processing (status: `queued`)
3. **Execute**: Worker process gets job from queue and executes (status: `started`)
4. **Complete**: Job execution completes, results stored in Redis (status: `finished`)
5. **Query**: Client queries results through job ID
6. **Failed**: Job execution fails, error information stored in results (status: `failed`)

#### Job Status

| Status | Description | Duration | Actions |
|--------|-------------|----------|---------|
| `queued` | Queued, waiting for execution | Usually < 1 second | Can cancel |
| `started` | Executing | Depends on task complexity | Can cancel |
| `finished` | Execution complete | Default 300 seconds (5 minutes) | View results |
| `failed` | Execution failed | Default 300 seconds (5 minutes) | View errors |
| `cancelled` | Cancelled | Default 1800 seconds (30 minutes) | View reason |

!!! info "Job Storage Time"
    Job results and status are stored in Redis with TTL:
    - **Job Results**: Default 300 seconds (5 minutes), configurable via `result_ttl` in config file
    - **Job Metadata**: Default 1800 seconds (30 minutes), configurable via `ttl` in config file
    - **Supports Customization**: Adjust via global `ttl` parameter in API request

### 4. Connection Reuse (Connection Reuse)

NetPulse uses long connection technology to improve performance, which is one of the key features for high system performance.

#### Connection Pool Management

- **Persistent Connections**: SSH connections remain active after task completion
- **Connection Reuse**: Multiple tasks for the same device share connections
- **Auto Reconnect**: Automatically re-establish connections when disconnected
- **Connection Cleanup**: Regularly clean up idle connections
- **Connection Monitoring**: Real-time monitoring of connection status and health

#### Performance Advantages

| Advantage | Description | Performance Improvement |
|-----------|-------------|-------------------------|
| **Reduce Connection Time** | Avoid repeated SSH connection establishment | Save connection establishment time |
| **Improve Execution Efficiency** | Reuse established connections | Improve operation efficiency |
| **Reduce Device Load** | Reduce number of device connections | Reduce connection overhead |
| **Support Concurrent Operations** | Multiple tasks execute in parallel | Improve concurrency capability |

!!! success "Connection Reuse Effect"
    In batch operation scenarios, connection reuse can reduce SSH connection establishment time and improve operation efficiency.

---

### 5. Monitoring and Logging (Monitoring & Logging)

NetPulse provides basic monitoring and logging systems:

#### System Monitoring

| Monitoring Item | Description | Access Method | Implementation Status |
|-----------------|-------------|---------------|----------------------|
| **Service Status** | Basic health check | `/health` API |
| **Job Statistics** | Job execution statistics | `/job` API |
| **Worker Status** | Worker process status | `/worker` API |

#### Logging System

| Function | Description | Implementation Status |
|----------|-------------|----------------------|
| **Multi-Level Logging** | DEBUG, INFO, WARNING, ERROR |
| **Sensitive Information Filtering** | Automatically filter passwords and other sensitive information |
| **Colored Output** | Console colored log display |

---

## System Components

NetPulse adopts a microservices architecture, with clear responsibilities for each component, supporting independent scaling.

### 1. Controller (Controller)

!!! success "API Gateway"
    Controller is the entry point of the system, responsible for handling all API requests.

| Attribute | Description |
|-----------|-------------|
| **Function** | Provides RESTful interface |
| **Port** | 9000 |
| **Responsibilities** | Receive client requests, verify API keys, dispatch tasks to queues, return job results |
| **Scalability** | Supports multi-instance deployment, load balancing |
| **Monitoring** | Provides health checks and performance metrics |

### 2. Worker (Worker Process)

!!! info "Task Execution Engine"
    Worker is the core execution component of the system, responsible for specific network device operations.

| Attribute | Description |
|-----------|-------------|
| **Function** | Execute specific network device operations |
| **Types** | `node-worker`: Node worker process<br>`fifo-worker`: FIFO queue worker process<br>`pinned-worker`: Device-bound worker process |
| **Responsibilities** | Get tasks from queue, establish device connections, execute network commands, return execution results |
| **Scalability** | Supports horizontal scaling, dynamically increase/decrease Worker count |
| **Fault Tolerance** | Supports task retry and error recovery |

### 3. Redis (Cache and Queue)

!!! warning "Data Storage Center"
    Redis is the data storage and message queue center of the system.

| Function | Purpose | Configuration |
|----------|---------|---------------|
| **Task Queue** | Store pending tasks | Persistent queue |
| **Connection Cache** | Cache connection information | TTL cache |
| **Result Storage** | Store task results | Configurable retention time |
| **Session Management** | Manage session state | Auto-expire cleanup |
| **Configuration Storage** | Store system configuration | Persistent storage |

### 4. Plugin System (Plugin System)

!!! tip "Extensible Architecture"
    Plugin system provides extensibility for NetPulse.

| Type | Function | Examples |
|------|----------|----------|
| **Driver Plugin** | Support new device types | Custom vendor drivers |
| **Template Plugin** | Custom template engines | Jinja2, TextFSM, TTP |
| **Scheduler Plugin** | Custom task scheduling | Scheduled tasks, conditional triggers |
| **Webhook Plugin** | Event notifications | Task completion notifications, error alerts |

---

## Key Terms

### API Related

| Term | Description |
|------|-------------|
| **API Key** | Key used for authentication |
| **Endpoint** | API interface address |
| **Request/Response** | Request and response format |
| **Status Code** | HTTP status code |

### Device Related

| Term | Description |
|------|-------------|
| **Device Type** | Device type identifier |
| **Connection Args** | Connection parameters |
| **Driver Args** | Driver parameters |
| **Command** | Network command to execute |

### Job Related

| Term | Description |
|------|-------------|
| **Job ID** | Unique job identifier |
| **Task** | Specific task to execute |
| **Queue** | Task queue |
| **Worker** | Worker process |

### Template Related

| Term | Description |
|------|-------------|
| **Jinja2** | Configuration template engine |
| **TextFSM** | Text parsing template |
| **TTP** | Configuration parsing template |
| **Template** | Template file |

---

## Best Practices

### 1. Connection Management

!!! success "Connection Optimization Recommendations"
    Reasonable connection management is key to improving system performance.

- **Queue Strategy Selection**: Use pinned queue for device binding, suitable for SSH long connection-based driver services
- **Timeout Settings**: Set connection timeout appropriately (recommend 30-60 seconds)
- **Connection Reuse**: Enable connection reuse to improve execution efficiency
- **Connection Monitoring**: Regularly check connection status, clean up abnormal connections in time
- **Connection Pool Configuration**: Adjust connection pool size based on device count

### 2. Job Execution

!!! info "Job Execution Optimization"
    Reasonable job execution strategies can improve system throughput.

- **Batch Operations**: Use batch operations to improve efficiency, reduce API call count
- **Timeout Settings**: Set job timeout appropriately, avoid long waits
- **Callback Notifications**: Enable webhook callback notifications to get execution results in time
- **Logging**: Record detailed operation logs for troubleshooting
- **Job Priority**: Set job priority appropriately, important tasks execute first

### 3. Error Handling

!!! warning "Error Handling Strategy"
    Complete error handling mechanisms ensure stable system operation.

- **Retry Mechanism**: Implement intelligent retry mechanism to handle temporary errors
- **Error Logging**: Record detailed error logs, including error context
- **Recovery Solutions**: Provide error recovery solutions, automatically handle common errors
- **Status Monitoring**: Monitor system status, discover and handle anomalies in time
- **Alert Mechanism**: Set up alert mechanism to notify operations personnel in time

### 4. Performance Optimization

!!! tip "Performance Tuning Recommendations"
    System performance optimization needs to be considered from multiple dimensions.

- **Connection Pool**: Use connection pool to reduce connection establishment overhead
- **Result Caching**: Enable result caching to avoid repeated calculations
- **Concurrency Control**: Configure concurrency appropriately, balance performance and resource usage
- **Resource Monitoring**: Monitor resource usage, adjust configuration in time
- **Load Balancing**: Use load balancing to distribute system pressure

---

## Next Steps

Now that you understand NetPulse's core concepts, we recommend:

1. **[Quick Start](quick-start.md)** - Learn basic API usage skills
2. **[Deployment Guide](deployment-guide.md)** - Learn production environment deployment
3. **[Postman Usage Guide](postman-guide.md)** - Use Postman to quickly test APIs

---