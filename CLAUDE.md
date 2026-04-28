# linuxmuster-base7 Project Documentation

## Project Overview

**linuxmuster-base7** is the core Python library and management toolset for linuxmuster.net 7.x, an open-source school network solution. The project provides essential infrastructure for setting up and managing school server environments, including device management, network configuration, and firewall integration.

- **Version**: 7.3.29
- **License**: GPL-3.0-or-later
- **Primary Maintainer**: thomas@linuxmuster.net
- **Organization**: Linuxmuster.net e.V.
- **Python Version**: ≥3.8

## Project Purpose

linuxmuster-base7 provides:
- **Initial Setup**: Complete server provisioning and configuration
- **Device Management**: Import and configure client devices (PCs, laptops) with DHCP, DNS, and PXE boot
- **Network Management**: Subnet configuration and firewall integration with OPNsense
- **User Management**: Integration with Samba AD and Sophomorix for school user management
- **Certificate Management**: SSL/TLS certificate generation and renewal
- **LINBO Integration**: Network boot infrastructure for client imaging

## Directory Structure

```
linuxmuster-base7/
├── src/                          # Python source code
│   ├── cli/                      # Command-line interface tools (10 scripts)
│   │   ├── import_devices.py    # Import devices from CSV to DHCP/DNS/LINBO
│   │   ├── import_subnets.py    # Import network subnets to DHCP/firewall
│   │   ├── setup.py              # Main setup orchestration
│   │   ├── renew_certs.py        # Certificate renewal (CA, server, firewall)
│   │   ├── opnsense_reset.py     # Reset firewall to post-setup state
│   │   ├── modini.py             # INI file modification utility
│   │   ├── update_ntpconf.py     # NTP configuration updates
│   │   ├── holiday.py            # Check if today is a holiday
│   │   └── holiday_generate.py   # Generate holiday configuration
│   │
│   ├── setup/                    # Setup modules (14 modules, alphabetically ordered)
│   │   ├── a_ini.py              # Read and validate setup.ini
│   │   ├── c_general-dialog.py   # Interactive setup dialogs
│   │   ├── d_templates.py        # Apply configuration templates
│   │   ├── e_fstab.py            # Configure filesystem mounts
│   │   ├── g_ssl.py              # Generate SSL certificates
│   │   ├── h_ssh.py              # Setup SSH keys and access
│   │   ├── helpers.py            # Shared helper functions for setup
│   │   ├── i_linbo.py            # Configure LINBO boot environment
│   │   ├── j_samba-provisioning.py # Provision Samba AD domain
│   │   ├── k_samba-users.py      # Create initial users and groups
│   │   ├── l_add-server.py       # Register additional servers
│   │   ├── m_firewall.py         # Configure OPNsense firewall
│   │   └── z_final.py            # Final cleanup and post-setup tasks
│   │
│   ├── examples/                 # Example/experimental code (not in production)
│   │   ├── base.py               # Example CLI base class (Template Method pattern)
│   │   └── logging.py            # Example unified logging module
│   │
│   ├── functions.py              # Shared utility functions used across all modules
│   └── __init__.py               # Package initialization
│
├── share/                        # Shared scripts and utilities
│   ├── dhcpd-update-samba-dns.py # DHCP event hook for DNS updates
│   ├── firewall/opnsense/        # OPNsense firewall utilities
│   │   ├── create-auth-config.py # Configure firewall authentication
│   │   └── create-keytab.py      # Create Kerberos keytabs for web proxy SSO
│   └── examples/
│       └── create-testusers.py   # Generate test users for development
│
├── etc/                          # Configuration file templates
├── debian/                       # Debian packaging files
├── tests/                        # Test suite
├── docs/                         # Additional documentation
├── .github/                      # GitHub Actions workflows
│
├── pyproject.toml                # Python project configuration (PEP 621)
├── setup.py                      # Legacy setup script (minimal)
├── MANIFEST.in                   # Package manifest
├── README.md                     # Project README
├── LICENSE                       # GPL-3.0 license
└── ToDo.md                       # Development task list
```

## Key Technologies & Dependencies

### Core Dependencies
- **paramiko**: SSH client library for remote firewall management
- **beautifulsoup4 + lxml**: XML/HTML parsing for configuration files
- **ldap3**: LDAP operations for user management
- **IPy, netaddr, netifaces**: Network address manipulation
- **python-apt**: APT package management integration
- **pythondialog**: Interactive TUI dialogs for setup
- **requests, urllib3**: HTTP/HTTPS API calls to OPNsense firewall

