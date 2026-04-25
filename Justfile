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

# Run tests in parallel (pass extra args: just test -v)
[group('dev')]
test *args:
    uv run pytest -n auto {{ args }}

# Run tests without parallelism for pdb/breakpoint() debugging
[group('dev')]
test-debug *args:
    uv run pytest -n0 {{ args }}

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

# ─── Release ──────────────────────────────────────────────────────────────────

# Show current version
[group('release')]
version:
    @grep '^version' pyproject.toml | cut -d'"' -f2

# Set version in pyproject.toml (e.g.: just bump 0.12.0)
[group('release')]
bump new_version:
    sed -i '' 's/^version = ".*"/version = "{{ new_version }}"/' pyproject.toml
    @echo "Version → {{ new_version }}"

# Build wheel and sdist into dist/
[group('release')]
build:
    uv build
    @echo "Artifacts in dist/"

# Create annotated git tag for the current version (run after committing the bump)
[group('release')]
tag:
    #!/usr/bin/env bash
    ver=$(grep '^version' pyproject.toml | cut -d'"' -f2)
    git tag -a "v${ver}" -m "Release v${ver}"
    echo "Tagged v${ver} — push with: git push origin v${ver}"

# Bump version, build, commit, and tag in one step (e.g.: just release 0.12.0)
[group('release')]
release new_version:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! git diff --quiet; then
        echo "Error: unstaged changes detected — commit or stash them first."
        exit 1
    fi
    sed -i '' 's/^version = ".*"/version = "{{ new_version }}"/' pyproject.toml
    echo "Version → {{ new_version }}"
    uv build
    echo "Artifacts in dist/"
    git add pyproject.toml
    if ! git diff --cached --quiet; then
        git commit -m "chore: bump version to {{ new_version }}"
    fi
    git tag -a "v{{ new_version }}" -m "Release v{{ new_version }}"
    echo "Done — push with: git push origin main --tags"

# ─── Application ──────────────────────────────────────────────────────────────

# Run mcpax CLI (pass args: just run --help)
[group('app')]
run *args:
    uv run mcpax {{ args }}

# Run mcpax TUI
[group('app')]
tui:
    uv run mcpax tui
