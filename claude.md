# ORBIT - Onboarding, Registration, Bootstrap & Integration Toolkit

## Project Overview

ORBIT is a modern, CI/CD-optimized Python toolkit for automating Cisco SD-WAN device onboarding and configuration management. It handles vManage-side operations after devices have discovered vBond, accepting device information from any source.

**Current Status**: Week 1-2 complete (foundation + edge onboarding), ready for integration testing

## Core Principles

Every decision must align with these principles:

1. **Tool-Agnostic**: Accept device lists from ANY source (containerlab, CML, Terraform, manual YAML)
2. **vManage-Side Only**: Handles onboarding AFTER devices discover vBond (not full PnP)
3. **Simple Input Format**: Generic YAML/JSON - parsers for common tools are optional
4. **Library-First**: Designed as library with optional CLI
5. **Clean Architecture**: Proper exceptions (no sys.exit()), optional logging, type hints
6. **Leverage Existing Tools**: Uses catalystwan and sastre (no reinventing)

See **DECISIONS.md** for detailed rationale on each principle.

## Architecture

```
ORBIT
├── Device Models (models.py) - Pydantic validation
├── Session Management (session.py) - Connection with retry
├── Device Onboarding (onboarding.py) - Controllers, validators, edges
├── Config Management (backup.py) - Sastre wrapper for backup/restore
├── Main Orchestrator (orbit.py) - Coordinates all operations
├── Optional Parsers (parsers/) - Extract info from infrastructure tools
└── CLI (cli.py) - Click + Rich interface
```

## Current Implementation

### ✅ Completed

**Core Infrastructure:**
- `models.py`: Pydantic schemas for device inventory (ManagerConfig, ControllerConfig, ValidatorConfig, EdgeConfig, DeviceInventory)
- `exceptions.py`: Custom exception hierarchy (OrbitError, OnboardingError, ConfigurationError, etc.)
- `session.py`: SessionManager with automatic retry logic and timeout handling
- `backup.py`: ConfigurationManager wrapping sastre with MRF region support (20.7+)
- `orbit.py`: Main Orbit orchestrator class with context manager support
- `cli.py`: Click-based CLI with Rich output formatting

**Device Onboarding (Control Plane):**
- Controllers and validators onboarding with credential fallback
- Skip existing devices functionality
- Wait for onboarding with readiness checks (reachability + certificates)
- Device inventory tracking by VPN 0 IP

**Backup/Restore:**
- Full backup via sastre (templates, policies, config-groups)
- MRF regions and subregions backup/restore (20.7+)
- Version detection and compatibility handling

**Edge Device Onboarding:**
- Find devices by serial number in vManage inventory ✅
- Wait for certificate installation ✅
- Attach device templates with variables ✅
- Attach config-groups (20.12+) ✅
- 38 unit tests with 81% coverage ✅
- Test topology available in `tests/topology/` ✅

### 📋 Backlog

- Integration tests against real infrastructure
- Containerlab parser implementation
- CI/CD helper utilities
- Additional parsers (CML, Terraform)
- Performance testing and optimization

## Device Inventory Format

ORBIT accepts a simple YAML/JSON format:

```yaml
manager:
  url: https://10.0.0.10
  username: admin
  password: admin

controllers:
  - ip: 172.16.0.101
    password: admin  # optional

validators:
  - ip: 172.16.0.201

edges:
  - serial: C8K-12345678-ABCD
    system_ip: 10.1.0.1
    site_id: 1
    template_name: branch_template
    values:
      hostname: edge1
      vpn0_inet_ip: 192.168.1.10/24
```

**Why This Format?** See DECISIONS.md ADR-001, ADR-002, ADR-003.

## Development Workflow

### Before Starting Work

1. **Read**:
   - WORKFLOW.md for development process
   - DECISIONS.md for architectural context
   - FRESH_START_PLAN.md for implementation guidance
   - TODO.md for current tasks

2. **Validate** against core principles:
   - Does this maintain tool-agnostic design?
   - Is this solving the right problem?
   - Can this be simpler?

3. **Document**:
   - Add entry to DECISIONS.md if architectural
   - Update TODO.md with task breakdown

### Implementation Process

```
1. Design → Document decision (if major)
2. Write tests (if applicable)
3. Implement with type hints and docstrings
4. Test manually
5. Update TODO.md progress
6. Validate against checklist (WORKFLOW.md)
7. Commit with proper message
```

### Commit Message Format