### Development Tools
- **pytest + pytest-cov**: Testing framework with coverage
- **black**: Code formatting
- **flake8**: Linting
- **mypy**: Type checking

## Command-Line Interface Tools

All CLI tools are accessible via `linuxmuster-<command>`:

### Device & Network Management
- **`linuxmuster-import-devices`**: Import devices from `/etc/linuxmuster/sophomorix/default-school/devices.csv`
  - Generates DHCP host declarations
  - Creates DNS entries (via dhcpd-update-samba-dns hook)
  - Configures PXE boot symlinks for LINBO
  - Generates GRUB boot configurations per device group

- **`linuxmuster-import-subnets`**: Import subnets from `/etc/linuxmuster/subnets.csv`
  - Configures DHCP subnet declarations
  - Sets up firewall static routes via OPNsense API
  - Updates netplan network configuration
  - Configures NTP subnet restrictions

### Setup & Configuration
- **`linuxmuster-setup`**: Main setup wizard
  - Orchestrates all setup modules in alphabetical order
  - Interactive or unattended mode
  - Validates prerequisites
  - Configures entire server stack (network, users, services, firewall)

- **`linuxmuster-modini`**: Modify INI configuration files
  - Syntax: `linuxmuster-modini <file> <section> <option> <value> [-r service]`
  - Optionally restart a service after modification

### Security & Certificates
- **`linuxmuster-renew-certs`**: Renew SSL/TLS certificates
  - Supports: CA, server, firewall certificates
  - Generates certificate chains and bundles
  - Uploads certificates to OPNsense firewall via API
  - Can renew individual certificates or all at once

- **`linuxmuster-opnsense-reset`**: Reset firewall to post-setup state
  - Validates firewall access
  - Uploads default configuration
  - Recreates Kerberos keytab for web proxy SSO
  - Waits for firewall to come back online

### Time & Calendar
- **`linuxmuster-update-ntpconf`**: Update NTP configuration
  - Configures NTP server settings
  - Sets subnet restrictions

- **`linuxmuster-holiday`**: Check if today is a holiday
  - Used for conditional operations in automation

- **`linuxmuster-holiday-generate`**: Generate holiday configuration
  - Fetches holiday data from external API
  - Creates local holiday database

## Setup Modules (Execution Order)

Setup modules are executed in alphabetical order (a → z). This ordering is critical:

1. **a_ini.py**: Read and validate `/var/lib/linuxmuster/setup.ini`
2. **c_general-dialog.py**: Interactive configuration dialogs (if needed)
3. **d_templates.py**: Apply configuration file templates (smb.conf, dhcpd.conf, etc.)
4. **e_fstab.py**: Configure filesystem mounts
5. **g_ssl.py**: Generate CA and server SSL certificates
6. **h_ssh.py**: Create SSH keys and configure firewall SSH access
7. **i_linbo.py**: Setup LINBO network boot environment
8. **j_samba-provisioning.py**: Provision Samba Active Directory domain
9. **k_samba-users.py**: Create global-admin and other initial users
10. **l_add-server.py**: Register additional servers (if configured)
11. **m_firewall.py**: Configure OPNsense firewall via API
12. **z_final.py**: Final tasks (cleanup, device import, subnet import, keytab creation)

### Setup Helper Module
- **helpers.py**: Shared functions for setup modules
  - `runWithLog()`: Execute commands with logging and error handling
  - Consistent subprocess execution
  - Secret masking for passwords in logs

## Core Shared Module: functions.py

The `functions.py` module provides shared utilities used across all CLI and setup modules:

### Key Functions (Categories)

**Setup & Configuration:**
- `getSetupValue(key)`: Read values from setup.ini
- `mySetupLogfile(__file__)`: Generate setup logfile path

**Device Management:**
- `getDevicesArray(fieldnrs, subnet, school)`: Read devices from CSV
- `getSubnetArray(subnet)`: Read subnet definitions

**LINBO/GRUB Boot Configuration:**
- `getGrubPart(partition)`: Convert partition to GRUB format (e.g., `/dev/sda1` → `(hd0,1)`)
- `getGrubOstype(osname)`: Detect OS type (linux, windows, etc.)
- `getStartconfOption(file, section, option)`: Parse LINBO start.conf files
- `getStartconfOsValues(file)`: Extract OS definitions from start.conf
- `getStartconfPartnr()`, `getStartconfPartlabel()`: Get partition metadata

**File Operations:**
- `readTextfile(path)`: Read text file with error handling
- `writeTextfile(path, content, mode)`: Write text file atomically

