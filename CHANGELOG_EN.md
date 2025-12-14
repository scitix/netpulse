# Changelog

## [0.3.0] - 2025-12-15

### Added

- **Credential Plugin Architecture**: New extensible credential plugin system that supports dynamically retrieving device authentication information from external credential management systems
  - Plugin-based design supporting multiple credential providers
  - Automatic credential resolution and injection into connection parameters
  - Support for referencing credentials via `credential` field in API requests, eliminating the need to pass plaintext passwords in requests
- **Vault KV Credential Plugin**: Integration with HashiCorp Vault KV v2 engine for secure credential management
  - Support for reading device credentials (username, password, etc.) from Vault KV v2
  - Support for both Token and AppRole authentication methods
  - Support for path whitelist (`allowed_paths`) to restrict access scope and enhance security
  - Support for namespace isolation
  - Support for credential caching (`cache_ttl`) to improve performance and reduce Vault API calls
  - Support for custom field mapping (`field_mapping`) to flexibly adapt to different Vault data structures
  - Support for versioned secret reading
  - Complete unit test coverage
- Support for template rendering before command execution and template parsing after execution
- Unit tests, end-to-end tests, and CI/CD integration
- **Enhanced Webhook Payload**: Webhook notifications now include comprehensive task context
  - Device information (host, device_type) for better task traceability
  - Driver information to identify execution method
  - Command/config information to track executed operations
  - Status field (success/failed) for quick identification
  - Improved formatting for multi-command results with readable output
  - Support for nested dict results (e.g., paramiko driver format)

### Changed

- **Major API Refactoring**: Unified API and CLI experience for simplified usage
  - **Unified Device Operation Interface** `/device/exec`: Automatically detects operation type (query/config), eliminating the need for separate endpoints
    - Automatically identifies as query operation when `command` field is present
    - Automatically identifies as config operation when `config` field is present
    - Auto-selects queue strategy based on driver type (can be manually specified)
  - **Unified Template Interface**: `/template/render` and `/template/parse` support automatic engine/parser detection
  - **Simplified Request Models**: Unified request/response format, reducing API complexity
  - **CLI Integration**: Integrated standalone `netpulse-client` package into main project for unified development experience
  - Refactored API design improves extensibility and maintainability
- Optimized Docker image build process to reduce image size
- Upgraded TTP template parser to 0.10.0

### Fixed

- Fixed missing failure callback in batch jobs
- Fixed serialization errors
- Fixed validation bugs
- Fixed test configuration reading issues
- Fixed Postman collection: updated test response field from `connection_time` to `latency`
- Fixed various test case bugs

### Documentation

- Added credential configuration guide documentation (English and Chinese), providing detailed instructions on configuring and using the Vault KV credential plugin
- Updated API documentation with credential-related field descriptions
- Fixed Postman collection examples
- Fixed documentation options

## [0.2.0] - 2025-11-09

### Added

- **Paramiko Driver**: New Paramiko driver supporting Linux server management
  - Support for multiple authentication methods (password, key file, key content)
  - Support for SFTP file transfer (upload/download/resume)
  - Support for SSH proxy/jump host connections
  - Support for sudo privilege execution and PTY mode

## [0.1.0] - 2025-7-04

### Added

- Initial version release
- Support for Netmiko, NAPALM, PyEAPI drivers
- Support for persistent connections, distributed architecture, and plugin system
- Support for template engines (Jinja2, TextFSM, TTP) and Webhook notifications

