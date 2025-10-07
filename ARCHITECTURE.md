# ORBIT - Onboarding, Registration, Bootstrap & Integration Toolkit - Architecture Overview

## High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        CI/CD Pipeline                            │
│  (GitLab CI / GitHub Actions / Jenkins)                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORBIT                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Topology     │  │ Onboarding   │  │ Backup       │          │
│  │ Loader       │  │ Manager      │  │ Manager      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                 │
│                            │                                     │
│                   ┌────────▼─────────┐                          │
│                   │  Session Manager │                          │
│                   └────────┬─────────┘                          │
└────────────────────────────┼──────────────────────────────────┬─┘
                             │                                  │
                   ┌─────────▼──────────┐          ┌───────────▼─────────┐
                   │   Catalystwan      │          │   Sastre            │
                   │   (Device APIs)    │          │   (Config Backup)   │
                   └─────────┬──────────┘          └───────────┬─────────┘
                             │                                  │
                             └──────────────┬───────────────────┘
                                            │
                                   ┌────────▼─────────┐
                                   │  SD-WAN Manager  │
                                   │  (vManage)       │
                                   └──────────────────┘
```

## Module Structure

```
sdwan-orbit/
├── src/
│   └── sdwan_orbit/
│       ├── __init__.py              # Public API exports
│       ├── orbit.py                 # Main Orbit class
│       ├── session.py               # Session management with retry
│       ├── onboarding.py            # Device onboarding logic
│       ├── backup.py                # Config backup/restore (sastre)
│       ├── topology.py              # Topology schema (pydantic)
│       ├── certificates.py          # Certificate management (optional)
│       ├── ci.py                    # CI/CD helper utilities
│       ├── exceptions.py            # Custom exceptions
│       └── cli.py                   # CLI interface (click)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── examples/
│   ├── topologies/
│   │   ├── small-hub-spoke.yaml
│   │   ├── medium.yaml
│   │   └── large.yaml
│   └── ci-cd/
│       ├── gitlab-ci.yml
│       └── github-actions.yml
├── docs/
├── pyproject.toml
└── README.md
```

## Core Components

### 1. TopologyDefinition (topology.py)

**Purpose**: Define SD-WAN topology as code

**Schema**:
```yaml
name: my-topology
org_name: my-org
manager:
  url: https://10.0.0.10
  username: admin
  password: secret
controllers:
  - ip: 172.16.0.101
validators:
  - ip: 172.16.0.201
edges:
  - site_id: 1
    system_ip: 10.1.0.1
ip_type: v4
software_version: "20.12.1"
```

**Validation**: Pydantic ensures type safety and validation

---

### 2. SessionManager (session.py)

**Purpose**: Manage connection to SD-WAN Manager

**Features**:
- Automatic retry on connection failure
- Connection pooling
- Session timeout handling
- Health checks

**Key Methods**:
```python
session_mgr = SessionManager(url, username, password)
session = session_mgr.connect(timeout=300)
session_mgr.close()
```

---

### 3. DeviceOnboarder (onboarding.py)

**Purpose**: Onboard controllers, validators, and edges

**Features**:
- Credential fallback (try default, then custom)
- Skip already-onboarded devices
- Parallel onboarding (ThreadPoolExecutor)
- Wait for onboarding completion
- Certificate signing (if using custom CA)

**Key Methods**:
```python
onboarder = DeviceOnboarder(session)
controller_uuids = onboarder.onboard_controllers(controller_list)
edge_uuids = onboarder.onboard_edges(edge_list)
onboarder.wait_for_onboarding(all_uuids, timeout=600)
```

---

### 4. ConfigurationManager (backup.py)

**Purpose**: Backup and restore SD-WAN configurations

**Features**:
- Wraps sastre for templates/policies/config groups
- MRF region backup (20.7+)
- Selective restore (tags)
- Template attachment after restore

**Key Methods**:
```python
config_mgr = ConfigurationManager(url, username, password)
config_mgr.backup(workdir="/backup")
config_mgr.restore(workdir="/backup", attach=True)
```

---

### 5. Orbit (orbit.py)

**Purpose**: Main entry point - coordinates all operations

**Features**:
- Load topology from YAML
- Deploy entire topology
- Backup configuration
- Restore configuration
- Cleanup

**Key Methods**:
```python
orch = Orbit.from_topology("topology.yaml")
results = orch.deploy()
orch.backup("/artifacts")
orch.restore("/artifacts", attach=True)
orch.cleanup()
```

---

### 6. CIHelper (ci.py)

**Purpose**: CI/CD-specific utilities

**Features**:
- Deploy and wait for healthy state
- Export test data
- Cleanup after tests
- Parallel deployment
- Idempotency

**Key Methods**:
```python
metadata = CIHelper.deploy_and_wait("topology.yaml")
CIHelper.wait_for_healthy(orch, timeout=1800)
CIHelper.export_test_data(orch, "/artifacts")
CIHelper.cleanup("topology.yaml", force=True)
```

---

## Data Flow

### Deployment Flow

```
1. Load Topology
   └─> Parse YAML
       └─> Validate with Pydantic

