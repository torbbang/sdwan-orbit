# ORBIT - TODO Tracker

Quick reference checklist for implementation progress. See FRESH_START_PLAN.md for detailed tasks and WORKFLOW.md for process.

---

## ✅ Week 1: Foundation (COMPLETED)

### Project Setup
- [x] Create project structure (src/, tests/, examples/)
- [x] Create pyproject.toml with dependencies
- [x] Create .gitignore and README.md
- [x] Set up git repository
- [x] Create WORKFLOW.md
- [x] Create DECISIONS.md

### Core Models & Exceptions
- [x] Create exceptions.py with custom exception hierarchy
- [x] Create models.py with Pydantic schemas
  - [x] ManagerConfig
  - [x] ControllerConfig
  - [x] ValidatorConfig
  - [x] EdgeConfig (serial-based)
  - [x] DeviceInventory
- [x] Create examples/devices.yaml

### Session Management
- [x] Create session.py with SessionManager
- [x] Implement connection retry logic
- [x] Implement timeout handling
- [x] Context manager support

### Device Onboarding (Control Plane)
- [x] Create onboarding.py with DeviceOnboarder
- [x] Implement onboard_controllers()
  - [x] Credential fallback (default → custom)
  - [x] Skip existing devices
  - [x] Return device UUIDs
- [x] Implement onboard_validators()
- [x] Implement wait_for_onboarding()
  - [x] Poll device status
  - [x] Check reachability
  - [x] Check certificate status

### Backup & Restore
- [x] Create backup.py with ConfigurationManager
- [x] Implement backup() via sastre
  - [x] Templates, policies, config groups
  - [x] MRF regions/subregions (20.7+)
- [x] Implement restore() via sastre
  - [x] Restore templates and policies
  - [x] Restore MRF regions
  - [x] Optional template attachment

### Main Orchestrator
- [x] Create orbit.py with Orbit class
- [x] Implement from_file() factory
- [x] Implement from_dict() factory
- [x] Implement onboard() method
- [x] Implement backup() method
- [x] Implement restore() method
- [x] Context manager support

### CLI Interface
- [x] Create cli.py with Click commands
- [x] Implement onboard command
- [x] Implement backup command
- [x] Implement restore command
- [x] Rich output formatting
- [x] Verbosity levels (-v, -vv)

### Parsers (Placeholder)
- [x] Create parsers/__init__.py
- [x] Create parsers/containerlab.py stub
- [x] NotImplementedError with helpful message

---

## 🔄 Week 2: Edge Onboarding & Parsers (CURRENT)

### Edge Device Onboarding (Priority: CRITICAL)

**Research Phase:**
- [ ] Study catalystwan edge device APIs
  - [ ] How to query devices by serial number
  - [ ] How to accept/approve devices
  - [ ] How to check certificate status
  - [ ] How device lifecycle works in vManage

**Implementation:**
- [ ] Implement edge discovery by serial
  - [ ] Query device inventory
  - [ ] Match by serial number
  - [ ] Handle device not found error
- [ ] Implement certificate handling
  - [ ] Check if cert already installed
  - [ ] Install/sign certificate if needed
  - [ ] Wait for cert installation
- [ ] Implement core onboard_edges() method
  - [ ] Process each edge in list
  - [ ] Skip existing if requested
  - [ ] Wait for device reachability
  - [ ] Return list of UUIDs
- [ ] Implement attach_template()
  - [ ] Find template by name
  - [ ] Build variable mapping
  - [ ] Attach template to device
  - [ ] Wait for attachment complete
- [ ] Implement attach_config_group() (20.12+)
  - [ ] Detect vManage version
  - [ ] Find config-group by name
  - [ ] Associate device with config-group
  - [ ] Wait for sync complete
- [ ] Error handling
  - [ ] Device not found (helpful message with serial)
  - [ ] Template not found
  - [ ] Variable validation errors
  - [ ] Certificate errors

**Testing:**
- [ ] Manual test with real/mock vManage
- [ ] Test template attachment
- [ ] Test config-group attachment
- [ ] Test error conditions
- [ ] Verify skip existing works

**Documentation:**
- [ ] Complete docstrings
- [ ] Add usage examples
- [ ] Update examples/devices.yaml with comments
- [ ] Document template variable requirements

### Containerlab Parser

**Research:**
- [ ] Run `containerlab inspect` to understand output
- [ ] Identify how SD-WAN devices are labeled
- [ ] Find where serial numbers are stored
- [ ] Determine node type detection strategy

**Implementation:**
- [ ] Implement parse_containerlab()
  - [ ] Run containerlab inspect subprocess
  - [ ] Parse JSON output
  - [ ] Extract device information
  - [ ] Map to DeviceInventory
- [ ] Implement Orbit.from_containerlab()
- [ ] Add CLI support: --from-containerlab flag
- [ ] Error handling
  - [ ] containerlab not installed
  - [ ] Lab not found
  - [ ] JSON parse errors
  - [ ] Missing required information