**Network & Firewall:**
- `waitForFw(wait)`: Wait for OPNsense firewall to become ready
- `firewallApi(path, data, method)`: Make API calls to OPNsense

**Logging & Output:**
- `printScript(msg, status)`: Consistent console output formatting
- Supports begin/end markers, progress indicators

**Certificate Operations:**
- `encodeCertToBase64(certfile)`: Encode certificate for firewall upload
- `readCertFromBase64(base64str)`: Decode certificate from firewall

## Configuration Files

### Main Configuration
- **`/var/lib/linuxmuster/setup.ini`**: Central setup configuration
  - Contains: network settings, domain info, firewall credentials, school name
  - Admin password is cleared after setup for security

### CSV Data Files
- **`/etc/linuxmuster/sophomorix/default-school/devices.csv`**: Device definitions
  - Columns: hostname, group, MAC, IP, subnet, role, dhcpopts, computertype, lmnreserved, pxeflag, etc.

- **`/etc/linuxmuster/subnets.csv`**: Network subnet definitions
  - Columns: subnet, gateway, nameserver, DHCP range, router IP

### Templates
Located in `/usr/share/linuxmuster/templates/`:
- `smb.conf.ini`: Samba configuration template
- `dhcpd.conf.linuxmuster`: DHCP server template
- `grub.cfg.*`: GRUB boot configuration templates for LINBO
- Various service-specific templates

## Development Workflow

### Code Style
- Follow PEP 8 (enforced by black with 100-char line length)
- Use **snake_case** for variables (e.g., `admin_password`, `device_count`)
- Use **camelCase** for functions (e.g., `getDevicesArray()`, `readTextfile()`)
- Use descriptive names (avoid abbreviations except common ones)
- Add comprehensive docstrings (Google style)
- Include inline comments explaining complex logic

### Refactoring Guidelines (Recent Changes)
1. **Constants over Magic Numbers**: Use named constants
2. **Comprehensive Comments**: Explain WHY, not just WHAT
3. **Error Handling**: Use f-strings, consistent error messages
4. **Import Organization**: Group stdlib, third-party, local imports
5. **Function Length**: Break down God functions (>100 lines)
6. **Single Responsibility**: One function, one purpose
7. **DRY Principle**: Extract common code into helpers

### Recent Refactoring Work (python-refactoring branch)
- Eliminated `subProc()` security vulnerabilities → `subprocess.run()`
- Created `setup/helpers.py` for shared setup functions
- Converted camelCase variables to snake_case where appropriate
- Added constants for magic numbers and permissions
- Comprehensive docstrings and inline comments
- Fixed shell injection vulnerabilities
- Consolidated duplicate logging implementations

### Testing
```bash
# Run test suite
pytest

# Run with coverage
pytest --cov=linuxmuster_base7 --cov-report=html

# Compile all Python files
find src -name "*.py" -exec python3 -m py_compile {} \;
```

### Building Package
```bash
# Build Debian package
./buildpackage.sh

# Build Python package
python3 -m build
```

## Important Patterns & Conventions

### Naming Conventions
- **Setup modules**: Single letter prefix indicates execution order (`a_ini.py`, `z_final.py`)
- **CLI scripts**: Descriptive names matching command (`import_devices.py` → `linuxmuster-import-devices`)
- **Variables**: snake_case (`device_array`, `admin_password`, `base_config_file_path`)
- **Functions**: camelCase (`getDevicesArray`, `readTextfile`, `encodeCertToBase64`)
- **Constants**: UPPER_SNAKE_CASE (`NETPLAN_PERMISSIONS`, `FIREWALL_WAIT_TIMEOUT`)

### File Headers
All Python files should have:
```python
#!/usr/bin/python3
#
# Module purpose
# author@linuxmuster.net
# YYYYMMDD (date of last significant change)
#
"""
Module docstring explaining purpose, features, and usage.
"""
```

### Logging Pattern
```python
import datetime
import os
import environment

logfile = environment.LOGDIR + '/script-name.log'

def logToFile(message):
    """Write message to logfile with timestamp."""
    try:
        with open(logfile, 'a') as f:
            timestamp = str(datetime.datetime.now()).split('.')[0]
            f.write(f'[{timestamp}] {message}\n')
    except Exception:
        pass  # Fail silently if logging fails
```

### Error Handling Pattern
```python
from functions import printScript
import sys

msg = 'Performing operation'
printScript(msg, '', False, False, True)
try:
    # Operation here
    printScript(' Success!', '', True, True, False, len(msg))
except Exception as error:
    printScript(f' Failed: {error}', '', True, True, False, len(msg))
    sys.exit(1)
```