2. Connect to Manager
   └─> SessionManager.connect()
       └─> Retry on failure
           └─> Return ManagerSession

3. Onboard Controllers
   └─> DeviceOnboarder.onboard_controllers()
       └─> For each controller:
           ├─> Try default credentials
           ├─> Fallback to custom password
           ├─> Skip if already onboarded
           └─> Return device UUID

4. Onboard Validators
   └─> DeviceOnboarder.onboard_validators()
       └─> (same as controllers)

5. Wait for Control Plane
   └─> DeviceOnboarder.wait_for_onboarding()
       └─> Poll device status
           └─> Wait for reachable + certificates installed

6. Onboard Edges
   └─> DeviceOnboarder.onboard_edges()
       └─> For each edge:
           ├─> Get available UUID from serial file
           ├─> Generate OTP token
           ├─> Wait for edge to join
           ├─> Attach template/config group
           └─> Return device UUID

7. Verify Deployment
   └─> Check all devices healthy
       └─> Return deployment results
```

### Backup Flow

```
1. Connect to Manager
   └─> SessionManager.connect()

2. Backup Templates/Policies
   └─> ConfigurationManager.backup()
       └─> Call sastre TaskBackup
           ├─> Backup device templates
           ├─> Backup feature templates
           ├─> Backup policies
           ├─> Backup config groups (20.12+)
           └─> Save to workdir

3. Backup MRF Regions (20.7+)
   └─> ConfigurationManager.backup_mrf_regions()
       └─> Query network-hierarchy API
           └─> Save regions and subregions as JSON

4. Return Success
```

### Restore Flow

```
1. Connect to Manager
   └─> SessionManager.connect()

2. Restore Templates/Policies
   └─> ConfigurationManager.restore()
       └─> Call sastre TaskRestore
           ├─> Restore device templates
           ├─> Restore feature templates
           ├─> Restore policies
           ├─> Restore config groups (20.12+)
           └─> Optionally attach to devices

3. Restore MRF Regions (if backed up)
   └─> ConfigurationManager.restore_mrf_regions()
       └─> POST to network-hierarchy API

4. Return Success
```

---

## Error Handling Strategy

### Exception Hierarchy

```
OrbitError (base)
├── OnboardingError
│   ├── CredentialError
│   ├── DeviceNotFoundError
│   └── OnboardingTimeoutError
├── ConfigurationError
│   ├── TemplateError
│   ├── PolicyError
│   └── AttachmentError
├── BackupRestoreError
│   ├── BackupError
│   └── RestoreError
├── TopologyError
│   ├── ValidationError
│   └── SchemaError
└── SessionError
    ├── ConnectionError
    └── AuthenticationError
