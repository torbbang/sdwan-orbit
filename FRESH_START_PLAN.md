# ORBIT - Revised Implementation Plan

**Goal**: Build a clean, CI/CD-optimized SD-WAN onboarding tool that handles vManage-side device operations after devices have discovered vBond.

**Timeline**: 2-3 weeks

**Key Principles** (See DECISIONS.md for rationale):
- ✅ Tool-agnostic device input (YAML/JSON + optional parsers)
- ✅ vManage-side operations only (post-discovery)
- ✅ Library-first design with optional CLI
- ✅ Clean exceptions (no sys.exit())
- ✅ Optional logging (never forced)
- ✅ Use catalystwan and sastre (no reinventing)

---

## Implementation Status

### ✅ Week 1: Foundation (COMPLETED)

**Day 1-2: Project Setup**
- [x] Create project structure
- [x] Set up pyproject.toml with dependencies
- [x] Create exception hierarchy
- [x] Create Pydantic models for device inventory
- [x] Create examples/devices.yaml
- [x] Set up git repository
- [x] Create WORKFLOW.md and DECISIONS.md

**Day 2-3: Core Infrastructure**
- [x] Implement SessionManager with retry logic
- [x] Implement DeviceOnboarder (controllers and validators)
- [x] Credential fallback (try default, then custom)
- [x] Skip existing devices functionality
- [x] Wait for onboarding with device readiness checks

**Day 4-5: Backup/Restore**
- [x] Implement ConfigurationManager (sastre wrapper)
- [x] Backup with MRF regions support (20.7+)
- [x] Restore with MRF regions support
- [x] Version detection

**Day 5: Orchestration & CLI**
- [x] Implement main Orbit class
- [x] Context manager support
- [x] from_file() and from_dict() factory methods
- [x] Implement CLI with Click + Rich
- [x] onboard, backup, restore commands

---

## 🔄 Week 2: Edge Onboarding & Parsers (IN PROGRESS)

### Day 6-7: Edge Device Onboarding

**Priority**: Critical path for MVP

**Tasks**:
- [ ] Research catalystwan edge device APIs
  - Find devices by serial number in inventory
  - Accept/approve devices
  - Install/sign certificates
  - Check device status

- [ ] Implement edge onboarding workflow
  ```python
  def onboard_edges(self, edges: List[EdgeConfig]) -> List[str]:
      # 1. Find each edge in vManage by serial number
      # 2. Check if already onboarded (skip if requested)
      # 3. Accept device / install certificate if needed
      # 4. Wait for device to become reachable
      # 5. Attach template or config-group (separate method)
      # 6. Return list of UUIDs
  ```

- [ ] Implement template attachment
  ```python
  def attach_template(self, device_uuid: str, template_name: str, variables: dict):
      # 1. Get template ID by name
      # 2. Validate template variables
      # 3. Attach template with variables
      # 4. Wait for attachment to complete
  ```

- [ ] Implement config-group attachment (20.12+)
  ```python
  def attach_config_group(self, device_uuid: str, config_group_name: str):
      # 1. Detect vManage version
      # 2. Get config-group ID by name
      # 3. Associate device with config-group
      # 4. Wait for sync complete
  ```

- [ ] Handle edge onboarding errors gracefully
  - Device not found
  - Certificate errors
  - Template not found
  - Variable validation errors

- [ ] Test with example device inventory
- [ ] Document edge onboarding in docstrings

**Reference**: sdwan-lab-deployment-tool/catalyst_sdwan_lab/tasks/add.py:348-580

---

### Day 8-9: Containerlab Parser

**Priority**: High (common use case)

**Tasks**:
- [ ] Research containerlab inspect output format
  ```bash
  containerlab inspect --name <lab> --format json
  ```

- [ ] Implement parser
  ```python
  def parse_containerlab(
      lab_name: str,
      manager_url: str,
      manager_username: str,
      manager_password: str
  ) -> DeviceInventory:
      # 1. Run containerlab inspect
      # 2. Parse JSON output
      # 3. Identify device types (vsmart, vbond, edge) by labels/kind
      # 4. Extract IPs and serials
      # 5. Build DeviceInventory
  ```

- [ ] Add Orbit.from_containerlab() method
- [ ] Add CLI flag: `orbit onboard --from-containerlab <lab>`
- [ ] Create example containerlab topology for testing
- [ ] Document containerlab integration

**Open Questions**:
- How does containerlab label SD-WAN devices?
- Where are serial numbers stored?
- How to detect vsmart vs vbond vs edge?

---

### Day 10: Testing & Documentation

