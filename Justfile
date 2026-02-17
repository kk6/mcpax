# mcpax development tasks

set shell := ["bash", "-euo", "pipefail", "-c"]

# Show all available recipes
default:
    @just --list --unsorted

# ─── Environment ──────────────────────────────────────────────────────────────

# Install development dependencies
[group('env')]
sync:
    uv sync

# Install all dependencies (including extras)
[group('env')]
sync-all:
    uv sync --all-extras

# Setup development environment (sync + pre-commit)
[group('env')]
setup: sync-all
    uv run pre-commit install

# ─── Development ──────────────────────────────────────────────────────────────

# Format code
[group('dev')]
fmt:
    uv run ruff format src tests

# Lint code (auto-fix)
[group('dev')]
lint:
    uv run ruff check src tests --fix

# Type check
[group('dev')]
typecheck:
    uv run ty check src

# Run tests (pass args: just test -v)
[group('dev')]
test *args:
    uv run pytest {{ args }}

# Run all quality checks (format, lint, typecheck, test)
[group('dev')]
check: fmt lint typecheck test

# Generate HTML coverage report
[group('dev')]
cov:
    uv run pytest --cov=src --cov-report=html
    @echo "Coverage report: htmlcov/index.html"

# ─── CI ───────────────────────────────────────────────────────────────────────

# Check code formatting (no fix)
[group('ci')]
ci-fmt:
    uv run ruff format --check src tests

# Lint code (no fix)
[group('ci')]
ci-lint:
    uv run ruff check src tests

# Check for Japanese characters in source code
[group('ci')]
ci-japanese:
    find src tests -type f -name "*.py" -not -path "*/.*" -exec ./scripts/check_no_japanese.sh {} +

# Run all CI checks (mirrors GitHub Actions)
[group('ci')]
ci: ci-japanese ci-fmt ci-lint typecheck test

# Run GitHub Actions locally with act (pass args: just act -j lint)
[group('ci')]
act *args:
    act {{ args }}

# ─── Application ──────────────────────────────────────────────────────────────

# Run mcpax CLI (pass args: just run --help)
[group('app')]
run *args:
    uv run mcpax {{ args }}

# Run mcpax TUI
[group('app')]
tui:
    uv run mcpax tui
