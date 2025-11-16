# API Usage Examples

## Overview

This document provides complete usage examples of NetPulse API in actual business scenarios, including device management, configuration operations, batch processing, and other common scenarios.

## Scenario 1: Vault Credential Management

### Business Requirements
- Securely store device credentials in Vault
- Use credential references in device operations
- Manage credential lifecycle (create, read, update, delete)

### Implementation

```python
import requests
from typing import Dict, Optional

class VaultCredentialManager:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
    
    def create_credential(self, path: str, username: str, password: str, metadata: Optional[Dict] = None) -> Dict:
        """Create credential in Vault"""
        payload = {
            "path": path,
            "username": username,
            "password": password
        }
        if metadata:
            payload["metadata"] = metadata
        
        response = requests.post(
            f"{self.base_url}/credential/vault/create",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def read_credential(self, path: str, show_password: bool = False) -> Dict:
        """Read credential from Vault"""
        payload = {
            "path": path,
            "show_password": show_password
        }
        response = requests.post(
            f"{self.base_url}/credential/vault/read",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def list_credentials(self, path_prefix: str = "", recursive: bool = True) -> Dict:
        """List credential paths"""
        payload = {
            "path_prefix": path_prefix,
            "recursive": recursive
        }
        response = requests.post(
            f"{self.base_url}/credential/vault/list",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def get_metadata(self, path: str) -> Dict:
        """Get credential metadata"""
        payload = {"path": path}
        response = requests.post(
            f"{self.base_url}/credential/vault/metadata",
            headers=self.headers,
            json=payload
        )
        return response.json()
    
    def delete_credential(self, path: str) -> Dict:
        """Delete credential from Vault"""
        payload = {"path": path}
        response = requests.post(
            f"{self.base_url}/credential/vault/delete",
            headers=self.headers,
            json=payload
        )
        return response.json()

# Usage Example
manager = VaultCredentialManager("http://localhost:9000", "your-api-key")

# 1. Create credential
result = manager.create_credential(
    path="sites/hq/admin",
    username="admin",
    password="secure_password",
    metadata={"description": "HQ site admin credentials", "site": "hq"}
)
print(f"Credential created: {result}")

# 2. Read credential (password hidden by default)
result = manager.read_credential("sites/hq/admin", show_password=False)
print(f"Credential: {result}")

# 3. Use credential in device operation
response = requests.post(
    "http://localhost:9000/device/execute",
    headers={"X-API-KEY": "your-api-key", "Content-Type": "application/json"},
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "credential_ref": "sites/hq/admin"  # Reference Vault credential
        },
        "command": "show version"
    }
)
print(f"Device operation result: {response.json()}")

# 4. List all credentials
result = manager.list_credentials(path_prefix="sites", recursive=True)
print(f"Credential paths: {result['data']['paths']}")

# 5. Get credential metadata
result = manager.get_metadata("sites/hq/admin")
print(f"Metadata: {result}")

# 6. Batch read credentials
response = requests.post(
    "http://localhost:9000/credential/vault/batch-read",
    headers={"X-API-KEY": "your-api-key", "Content-Type": "application/json"},
    json={
        "paths": ["sites/hq/admin", "sites/branch1/admin", "devices/core/backup"],
        "show_password": False
    }
)
print(f"Batch read result: {response.json()}")

# 7. Delete credential
result = manager.delete_credential("sites/hq/admin")
print(f"Credential deleted: {result}")
```

### Best Practices

**Path Naming**:
- Use hierarchical structure: `sites/{site}/{role}`, `devices/{type}/{purpose}`
- Keep paths descriptive and consistent

**Metadata Management**:
- Add descriptions, tags, and custom metadata for lifecycle management
- Use metadata API to track credential changes

**Security**:
- Never expose passwords in logs or API requests
- Use `show_password: false` by default
- Regularly rotate passwords and create new versions

## Scenario 2: Network Device Discovery

### Business Requirements
- Discover all devices in the network
- Collect basic device information
- Verify device connectivity

### Implementation