### Security Considerations
1. **Never log passwords**: Use `maskSecrets` parameter in `runWithLog()`
2. **Restrict file permissions**: Use `0o600` for sensitive files (netplan, setup.ini)
3. **Avoid shell=True**: Always use list arguments for subprocess
4. **Validate input**: Check user input before system calls
5. **Remove secrets after use**: Clear admin password from setup.ini after setup

## Integration Points

### External Systems
- **Samba AD**: Domain controller, user authentication
- **Sophomorix**: User and group management system
- **OPNsense**: Firewall and router (configured via API)
- **LINBO**: Network boot and imaging system
- **ISC DHCP**: DHCP server with event hooks
- **NTP/ntpsec**: Time synchronization
- **AppArmor**: Security profiles for services

### File System Locations
- **`/var/lib/linuxmuster/`**: Runtime data, setup.ini, device links
- **`/etc/linuxmuster/`**: Configuration files, CSV data
- **`/var/log/linuxmuster/`**: Log files for all operations
- **`/srv/linbo/`**: LINBO boot files and images
- **`/etc/dhcp/`**: DHCP configuration and device configs
- **`/etc/netplan/`**: Network configuration
- **`/usr/lib/linuxmuster/`**: Library files (environment module)

### Environment Module
Located at `/usr/lib/linuxmuster/environment.py`, provides system-wide constants:
```python
import environment

environment.LOGDIR          # /var/log/linuxmuster
environment.SETUPINI        # /var/lib/linuxmuster/setup.ini
environment.WIMPORTDATA     # /etc/linuxmuster/sophomorix/.../devices.csv
environment.LINBODIR        # /srv/linbo
environment.DHCPDEVCONF     # /etc/dhcp/devices.conf
# ... and many more
```

## Debugging & Troubleshooting

### Log Files
Each CLI tool and setup module writes to its own log file in `/var/log/linuxmuster/`:
- `setup.*.log`: Setup module logs (e.g., `setup.a_ini.log`, `setup.z_final.log`)
- `import-devices.log`: Device import operations
- `import-subnets.log`: Subnet import operations
- `renew-certs.log`: Certificate renewal operations

### Common Issues
1. **Import fails**: Check CSV file syntax in `/etc/linuxmuster/sophomorix/default-school/devices.csv`
2. **Firewall unreachable**: Verify SSH key in `/root/.ssh/id_rsa_linuxmuster-opnsense`
3. **Certificate errors**: Check CA certificate in `/etc/linuxmuster/ssl/cacert.pem`
4. **DHCP not updating**: Check dhcpd-update-samba-dns.py hook is executable
5. **Setup fails**: Review logs in `/var/log/linuxmuster/setup.*.log` for specific module

### Development Mode
For testing without affecting production:
- Set `skipfw = True` in setup.ini to skip firewall operations
- Use `--school test-school` parameter for separate school testing
- Test on VM snapshots (use `tests/test_setup_integration.sh`)

## Resources

- **Documentation**: https://docs.linuxmuster.net
- **Community Forum**: https://ask.linuxmuster.net
- **Source Code**: https://github.com/linuxmuster/linuxmuster-base7
- **Issue Tracker**: https://github.com/linuxmuster/linuxmuster-base7/issues
- **Release Notes**: https://github.com/linuxmuster/linuxmuster-base7/releases

## Contributing

When contributing to this project:
1. Follow existing code style and patterns (snake_case for variables, camelCase for functions)
2. Add comprehensive docstrings and comments
3. Update this Claude.md if you add new modules or change structure
4. Test thoroughly (compile check + functional testing)
5. Update header dates (YYYYMMDD) in modified files
6. Write descriptive commit messages following the established format
7. Consider security implications (especially for shell commands, file permissions)

## Notes for AI Assistants

When working on this codebase:
- **Always read files before editing** to understand current implementation
- **Preserve existing patterns** unless explicitly refactoring
- **Follow naming conventions**: snake_case for variables, camelCase for functions, UPPER_SNAKE_CASE for constants
- **Update header dates** to current date (YYYYMMDD format)
- **Test compilation** after changes: `python3 -m py_compile <file>`
- **Check imports** after moving files
- **Maintain alphabetical order** of setup modules (critical for execution)
- **Document security-sensitive operations** (passwords, file permissions, SSH keys)
- **Ask for clarification** if uncertain about intended behavior
- **Examples directory** (`src/examples/`) is for reference only, not production code
