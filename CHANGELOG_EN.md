# Changelog

## [0.4.0] - 2026-02-23

> [!CAUTION]
> **BREAKING CHANGES**: This version introduces a major update with significant refactoring of the API and Response structures. It is NOT backward compatible.

### Added

- **API Structure Flattening**: Refactored response models and removed redundant nesting layers. API results are now more intuitive, significantly reducing development complexity for third-party integrations and frontend displays.
- **Standardized Driver Output**: Unified the execution result models (`list[DriverExecutionResult]`) across various drivers including Arista, Cisco, and Linux. Developers can now use consistent logic to process execution results from cross-vendor devices.
- **Enhanced Background Async Task System (Paramiko)**:
  - **Non-blocking Task Initialization**: Optimized the startup process, completely resolving the main process blocking and deadlock issues when Workers initiate long-running tasks.
  - **Task Auto-Discovery and Recovery**: Introduced a task scanning mechanism that supports automatically finding and re-tracking task progress from remote hosts after service restarts or connection disruptions.
  - **Efficient Incremental Log Tracking**: Introduced a read algorithm based on byte offsets, supporting "incremental pulling" of background task outputs, drastically reducing network overhead when viewing GB-level log files.
  - **Precise ID-based Process Identification**: Adopted Task ID injection technology (`exec -a`) to ensure the uniqueness of background process identification, eliminating false positives and cleanup conflicts that occur with process name-based checks.
- **Operations Automation and Security Enhancements**:
  - **Dynamic Path Template Rendering**: Enabled the use of Jinja2 templates in file transfer paths to automatically generate storage directories based on metadata such as hostnames and dates, facilitating automated file archiving.
  - **Secure Credential Asset Lifecycle**: Deeply integrated with the Vault credential system to support the secure transmission of encrypted private keys or authorization files to target devices, ensuring the safety of sensitive assets during transit.
  - **Command-Level Structured Parsing**: Supported independent parsing for each output in batch commands, achieving precise mapping between execution sequences and structured data (JSON).
- **Multi-level Persistent Credential Caching**: Implemented a two-tier persistent caching mechanism based on Memory + Redis. This effectively reduces Vault server load and improves overall connection stability when managing large-scale infrastructure.
- **AI-Native Support**: Built an AI knowledge base system (including `llms.txt`, `openapi.json`, and `repomix` source context), significantly enhancing LLMs' understanding of complex systems and boosting AI-assisted development efficiency.

### Changed

- **Logic Cleanup**: Removed non-standard automatic JSON detection logic, centralizing it to be handled by parsing plugins.
- **API Collection Synchronization**: Fully updated the Postman API Collection to the latest RESTful standards, covering all background task management endpoints.

### Fixed

- **Runtime NameError Fix**: Resolved a critical NameError in the driver layer caused by circular imports and Pydantic validation timing.
- **Background Task Tracking Fix**: Fixed a bug where async task log offsets and running statuses could not be correctly synchronized in the Redis registry.
- **Unified Model Paths**: Resolved the import conflict for `ParamikoFileTransferOperation`, which is now merged into the cross-platform universal `FileTransferModel`.
- **Driver Return Consistency**: Fixed the issue where the Napalm driver returned a dictionary instead of a list for empty commands, eliminating format discrepancies across drivers.


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
  - SFTP file transfer (upload/download/resume)
  - Support for SSH proxy/jump host connections
  - Support for sudo privilege execution and PTY mode

## [0.1.0] - 2025-7-04

### Added

- Initial version release
- Support for Netmiko, NAPALM, PyEAPI drivers
- Support for persistent connections, distributed architecture, and plugin system
- Support for template engines (Jinja2, TextFSM, TTP) and Webhook notifications
