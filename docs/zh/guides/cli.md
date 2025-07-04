# CLI 工具

NetPulse 提供了基于设备资产表格的批量操作CLI工具，专门用于网络设备的批量运维管理。

## 工具概览

### 📊 `netpulse-cli` - 批量表格工具
- **适用场景**: 基于设备资产表格的批量运维操作
- **特点**: 专注CSV/Excel处理、简化的批量操作流程、仅使用Netmiko驱动
- **命令格式**: `netpulse-cli <pull|push> devices.csv "command"`

## 功能

- 支持 CSV 和 Excel (XLSX/XLS) 格式的设备资产表格
- 基于厂商名称自动设置 Netmiko 驱动类型
- 在多个设备上批量执行命令和推送配置
- 监控异步任务执行状态
- 基于模板的输出解析和配置渲染
- 使用统一设备API (`/device/execute` 和 `/device/bulk`) 获得更好的性能
- 智能队列策略和超时管理
- 自动操作类型识别（根据command或config字段）

!!! note
    此工具仅使用 NetPulse 的 Netmiko 驱动，专注于网络设备的SSH连接操作。

## API架构

CLI工具基于NetPulse的统一设备操作API构建，采用优化的分层参数结构：

### 参数结构
```json
{
  "driver": "netmiko",
  "devices": [...],
  "connection_args": {
    // 驱动连接和认证参数
    "device_type": "cisco_ios",
    "username": "admin",
    "password": "admin123"
  },
  "command": "show version",        // Exec操作
  "config": "interface Gi0/1",      // Bulk操作  
  "driver_args": {
    // 驱动特定执行参数
    "read_timeout": 30,
    "delay_factor": 2,
    "auto_find_prompt": true
  },
  "options": {
    // 全局处理选项
    "parsing": {...},
    "rendering": {...},
    "queue_strategy": "pinned",
    "ttl": 600
  }
}
```

### 智能化功能
- **自动队列选择**: 批量操作自动使用"pinned"策略确保设备处理一致性
- **优化超时设置**: 批量操作默认600秒超时，适合大规模设备操作
- **操作自动识别**: 根据`command`或`config`字段自动识别Exec/Bulk操作
- **错误处理增强**: 更详细的错误信息和状态追踪

## 安装

!!! tip
    该工具和 NetPulse API 可以分开部署。建议使用 pip 安装在本地使用。

```bash
# 在项目根目录下安装CLI工具
pip install .[tool]

# 或者从源码安装
git clone https://github.com/your-org/netpulse.git
cd netpulse
pip install -e .[tool]
```

## 使用方法

```bash
netpulse-cli [全局选项] <子命令> [子选项] <表格文件> <命令或配置> 
```

### 全局参数

- `--endpoint`: NetPulse API 端点（默认：http://localhost:9000）
- `--api-key`: 用于身份验证的 API 密钥（默认：MY_API_KEY）
- `--interval/-i`: 任务状态检查的间隔时间（秒）（默认：5）
- `--timeout/-t`: 等待任务完成的最大时间（秒）（默认：300）

### 子命令

#### Pull - 执行命令

`pull`: 在网络设备上执行命令并获取输出

```bash
netpulse-cli pull devices.csv "show version"
```

**子选项：**
- `--template-type/--type`: 解析模板类型（textfsm/ttp）
- `--template/-T`: 模板文件 URI
- `--force/-f`: 跳过执行确认提示
- `--vendor`: 按厂商名称过滤设备（不区分大小写）
- `--monitor/-m`: 监控任务执行进度（默认：true）

#### Push - 批量配置

`push`: 将配置批量推送到网络设备

```bash
netpulse-cli push devices.csv "interface ge-0/0/0" "description test"
```

**子选项：**
- `--template-type/--type`: 渲染模板类型（jinja2）
- `--template/-T`: 模板文件 URI
- `--save`: 保存配置到启动配置（默认：false）
- `--enable`: 推送前进入启用模式（默认：true）
- `--force/-f`: 跳过执行确认提示
- `--vendor`: 按厂商名称过滤设备（不区分大小写）
- `--monitor/-m`: 监控任务执行进度（默认：true）

### 参数

- `设备文件`: 包含设备信息的 CSV 或 Excel 文件路径
- `命令或配置`: 在设备上执行的命令（对于 push 子命令，这是要推送的配置）

## 设备表格格式

工具期望输入文件包含以下列：