```python
import requests
import json
from typing import List, Dict

class NetworkDiscovery:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-KEY": api_key}
    
    def discover_devices(self, device_list: List[Dict]) -> Dict:
        """Network device discovery"""
        results = {
            "discovered": [],
            "failed": [],
            "total": len(device_list)
        }
        
        for device in device_list:
            try:
                # 1. Test device connection
                connection_result = self.test_device_connection(device)
                
                if connection_result["success"]:
                    # 2. Collect device information
                    device_info = self.collect_device_info(device)
                    results["discovered"].append({
                        "device": device,
                        "connection": connection_result,
                        "info": device_info
                    })
                else:
                    results["failed"].append({
                        "device": device,
                        "error": connection_result["error_message"]
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "device": device,
                    "error": str(e)
                })
        
        return results
    
    def test_device_connection(self, device: Dict) -> Dict:
        """Test device connection"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device["device_type"],
                "host": device["host"],
                "username": device["username"],
                "password": device["password"],
                "port": device.get("port", 22),
                "timeout": 30
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/test-connection",
            json=payload,
            headers=self.headers
        )
        
        result = response.json()
        return result["data"]
    
    def collect_device_info(self, device: Dict) -> Dict:
        """Collect device information"""
        commands = [
            "show version",
            "show ip interface brief",
            "show running-config | include hostname"
        ]
        
        device_info = {}
        
        for command in commands:
            payload = {
                "driver": "netmiko",
                "connection_args": {
                    "device_type": device["device_type"],
                    "host": device["host"],
                    "username": device["username"],
                    "password": device["password"]
                },
                "command": command,
                "options": {
                    "queue_strategy": "pinned",
                    "ttl": 300
                }
            }
            
            response = requests.post(
                f"{self.base_url}/device/execute",
                json=payload,
                headers=self.headers
            )
            
            job_result = response.json()
            job_id = job_result["data"]["id"]
            
            # Wait for job completion
            job_status = self.wait_for_job_completion(job_id)
            
            if job_status["status"] == "finished":
                device_info[command] = job_status["result"]["output"]
            else:
                device_info[command] = f"Error: {job_status['result']['error']}"
        
        return device_info
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 300):
        """Wait for job completion"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/job?id={job_id}",
                headers=self.headers
            )
            
            job_status = response.json()["data"][0]
            
            if job_status["status"] in ["finished", "failed"]:
                return job_status
            
            time.sleep(1)
        
        raise TimeoutError(f"Job {job_id} execution timeout")

# Usage example
discovery = NetworkDiscovery("http://localhost:9000", "your_api_key")

devices = [
    {
        "host": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "device_type": "cisco_ios"
    },
    {
        "host": "192.168.1.2",
        "username": "admin",
        "password": "admin123",
        "device_type": "cisco_ios"
    },
    {
        "host": "192.168.1.3",
        "username": "admin",
        "password": "admin123",
        "device_type": "juniper_junos"
    }
]

results = discovery.discover_devices(devices)
print(f"Discovered devices: {len(results['discovered'])}")
print(f"Failed devices: {len(results['failed'])}")
```

## Scenario 2: Batch Configuration Backup

### Business Requirements
- Regularly backup configurations of all devices
- Support multiple device types
- Save configurations to file system

### Implementation