```
<type>: <short summary>

<optional detailed description>

<optional footer>
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

See WORKFLOW.md for complete standards.

## Code Standards

**Python Style:**
- Line length: 100 characters
- Formatting: Black
- Linting: Ruff
- Type checking: mypy (strict)

**Naming:**
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

**Error Handling:**
- Always use custom exceptions from exceptions.py
- Never call sys.exit() - raise exceptions instead
- Provide helpful error messages
- Log at appropriate levels

**Example:**
```python
try:
    result = risky_operation()
except SomeError as e:
    logger.error(f"Operation failed: {e}")
    raise OnboardingError(f"Failed to onboard device: {e}") from e
```

## Module Overview

### models.py
Pydantic models for data validation:
- `ManagerConfig`: vManage connection details
- `ControllerConfig`: vSmart controller config
- `ValidatorConfig`: vBond validator config
- `EdgeConfig`: WAN Edge with serial + template variables
- `DeviceInventory`: Complete device inventory

**Key Method**: `DeviceInventory.from_yaml(path)` - load from file

### session.py
Session management with retry logic:
- `SessionManager`: Manages vManage connection
- Automatic retry with exponential backoff
- Configurable timeout and retry count
- Context manager support

**Usage:**
```python
with SessionManager(url, username, password) as mgr:
    mgr.connect()
    # Use mgr.session
```

### onboarding.py
Device onboarding operations:
- `DeviceOnboarder`: Handles all onboarding
- `onboard_controllers()`: Onboard vSmart controllers
- `onboard_validators()`: Onboard vBond validators
- `onboard_edges()`: Onboard WAN Edges (IN PROGRESS)
- `wait_for_onboarding()`: Wait for devices to be ready

**Features:**
- Credential fallback (try default, then custom)
- Skip existing devices
- Parallel operations (future)

### backup.py
Configuration backup/restore via sastre:
- `ConfigurationManager`: Wraps sastre operations
- `backup()`: Backup templates, policies, config-groups
- `restore()`: Restore configuration
- `_backup_mrf_regions()`: Backup MRF (20.7+)
- `_restore_mrf_regions()`: Restore MRF

### orbit.py
Main orchestrator:
- `Orbit`: Main class coordinating all operations
- `from_file()`: Load from YAML file
- `from_dict()`: Load from dictionary
- `from_containerlab()`: Parse containerlab (TODO)
- `onboard()`: Onboard all devices
- `backup()`: Backup configuration
- `restore()`: Restore configuration

**Usage:**
```python
with Orbit.from_file("devices.yaml") as orch:
    results = orch.onboard()
    orch.backup("/artifacts")
```

### cli.py
CLI interface:
- `orbit onboard <file>`: Onboard devices
- `orbit backup`: Backup configuration
- `orbit restore`: Restore configuration
- Rich formatting for nice output
- Verbosity levels: -v (INFO), -vv (DEBUG)

### parsers/containerlab.py
Containerlab parser (STUB):
- `parse_containerlab()`: Parse containerlab inspect output
- Not yet implemented - raises NotImplementedError

## Testing Strategy

### Unit Tests (TODO)
- Mock external APIs (catalystwan, sastre)
- Test business logic in isolation
- Test error conditions
- Target: >80% coverage

### Integration Tests (Future)
- Test against real/mock vManage
- End-to-end workflows
- CI/CD integration

### Manual Testing Checklist
See FRESH_START_PLAN.md Day 10 for detailed checklist.

## Dependencies

**Core:**
- catalystwan>=0.33.10 - Cisco SD-WAN SDK
- cisco-sdwan>=1.26 - Sastre for backup/restore
- pydantic>=2.0 - Data validation
- pyyaml>=6.0 - YAML parsing

**CLI:**
- click>=8.0 - CLI framework
- rich>=13.0 - Terminal formatting

**Dev:**
- pytest>=7.0 - Testing
- black>=23.0 - Formatting
- ruff>=0.1.0 - Linting
- mypy>=1.0 - Type checking

## Reference Code

The `sdwan-lab-deployment-tool/` directory contains the original CML-focused tool.

**What to Reference:**
- Onboarding workflows: catalyst_sdwan_lab/tasks/utils.py:317-408
- Edge onboarding: catalyst_sdwan_lab/tasks/add.py:348-580
- Credential fallback pattern: utils.py:365-392
- Retry/polling logic: utils.py:605-642

**What to AVOID:**
- sys.exit() calls - use exceptions
- Forced logging - make it optional
- CML coupling - keep tool-agnostic
- Hardcoded paths - make configurable

## Key Architectural Decisions

See DECISIONS.md for complete list. Key decisions:

1. **ADR-001**: Tool-agnostic device input (not topology management)
2. **ADR-002**: Post-discovery onboarding only (not full PnP)
3. **ADR-003**: Serial-based edge configuration
4. **ADR-005**: Exception-based error handling (no sys.exit)
5. **ADR-006**: Optional logging
6. **ADR-007**: Sastre for backup/restore
7. **ADR-008**: Catalystwan for vManage API
8. **ADR-011**: Library-first design

## Current Sprint (Week 3+)

**Goal**: Integration testing and containerlab parser

**Next Tasks**:
1. Write integration tests using `tests/topology/`
2. Implement containerlab parser
3. Add CI/CD examples
4. Performance testing
5. Documentation improvements

See TODO.md for detailed task breakdown.

## Open Questions

Document answers in DECISIONS.md:

1. **Certificate Management**: Use vManage's built-in CA or support custom CA?
2. **Template Variables**: How to validate required template variables?
3. **Version Handling**: How to handle version-specific features gracefully?
4. **Containerlab Detection**: How to identify device types in containerlab?
5. **Error Recovery**: Should we support partial rollback?

## Troubleshooting

### Common Issues

**Import errors:**
```bash
pip install -e .
```

**Type check failures:**
```bash
mypy src/
```

**Formatting:**
```bash
black src/ tests/
ruff check src/ tests/
```

### Debugging

Enable DEBUG logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or use CLI:
```bash
orbit onboard devices.yaml -vv
```

## Quick Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run CLI
orbit onboard examples/devices.yaml
orbit backup --manager https://vmanage -u admin -p admin /backup
orbit restore --manager https://vmanage -u admin -p admin /backup

# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Run tests (when implemented)
pytest

# View files
ls -la src/sdwan_orbit/
cat src/sdwan_orbit/models.py
```

