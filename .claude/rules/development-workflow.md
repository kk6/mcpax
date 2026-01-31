# Development Workflow

## Development Environment Setup

```bash
uv sync  # Install development dependencies
```

## TDD (t-wada style)

1. **Red**: Write a failing test
2. **Green**: Write minimal code to pass the test
3. **Refactor**: Refactor the code

Always write tests first. Tests must exist before writing implementation code.

## Code Quality

- Add type hints to all functions and methods
- `uv run ty check src` must pass without errors
- `uv run ruff check src` must pass without errors
- Code must be formatted with `uv run ruff format src`

## Pre-commit Checklist

```bash
uv run ruff format src tests
uv run ruff check src tests --fix
uv run ty check src
uv run pytest
```

## Testing Strategy

### Directory Structure
```
tests/
├── conftest.py             # Shared fixtures
├── unit/                   # Unit tests
│   ├── test_models.py
│   ├── test_config.py
│   └── test_api.py
├── integration/            # Integration tests
│   └── test_manager.py
└── fixtures/               # Test data
    ├── config.toml
    └── projects.toml
```

### Mocking Strategy
- Modrinth API: Mock with `pytest-httpx`
- Filesystem: Use `tmp_path` fixture
- Tests that hit actual API must be marked with `@pytest.mark.integration`