```

### Retry Policy

**Retryable Errors**:
- Network timeouts
- Connection refused
- Rate limiting (429)
- Server errors (500-599)

**Non-Retryable Errors**:
- Authentication failures (401, 403)
- Not found (404)
- Invalid input (400)
- Resource conflicts (409)

**Strategy**:
```python
max_retries = 3
backoff_factor = 2.0  # exponential backoff
retry_on = [ConnectionError, TimeoutError, RateLimitError]
```

---

## Configuration Management

### Config File Support

**Environment Variables**:
```bash
SDWAN_MANAGER_URL
SDWAN_USERNAME
SDWAN_PASSWORD
SDWAN_LOG_LEVEL
SDWAN_STATE_FILE
```

**Config File** (optional):
```yaml
# ~/.sdwan-orbit/config.yaml
manager:
  url: https://10.0.0.10
  username: admin
  verify_ssl: false

defaults:
  timeout: 300
  retry_count: 3
  parallel_workers: 3

logging:
  level: INFO
  format: json
```

---

## Testing Strategy

### Unit Tests
- Mock all external APIs (catalystwan, sastre)
- Test business logic in isolation
- 100% coverage of core modules

### Integration Tests
- Test against real/test SD-WAN manager
- Verify end-to-end workflows
- Test error scenarios

### CI/CD Tests
- Deploy → Test → Cleanup cycle
- Parallel topology tests
- Idempotency tests

---

## Performance Considerations

### Parallel Operations

**Concurrent onboarding**:
```python
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(onboard_device, d) for d in devices]
    results = [f.result() for f in futures]
```

**Batching**:
- Batch device inventory queries
- Batch certificate signing
- Batch health checks

### Caching

**Session caching**:
- Cache manager session (reuse across operations)
- Cache device inventory (TTL: 60s)
- Cache template lookups (TTL: 300s)

---

## Security Considerations

**Credentials**:
- ❌ Never store passwords in topology files (use env vars)
- ✅ Support credential providers (Vault, AWS Secrets Manager)
- ✅ Use HTTPS with certificate verification
- ✅ Clear sensitive data from logs

**Network**:
- ✅ Use TLS 1.2+ only
- ✅ Validate SSL certificates (unless explicitly disabled)
- ✅ Timeout all network operations

**State Files**:
- ✅ Encrypt state files (contain device UUIDs, metadata)
- ✅ Restrict file permissions (0600)

---

## Comparison to Old Tool

| Aspect | Old Tool (CML-focused) | New Tool (CI/CD-focused) |
|--------|------------------------|--------------------------|
| **Purpose** | CML lab automation | CI/CD deployment |
| **Topology** | Generated from template | Defined in YAML |
| **Infrastructure** | Creates VMs in CML | Uses existing infrastructure |
| **Dependencies** | virl2-client, pyats, catalystwan, sastre | catalystwan, sastre only |
| **LOC** | ~3200 lines | ~800 lines (estimated) |
| **Architecture** | CLI tasks + utils | Library + optional CLI |
| **Error Handling** | sys.exit() | Proper exceptions |
| **Logging** | Forced | Optional |
| **Testability** | Hard (CML coupling) | Easy (mocked APIs) |
| **Flexibility** | Limited to CML | Infrastructure-agnostic |

---

## Quick Reference

### Typical CI/CD Usage

```yaml
# .gitlab-ci.yml
test_topology:
  script:
    - pip install sdwan-orbit
    - orbit deploy topologies/test.yaml
    - pytest tests/
    - orbit backup /artifacts
  after_script:
    - orbit cleanup topologies/test.yaml
  artifacts:
    paths: [/artifacts]
```

### Programmatic Usage

```python
from sdwan_orbit import Orbit

# Deploy
orch = Orbit.from_topology("topology.yaml")
results = orch.deploy()

# Run tests
# ...

# Backup
orch.backup("/artifacts")

# Cleanup
orch.cleanup()
```

---

**For detailed implementation instructions, see FRESH_START_PLAN.md**
**For task tracking, see TODO.md**
