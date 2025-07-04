# Architecture Overview

NetPulse is a distributed RESTful proxy for network device operations, built on a modular architecture with the following key components:

<div style="max-width: 80%; margin: 0 auto;">
```mermaid
flowchart TB
    %% ─────────────────── Node Style Definitions ───────────────────
    classDef client fill:#F3E5F5,stroke:#8E24AA,stroke-width:2px;
    classDef api    fill:#9ce8e4,stroke:#05998b,stroke-width:2px;
    classDef queue  fill:#FFD3D0,stroke:#D82C20,stroke-width:3px;
    classDef nodew   fill:#E6F4EA,stroke:#4B8B3B,stroke-width:2px;       %% olive green
    classDef fifow   fill:#FDF6E3,stroke:#C29F48,stroke-width:2px;      %% beige
    classDef pinnedw fill:#E6F2FA,stroke:#3D7E9A,stroke-width:2px;      %% soft blue


    %% ─────────────────── Clients (forced horizontal) ───────────────
    subgraph clients [Clients]
        A1[API Client 1]:::client
        A2[API Client 2]:::client
        A3[API Client 3]:::client
        %% helper edges to keep same rank
        A1 --- A2
        A2 --- A3
    end

    %% ─────────────────── API Layer ────────────────────────────────
    subgraph apis [API Servers]
        direction LR
        B1[Controller 1]:::api
        B2[Controller 2]:::api
        B3[Controller 3]:::api
        B1 --- B2
        B2 --- B3
    end

    %% ─────────────────── Redis Queue ──────────────────────────────
    C(["Redis Job Queue"]):::queue

    %% ─────────────────── Worker Layer ─────────────────────────────
    subgraph workers [Workers]
        subgraph W1 [FIFO Worker]
            D1[FIFO Worker → Devices]:::fifow
        end
        subgraph W2 [Node Worker]
            D2[Node Worker]:::nodew
            subgraph pinned [Pinned Workers]
                P1[Pinned Worker → Device 1]:::pinnedw
                P2[Pinned Worker → Device 2]:::pinnedw
            end
        end
    end

    %% ─────────────────── Connections ──────────────────────────────
    clients -->|HTTP Requests| apis
    apis -->|Scheduling| C
    C -->|Async Jobs| D1
    C -->|Async Jobs| D2
    D2 -->|Managed| P1
    D2 -->|Managed| P2

    %% ─────────────────── Subgraph Styles ──────────────────────────
    style clients fill:#FDF8FF,stroke:#C5A3E0,stroke-width:2px,stroke-dasharray:4 4
    style apis    fill:#E0F7FA,stroke:#05998b,stroke-width:2px,stroke-dasharray:4 4
    style workers fill:#FCFCFA,stroke:#CCCCCC,stroke-width:2px,stroke-dasharray:4 4
    style W1 fill:#FBF9F2,stroke:#CBBE9A,stroke-width:1.5px
    style W2 fill:#F1F8E9,stroke:#66BB6A,stroke-width:1.5px
    style pinned fill:#F0F7FA,stroke:#7DAFC5,stroke-width:1.5px


    %% ─────────────────── Hide invisible helper edges ─────────────
    linkStyle 0,1,2,3 stroke-width:0px;
    linkStyle 4,5,6,7,8,9 stroke-width:2px;

```
</div>

## Core Components

1. **RESTful API**
    - Built on FastAPI
    - Handles incoming requests, validates and queues tasks

2. **Message Queue**
    - Redis-based task queue (based on RQ)
    - Used for state synchronization in multi-master multi-slave architecture
    - Stores task states and execution results

3. **Worker Nodes**
    - Three types of Workers designed to handle different types of tasks
    - FIFO Worker: Processes tasks in order
    - Node Worker: Acts as a daemon managing Pinned Workers and node state
    - Pinned Worker: Maintains connection with a single device, executes tasks for that device serially

4. **Plugin System**
    - Extensible plugin system including device drivers, schedulers, template engines, and webhooks
    - Clear interface definitions for easy secondary development and integration

## Design Philosophy

NetPulse's core design philosophy lies in the division of labor among three types of Workers.

In network operations, there are typically two types of tasks:

- **Query Tasks:** Pulling device status, checking configuration information, etc.
- **Configuration Tasks:** Pushing and applying device configurations

<div style="max-width: 40%; margin: 0 auto;">
```mermaid
graph LR
    classDef query fill:#FDF6E3,stroke:#C29F48,stroke-width:2px;      %% beige
    classDef config fill:#E6F2FA,stroke:#3D7E9A,stroke-width:2px;      %% soft blue

    QT[Query Tasks]:::query
    CT[Config Tasks]:::config

    Q1[Pulling Device Status]:::query
    Q2[Checking Configuration Information]:::query
    C1[Pushing and Applying Device Configurations]:::config

    QT --> Q1
    QT --> Q2
    CT --> C1
```
</div>
<div style="max-width: 80%; margin: 0 auto;">
```mermaid
graph TD
    classDef note fill:#FFFFFF,stroke:#000000,stroke-dasharray: 5 5;  %% dashed box for notes

    Note1["<div style='width:300px'><b>Query Tasks</b><br>No specific execution order required</div>"]:::note
    Note2["<div style='width:300px'><b>Config Tasks</b><br>Predictable execution order required</div>"]:::note
```
</div>

