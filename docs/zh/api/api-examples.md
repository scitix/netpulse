# API 使用示例

## 概述

本文档提供了 NetPulse API 在实际业务场景中的完整使用示例，包括设备管理、配置操作、批量处理等常见场景。

## 场景1: Vault 凭据管理

### 业务需求
- 安全地存储和管理网络设备凭据
- 在设备操作中使用 Vault 凭据，避免在请求中传递密码
- 管理凭据的版本和元数据

### 实现方案

```python
import requests
from typing import Dict, List

class VaultCredentialManager:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-API-KEY": api_key}
    
    def create_credential(self, path: str, username: str, password: str, metadata: Dict = None) -> Dict:
        """创建或更新 Vault 凭据"""
        payload = {
            "path": path,
            "username": username,
            "password": password,
            "metadata": metadata or {}
        }
        
        response = requests.post(
            f"{self.base_url}/credential/vault/create",
            json=payload,
            headers=self.headers
        )
        
        return response.json()
    
    def read_credential(self, path: str, show_password: bool = False) -> Dict:
        """读取 Vault 凭据"""
        payload = {
            "path": path,
            "show_password": show_password
        }
        
        response = requests.post(
            f"{self.base_url}/credential/vault/read",
            json=payload,
            headers=self.headers
        )
        
        return response.json()
    
    def list_credentials(self, path_prefix: str = None, recursive: bool = True) -> List[str]:
        """列出 Vault 凭据路径"""
        payload = {
            "path_prefix": path_prefix,
            "recursive": recursive
        }
        
        response = requests.post(
            f"{self.base_url}/credential/vault/list",
            json=payload,
            headers=self.headers
        )
        
        result = response.json()
        return result["data"]["paths"]
    
    def get_metadata(self, path: str) -> Dict:
        """获取凭据元数据"""
        payload = {"path": path}
        
        response = requests.post(
            f"{self.base_url}/credential/vault/metadata",
            json=payload,
            headers=self.headers
        )
        
        return response.json()
    
    def delete_credential(self, path: str) -> Dict:
        """删除 Vault 凭据"""
        payload = {"path": path}
        
        response = requests.post(
            f"{self.base_url}/credential/vault/delete",
            json=payload,
            headers=self.headers
        )
        
        return response.json()

# 使用示例
manager = VaultCredentialManager("http://localhost:9000", "your_api_key")

# 1. 创建凭据
result = manager.create_credential(
    path="sites/hq/admin",
    username="admin",
    password="admin123",
    metadata={"description": "HQ site admin credentials", "site": "hq"}
)
print(f"创建凭据: {result}")

# 2. 读取凭据（不显示密码）
credential = manager.read_credential("sites/hq/admin", show_password=False)
print(f"凭据信息: {credential}")

# 3. 列出所有站点凭据
paths = manager.list_credentials(path_prefix="sites", recursive=True)
print(f"站点凭据: {paths}")

# 4. 获取凭据元数据
metadata = manager.get_metadata("sites/hq/admin")
print(f"元数据: {metadata}")

# 5. 在设备操作中使用 Vault 凭据
device_response = requests.post(
    "http://localhost:9000/device/execute",
    json={
        "driver": "netmiko",
        "connection_args": {
            "device_type": "cisco_ios",
            "host": "192.168.1.1",
            "credential_ref": "sites/hq/admin"  # 使用 Vault 凭据
        },
        "command": "show version"
    },
    headers={"X-API-KEY": "your_api_key"}
)
print(f"设备操作结果: {device_response.json()}")

# 6. 批量读取凭据
response = requests.post(
    "http://localhost:9000/credential/vault/batch-read",
    headers={"X-API-KEY": "your_api_key", "Content-Type": "application/json"},
    json={
        "paths": ["sites/hq/admin", "sites/branch1/admin", "devices/core/backup"],
        "show_password": False
    }
)
print(f"批量读取结果: {response.json()}")

# 7. 删除凭据
result = manager.delete_credential("sites/hq/admin")
print(f"凭据已删除: {result}")
```

### 最佳实践