```python
import requests
import json
import os
from datetime import datetime
from typing import List, Dict

class ConfigBackup:
    def __init__(self, base_url: str, api_key: str, backup_dir: str = "backups"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-KEY": api_key}
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def backup_all_devices(self, devices: List[Dict]) -> Dict:
        """Backup all device configurations"""
        backup_results = {
            "success": [],
            "failed": [],
            "total": len(devices)
        }
        
        for device in devices:
            try:
                backup_result = self.backup_single_device(device)
                if backup_result["success"]:
                    backup_results["success"].append(backup_result)
                else:
                    backup_results["failed"].append(backup_result)
            except Exception as e:
                backup_results["failed"].append({
                    "device": device,
                    "error": str(e)
                })
        
        return backup_results
    
    def backup_single_device(self, device: Dict) -> Dict:
        """Backup single device configuration"""
        # Determine backup commands
        backup_commands = self.get_backup_commands(device["device_type"])
        
        backup_data = {
            "device": device,
            "timestamp": datetime.now().isoformat(),
            "configs": {}
        }
        
        for command_name, command in backup_commands.items():
            try:
                payload = {
                    "driver": "netmiko",
                    "connection_args": {
                        "device_type": device["device_type"],
                        "host": device["host"],
                        "username": device["username"],
                        "password": device["password"]
                    },
                    "command": command,
                    "options": {
                        "queue_strategy": "pinned",
                        "ttl": 300
                    }
                }
                
                response = requests.post(
                    f"{self.base_url}/device/execute",
                    json=payload,
                    headers=self.headers
                )
                
                job_result = response.json()
                job_id = job_result["data"]["id"]
                
                # Wait for job completion
                job_status = self.wait_for_job_completion(job_id)
                
                if job_status["status"] == "finished":
                    backup_data["configs"][command_name] = job_status["result"]["output"]
                else:
                    backup_data["configs"][command_name] = f"Error: {job_status['result']['error']}"
                    
            except Exception as e:
                backup_data["configs"][command_name] = f"Error: {str(e)}"
        
        # Save backup file
        filename = f"{device['host']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.backup_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        backup_data["filepath"] = filepath
        backup_data["success"] = True
        
        return backup_data
    
    def get_backup_commands(self, device_type: str) -> Dict[str, str]:
        """Get backup commands based on device type"""
        commands = {
            "cisco_ios": {
                "running_config": "show running-config",
                "startup_config": "show startup-config",
                "version": "show version",
                "interfaces": "show ip interface brief"
            },
            "juniper_junos": {
                "running_config": "show configuration",
                "startup_config": "show configuration | display-set",
                "version": "show version",
                "interfaces": "show interfaces terse"
            },
            "arista_eos": {
                "running_config": "show running-config",
                "startup_config": "show startup-config",
                "version": "show version",
                "interfaces": "show ip interface brief"
            }
        }
        
        return commands.get(device_type, commands["cisco_ios"])
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 300):
        """Wait for job completion"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/job?id={job_id}",
                headers=self.headers
            )
            
            job_status = response.json()["data"][0]
            
            if job_status["status"] in ["finished", "failed"]:
                return job_status
            
            time.sleep(1)
        
        raise TimeoutError(f"Job {job_id} execution timeout")

# Usage example
backup = ConfigBackup("http://localhost:9000", "your_api_key", "config_backups")

devices = [
    {
        "host": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "device_type": "cisco_ios"
    },
    {
        "host": "192.168.1.2",
        "username": "admin",
        "password": "admin123",
        "device_type": "juniper_junos"
    }
]

results = backup.backup_all_devices(devices)
print(f"Backup successful: {len(results['success'])}")
print(f"Backup failed: {len(results['failed'])}")
```

## Scenario 3: Configuration Change Management

### Business Requirements
- Safely push configuration changes
- Support configuration rollback
- Backup before changes

### Implementation