These two types of tasks present different requirements for operators. Simply put, query tasks often do not require a specific order, while configuration tasks must guarantee order on a single device. Moreover, users often expect query tasks to execute quickly, while configuration tasks can tolerate queuing. This leads to the necessity of designing two types of Workers: Pinned Workers and FIFO Workers.

Pinned Workers are specifically responsible for connecting to one device, maintaining a one-to-one relationship with the device. Therefore, when clients send tasks to Pinned Workers, they can guarantee that tasks are executed strictly in order on the device. This makes Pinned Workers very suitable for handling configuration tasks.

FIFO Workers have no binding relationship with devices. A system can deploy multiple FIFO Workers. Multiple FIFO Workers simultaneously retrieve tasks from Redis and execute them as quickly as possible. This parallelism shortens task queuing time but also means there is no strict guarantee of order between tasks. Therefore, FIFO Workers are very suitable for completing query tasks.

<div style="max-width: 80%; margin: 0 auto;">
```mermaid
graph TD
    classDef pinnedw fill:#E6F2FA,stroke:#3D7E9A,stroke-width:2px;      %% soft blue
    classDef fifow fill:#FDF6E3,stroke:#C29F48,stroke-width:2px;      %% beige
    classDef nodew fill:#E6F4EA,stroke:#4B8B3B,stroke-width:2px;      %% olive green
    classDef device fill:#DCDCDC,stroke:#696969,stroke-width:2px;     %% gray 

    subgraph NodeWorker [Node / Container]
        NW[Node Worker]:::nodew

        subgraph PinnedWorkers [Pinned Workers]
            PW1[Pinned Worker]:::pinnedw
            PW2[Pinned Worker]:::pinnedw
        end
    end

    subgraph FIFOWorkers [FIFO Workers]
        FW1[FIFO Worker 1]:::fifow
        FW2[FIFO Worker 2]:::fifow
    end

    NW -->|Generates & Manages | PW1
    NW -->|Generates & Manages | PW2
    PW1 -->|Config / Query Tasks| Device1[Device 1]:::device
    PW2 -->|Config / Query Tasks| Device2[Device 2]:::device
    FIFOWorkers -->|Query Tasks| Device3[Device 3]:::device
    FIFOWorkers -->|Query Tasks| Device4[Device 4]:::device
    FIFOWorkers -->|Query Tasks| Device5[Device 5]:::device


    style NodeWorker fill:#F1F8E9,stroke:#66BB6A,stroke-width:1.5px
    style PinnedWorkers fill:#F0F7FA,stroke:#7DAFC5,stroke-width:1.5px
    style FIFOWorkers fill:#FBF9F2,stroke:#CBBE9A,stroke-width:1.5px
```
</div>

During deployment, we can pre-start a specified number of FIFO Workers, but it's impossible to pre-start Pinned Workers because we cannot predict which devices users will operate on. Therefore, Pinned Workers must be generated dynamically, and Node Workers serve as "daemon processes" to dynamically generate Pinned Workers within containers and nodes.

In addition to the above basic design considerations, we further utilize the characteristic that a single Pinned Worker is only associated with one device to implement SSH Session persistence in Pinned Workers, further improving task execution stability and reducing latency (refer to [SSH Keepalive](./drivers.md)).

# Feature Comparison

Compared to existing projects like NetPalm, NetPulse has the following significant advantages:

## Streamlined Functionality

NetPulse conducted in-depth analysis of business requirements during its initial design and fully considered functionality universality. Compared to NetPalm, NetPulse focuses on the core functionality of command execution, leaving auxiliary functions like template management and scheduled task triggers to upper-layer business systems. This streamlined design philosophy makes NetPulse easier to maintain while better integrating into existing infrastructure environments.

## Excellent Performance

NetPulse achieves significant performance improvements through three key technologies:

- **Connection Keepalive Mechanism**: By maintaining long connections, it greatly reduces execution delays caused by repeatedly establishing connections, achieving rapid command execution.
- **Diverse Scheduling Algorithms**: Provides multiple scheduling strategies such as load balancing and resource centralization, performing better than NetPalm's single greedy algorithm.
- **Batch Command Interface**: Supports batch command execution, effectively reducing duplicate request overhead during large-scale device operations. Combined with batch scheduling algorithms, the performance advantages are even more pronounced.

## High Availability

NetPulse's distributed architecture design provides excellent scalability and fault tolerance capabilities. Through the multi-master multi-slave architecture, the system can maintain stable operation even when some nodes fail, ensuring business continuity.

## Flexible Extension

The plugin system design allows users to easily extend NetPulse's functionality according to their needs. Whether adding new device drivers, implementing custom scheduling algorithms, or integrating with existing systems, it can be achieved through plugins.

---

For more detailed information about specific components, see:
- [Driver System](drivers.md)
- [Template System](templates.md)
- [Scheduler System](schedulers.md)
- [Plugin System](plugins.md)
- [Webhook System](webhooks.md) 