**路径命名**：
- 使用层级结构：`sites/{site}/{role}`、`devices/{type}/{purpose}`
- 保持路径描述性和一致性

**元数据管理**：
- 添加描述、标签和自定义元数据，用于生命周期管理
- 使用元数据 API 追踪凭据变更历史

**安全建议**：
- 不在日志或 API 请求中暴露密码
- 默认使用 `show_password: false`
- 定期轮换密码并创建新版本

## 场景2: 网络设备发现

### 业务需求
- 发现网络中的所有设备
- 收集设备基本信息
- 验证设备连接性

### 实现方案

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
        """网络设备发现"""
        results = {
            "discovered": [],
            "failed": [],
            "total": len(device_list)
        }
        
        for device in device_list:
            try:
                # 1. 测试设备连接
                connection_result = self.test_device_connection(device)
                
                if connection_result["success"]:
                    # 2. 收集设备信息
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
        """测试设备连接"""
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
        """收集设备信息"""
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
            
            # 等待任务完成
            job_status = self.wait_for_job_completion(job_id)
            
            if job_status["status"] == "finished":
                device_info[command] = job_status["result"]["output"]
            else:
                device_info[command] = f"Error: {job_status['result']['error']}"
        
        return device_info
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 300):
        """等待任务完成"""
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
        
        raise TimeoutError(f"任务 {job_id} 执行超时")

# 使用示例
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
print(f"发现设备: {len(results['discovered'])}")
print(f"失败设备: {len(results['failed'])}")
```

## 场景2: 批量配置备份

### 业务需求
- 定期备份所有设备的配置
- 支持多种设备类型
- 保存配置到文件系统

### 实现方案

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
        """备份所有设备配置"""
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
        """备份单个设备配置"""
        # 确定备份命令
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
                
                # 等待任务完成
                job_status = self.wait_for_job_completion(job_id)
                
                if job_status["status"] == "finished":
                    backup_data["configs"][command_name] = job_status["result"]["output"]
                else:
                    backup_data["configs"][command_name] = f"Error: {job_status['result']['error']}"
                    
            except Exception as e:
                backup_data["configs"][command_name] = f"Error: {str(e)}"
        
        # 保存备份文件
        filename = f"{device['host']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.backup_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        backup_data["filepath"] = filepath
        backup_data["success"] = True
        
        return backup_data
    
    def get_backup_commands(self, device_type: str) -> Dict[str, str]:
        """根据设备类型获取备份命令"""
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
        """等待任务完成"""
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
        
        raise TimeoutError(f"任务 {job_id} 执行超时")

# 使用示例
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
print(f"备份成功: {len(results['success'])}")
print(f"备份失败: {len(results['failed'])}")
```

## 场景3: 配置变更管理

### 业务需求
- 安全地推送配置变更
- 支持配置回滚
- 变更前备份

### 实现方案

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
        """安全的配置变更"""
        change_result = {
            "device": device,
            "description": description,
            "backup": None,
            "change": None,
            "rollback": None,
            "success": False
        }
        
        try:
            # 1. 备份当前配置
            change_result["backup"] = self.backup_config(device)
            
            # 2. 推送配置变更
            change_result["change"] = self.push_config(device, config_commands)
            
            if change_result["change"]["success"]:
                change_result["success"] = True
                print(f"✅ 设备 {device['host']} 配置变更成功")
            else:
                # 3. 配置失败，执行回滚
                change_result["rollback"] = self.rollback_config(device, change_result["backup"])
                print(f"❌ 设备 {device['host']} 配置变更失败，已回滚")
                
        except Exception as e:
            change_result["error"] = str(e)
            print(f"❌ 设备 {device['host']} 配置变更异常: {e}")
        
        return change_result
    
    def backup_config(self, device: Dict) -> Dict:
        """备份设备配置"""
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
        """推送配置变更"""
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
        """回滚配置"""
        if not backup["success"] or not backup["config"]:
            return {"success": False, "error": "备份配置不可用"}
        
        # 解析备份配置并生成回滚命令
        rollback_commands = self.generate_rollback_commands(backup["config"])
        
        return self.push_config(device, rollback_commands)
    
    def generate_rollback_commands(self, backup_config: str) -> List[str]:
        """生成回滚命令"""
        # 这里简化处理，实际应该解析配置并生成对应的回滚命令
        lines = backup_config.split('\n')
        rollback_commands = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('!') and not line.startswith('version'):
                rollback_commands.append(line)
        
        return rollback_commands
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 300):
        """等待任务完成"""
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
        
        raise TimeoutError(f"任务 {job_id} 执行超时")