```python
import requests
import json
from typing import Dict, List

class ConfigChangeManager:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-KEY": api_key}
    
    def safe_config_change(self, device: Dict, config_commands: List[str], 
                          description: str = "") -> Dict:
        """Safe configuration change"""
        change_result = {
            "device": device,
            "description": description,
            "backup": None,
            "change": None,
            "rollback": None,
            "success": False
        }
        
        try:
            # 1. Backup current configuration
            change_result["backup"] = self.backup_config(device)
            
            # 2. Push configuration change
            change_result["change"] = self.push_config(device, config_commands)
            
            if change_result["change"]["success"]:
                change_result["success"] = True
                print(f"✅ Device {device['host']} configuration change successful")
            else:
                # 3. Configuration failed, execute rollback
                change_result["rollback"] = self.rollback_config(device, change_result["backup"])
                print(f"❌ Device {device['host']} configuration change failed, rolled back")
                
        except Exception as e:
            change_result["error"] = str(e)
            print(f"❌ Device {device['host']} configuration change exception: {e}")
        
        return change_result
    
    def backup_config(self, device: Dict) -> Dict:
        """Backup device configuration"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device["device_type"],
                "host": device["host"],
                "username": device["username"],
                "password": device["password"]
            },
            "command": "show running-config",
            "options": {
                "queue_strategy": "pinned",
                "ttl": 300
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            json=payload,
            headers=self.headers
        )
        
        job_result = response.json()
        job_id = job_result["data"]["id"]
        
        job_status = self.wait_for_job_completion(job_id)
        
        return {
            "success": job_status["status"] == "finished",
            "config": job_status["result"]["output"] if job_status["status"] == "finished" else None,
            "error": job_status["result"]["error"] if job_status["status"] == "failed" else None
        }
    
    def push_config(self, device: Dict, config_commands: List[str]) -> Dict:
        """Push configuration change"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device["device_type"],
                "host": device["host"],
                "username": device["username"],
                "password": device["password"],
                "enable_mode": True
            },
            "config": config_commands,
            "driver_args": {
                "save": True,
                "exit_config_mode": True
            },
            "options": {
                "queue_strategy": "pinned",
                "ttl": 300
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            json=payload,
            headers=self.headers
        )
        
        job_result = response.json()
        job_id = job_result["data"]["id"]
        
        job_status = self.wait_for_job_completion(job_id)
        
        return {
            "success": job_status["status"] == "finished",
            "output": job_status["result"]["retval"] if job_status["status"] == "finished" and job_status.get("result") else None,
            "error": job_status["result"]["error"] if job_status["status"] == "failed" and job_status.get("result") else None
        }
    
    def rollback_config(self, device: Dict, backup: Dict) -> Dict:
        """Rollback configuration"""
        if not backup["success"] or not backup["config"]:
            return {"success": False, "error": "Backup configuration unavailable"}
        
        # Parse backup configuration and generate rollback commands
        rollback_commands = self.generate_rollback_commands(backup["config"])
        
        return self.push_config(device, rollback_commands)
    
    def generate_rollback_commands(self, backup_config: str) -> List[str]:
        """Generate rollback commands"""
        # Simplified processing here, actual implementation should parse configuration and generate corresponding rollback commands
        lines = backup_config.split('\n')
        rollback_commands = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('!') and not line.startswith('version'):
                rollback_commands.append(line)
        
        return rollback_commands
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 300):
        """Wait for job completion"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/job?id={job_id}",
                headers=self.headers
            )
            
            job_status = response.json()["data"][0]
            
            if job_status["status"] in ["finished", "failed"]:
                return job_status
            
            time.sleep(1)
        
        raise TimeoutError(f"Job {job_id} execution timeout")

# Usage example
config_manager = ConfigChangeManager("http://localhost:9000", "your_api_key")

device = {
    "host": "192.168.1.1",
    "username": "admin",
    "password": "admin123",
    "device_type": "cisco_ios"
}

config_commands = [
    "interface GigabitEthernet0/1",
    " description Test Interface",
    " ip address 192.168.1.1 255.255.255.0",
    " no shutdown"
]

result = config_manager.safe_config_change(device, config_commands, "Add test interface configuration")
print(f"Configuration change result: {result['success']}")
```

## Scenario 4: Batch Device Monitoring

### Business Requirements
- Regularly monitor device status
- Collect performance data
- Generate monitoring reports

### Implementation

