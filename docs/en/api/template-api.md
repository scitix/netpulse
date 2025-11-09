# Template Operation API

## Overview

Template Operation API provides configuration template rendering and command output parsing functions, supporting multiple template engines and parsers.

## API Endpoints

### POST /template/render

Render configuration template.

**Function Description**:
- Supports multiple template engines (Jinja2, Mako, etc.)
- Supports variable substitution and conditional logic
- Supports template file references

**Request Example**:

```bash
curl -X POST "http://localhost:9000/template/render" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "jinja2",
    "template": "interface {{ interface_name }}\n description {{ description }}",
    "context": {
      "interface_name": "GigabitEthernet0/1",
      "description": "Test Interface"
    }
  }'
```

**Request Model**:

```json
{
  "name": "jinja2|mako|string",
  "template": "interface {{ interface_name }}\n description {{ description }}",
  "context": {
    "interface_name": "GigabitEthernet0/1",
    "description": "Test Interface"
  }
}
```

### POST /template/render/{name}

Render using specified template engine.

**Request Example**:

```bash
curl -X POST "http://localhost:9000/template/render/jinja2" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "interface {{ interface_name }}\n description {{ description }}",
    "context": {
      "interface_name": "GigabitEthernet0/1",
      "description": "Test Interface"
    }
  }'
```

### POST /template/parse

Parse command output.

**Function Description**:
- Supports multiple parsers (TextFSM, TTP, etc.)
- Supports structured data extraction
- Supports custom parsing templates

**Request Example**:

```bash
curl -X POST "http://localhost:9000/template/parse" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "textfsm",
    "template": "file:///templates/show_version.textfsm",
    "context": "Cisco IOS Software, Version 15.2(4)S7..."
  }'
```

**Request Model**:

```json
{
  "name": "textfsm|ttp|regex",
  "template": "file:///templates/show_version.textfsm",
  "context": "Cisco IOS Software, Version 15.2(4)S7..."
}
```

### POST /template/parse/{name}

Parse using specified parser.

**Request Example**:

```bash
curl -X POST "http://localhost:9000/template/parse/textfsm" \
  -H "X-API-KEY: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "file:///templates/show_version.textfsm",
    "context": "Cisco IOS Software, Version 15.2(4)S7..."
  }'
```

## Response Models

### BaseResponse

Template operation response.

```json
{
  "code": 200,
  "message": "success",
  "data": "interface GigabitEthernet0/1\n description Test Interface"
}
```

### Parse Response Example

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "version": "15.2(4)S7",
      "hostname": "Router1",
      "uptime": "2 weeks, 3 days, 4 hours, 30 minutes"
    }
  ]
}
```

## Supported Template Engines

### Jinja2

Most commonly used template engine with concise and powerful syntax.

**Template Example**:

```jinja2
interface {{ interface_name }}
 description {{ description }}
{% if ip_address %}
 ip address {{ ip_address }} {{ subnet_mask }}
{% endif %}
{% if vlan %}
 switchport access vlan {{ vlan }}
{% endif %}
 no shutdown
```

**Usage Example**:

```python
import requests

# Render Jinja2 template
response = requests.post(
    "http://localhost:9000/template/render/jinja2",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "template": "interface {{ interface_name }}\n description {{ description }}",
        "context": {
            "interface_name": "GigabitEthernet0/1",
            "description": "Test Interface"
        }
    }
)

rendered_config = response.json()["data"]
print(rendered_config)
```

### Mako

High-performance template engine, suitable for complex templates.

**Template Example**:

```mako
interface ${interface_name}
 description ${description}
% if ip_address:
 ip address ${ip_address} ${subnet_mask}
% endif
 no shutdown
```

### String Template

Simple string substitution, suitable for basic scenarios.

**Template Example**:

```
interface {interface_name}
 description {description}
 ip address {ip_address} {subnet_mask}
 no shutdown
```

## Supported Parsers

### TextFSM

Text parser developed by Cisco, suitable for network device output.

**Template Example**:

```
Value VERSION ([\d.()]+)
Value HOSTNAME (\S+)
Value UPTIME (.+)

Start
  ^Cisco IOS Software, Version ${VERSION} -> Continue
  ^.*uptime is ${UPTIME} -> Continue
  ^${HOSTNAME}# -> Record
```

**Usage Example**:

```python
# Parse show version output
response = requests.post(
    "http://localhost:9000/template/parse/textfsm",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "template": "file:///templates/show_version.textfsm",
        "context": """
Cisco IOS Software, Version 15.2(4)S7
Router1 uptime is 2 weeks, 3 days, 4 hours, 30 minutes
Router1#
        """
    }
)