**Tasks**:
- [ ] Write unit tests for onboarding module
  - Mock catalystwan APIs
  - Test credential fallback
  - Test skip existing
  - Test error conditions

- [ ] Write unit tests for edge onboarding
  - Mock device inventory lookup
  - Mock template attachment
  - Test config-group attachment

- [ ] Manual integration testing checklist
  - [ ] Controller onboarding with fallback
  - [ ] Validator onboarding
  - [ ] Edge onboarding with template
  - [ ] Edge onboarding with config-group
  - [ ] Backup to directory
  - [ ] Restore from backup
  - [ ] Error handling (wrong credentials, device not found, etc.)

- [ ] Update README.md with complete examples
- [ ] Update claude.md with current state
- [ ] Verify all docstrings are complete

---

## 📋 Week 3: Polish & Additional Features (BACKLOG)

### Optional: Certificate Management

**Decision Needed**: Do we need custom CA support?

**If YES**:
- [ ] Implement CertificateManager class
- [ ] Sign CSRs with custom CA
- [ ] Batch certificate signing (parallel)
- [ ] Document certificate setup

**If NO**:
- [ ] Document using vManage's built-in CA
- [ ] Update examples accordingly

### Optional: Additional Parsers

- [ ] CML parser (if needed)
- [ ] Terraform state parser (if needed)
- [ ] Generic JSON parser

### Optional: CI/CD Helpers

- [ ] Create ci.py module
- [ ] deploy_and_wait() helper
- [ ] wait_for_healthy() with BFD checks
- [ ] export_test_data() for test validation
- [ ] cleanup() for teardown

### Testing

- [ ] Increase test coverage to >80%
- [ ] Add integration tests (requires test vManage)
- [ ] Add example CI/CD pipeline (.gitlab-ci.yml, .github/workflows)

### Documentation

- [ ] Write tutorial/walkthrough
- [ ] Document common use cases
- [ ] Troubleshooting guide
- [ ] Migration guide from old tool

---

## Key Differences from Original Plan

| Aspect | Original Plan | Actual Implementation | Rationale |
|--------|--------------|----------------------|-----------|
| **Topology** | Manage topology definitions | Accept device lists only | Topology already managed by other tools (see ADR-001) |
| **Discovery** | PnP from scratch | Post-vBond discovery only | Infrastructure tools handle discovery (see ADR-002) |
| **Edge Config** | UUID + separate variables | Serial + system_ip + site_id + values dict | Serial is the primary identifier (see ADR-003) |
| **Scope** | ~800 lines, 15 days | ~500 lines core, 10 days | Simpler scope = less code |

---

## Implementation Guidelines

Follow WORKFLOW.md for:
- Development process
- Validation checklists
- Commit standards
- Testing requirements

Document major decisions in DECISIONS.md.

---

## Current Priorities

### Must Have (MVP)
1. ✅ Controllers/validators onboarding
2. ✅ Backup/restore
3. 🔄 Edge device onboarding
4. 🔄 Template attachment
5. 🔄 Config-group attachment (20.12+)
6. 🔄 Containerlab parser

### Nice to Have
7. Certificate management (custom CA)
8. Additional parsers (CML, Terraform)
9. CI/CD helpers
10. Comprehensive tests

### Future
11. Configuration drift detection
12. Multi-manager support
13. Advanced health checks
14. Template/policy library

---

## Open Questions to Resolve

1. **Certificate Management**:
   - Use vManage's built-in CA or support custom CA?
   - Do controllers auto-generate certificates?

2. **Edge Template Variables**:
   - How to validate required template variables?
   - Should we fetch template definition from vManage?

3. **Version Detection**:
   - How to handle version-specific features gracefully?
   - Should we warn about unsupported versions?

4. **Containerlab Integration**:
   - What's the best way to identify device types?
   - Where are serial numbers stored in containerlab?

5. **Error Recovery**:
   - Should we support partial rollback?
   - How to handle partially onboarded topologies?

Document answers in DECISIONS.md as they're resolved.

---

## Success Criteria

At MVP completion:

- ✅ Clean Python library (no sys.exit)
- ✅ Proper exception handling
- ✅ Session management with retry
- ✅ Controllers/validators onboarding
- ✅ Backup/restore via sastre
- ✅ CLI with rich output
- ✅ Documentation and examples
- 🔄 Edge device onboarding (in progress)
- 🔄 Template/config-group attachment (pending)
- 🔄 Containerlab parser (pending)

For v1.0:

- All MVP features complete
- Comprehensive tests (>80% coverage)
- CI/CD integration examples
- Migration guide
- Troubleshooting docs

---

**See WORKFLOW.md for development process and validation checklists.**
