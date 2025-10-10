# ORBIT - Onboarding, Registration, Bootstrap & Integration Toolkit

A modern, CI/CD-optimized Python toolkit for automating Cisco SD-WAN device onboarding and configuration management.

## Features

- **Tool-Agnostic**: Works with device info from any source (containerlab, CML, Terraform, manual YAML)
- **Simple Input**: Generic YAML/JSON device list with optional parsers for common tools
- **vManage Integration**: Handles device onboarding after they've discovered vBond
- **Edge Device Onboarding**: Certificate installation, template/config-group attachment
- **Template & Config-Group Support**: Attach device templates (pre-20.12) or configuration groups (20.12+)
- **Configuration Management**: Backup/restore templates and policies via sastre
- **CI/CD Ready**: Designed for automated pipelines with proper error handling
- **Clean Architecture**: Library-first design with optional CLI

## Installation

```bash
pip install sdwan-orbit
```

### Development Installation

```bash
git clone https://github.com/your-org/sdwan-orbit.git
cd sdwan-orbit
pip install -e ".[dev]"
```

## Quick Start

### 1. Create a device list

```yaml
# devices.yaml
manager:
  url: https://10.0.0.10
  username: admin
  password: admin

controllers:
  - ip: 172.16.0.101
  - ip: 172.16.0.102

validators:
  - ip: 172.16.0.201

edges:
  - serial: C8K-12345678-ABCD  # Device serial number
    system_ip: 10.1.0.1
    site_id: 1
    template_name: branch_template  # Optional: device template
    values:  # Optional: template variables
      hostname: edge1
      vpn0_inet_ip: 192.168.1.10/24

  - serial: C8K-87654321-EFGH
    system_ip: 10.2.0.1
    site_id: 2
    config_group: branch_config_group  # Optional: config group (20.12+)
```

### 2. Onboard devices

```bash
orbit onboard devices.yaml
```

### 3. Backup configuration

```bash
orbit backup --manager https://10.0.0.10 -u admin -p admin /artifacts
```

## Usage

### Programmatic

```python
from sdwan_orbit import Orbit

# From device list file
orch = Orbit.from_file("devices.yaml")
results = orch.onboard()

# From containerlab
orch = Orbit.from_containerlab("sdwan-lab")
results = orch.onboard()

# Backup
orch.backup("/artifacts")
```

### CLI

```bash
# Onboard from device list
orbit onboard devices.yaml

# Onboard from containerlab
orbit onboard --from-containerlab sdwan-lab

# Backup configuration
orbit backup --manager https://10.0.0.10 -u admin -p admin /artifacts

# Restore configuration
orbit restore --manager https://10.0.0.10 -u admin -p admin /artifacts --attach
```

### CI/CD Integration

```yaml
# .gitlab-ci.yml
test_sdwan:
  script:
    - containerlab deploy -t topology.clab.yml
    - orbit onboard --from-containerlab sdwan-lab
    - pytest tests/
    - orbit backup --manager https://vmanage:8443 -u admin -p $PASS /artifacts
  after_script:
    - containerlab destroy -t topology.clab.yml
  artifacts:
    paths: [/artifacts]
```

## Documentation

See [claude.md](claude.md) for detailed architecture and design decisions.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
