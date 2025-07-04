# Device Driver Module

NetPulse provides extensible driver support through its plugin system. Users can use three built-in supported drivers or develop custom drivers as needed.

## Core Drivers

| Driver    | Protocol       | Vendor Support              | Key Features                         | Dependencies       |
|-----------|----------------|-----------------------------|--------------------------------------|--------------------|
| Netmiko   | SSH/Telnet     | 30+ vendors                 | CLI command execution, **SSH keepalive** | netmiko~=4.5.0     |
| NAPALM    | API/SSH        | Multi-vendor (Cisco/Juniper/Arista) | Configuration management, status collection | napalm~=5.0.0      |
| pyeAPI    | HTTP/HTTPS     | Arista EOS only             | Native EOS API access, HTTP-based eAPI | pyeapi~=1.0.4      |

## Specifying Device Drivers

In the /device/execute and /device/bulk APIs, use the `driver` field to specify the driver needed for this task:

```json
{
  "driver": "netmiko",
  "connection_args": {
    "device_type": "cisco_ios",
    "host": "192.168.1.1",
    "username": "admin",
    "password": "password123"
  },
  ...
}
```

Note that when selecting different drivers, the fields in `connection_args` may vary. Please refer to the driver's documentation for details.

## Custom Driver Development

To add support for new protocols/vendors, implement a custom driver through the following steps:

1. Create a new directory in `netpulse/plugins/drivers/`
2. Inherit from the `BaseDriver` class and implement required methods
   ```python
   class CustomDriver(BaseDriver):
       driver_name = "custom"

       def connect(self):
       # ...

       # For specific methods, please refer to the BaseDriver class
   ```
3. Register the driver in `__init__.py`
   ```python
    __all__ = [CustomDriver]
   ```

For detailed information about the plugin system, please refer to the [Plugin Development Guide](./plugins.md).

## Netmiko

The most mature and stable driver in NetPulse is the Netmiko driver, supporting over 30 types of network devices. The Netmiko driver uses SSH and Telnet protocols to communicate with devices, supporting CLI command execution.

When using [Pinned Workers](./architecture.md) with the Netmiko driver, the Worker will create a new SSH connection and periodically send keepalive commands and KeepAlive packets. This maintains connection activity at both the TCP connection and application protocol levels, avoiding delays caused by SSH connection drops and reconnections.

Users can configure SSH keepalive time through the `keepalive` parameter. When SSH keepalive fails, the Pinned Worker will automatically exit. When tasks are sent again, a new Pinned Worker will be created to connect to the device. 