# 使用示例
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

result = config_manager.safe_config_change(device, config_commands, "添加测试接口配置")
print(f"配置变更结果: {result['success']}")
```

## 场景4: 批量设备监控

### 业务需求
- 定期监控设备状态
- 收集性能数据
- 生成监控报告

### 实现方案

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
        """批量监控设备"""
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
        """监控单个设备"""
        device_status = {
            "device": device,
            "status": "unknown",
            "timestamp": datetime.now().isoformat(),
            "metrics": {}
        }
        
        try:
            # 1. 测试连接
            connection_result = self.test_connection(device)
            
            if not connection_result["success"]:
                device_status["status"] = "offline"
                device_status["error"] = connection_result["error_message"]
                return device_status
            
            device_status["status"] = "online"
            
            # 2. 收集性能指标
            device_status["metrics"] = self.collect_metrics(device)
            
        except Exception as e:
            device_status["status"] = "error"
            device_status["error"] = str(e)
        
        return device_status
    
    def test_connection(self, device: Dict) -> Dict:
        """测试设备连接"""
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
        """收集性能指标"""
        metrics = {}
        
        # 收集接口状态
        interface_result = self.execute_command(device, "show ip interface brief")
        if interface_result["success"]:
            metrics["interfaces"] = self.parse_interface_status(interface_result["output"])
        
        # 收集CPU使用率
        cpu_result = self.execute_command(device, "show processes cpu")
        if cpu_result["success"]:
            metrics["cpu"] = self.parse_cpu_usage(cpu_result["output"])
        
        # 收集内存使用率
        memory_result = self.execute_command(device, "show memory statistics")
        if memory_result["success"]:
            metrics["memory"] = self.parse_memory_usage(memory_result["output"])
        
        return metrics
    
    def execute_command(self, device: Dict, command: str) -> Dict:
        """执行设备命令"""
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
        """解析接口状态"""
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
        """解析CPU使用率"""
        # 简化解析，实际应该根据具体设备类型解析
        return {"usage": "N/A", "raw_output": output}
    
    def parse_memory_usage(self, output: str) -> Dict:
        """解析内存使用率"""
        # 简化解析，实际应该根据具体设备类型解析
        return {"usage": "N/A", "raw_output": output}
    
    def wait_for_job_completion(self, job_id: str, timeout: int = 60):
        """等待任务完成"""
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
        
        raise TimeoutError(f"任务 {job_id} 执行超时")

# 使用示例
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

# 定期监控
while True:
    results = monitor.monitor_devices(devices)
    
    print(f"监控报告 - {datetime.now()}")
    print(f"在线设备: {results['summary']['online']}")
    print(f"离线设备: {results['summary']['offline']}")
    print(f"错误设备: {results['summary']['error']}")
    
    # 等待5分钟后再次监控
    time.sleep(300)
```

## 最佳实践

### 1. 错误处理
- 始终检查API响应状态
- 实现重试机制
- 记录详细的错误日志

### 2. 性能优化
- 使用批量操作减少API调用
- 合理设置超时时间
- 避免频繁的状态查询

### 3. 安全考虑
- 使用环境变量存储敏感信息
- 定期轮换API密钥
- 限制API访问权限

### 4. 监控告警
- 设置任务执行超时告警
- 监控Worker健康状态
- 记录API调用统计

---

## 相关文档

- [API概览](./api-overview.md) - 了解所有API接口
- [设备操作 API](./device-api.md) - 设备操作核心接口
- [Vault 凭据管理 API](./credential-api.md) - Vault 凭据管理接口
- [API最佳实践](./api-best-practices.md) - 使用建议和优化技巧 