| 列名       | 描述                          | 必填 | 默认值 |
|-----------|--------------------------------------|----------|---------|
| Selected  | 是否包含该设备        | 是      | -       |
| Name      | 设备名称                          | 否       | -       |
| Site      | 站点信息                     | 否       | -       |
| Location  | 物理位置                    | 否       | -       |
| Rack      | 机架位置                        | 否       | -       |
| Vendor    | 设备厂商（用于决定驱动）     | 是      | -       |
| Model     | 设备型号                         | 否       | -       |
| IP        | 设备 IP 地址                    | 是      | -       |
| Port      | SSH 端口                             | 否       | 22      |
| Username  | SSH 用户名                         | 是      | -       |
| Password  | SSH 密码                         | 是      | -       |
| Keepalive | SSH 保活间隔（秒）     | 否       | -       |

**示例CSV：**
```csv
Selected,Name,Site,Location,Rack,Vendor,Model,IP,Port,Username,Password,Keepalive
True,Simulator,AB,XX,L01,Cisco,Cisco Simulator,172.17.0.1,10005,admin,admin,180
```

### 支持的厂商

工具自动将厂商名称映射到设备类型：
- Arista → arista_eos
- Cisco → cisco_ios  
- Fortinet → fortinet
- H3C → hp_comware
- Huawei → huawei

!!! note
    如果厂商不在上述映射中，Vendor 字段将直接传递给 Netmiko。

## 使用方法

### 基础操作

**Exec操作 - 执行命令：**
```bash
# 基础Exec操作
netpulse-cli exec devices.csv "show version"

# 筛选特定厂商设备
netpulse-cli exec devices.csv "show version" --vendor cisco

# 跳过确认提示
netpulse-cli pull devices.csv "show version" --force

# 自定义API端点
netpulse-cli --endpoint http://api.example.com pull devices.csv "show version"

# 获取接口状态
netpulse-cli pull devices.csv "show ip interface brief" --vendor cisco

# 获取路由表
netpulse-cli pull devices.csv "show ip route" --force --no-monitor
```

**Push操作 - 批量配置：**
```bash
# 基础Push操作（单条配置）
netpulse-cli push devices.csv "hostname NEW-HOSTNAME"

# 多条配置（自动合并为多行）
netpulse-cli push devices.csv "interface GigabitEthernet0/1" "description Uplink to Core" "no shutdown"

# 推送配置并保存到启动配置
netpulse-cli push devices.csv "ntp server 1.1.1.1" --save

# 推送配置时不进入启用模式
netpulse-cli push devices.csv "show version" --no-enable

# 推送SNMP配置到Cisco设备
netpulse-cli push devices.csv "snmp-server community public RO" --vendor cisco

# 批量配置VLAN
netpulse-cli push devices.csv "vlan 100" "name MGMT_VLAN" "exit" --vendor cisco --save
```

### 模板用法

**使用TextFSM模板解析输出：**
```bash
# 使用本地TextFSM模板解析show version输出
netpulse-cli pull devices.csv "show version" \
  --template-type textfsm \
  --template /root/templates/show_version.textfsm

# 使用TTP模板解析接口信息
netpulse-cli pull devices.csv "show ip interface brief" \
  --template-type ttp \
  --template interface_brief.ttp
```

**使用Jinja2模板渲染配置：**
```bash
# 使用Jinja2模板批量配置接口
netpulse-cli push devices.csv '{"interface": "GigabitEthernet0/1", "description": "Uplink"}' \
  --template-type jinja2 \
  --template /root/templates/interface.j2

# 使用模板批量配置OSPF
netpulse-cli push devices.csv '{"area": "0", "network": "192.168.1.0/24"}' \
  --template-type jinja2 \
  --template ospf_config.j2
```

### 高级用法

**监控和超时控制：**
```bash
# 自定义监控间隔和超时时间
netpulse-cli --interval 10 --timeout 600 pull devices.csv "show running-config"

# 禁用监控（提交任务后立即返回）
netpulse-cli pull devices.csv "show version" --no-monitor

# 长时间配置任务
netpulse-cli --timeout 1800 push devices.csv "copy running-config startup-config" --force
```

## 输出结果

工具将执行结果保存到带有时间戳的 CSV 文件中（例如 `result_20250409_144530.csv`）。结果文件包含以下信息：

| 列名 | 描述 |
|--------|-------------|
| IP | 设备 IP 地址 |
| Name | 设备名称（如果提供） |
| Vendor | 设备厂商（如果提供） |
| Command | 执行的命令 |
| Status | 任务执行状态 |
| Job ID | 唯一任务标识符 |
| Result | 命令输出或错误信息 |
| Error | 详细错误信息（如果有） |
| Start Time | 任务开始时间 |
| End Time | 任务完成时间 |

## 模板系统

