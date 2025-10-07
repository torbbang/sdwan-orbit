# Architectural Decision Log

This document tracks major architectural and design decisions made during ORBIT development.

## Format

Each decision follows this structure:
- **Date**: When the decision was made
- **Status**: Accepted | Rejected | Superseded | Deprecated
- **Context**: What problem we're trying to solve
- **Decision**: What we decided to do
- **Rationale**: Why we made this decision
- **Consequences**: Implications of this decision
- **Alternatives Considered**: Other options and why they were rejected

---

## ADR-001: Tool-Agnostic Device Input

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Original plan included a topology definition system (YAML schemas with Pydantic). However, topology is already managed by external tools (containerlab, CML, Terraform, etc.).

**Decision**: ORBIT accepts generic device lists in YAML/JSON format and provides optional parsers for common tools, rather than managing topology itself.

**Rationale**:
- Topology creation is already solved by containerlab and other tools
- Users want flexibility to use any infrastructure tool
- Simpler scope = faster development and easier maintenance
- Tool-agnostic approach is more flexible

**Consequences**:
- Positive: Simpler codebase, no topology logic needed
- Positive: Works with any infrastructure tool
- Positive: Users can manually create device lists
- Negative: Need parsers for each tool (but optional)
- Negative: User responsible for providing correct device info

**Alternatives Considered**:
1. **Topology-as-Code (original plan)**: Would lock users into our schema
2. **Containerlab-only**: Too restrictive, not tool-agnostic
3. **CML-only**: Same issue as containerlab-only

---

## ADR-002: Post-Discovery Onboarding Only

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Original plan mentioned PnP (Plug and Play) workflows, which could imply ORBIT handles the full device discovery process.

**Decision**: ORBIT handles only the vManage side of onboarding AFTER devices have already discovered vBond. Device discovery (DHCP, DNS, manual config) is out of scope.

**Rationale**:
- Device discovery is infrastructure-specific and already handled by deployment tools
- vManage operations (accept devices, sign certs, attach templates) are the valuable automation
- Clearer separation of concerns
- Simpler scope

**Consequences**:
- Positive: Clearer scope and purpose
- Positive: Works with any discovery method
- Positive: Simpler implementation
- Negative: Requires devices to be pre-configured to reach vBond
- Negative: May need to clarify "not full PnP" in docs

**Alternatives Considered**:
1. **Full PnP**: Too complex, infrastructure-specific
2. **Bootstrap file generation**: Already handled by containerlab/CML

---

## ADR-003: Serial-Based Edge Configuration

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Need to match edge devices in device inventory to devices waiting in vManage, and attach appropriate templates/config-groups.

**Decision**: Use serial number as the primary identifier for edge devices, with template variables in a separate `values` dict:

```yaml
edges:
  - serial: C8K-12345678-ABCD
    system_ip: 10.1.0.1
    site_id: 1
    template_name: branch_template
    values:
      hostname: edge1
      vpn0_inet_ip: 192.168.1.10/24
```

**Rationale**:
- Serial number is the unique identifier in vManage
- System IP and site ID often needed for matching/validation
- Template variables vary by deployment and template
- Clean separation between required fields and template-specific values

**Consequences**:
- Positive: Clear structure
- Positive: Easy to match devices in vManage by serial
- Positive: Flexible values dict for any template variables
- Negative: User must know serial numbers (but usually available from infrastructure tool)

**Alternatives Considered**:
1. **UUID-based**: UUIDs are internal to vManage, harder for users to know
2. **All-flat structure**: Mixing required and optional fields is confusing
3. **Serial as dict key**: Less standard YAML structure, harder to validate with Pydantic

---

## ADR-004: Separate Controllers and Validators in Config

**Date**: 2025-10-07
**Status**: Accepted

**Context**: vSmart controllers and vBond validators are both "control plane" components but have different personalities in vManage.

**Decision**: Keep controllers and validators as separate lists in device inventory:

```yaml
controllers:
  - ip: 172.16.0.101
validators:
  - ip: 172.16.0.201
```

**Rationale**:
- Different API personalities ('vsmart' vs 'vbond')
- Clearer for users what each device is
- Matches SD-WAN terminology

**Consequences**:
- Positive: Clear and explicit
- Positive: Easy to understand
- Negative: Slightly more verbose than a single "control_components" list

**Alternatives Considered**:
1. **Single control_components list with type field**: More verbose per item
2. **Auto-detect from personality**: Requires accessing device before knowing type

---

## ADR-005: Exception-Based Error Handling (No sys.exit)

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Reference tool (sdwan-lab-deployment-tool) uses sys.exit() throughout, making it unusable as a library.

**Decision**: Use proper exception hierarchy and never call sys.exit(). CLI handles exceptions at the top level.

**Rationale**:
- Library-first design: users can catch and handle exceptions
- CI/CD friendly: programmatic error handling
- Testable: can test error conditions
- Python best practices

**Consequences**:
- Positive: Usable as library
- Positive: Proper error propagation
- Positive: Testable
- Negative: CLI must handle exceptions (but that's normal)

**Alternatives Considered**:
1. **sys.exit() like reference tool**: Makes it CLI-only, not a library
2. **Return error codes**: Non-Pythonic, harder to provide context

---

## ADR-006: Optional Logging

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Reference tool forces logging configuration. Library users may want control over logging.

**Decision**: ORBIT modules use Python's logging module but never configure it. Users configure logging themselves (or use CLI's configuration).

