# ORBIT Development Workflow

This document defines the development process, validation criteria, and workflow to ensure ORBIT stays true to its goals.

## Core Principles

Before any implementation decision, validate against these principles:

1. **Tool-Agnostic**: Works with device info from ANY source
2. **vManage-Side Only**: Handles onboarding after devices discover vBond
3. **Simple & Clean**: No unnecessary abstractions, proper exceptions, optional logging
4. **CI/CD First**: Designed for automated pipelines
5. **Library First**: CLI is optional convenience layer

## Development Process

### 1. Before Starting a Feature

**Ask:**
- Does this align with core principles?
- Is this solving a real problem or adding complexity?
- Can this be done simpler?
- Does this maintain tool-agnostic design?

**Document in DECISIONS.md:**
- What problem does this solve?
- What alternatives were considered?
- Why was this approach chosen?

### 2. Implementation Approach

**Order of Operations:**
```
1. Design → Document in DECISIONS.md
2. Write tests (if applicable)
3. Implement
4. Document (docstrings + examples)
5. Update TODO.md progress
6. Validate against checklist
7. Commit
```

**Module Completion Criteria:**
- [ ] Core functionality works
- [ ] Docstrings for all public APIs
- [ ] Type hints complete
- [ ] Example usage in docstring or examples/
- [ ] Error handling with proper exceptions
- [ ] Logging at appropriate levels (optional for users)
- [ ] Updated TODO.md

### 3. Testing Strategy

**Unit Tests (Required):**
- Mock external APIs (catalystwan, sastre)
- Test business logic in isolation
- Test error conditions

**Integration Tests (Future):**
- Test against real/mock vManage
- End-to-end workflows

**Manual Testing Checklist:**
- Test with example device inventory
- Verify error messages are helpful
- Check logging output at different verbosity levels

### 4. Documentation Requirements

**Code Documentation:**
- Module docstrings explaining purpose
- Class docstrings with usage examples
- Function docstrings with Args/Returns/Raises
- Type hints for all parameters and returns

**User Documentation:**
- README.md for quick start
- claude.md for architecture and context
- Examples in examples/ directory
- DECISIONS.md for architectural choices

## Git Workflow

### Branch Strategy

```
main (stable)
  └─ feature/[feature-name]  (development)
```

**Branches:**
- `main`: Stable, working code
- `feature/*`: Feature development
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

### Commit Message Format

```
<type>: <short summary>

<optional detailed description>

<optional footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation only
- `test`: Tests only
- `chore`: Maintenance (dependencies, etc.)

**Examples:**
```
feat: implement controller onboarding with credential fallback

- Try default 'admin' password first
- Fallback to custom password
- Skip already onboarded devices
- Return list of device UUIDs

Closes #12
```

```
fix: handle missing certificate status in device check

Device readiness check now handles missing certificate-status
field gracefully by treating it as not ready.
```

### When to Commit

**Commit when:**
- A logical unit of work is complete
- All tests pass (when we have tests)
- Code is documented
- Validation checklist passes

**Don't commit:**
- Broken code
- Work in progress (use branches)
- Debug code or commented-out blocks
- Secrets or credentials

## Validation Checklist

### Before Implementing

- [ ] Reviewed against core principles
- [ ] Checked for existing solutions
- [ ] Documented decision in DECISIONS.md
- [ ] Updated TODO.md with task breakdown

### Before Committing

**Code Quality:**
- [ ] No sys.exit() calls (use exceptions)
- [ ] No forced logging (all logging optional)
- [ ] Proper exception handling
- [ ] Type hints present
- [ ] No hardcoded values that should be configurable

**Documentation:**
- [ ] Docstrings complete
- [ ] Type hints accurate
- [ ] Examples provided (if public API)
- [ ] DECISIONS.md updated (if architectural change)
- [ ] TODO.md updated

**Testing:**
- [ ] Manual testing completed
- [ ] Error cases tested
- [ ] Edge cases considered

**Integration:**
- [ ] Changes work with existing code
- [ ] No breaking changes to public API (or documented)
- [ ] Dependencies are minimal and justified

### Before Release

- [ ] All TODO.md tasks for milestone complete
- [ ] README.md accurate and up to date
- [ ] Examples work
- [ ] No critical bugs
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml

## Decision Making Process

### When to Deviate from Plan

**Valid Reasons:**
1. Technical impossibility discovered
2. Simpler solution found
3. External dependencies changed
4. User requirements clarified

**Process:**
1. Identify deviation and reason
2. Document in DECISIONS.md
3. Update affected documentation
4. Update TODO.md if needed
5. Notify team/stakeholders (if applicable)

### Major vs Minor Decisions

**Major Decisions** (require DECISIONS.md entry):
- Architectural changes
- Scope changes
- API design
- Dependency additions
- Breaking changes

**Minor Decisions** (commit message sufficient):
- Implementation details
- Code organization
- Variable naming
- Internal refactoring

## Code Standards

### Python Style

- **Line length**: 100 characters
- **Formatting**: Black
- **Linting**: Ruff
- **Type checking**: mypy (strict mode)

### Naming Conventions

- **Classes**: `PascalCase`
- **Functions/methods**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`
- **Type variables**: `T`, `K`, `V` or descriptive