```python
import requests
import json
import time
from datetime import datetime
from typing import List, Dict

class DeviceMonitor:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-KEY": api_key}
    
    def monitor_devices(self, devices: List[Dict]) -> Dict:
        """Batch monitor devices"""
        monitor_results = {
            "devices": [],
            "summary": {
                "total": len(devices),
                "online": 0,
                "offline": 0,
                "error": 0
            }
        }
        
        for device in devices:
            try:
                device_status = self.monitor_single_device(device)
                monitor_results["devices"].append(device_status)
                
                if device_status["status"] == "online":
                    monitor_results["summary"]["online"] += 1
                elif device_status["status"] == "offline":
                    monitor_results["summary"]["offline"] += 1
                else:
                    monitor_results["summary"]["error"] += 1
                    
            except Exception as e:
                monitor_results["devices"].append({
                    "device": device,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                monitor_results["summary"]["error"] += 1
        
        return monitor_results
    
    def monitor_single_device(self, device: Dict) -> Dict:
        """Monitor single device"""
        device_status = {
            "device": device,
            "status": "unknown",
            "timestamp": datetime.now().isoformat(),
            "metrics": {}
        }
        
        try:
            # 1. Test connection
            connection_result = self.test_connection(device)
            
            if not connection_result["success"]:
                device_status["status"] = "offline"
                device_status["error"] = connection_result["error_message"]
                return device_status
            
            device_status["status"] = "online"
            
            # 2. Collect performance metrics
            device_status["metrics"] = self.collect_metrics(device)
            
        except Exception as e:
            device_status["status"] = "error"
            device_status["error"] = str(e)
        
        return device_status
    
    def test_connection(self, device: Dict) -> Dict:
        """Test device connection"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device["device_type"],
                "host": device["host"],
                "username": device["username"],
                "password": device["password"],
                "timeout": 10
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/test-connection",
            json=payload,
            headers=self.headers
        )
        
        result = response.json()
        return result["data"]
    
    def collect_metrics(self, device: Dict) -> Dict:
        """Collect performance metrics"""
        metrics = {}
        
        # Collect interface status
        interface_result = self.execute_command(device, "show ip interface brief")
        if interface_result["success"]:
            metrics["interfaces"] = self.parse_interface_status(interface_result["output"])
        
        # Collect CPU usage
        cpu_result = self.execute_command(device, "show processes cpu")
        if cpu_result["success"]:
            metrics["cpu"] = self.parse_cpu_usage(cpu_result["output"])
        
        # Collect memory usage
        memory_result = self.execute_command(device, "show memory statistics")
        if memory_result["success"]:
            metrics["memory"] = self.parse_memory_usage(memory_result["output"])
        
        return metrics
    
    def execute_command(self, device: Dict, command: str) -> Dict:
        """Execute device command"""
        payload = {
            "driver": "netmiko",
            "connection_args": {
                "device_type": device["device_type"],
                "host": device["host"],
                "username": device["username"],
                "password": device["password"]
            },
            "command": command,
            "options": {
                "queue_strategy": "pinned",
                "ttl": 60
            }
        }
        
        response = requests.post(
            f"{self.base_url}/device/execute",
            json=payload,
            headers=self.headers
        )
        
        job_result = response.json()
        job_id = job_result["data"]["id"]
        
        job_status = self.wait_for_job_completion(job_id, timeout=60)
        
        return {
            "success": job_status["status"] == "finished",
            "output": job_status["result"]["retval"] if job_status["status"] == "finished" and job_status.get("result") else None,
            "error": job_status["result"]["error"] if job_status["status"] == "failed" and job_status.get("result") else None
        }
    
    def parse_interface_status(self, output: str) -> Dict:
        """Parse interface status"""
        interfaces = {}
        lines = output.split('\n')
        
        for line in lines:
            if 'Interface' in line and 'IP-Address' in line:
                continue
            
            parts = line.split()
            if len(parts) >= 4:
                interface_name = parts[0]
                interfaces[interface_name] = {
                    "ip_address": parts[1] if parts[1] != "unassigned" else None,
                    "status": parts[2],
                    "protocol": parts[3]
                }
        
        return interfaces
    
    def parse_cpu_usage(self, output: str) -> Dict:
        """Parse CPU usage"""
        # Simplified parsing, actual implementation should parse based on specific device type
        return {"usage": "N/A", "raw_output": output}
    
    def parse_memory_usage(self, output: str) -> Dict:
        """Parse memory usage"""
        # Simplified parsing, actual implementation should parse based on specific device type
        return {"usage": "N/A", "raw_output": output}
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 60):
        """Wait for job completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.base_url}/job?id={job_id}",
                headers=self.headers
            )
            
            job_status = response.json()["data"][0]
            
            if job_status["status"] in ["finished", "failed"]:
                return job_status
            
            time.sleep(1)
        
        raise TimeoutError(f"Job {job_id} execution timeout")

# Usage example
monitor = DeviceMonitor("http://localhost:9000", "your_api_key")

devices = [
    {
        "host": "192.168.1.1",
        "username": "admin",
        "password": "admin123",
        "device_type": "cisco_ios"
    },
    {
        "host": "192.168.1.2",
        "username": "admin",
        "password": "admin123",
        "device_type": "cisco_ios"
    }
]

# Regular monitoring
while True:
    results = monitor.monitor_devices(devices)
    
    print(f"Monitoring Report - {datetime.now()}")
    print(f"Online devices: {results['summary']['online']}")
    print(f"Offline devices: {results['summary']['offline']}")
    print(f"Error devices: {results['summary']['error']}")
    
    # Wait 5 minutes before next monitoring
    time.sleep(300)
```

## Best Practices

### 1. Error Handling
- Always check API response status
- Implement retry mechanism
- Record detailed error logs

### 2. Performance Optimization
- Use batch operations to reduce API calls
- Set timeout appropriately
- Avoid frequent status queries

### 3. Security Considerations
- Use environment variables to store sensitive information
- Regularly rotate API keys
- Limit API access permissions

### 4. Monitoring and Alerting
- Set task execution timeout alerts
- Monitor Worker health status
- Record API call statistics

---

## Related Documentation

- [API Overview](./api-overview.md) - Learn about all API interfaces
- [Device Operation API](./device-api.md) - Core device operation interfaces
- [Vault Credential Management API](./credential-api.md) - Vault credential management interface
- [API Best Practices](./api-best-practices.md) - Usage recommendations and optimization tips
