# NetPulse CLI Tool

NetPulse provides a batch operation CLI tool based on device asset tables, specifically designed for bulk network device management.

## Tool Overview

### 📊 `netpulse-cli` - Batch Table Tool
- **Use Case**: Bulk operations based on device asset tables
- **Features**: Focus on CSV/Excel processing, simplified batch operation workflow, Netmiko driver only
- **Command Format**: `netpulse-cli <exec|bulk> devices.csv "command"`

## Features

- Support for device asset tables in CSV and Excel (XLSX/XLS) formats
- Automatic setting of Netmiko driver types based on vendor names
- Batch execution of commands and configuration push on multiple devices
- Monitoring of asynchronous task execution status
- Template-based output parsing and configuration rendering
- Uses unified device API (`/device/execute` and `/device/bulk`) for better performance
- Smart queue strategy and timeout management
- Automatic operation type recognition (based on command or config fields)

!!! note
    This tool only uses NetPulse's Netmiko driver, focusing on SSH connections to network devices.

## API Architecture

The CLI tool is built on NetPulse's unified device operation API with optimized layered parameter structure:

### Parameter Structure
```json
{
  "driver": "netmiko",
  "devices": [...],
  "connection_args": {
    // Driver connection and authentication parameters
    "device_type": "cisco_ios",
    "username": "admin",
    "password": "admin123"
  },
  "command": "show version",        // Exec operation
  "config": "interface Gi0/1",      // Bulk operation  
  "driver_args": {
    // Driver-specific execution parameters
    "read_timeout": 30,
    "delay_factor": 2,
    "auto_find_prompt": true
  },
  "options": {
    // Global processing options
    "parsing": {...},
    "rendering": {...},
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

### Smart Features
- **Automatic Queue Selection**: Batch operations automatically use "pinned" strategy for device processing consistency
- **Optimized Timeout Settings**: Batch operations default to 600 seconds timeout, suitable for large-scale device operations
- **Operation Auto-Recognition**: Automatically recognizes Exec/Bulk operations based on `command` or `config` fields
- **Enhanced Error Handling**: More detailed error information and status tracking

## Installation

!!! tip
    This tool and the NetPulse API can be deployed separately. It is recommended to install locally using pip.

```bash
# Install CLI tool in the project root directory
pip install .[tool]

# Or install from source
git clone https://github.com/your-org/netpulse.git
cd netpulse
pip install -e .[tool]
```

## Usage Syntax

```bash
netpulse-cli [global options] <subcommand> [suboptions] <table file> <command or config> 
```

### Global Options

- `--endpoint`: NetPulse API endpoint (default: http://localhost:9000)
- `--api-key`: API key for authentication (default: MY_API_KEY)
- `--interval/-i`: Interval for checking task status (seconds) (default: 5)
- `--timeout/-t`: Maximum time to wait for task completion (seconds) (default: 300)

### Subcommands

#### Exec - Execute Commands

`exec`: Execute commands on network devices and retrieve output

```bash
netpulse-cli exec devices.csv "show version"
```

**Suboptions:**
- `--template-type/--type`: Parsing template type (textfsm/ttp)
- `--template/-T`: Template file URI
- `--force/-f`: Skip execution confirmation prompt
- `--vendor`: Filter devices by vendor name (case-insensitive)
- `--monitor/-m`: Monitor task execution progress (default: true)

#### Bulk - Batch Configuration

`bulk`: Push configurations to network devices in bulk

```bash
netpulse-cli bulk devices.csv "interface ge-0/0/0" "description test"
```

**Suboptions:**
- `--template-type/--type`: Rendering template type (jinja2)
- `--template/-T`: Template file URI
- `--save`: Save configuration to startup configuration (default: false)
- `--enable`: Enter enable mode before pushing configuration (default: true)
- `--force/-f`: Skip execution confirmation prompt
- `--vendor`: Filter devices by vendor name (case-insensitive)
- `--monitor/-m`: Monitor task execution progress (default: true)

### Parameters

- `Device File`: Path to a CSV or Excel file containing device information
- `Command or Config`: Command to execute on the device (for push subcommand, this is the configuration to push)

## Device Table Format

The tool expects the input file to contain the following columns:

| Column Name | Description | Required | Default |
|------------|-------------|----------|---------|
| Selected | Whether to include this device | Yes | - |
| Name | Device name | No | - |
| Site | Site information | No | - |
| Location | Physical location | No | - |
| Rack | Rack location | No | - |
| Vendor | Device vendor (used to determine driver) | Yes | - |
| Model | Device model | No | - |
| IP | Device IP address | Yes | - |
| Port | SSH port | No | 22 |
| Username | SSH username | Yes | - |
| Password | SSH password | Yes | - |
| Keepalive | SSH keepalive interval (seconds) | No | - |

**Example CSV:**
```csv
Selected,Name,Site,Location,Rack,Vendor,Model,IP,Port,Username,Password,Keepalive
True,Simulator,AB,XX,L01,Cisco,Cisco Simulator,172.17.0.1,10005,admin,admin,180
```

### Supported Vendors

The tool automatically maps vendor names to device types:
- Arista → arista_eos
- Cisco → cisco_ios  
- Fortinet → fortinet
- H3C → hp_comware
- Huawei → huawei

!!! note
    If the vendor is not in the above mapping, the Vendor field will be passed directly to Netmiko.

## Usage Examples

### Basic Operations

**Exec Operations - Execute Commands:**
```bash
# Basic Exec operation
netpulse-cli exec devices.csv "show version"

