<!-- This file is for OpenAI Codex. See CLAUDE.md for the authoritative project guidelines. -->

# Repository Guidelines

## Project Structure & Module Organization
- `README.md` covers usage and development commands.
- `docs/` holds requirements, architecture, and API notes (see `docs/10_summary.md` for an index).
- Source code is planned under `src/mcpax/` with `core/`, `cli/`, and `tui/` layers (documented in `CLAUDE.md`).
- Tests are planned under `tests/` with `unit/`, `integration/`, and `fixtures/` (also in `CLAUDE.md`).

## Build, Test, and Development Commands
- `uv sync`: install development dependencies.
- `pytest`: run the test suite.
- `ty check src`: run type checks.
- `ruff check src`: run linting.
- `ruff format src`: apply formatting.
- Suggested pre-commit flow (from `CLAUDE.md`):
  - `uv run ruff format src tests`
  - `uv run ruff check src tests --fix`
  - `uv run ty check src`
  - `uv run pytest`

## Coding Style & Naming Conventions
- Python 3.13+ with type hints on all functions and methods.
- Use `ruff format` and `ruff check` to keep formatting and lint rules consistent.
- Follow the planned module boundaries: CLI/TUI depend on `core/` only (no reverse deps).

## Testing Guidelines
- Test stack: `pytest`, `pytest-asyncio`, `pytest-httpx`.
- Unit tests live in `tests/unit/`; integration tests in `tests/integration/`.
- Use `tmp_path` for filesystem work and `pytest-httpx` for API mocks.
- Mark networked tests with `@pytest.mark.integration` and keep them isolated.

## Commit & Pull Request Guidelines
- Commit history currently uses a `type: summary` pattern (example: `docs: add requirement definitions...`).
- Keep commits focused and include the test status in PR descriptions (e.g., `pytest`, `ruff check`).
- For doc-only changes, mention the updated files in the PR summary.

## Configuration Tips
- Local config files are `config.toml` and `projects.toml` (examples in `README.md`).
- State tracking is expected in `.mcpax-state.json` (see `docs/10_summary.md`).