## Project Structure

```
sdwan-orbit/
├── src/
│   └── sdwan_orbit/
│       ├── __init__.py           # Public API
│       ├── models.py             # Pydantic models
│       ├── exceptions.py         # Exception hierarchy
│       ├── session.py            # Session management
│       ├── onboarding.py         # Device onboarding
│       ├── backup.py             # Config backup/restore
│       ├── orbit.py              # Main orchestrator
│       ├── cli.py                # CLI interface
│       └── parsers/
│           ├── __init__.py
│           └── containerlab.py   # Containerlab parser (stub)
├── tests/
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── examples/
│   └── devices.yaml              # Example device inventory
├── WORKFLOW.md                   # Development process
├── DECISIONS.md                  # Architectural decisions
├── FRESH_START_PLAN.md          # Implementation plan
├── TODO.md                       # Task tracking
├── ARCHITECTURE.md              # Original architecture (outdated)
├── README.md                    # User documentation
├── claude.md                    # This file (AI context)
├── pyproject.toml              # Python project config
└── .gitignore
```

## For AI Assistants (Claude)

When working on this project:

1. **Always check** DECISIONS.md before making architectural changes
2. **Follow** WORKFLOW.md for development process
3. **Update** TODO.md as you complete tasks
4. **Document** new decisions in DECISIONS.md
5. **Validate** against core principles before proceeding
6. **Use** the reference code for patterns, not copy-paste
7. **Never** use sys.exit() - always raise exceptions
8. **Never** force logging configuration
9. **Always** add type hints and docstrings
10. **Test** manually before marking complete

**Current Priority**: Integration testing and containerlab parser (see TODO.md)

## Getting Started (for new contributors)

1. Read this file (claude.md) completely
2. Read WORKFLOW.md for process
3. Read DECISIONS.md for context
4. Check TODO.md for current tasks
5. Look at examples/devices.yaml for format
6. Run `pip install -e ".[dev]"` to set up
7. Follow WORKFLOW.md validation checklist

## Success Criteria

**MVP Complete When:**
- ✅ Controllers/validators onboarding works
- ✅ Backup/restore works
- ✅ Edge onboarding works
- ✅ Template/config-group attachment works
- ✅ Unit tests pass (38 tests, 81% coverage)
- 📋 Integration tests
- 📋 Containerlab parser works

**v1.0 Complete When:**
- All MVP features
- Integration tests complete
- CI/CD examples
- Migration guide
- Troubleshooting docs

Current status: **~85% to MVP**, **~60% to v1.0**

---

**Remember**: This is a tool-agnostic, library-first, vManage-side onboarding tool. Keep it simple, keep it clean, and validate against the core principles.
