# Template Operation API

Provides standalone template rendering and output parsing endpoints. Templates can also be embedded directly in device operation requests via the `rendering` and `parsing` fields.

## Endpoints

### POST /template/render

Render a configuration template.

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

**`POST /template/render/{name}`** — shorthand with engine name in the URL path:
```bash
curl -X POST "http://localhost:9000/template/render/jinja2" ...
```

**Response:**
```json
{"code": 200, "message": "success", "data": "interface GigabitEthernet0/1\n description Test Interface"}
```

### POST /template/parse

Parse command output into structured data.

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

**`POST /template/parse/{name}`** — shorthand with parser name in the URL path.

**Response:**
```json
{"code": 200, "message": "success", "data": [{"version": "15.2(4)S7", "hostname": "Router1"}]}
```

## Template Engines

### Jinja2

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

### Mako

```mako
interface ${interface_name}
 description ${description}
% if ip_address:
 ip address ${ip_address} ${subnet_mask}
% endif
 no shutdown
```

### String Template

Simple `{variable}` substitution for basic cases:
```
interface {interface_name}
 description {description}
 ip address {ip_address} {subnet_mask}
```

## Parsers

### TextFSM

Text parser for network device output. Template example:

```
Value VERSION ([\d.()]+)
Value HOSTNAME (\S+)
Value UPTIME (.+)

Start
  ^Cisco IOS Software, Version ${VERSION} -> Continue
  ^.*uptime is ${UPTIME} -> Continue
  ^${HOSTNAME}# -> Record
```

### TTP (Template Text Parser)

Matches output structure with a template:
```
interface {{ interface_name }}
 description {{ description }}
 ip address {{ ip_address }} {{ subnet_mask }}
```

### Regex

Single regular expression for simple extraction:
```json
{
  "name": "regex",
  "template": "Version ([\\d.()]+)",
  "context": "Cisco IOS Software, Version 15.2(4)S7"
}
```

## Template File Paths

The `template` field accepts inline strings or file references:

| Format | Example |
|--------|---------|
| Inline | `"interface {{ name }}\n description {{ desc }}"` |
| Absolute path | `/templates/interface.j2` |
| File protocol | `file:///templates/show_version.textfsm` |

Suggested directory structure:
```
templates/
├── cisco/interface.j2
├── juniper/routing.j2
└── common/show_version.textfsm
```