**Rationale**:
- Library best practices: never configure logging
- Users may have existing logging setup
- CLI can provide sensible defaults

**Consequences**:
- Positive: Flexible for library users
- Positive: No forced output
- Positive: Works with any logging configuration
- Negative: Library users must set up logging (but standard practice)

**Alternatives Considered**:
1. **Force logging like reference tool**: Bad practice for libraries
2. **No logging at all**: Loses diagnostic information

---

## ADR-007: Sastre for Backup/Restore

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Need configuration backup and restore functionality. Sastre is Cisco's official tool.

**Decision**: Use sastre (cisco-sdwan) library directly rather than reimplementing backup/restore logic.

**Rationale**:
- Sastre is official, maintained, and comprehensive
- No need to reimplement complex logic
- Handles all SD-WAN versions correctly
- Supports templates, policies, config-groups, MRF regions

**Consequences**:
- Positive: Reliable and maintained
- Positive: Feature-complete
- Positive: Less code to maintain
- Negative: Dependency on external tool
- Negative: Must stay compatible with sastre API changes

**Alternatives Considered**:
1. **Reimplement backup/restore**: Massive effort, error-prone
2. **Use sastre CLI via subprocess**: Less flexible, harder to integrate

---

## ADR-008: Catalystwan for vManage API

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Need to interact with vManage REST API for device operations.

**Decision**: Use catalystwan SDK for all vManage API interactions.

**Rationale**:
- Official Cisco SDK (cisco-open GitHub)
- Type-safe and well-structured
- Handles authentication and session management
- Active maintenance

**Consequences**:
- Positive: Type hints and IDE support
- Positive: Handles API complexity
- Positive: Session management built-in
- Negative: Dependency on external SDK
- Negative: Must track API changes

**Alternatives Considered**:
1. **Direct REST API calls**: More brittle, no type safety
2. **vmanage_client**: Older, less maintained
3. **Custom API wrapper**: Reinventing the wheel

---

## ADR-009: Pydantic V2 for Validation

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Need to validate device inventory input and provide good error messages.

**Decision**: Use Pydantic v2 for all data validation and models.

**Rationale**:
- Excellent validation with clear error messages
- Type safety
- Built-in serialization (YAML/JSON)
- Performance (v2 is much faster)
- Good documentation

**Consequences**:
- Positive: Robust validation
- Positive: Great error messages
- Positive: Type safety
- Negative: Requires Python 3.9+ (acceptable)

**Alternatives Considered**:
1. **Manual validation**: Error-prone, poor error messages
2. **Dataclasses + validators**: More verbose, less features
3. **Marshmallow**: Less type-safe, older

---

## ADR-010: Click + Rich for CLI

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Need a user-friendly CLI with good output formatting.

**Decision**: Use Click for CLI framework and Rich for formatted output.

**Rationale**:
- Click: Industry standard, great UX, good docs
- Rich: Beautiful terminal output, progress bars, tables
- Both well-maintained and widely used
- Good integration

**Consequences**:
- Positive: Professional CLI UX
- Positive: Good error messages and help
- Positive: Easy to extend
- Negative: Two dependencies (but both valuable)

**Alternatives Considered**:
1. **argparse**: More verbose, less user-friendly
2. **Typer**: Good but less mature than Click
3. **Plain print**: Poor UX, no formatting

---

## ADR-011: Library-First Design

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Tool could be designed as CLI-first or library-first.

**Decision**: Design as a library with optional CLI convenience layer.

**Rationale**:
- Maximum flexibility for users
- Can be imported and used programmatically
- Easy to integrate into other tools
- CLI is just a thin wrapper

**Consequences**:
- Positive: Flexible for all use cases
- Positive: Programmatic access
- Positive: CI/CD friendly
- Negative: More design consideration (but worth it)

**Alternatives Considered**:
1. **CLI-only (like reference tool)**: Inflexible
2. **CLI with --library-mode flag**: Awkward

---

## ADR-012: Python 3.9+ Minimum Version

**Date**: 2025-10-07
**Status**: Accepted

**Context**: Need to choose minimum Python version.

**Decision**: Require Python 3.9 or higher.

**Rationale**:
- Pydantic v2 requires 3.8+
- Type hints improvements in 3.9 (list[str] vs List[str])
- 3.9 is widely available (released 2020)
- Enterprise systems usually have 3.9+

**Consequences**:
- Positive: Modern Python features
- Positive: Better type hints
- Negative: Excludes systems stuck on 3.8 or older (rare)

**Alternatives Considered**:
1. **Python 3.8**: Missing some type hint improvements
2. **Python 3.10+**: Too restrictive, excludes many systems

---

## Future Decisions to Document

As we continue development, document decisions about:
- Certificate management approach (custom CA vs built-in)
- Edge onboarding implementation details
- Containerlab parser implementation
- Testing strategy
- CI/CD integration approach
- Multi-tenancy support (if needed)
- Version management strategy