### Error Handling

**Always:**
- Use custom exceptions from `exceptions.py`
- Raise exceptions, never sys.exit()
- Provide helpful error messages
- Log errors appropriately

**Example:**
```python
try:
    result = risky_operation()
except SomeError as e:
    logger.error(f"Operation failed: {e}")
    raise OnboardingError(f"Failed to onboard device: {e}") from e
```

### Logging Best Practices

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (recoverable issues)
- **ERROR**: Error messages (but execution continues)
- **Never force logging level** on users

## Module Implementation Checklist

When implementing a new module:

### 1. Planning Phase
- [ ] Purpose clearly defined
- [ ] Interface designed
- [ ] Dependencies identified
- [ ] Documented in DECISIONS.md

### 2. Implementation Phase
- [ ] Create module file
- [ ] Implement core functionality
- [ ] Add error handling
- [ ] Add logging (optional)
- [ ] Add type hints

### 3. Documentation Phase
- [ ] Module docstring
- [ ] Class docstrings
- [ ] Method docstrings
- [ ] Usage examples
- [ ] Update README.md if needed

### 4. Testing Phase
- [ ] Unit tests written
- [ ] Edge cases tested
- [ ] Error cases tested
- [ ] Manual testing completed

### 5. Integration Phase
- [ ] Integrate with existing code
- [ ] Update main orchestrator if needed
- [ ] Update CLI if needed
- [ ] Update examples

## Progress Tracking

### TODO.md Structure

```markdown
## Current Sprint/Phase
- [ ] Task 1
  - [ ] Subtask 1.1
  - [ ] Subtask 1.2
- [ ] Task 2

## Backlog
- [ ] Future task 1
- [ ] Future task 2

## Completed
- [x] Done task 1
- [x] Done task 2
```

### Status Updates

Update TODO.md:
- When starting a task: Add to "In Progress"
- When completing a task: Move to "Completed"
- When discovering new work: Add to "Backlog"
- When blocked: Add note with blocker info

## Review Process

### Self-Review Checklist

Before considering work complete:
- [ ] Read through all changed code
- [ ] Check for TODOs or FIXMEs
- [ ] Verify error messages are helpful
- [ ] Test error conditions
- [ ] Review against core principles
- [ ] Run through validation checklist

### Documentation Review

- [ ] claude.md reflects current state
- [ ] README.md is accurate
- [ ] DECISIONS.md is up to date
- [ ] Examples work
- [ ] Docstrings are clear

## Troubleshooting Process

When something doesn't work:

1. **Identify the Problem**
   - What is the expected behavior?
   - What is the actual behavior?
   - Can you reproduce it?

2. **Debug**
   - Add logging at DEBUG level
   - Check error messages
   - Review related code

3. **Fix**
   - Implement fix
   - Test fix
   - Add test to prevent regression (if applicable)

4. **Document**
   - Update docstrings if behavior unclear
   - Add to examples if common use case
   - Note in DECISIONS.md if architectural issue

## Release Checklist

When preparing for a release:

### Pre-Release
- [ ] All planned features complete
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Examples tested
- [ ] CHANGELOG.md updated
- [ ] Version bumped

### Release
- [ ] Tag release in git
- [ ] Build package
- [ ] Test installation
- [ ] Deploy (if applicable)

### Post-Release
- [ ] Update TODO.md for next milestone
- [ ] Document lessons learned
- [ ] Plan next sprint

## Continuous Improvement

This workflow is not set in stone. Update it when:
- Better practices are discovered
- Pain points are identified
- Tools change
- Team grows

Document workflow changes in DECISIONS.md.
