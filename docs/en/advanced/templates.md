# Template System

This guide describes how to use NetPulse's template system for configuration rendering and output parsing.

## Supported Template Engines

- **Jinja2** — For configuration rendering
- **TextFSM** — For command output parsing
- **TTP** — For structured data parsing

## Configuration Rendering

### Jinja2 Template Example

```jinja2
interface {{ interface_name }}
 description {{ description }}
{% if vlan %}
 switchport mode access
 switchport access vlan {{ vlan }}
{% endif %}
```

### API Usage

```json
{
  "name": "jinja2",
  "template": "interface {{ interface_name }}\n description {{ description }}",
  "context": {
    "interface_name": "GigabitEthernet0/1",
    "description": "Test Interface"
  }
}
```

## Output Parsing

### TextFSM Template Example

```textfsm
Value INTERFACE (\S+)
Value IP_ADDRESS (\S+)
Value STATUS (\S+)

Start
  ^Interface\s+IP-Address\s+OK\?\s+Method\s+Status\s+Protocol -> Record
  ^${INTERFACE}\s+${IP_ADDRESS}\s+\S+\s+\S+\s+${STATUS}\s+\S+ -> Record
```

### API Usage

```json
{
  "name": "textfsm",
  "template": "file:///templates/show_ip_int_brief.textfsm",
  "context": "Interface IP-Address OK? Method Status Protocol\nGigabitEthernet0/1 192.168.1.1 YES manual up up"
}
```

## Best Practices

- Use templates to standardize configuration and parsing across devices
- Store templates in a centralized location for easy management
- Test templates with sample data before production use

---

For more information, see:
- [API Reference](../guides/api.md) 