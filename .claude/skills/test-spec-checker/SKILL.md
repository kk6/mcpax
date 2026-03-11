---
name: test-spec-checker
description: >
  Audit test coverage as living specification by comparing implementation against test cases.
  Detects specification gaps (public APIs without tests), contradictions (tests asserting behavior
  that differs from implementation), stale tests (testing removed/changed code), and missing
  edge cases. Use this skill when the user asks to check test coverage, verify spec coverage,
  audit tests, find contradictions between tests and code, or ensure tests serve as reliable
  specification. Also trigger for phrases like "are my tests up to date", "do tests match the
  implementation", "spec coverage", "test audit", "仕様カバレッジ", "テストと実装の矛盾",
  "テストの網羅性". Supports scoped checks (e.g., "check CLI spec coverage", "audit TUI tests")
  as well as full-project audits.
---

# Test-as-Spec Checker

Tests are the primary specification and source of truth for this project. Documentation can drift,
but a passing test suite that covers the right behaviors is a living, verified spec. This skill
audits whether the test suite fulfills that role.

## Output Language

The report MUST be written entirely in Japanese. All section headers, descriptions, explanations,
and summaries should use Japanese. Only code identifiers (function names, file paths, enum values,
etc.) remain in their original English form.

## Philosophy

A good spec-test should answer: "If I only read the tests, would I understand what this code is
supposed to do?" If a public function has no test, its behavior is unspecified. If a test asserts
one thing but the code does another, one of them is wrong — and the skill should surface that
conflict so a human can decide which is the bug.

## Scope Resolution

The user may request a check at different granularities. Map their request to source/test paths:

| User says | Source scope | Test scope |
|-----------|-------------|------------|
| "全体" / "all" / no qualifier | `src/mcpax/` | `tests/` |
| "core" | `src/mcpax/core/` | `tests/unit/test_*.py` (excluding tui/) |
| "cli" | `src/mcpax/cli/` | `tests/unit/test_cli.py` |
| "tui" | `src/mcpax/tui/` | `tests/unit/tui/` |
| "models" / "api" / etc. | `src/mcpax/core/<module>.py` | `tests/unit/test_<module>.py` |
| specific file path | that file | corresponding test file |

If the scope is ambiguous, ask the user to clarify.

## Audit Process

Perform the following checks in order. Use subagents for parallelism where possible.

### Phase 1: Inventory

1. **Read source files** in scope — extract all public API surfaces:
   - Classes and their public methods (exclude `_private` and `__dunder__` except `__init__`)
   - Module-level functions
   - Enum members and their values
   - Pydantic model fields, validators, and computed properties
   - CLI commands and their parameters (for cli/app.py)
   - TUI screens, widgets, and their key bindings (for tui/)

2. **Read test files** in scope — extract all test targets:
   - What function/method/class each test exercises
   - What behavior each test asserts (from test name, docstring, and assertion)
   - Edge cases covered (error paths, boundary values, None/empty inputs)

### Phase 2: Gap Analysis

Compare the inventory to find:

#### 2a. Specification Gaps (Missing Tests)
Public APIs that have no corresponding test. Prioritize by risk:
- **Critical**: Functions that perform I/O (API calls, file operations, downloads)
- **High**: Functions with branching logic (if/match) or error handling
- **Medium**: Data transformations and validators
- **Low**: Simple property accessors, `__repr__`, trivial delegation

#### 2b. Edge Case Gaps
For tested functions, check whether these scenarios are covered:
- Error/exception paths (what happens when things fail?)
- Boundary values (empty lists, None, zero, max values)
- Invalid inputs at system boundaries
- Concurrent/async edge cases (for async functions)

### Phase 3: Contradiction Detection (Priority)

This is the most important check. For each tested function:

1. **Read the test assertions** — what behavior does the test expect?
2. **Read the implementation** — what does the code actually do?
3. **Compare** — look for these contradiction types:

| Contradiction Type | Example |
|-------------------|---------|
| **Return value mismatch** | Test expects `None` on not-found, but code raises an exception |
| **Side effect mismatch** | Test doesn't verify a file write that the implementation performs |
| **Parameter handling** | Test passes args in one form, but implementation signature changed |
| **Error behavior** | Test expects a specific exception, but code raises a different one or swallows it |
| **Default value drift** | Test hardcodes an old default that the implementation has since changed |
| **Enum/constant drift** | Test uses enum values that were renamed or removed |
| **Async behavior** | Test mocks sync behavior but implementation is async (or vice versa) |

For each potential contradiction found, verify it carefully before reporting. Read both the test
and implementation code thoroughly — some apparent contradictions are actually correct (e.g.,
the test may be testing a mock, not the real implementation).

### Phase 4: Staleness Check

Look for tests that may be outdated:
- Tests for functions/methods that no longer exist
- Tests referencing old parameter names or signatures
- Tests importing symbols that have been moved or renamed
- Test fixtures that no longer match the real data structures

## Report Format

Output the report in this structure:

```markdown
# Test-as-Spec Audit Report

**Scope**: [what was checked]
**Date**: [today's date]
**Summary**: [one-line overall assessment]

## Contradictions Found

> These require immediate attention — the test and implementation disagree.

### [Contradiction title]
- **Source**: `src/mcpax/path/file.py:NN` — `function_name()`
- **Test**: `tests/unit/test_file.py:NN` — `test_function_scenario()`
- **Issue**: [Clear description of the disagreement]
- **Test says**: [What the test asserts]
- **Code does**: [What the implementation actually does]
- **Suggested fix**: [Which side is likely correct, and what to change]

## Specification Gaps

> Public APIs without test coverage — their behavior is unspecified.

| Priority | Module | Function/Method | Reason |
|----------|--------|-----------------|--------|
| Critical | api.py | `retry_request()` | I/O with retry logic, untested |
| High | config.py | `validate_paths()` | Branching validation, untested |
| ... | ... | ... | ... |

## Edge Case Gaps

> Tested functions missing important scenarios.

| Function | Missing Scenario | Risk |
|----------|-----------------|------|
| `get_project()` | 500 error response | API may change error format |
| ... | ... | ... |

## Stale Tests

> Tests that may reference outdated code.

| Test | Issue |
|------|-------|
| `test_old_feature()` | Tests function `foo()` which was removed in commit X |
| ... | ... |

## Coverage Summary

| Category | Count |
|----------|-------|
| Public APIs in scope | NN |
| APIs with tests | NN |
| Spec coverage | NN% |
| Contradictions found | NN |
| Edge case gaps | NN |
| Stale tests | NN |
```

## Important Guidelines

- **Be precise about contradictions.** A false positive erodes trust in the report. When in doubt,
  note it as "potential contradiction — needs human review" rather than stating it definitively.
- **Read actual code, don't guess.** Always read both the test file and the source file before
  claiming a gap or contradiction. Never report based on file names or function names alone.
- **Include line numbers.** When referencing source code or test code, always include the line
  number (e.g., `src/mcpax/core/api.py:142`). This makes the report directly actionable — the
  reader can jump to the exact location. If a function spans multiple lines, reference the line
  where the function is defined.
- **Respect test intent.** Some tests deliberately test partial behavior (e.g., only the happy
  path). This is a gap, not a contradiction.
- **Consider mocks.** A test using `pytest-httpx` to mock HTTP responses is testing the client's
  handling of those responses, not the real API. This is intentional and correct.
- **Prioritize actionability.** The report should make it easy for the user to decide what to fix
  first. Contradictions > Critical gaps > High gaps > Edge cases > Stale tests.