# Filter specific vendor devices
netpulse-cli exec devices.csv "show version" --vendor cisco

# Skip confirmation prompt
netpulse-cli exec devices.csv "show version" --force

# Custom API endpoint
netpulse-cli --endpoint http://api.example.com exec devices.csv "show version"

# Get interface status
netpulse-cli exec devices.csv "show ip interface brief" --vendor cisco

# Get routing table
netpulse-cli exec devices.csv "show ip route" --force --no-monitor
```

**Bulk Operations - Batch Configuration:**
```bash
# Basic Bulk operation (single config line)
netpulse-cli bulk devices.csv "hostname NEW-HOSTNAME"

# Multiple config lines (automatically merged)
netpulse-cli bulk devices.csv "interface GigabitEthernet0/1" "description Uplink to Core" "no shutdown"

# Push configuration and save to startup config
netpulse-cli bulk devices.csv "ntp server 1.1.1.1" --save

# Push configuration without entering enable mode
netpulse-cli bulk devices.csv "show version" --no-enable

# Push SNMP config to Cisco devices
netpulse-cli bulk devices.csv "snmp-server community public RO" --vendor cisco

# Batch configure VLAN
netpulse-cli bulk devices.csv "vlan 100" "name MGMT_VLAN" "exit" --vendor cisco --save
```

### Template Usage

This tool basically follows the usage in [Template System](../advanced/templates.md), but has different file reading behavior.

**Using TextFSM template for output parsing:**
```bash
# Use local TextFSM template to parse show version output
netpulse-cli exec devices.csv "show version" \
  --template-type textfsm \
  --template /root/templates/show_version.textfsm

# Use TTP template to parse interface information
netpulse-cli exec devices.csv "show ip interface brief" \
  --template-type ttp \
  --template interface_brief.ttp
```

**Using Jinja2 template for configuration rendering:**
```bash
# Use Jinja2 template for batch interface configuration
netpulse-cli bulk devices.csv '{"interface": "GigabitEthernet0/1", "description": "Uplink"}' \
  --template-type jinja2 \
  --template /root/templates/interface.j2

# Use template for batch OSPF configuration
netpulse-cli bulk devices.csv '{"area": "0", "network": "192.168.1.0/24"}' \
  --template-type jinja2 \
  --template ospf_config.j2
```

### Advanced Usage

**Monitoring and timeout control:**
```bash
# Custom monitoring interval and timeout
netpulse-cli --interval 10 --timeout 600 exec devices.csv "show running-config"

# Disable monitoring (return immediately after job submission)
netpulse-cli exec devices.csv "show version" --no-monitor

# Long-running configuration tasks
netpulse-cli --timeout 1800 bulk devices.csv "copy running-config startup-config" --force
```

## Output Results

The tool saves execution results to a timestamped CSV file (e.g., `result_20250409_144530.csv`). The result file contains the following information:

| Column | Description |
|--------|-------------|
| IP | Device IP address |
| Name | Device name (if provided) |
| Vendor | Device vendor (if provided) |
| Command | Executed command |
| Status | Task execution status |
| Job ID | Unique task identifier |
| Result | Command output or error information |
| Error | Detailed error information (if any) |
| Start Time | Task start time |
| End Time | Task completion time |

## Template System

This tool basically follows the usage in [Template System](../advanced/templates.md), but has different file reading behavior.

### Template File Processing

For convenience in using template files from the command line, the `--template` value is first interpreted as a POSIX path:

1. **Local File**: If the path exists, its content is read and sent to NetPulse API
2. **Template Content**: If the path doesn't exist, it is treated as template content (`plaintext`) and sent directly to NetPulse API
3. **Remote File**: If a URI starting with `file://` is provided, the API Server reads that file