parsed_data = response.json()["data"]
print(parsed_data)
```

### TTP

Template Text Parser, supports multiple formats.

**Template Example**:

```
interface {{ interface_name }}
 description {{ description }}
 ip address {{ ip_address }} {{ subnet_mask }}
 no shutdown
```

### Regex

Regular expression parsing, suitable for simple scenarios.

**Usage Example**:

```python
# Use regular expression parsing
response = requests.post(
    "http://localhost:9000/template/parse/regex",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json={
        "template": r"Version (\d+\.\d+\([^)]+\))",
        "context": "Cisco IOS Software, Version 15.2(4)S7"
    }
)
```

## Template File Management

### File Path Format

Supports multiple file path formats:

- **Absolute Path**: `/templates/interface.j2`
- **Relative Path**: `templates/interface.j2`
- **File Protocol**: `file:///templates/interface.j2`

### Template Directory Structure

```
templates/
├── cisco/
│   ├── interface.j2
│   ├── vlan.j2
│   └── routing.j2
├── juniper/
│   ├── interface.j2
│   └── routing.j2
└── common/
    ├── show_version.textfsm
    └── show_interfaces.textfsm
```

## Usage Examples

### 1. Configuration Template Rendering

```python
import requests

# Render interface configuration template
template_data = {
    "name": "jinja2",
    "template": """
interface {{ interface_name }}
 description {{ description }}
{% if ip_address %}
 ip address {{ ip_address }} {{ subnet_mask }}
{% endif %}
{% if vlan %}
 switchport access vlan {{ vlan }}
{% endif %}
 no shutdown
""",
    "context": {
        "interface_name": "GigabitEthernet0/1",
        "description": "Test Interface",
        "ip_address": "192.168.1.10",
        "subnet_mask": "255.255.255.0",
        "vlan": 100
    }
}

response = requests.post(
    "http://localhost:9000/template/render",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json=template_data
)

config = response.json()["data"]
print(config)
```

### 2. Command Output Parsing

```python
# Parse show interfaces output
parse_data = {
    "name": "textfsm",
    "template": "file:///templates/show_interfaces.textfsm",
    "context": """
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/1    192.168.1.1    YES NVRAM  up                    up
GigabitEthernet0/2    unassigned     YES unset  down                  down
"""
}

response = requests.post(
    "http://localhost:9000/template/parse",
    headers={
        "X-API-KEY": "your_key",
        "Content-Type": "application/json"
    },
    json=parse_data
)

interfaces = response.json()["data"]
for interface in interfaces:
    print(f"Interface: {interface['interface']}, Status: {interface['status']}")
```

### 3. Batch Configuration Generation

```python
# Batch generate interface configurations
interfaces = [
    {"name": "GigabitEthernet0/1", "description": "LAN1", "ip": "192.168.1.1"},
    {"name": "GigabitEthernet0/2", "description": "LAN2", "ip": "192.168.2.1"},
    {"name": "GigabitEthernet0/3", "description": "WAN", "ip": "10.0.0.1"}
]

configs = []
for interface in interfaces:
    response = requests.post(
        "http://localhost:9000/template/render/jinja2",
        headers={
            "X-API-KEY": "your_key",
            "Content-Type": "application/json"
        },
        json={
            "template": """
interface {{ name }}
 description {{ description }}
 ip address {{ ip }} 255.255.255.0
 no shutdown
""",
            "context": interface
        }
    )
    configs.append(response.json()["data"])

# Merge all configurations
full_config = "\n".join(configs)
print(full_config)
```

## Best Practices

### 1. Template Design

- **Modularization**: Split complex templates into multiple small templates
- **Reusability**: Design common template components
- **Parameterization**: Use variables instead of hardcoded values

### 2. Error Handling

```python
try:
    response = requests.post(url, json=template_data)
    response.raise_for_status()
    result = response.json()["data"]
except requests.exceptions.RequestException as e:
    print(f"Template rendering failed: {e}")
except KeyError as e:
    print(f"Response format error: {e}")
```

### 3. Performance Optimization

- **Cache Templates**: Avoid reloading the same templates repeatedly
- **Batch Processing**: Process multiple templates at once
- **Async Processing**: Use async processing for large numbers of templates

### 4. Security Considerations

- **Input Validation**: Validate template variables
- **Path Restrictions**: Limit template file access paths
- **Access Control**: Control template access permissions

## Notes

1. **Template Syntax**: Different template engines have different syntax
2. **File Paths**: Ensure template file paths are correct
3. **Variable Types**: Pay attention to variable type matching
4. **Error Handling**: Handle template rendering and parsing errors
5. **Performance Impact**: Complex templates may affect performance

---

## Related Documentation

- [API Overview](./api-overview.md) - Learn about all API interfaces
- [Device Operation API](./device-api.md) - Core device operation interfaces