**Testing:**
- [ ] Create test containerlab topology
- [ ] Test parser with real containerlab output
- [ ] Test error conditions

**Documentation:**
- [ ] Document containerlab integration
- [ ] Add containerlab example
- [ ] Document limitations

### Testing & Quality

**Unit Tests:**
- [ ] Test SessionManager retry logic
- [ ] Test onboarding credential fallback
- [ ] Test skip existing logic
- [ ] Test edge onboarding (mocked)
- [ ] Test backup/restore (mocked)
- [ ] Test Pydantic validation

**Documentation:**
- [ ] Verify all docstrings complete
- [ ] Update README with edge examples
- [ ] Add troubleshooting section
- [ ] Document common errors

---

## 📋 Week 3: Polish & Optionals (BACKLOG)

### Optional: Certificate Management

**Decision Point:** Do we need custom CA support?

If YES:
- [ ] Create certificates.py
- [ ] Implement CertificateManager
- [ ] Load CA cert and key
- [ ] Sign CSRs
- [ ] Batch signing (parallel)
- [ ] Add to onboarding flow
- [ ] Document certificate setup

If NO:
- [ ] Document using vManage's built-in CA
- [ ] Update architecture docs

### Optional: Additional Parsers

**CML Parser (if needed):**
- [ ] Research CML topology export format
- [ ] Implement parse_cml()
- [ ] Add Orbit.from_cml()
- [ ] CLI support
- [ ] Documentation

**Terraform State Parser (if needed):**
- [ ] Research Terraform state format for SD-WAN
- [ ] Implement parse_terraform()
- [ ] Add Orbit.from_terraform()
- [ ] CLI support
- [ ] Documentation

### Optional: CI/CD Helpers

- [ ] Create ci.py module
- [ ] Implement deploy_and_wait()
- [ ] Implement wait_for_healthy()
  - [ ] Check control connections
  - [ ] Check BFD sessions
  - [ ] Check reachability
- [ ] Implement export_test_data()
- [ ] Implement cleanup()
- [ ] Document CI/CD integration

### Testing

- [ ] Increase unit test coverage to >80%
- [ ] Add integration tests (requires test vManage)
- [ ] Add pytest fixtures
- [ ] Add mocks for catalystwan/sastre
- [ ] Document testing approach

### CI/CD Examples

- [ ] Create .gitlab-ci.yml example
- [ ] Create .github/workflows example
- [ ] Document CI/CD patterns
- [ ] Add example test suite

### Documentation

- [ ] Write getting started tutorial
- [ ] Document common use cases
- [ ] Create troubleshooting guide
- [ ] Write migration guide from old tool
- [ ] Add API reference (auto-generated)
- [ ] Add architecture diagrams

### Release Preparation

- [ ] Create CHANGELOG.md
- [ ] Version bump to 0.1.0
- [ ] Test installation from PyPI (test.pypi.org)
- [ ] Tag release
- [ ] Write release notes

---

## Future Enhancements

### Advanced Features
- [ ] Configuration drift detection
- [ ] Multi-manager support (deploy across regions)
- [ ] Parallel deployment optimization
- [ ] Template/policy library
- [ ] Automated rollback on failure
- [ ] Dry-run mode (show what would be done)

### Monitoring & Observability
- [ ] Export Prometheus metrics
- [ ] Health check endpoints
- [ ] Deployment status tracking
- [ ] Audit logging

### UI/UX
- [ ] Web UI for topology visualization
- [ ] Interactive device selection
- [ ] Progress bars for long operations
- [ ] Deployment history

---

## Decision Points to Resolve

See FRESH_START_PLAN.md "Open Questions" section.

Priority decisions needed:
1. **Certificate Management**: Custom CA or built-in?
2. **Template Variables**: How to validate? Fetch template schema?
3. **Version Handling**: How to handle version-specific features?
4. **Containerlab Detection**: How to identify device types?
5. **Error Recovery**: Support partial rollback?

Document decisions in DECISIONS.md.

---

## Current Sprint Focus

**Sprint Goal**: Complete MVP with edge onboarding

**This Week:**
1. Edge device onboarding implementation
2. Template and config-group attachment
3. Basic testing and validation
4. Documentation updates

**Next Week:**
1. Containerlab parser
2. Comprehensive testing
3. Polish and bug fixes
4. Release preparation

---

## Progress Summary

**Completed**: 50+ tasks (Week 1 foundation)
**In Progress**: Edge onboarding (Week 2)
**Remaining**: ~30 tasks for MVP

**Estimated Completion**: End of Week 2 for MVP

---

**See WORKFLOW.md for how to work on these tasks.**
**See DECISIONS.md for architectural decisions.**
**See FRESH_START_PLAN.md for detailed implementation guidance.**