该工具基本遵循 [模板系统](../advanced/templates.md) 中的使用方式，但是具有不同的文件读取行为。

### 模板文件处理

为了便于在命令行中使用模板文件，`--template` 的值会首先被解释为 POSIX 路径：

1. **本地文件**: 如果路径存在，则读取其内容发送到 NetPulse API
2. **模板内容**: 如果路径不存在，则将其视为模板内容（`plaintext`），直接发送到 NetPulse API
3. **远程文件**: 如果提供 `file://` 开头的 URI，则由 API Server 读取该文件

### 模板使用示例

**案例 1：远程文件**
```bash
netpulse-cli pull devices.csv "show version" \
  --template-type textfsm \
  --template file:///root/templates/show_version.textfsm
```

**案例 2：本地文件**
```bash
netpulse-cli pull devices.csv "show version" \
  --template-type textfsm \
  --template /root/templates/show_version.textfsm
```

**案例 3：直接提供模板内容**
```bash
netpulse-cli push devices.csv '{"interface": "GigabitEthernet0/1", "description": "Test"}' \
  --template-type jinja2 \
  --template "interface {{ interface }}\n description {{ description }}"
```

## 最佳实践

### Shell脚本示例

**配置备份脚本：**
```bash
#!/bin/bash
# backup_configs.sh

DEVICES_FILE="production_devices.csv"
BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

echo "开始备份配置..."

# 执行配置备份
netpulse-cli pull "$DEVICES_FILE" "show running-config" \
  --force \
  --timeout 1800 \
  2>&1 | tee "$BACKUP_DIR/backup.log"

if [ $? -eq 0 ]; then
    echo "配置备份完成，日志保存在 $BACKUP_DIR/backup.log"
else
    echo "配置备份失败"
    exit 1
fi
```

**批量配置部署脚本：**
```bash
#!/bin/bash
# deploy_ntp_config.sh

DEVICES_FILE="devices.csv"
NTP_CONFIG="ntp server 1.1.1.1\nntp server 8.8.8.8"

echo "部署NTP配置到所有设备..."

# 推送NTP配置
netpulse-cli push "$DEVICES_FILE" "$NTP_CONFIG" \
  --save \
  --force \
  --timeout 600

echo "NTP配置部署完成"
```

### 与其他工具集成

**与cron定时任务集成：**
```bash
# 每天凌晨2点执行配置备份
0 2 * * * /opt/scripts/backup_configs.sh >> /var/log/netpulse-backup.log 2>&1
```

**与监控系统集成：**
```bash
#!/bin/bash
# health_check.sh

# 检查设备状态
netpulse-cli pull devices.csv "show version" --force --no-monitor > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "设备连接正常"
    exit 0
else
    echo "设备连接异常"
    exit 1
fi
```

## 故障排查

### 常见问题

1. **连接超时**
   ```bash
   # 增加超时时间
   netpulse-cli --timeout 600 exec devices.csv "show version"
   ```

2. **认证失败**
   ```bash
   # 检查设备文件中的用户名密码是否正确
   # 确认设备类型映射是否正确
   ```

3. **批量操作部分失败**
   ```bash
   # 检查结果CSV文件中的错误信息
   # 使用 --vendor 选项分批处理不同厂商设备
   ```

4. **模板解析错误**
   ```bash
   # 确认模板文件路径正确
   # 验证模板语法是否正确
   ```

### 调试技巧

**查看详细信息：**
- 检查生成的结果CSV文件中的Error列
- 查看任务执行的Start Time和End Time
- 使用 `--force` 跳过确认提示进行快速测试

**分步调试：**
```bash
# 1. 先测试单个厂商
netpulse-cli exec devices.csv "show version" --vendor cisco

# 2. 测试简单命令
netpulse-cli exec devices.csv "show version" --force

# 3. 逐步增加复杂性
netpulse-cli exec devices.csv "show running-config" --template-type textfsm

# 4. 测试配置推送
netpulse-cli bulk devices.csv "hostname TEST-DEVICE" --vendor cisco --force
```

## 性能优化

### 批量操作优化

- **合理设置超时**: 根据命令复杂度调整 `--timeout` 参数
- **分批处理**: 对于大量设备，可以按厂商或站点分批执行
- **模板优化**: 使用合适的解析模板提高结果处理效率

### 网络优化

- **并发控制**: CLI工具会自动使用"pinned"队列策略进行并发控制
- **连接复用**: Netmiko驱动会自动管理SSH连接的复用和保活
- **错误恢复**: 工具具备自动重试和错误恢复机制

通过本CLI工具，您可以高效地进行网络设备的批量运维操作，实现配置管理、信息收集等自动化任务。