### Template Usage Examples

**Case 1: Remote File**
```bash
netpulse-cli exec devices.csv "show version" \
  --template-type textfsm \
  --template file:///root/templates/show_version.textfsm
```

**Case 2: Local File**
```bash
netpulse-cli exec devices.csv "show version" \
  --template-type textfsm \
  --template /root/templates/show_version.textfsm
```

**Case 3: Direct Template Content**
```bash
netpulse-cli bulk devices.csv '{"interface": "GigabitEthernet0/1", "description": "Test"}' \
  --template-type jinja2 \
  --template "interface {{ interface }}\n description {{ description }}"
```

## Scripting Integration

### Shell Script Examples

**Configuration Backup Script:**
```bash
#!/bin/bash
# backup_configs.sh

DEVICES_FILE="production_devices.csv"
BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

echo "Starting configuration backup..."

# Execute configuration backup
netpulse-cli exec "$DEVICES_FILE" "show running-config" \
  --force \
  --timeout 1800 \
  2>&1 | tee "$BACKUP_DIR/backup.log"

if [ $? -eq 0 ]; then
    echo "Configuration backup completed, log saved in $BACKUP_DIR/backup.log"
else
    echo "Configuration backup failed"
    exit 1
fi
```

**Batch Configuration Deployment Script:**
```bash
#!/bin/bash
# deploy_ntp_config.sh

DEVICES_FILE="devices.csv"
NTP_CONFIG="ntp server 1.1.1.1\nntp server 8.8.8.8"

echo "Deploying NTP configuration to all devices..."

# Push NTP configuration
netpulse-cli bulk "$DEVICES_FILE" "$NTP_CONFIG" \
  --save \
  --force \
  --timeout 600

echo "NTP configuration deployment completed"
```

### Integration with Other Tools

**Integration with cron jobs:**
```bash
# Execute configuration backup daily at 2 AM
0 2 * * * /opt/scripts/backup_configs.sh >> /var/log/netpulse-backup.log 2>&1
```

**Integration with monitoring systems:**
```bash
#!/bin/bash
# health_check.sh

# Check device status
netpulse-cli exec devices.csv "show version" --force --no-monitor > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "Device connections normal"
    exit 0
else
    echo "Device connections abnormal"
    exit 1
fi
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   ```bash
   # Increase timeout
   netpulse-cli --timeout 600 exec devices.csv "show version"
   ```

2. **Authentication Failure**
   ```bash
   # Check username/password in device file
   # Verify device type mapping is correct
   ```

3. **Partial Failure in Batch Operations**
   ```bash
   # Check error information in result CSV file
   # Use --vendor option to process different vendor devices in batches
   ```

4. **Template Parsing Error**
   ```bash
   # Confirm template file path is correct
   # Verify template syntax is correct
   ```

### Debugging Tips

**View Detailed Information:**
- Check the Error column in the generated result CSV file
- View task execution Start Time and End Time
- Use `--force` to skip confirmation prompts for quick testing

**Step-by-step Debugging:**
```bash
# 1. Test single vendor first
netpulse-cli exec devices.csv "show version" --vendor cisco

# 2. Test simple commands
netpulse-cli exec devices.csv "show version" --force

# 3. Gradually increase complexity
netpulse-cli exec devices.csv "show running-config" --template-type textfsm

# 4. Test configuration push
netpulse-cli bulk devices.csv "hostname TEST-DEVICE" --vendor cisco --force
```

## Performance Optimization

### Batch Operation Optimization

- **Reasonable Timeout Settings**: Adjust `--timeout` parameter based on command complexity
- **Batch Processing**: For large numbers of devices, process by vendor or site in batches
- **Template Optimization**: Use appropriate parsing templates to improve result processing efficiency

### Network Optimization

- **Concurrency Control**: CLI tool automatically uses "pinned" queue strategy for concurrency control
- **Connection Reuse**: Netmiko driver automatically manages SSH connection reuse and keepalive
- **Error Recovery**: Tool has automatic retry and error recovery mechanisms

Through this CLI tool, you can efficiently perform bulk network device operations and achieve automation tasks such as configuration management and information collection.
