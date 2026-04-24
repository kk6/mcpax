<!-- This file is for OpenAI Codex. See CLAUDE.md for the authoritative project guidelines. -->

# Repository Guidelines

## Project Structure & Module Organization
- `README.md` covers usage and development commands.
- `docs/` holds requirements, architecture, and API notes (see `docs/10_summary.md` for an index).
- Source code lives under `src/mcpax/` with `core/`, `cli/`, and `tui/` layers (documented in `CLAUDE.md`).
- `core/` contains the business logic and should stay independent of CLI/TUI presentation concerns.
- `core/version_resolver.py` owns Modrinth version compatibility and pinned-version resolution.
- `core/manager.py` is a compatibility facade. Keep new update/install logic in focused services such as `UpdateChecker`, `UpdateApplier`, `InstallPlanner`, `FileService`, and `StateStore`.
- Tests live under `tests/` with `unit/`, `integration/`, and `fixtures/` (also in `CLAUDE.md`).

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
- User-facing strings in `src/` and `tests/` must be English, matching `CLAUDE.md`.

## Refactoring Direction
- Prefer small Fowler-style refactorings over a large rewrite: Extract Function, Introduce Parameter Object, Split Phase, Extract Class, Move Function, and Rename for clarity.
- Use a lightweight Clean Architecture approach, not full DDD. Keep domain decisions in `core/`, and keep I/O details in adapters or infrastructure-style modules as they emerge.
- Preserve existing public behavior unless an issue explicitly asks for a behavior change.
- Keep `ModrinthClient` focused on HTTP/API concerns. Compatibility decisions should live in `VersionResolver` or similar core services.
- Keep update checking in `UpdateChecker` and update application in `UpdateApplier`.
- Keep `.mcpax-state.json` handling in `StateStore` and target directory / placement / backup / delete operations in `FileService`.
- CLI/TUI should call core use cases and render results; avoid putting update/install business rules in presentation code.

## Testing Guidelines
- Test stack: `pytest`, `pytest-asyncio`, `pytest-httpx`.
- Unit tests live in `tests/unit/`; integration tests in `tests/integration/`.
- Use `tmp_path` for filesystem work and `pytest-httpx` for API mocks.
- Mark networked tests with `@pytest.mark.integration` and keep them isolated.
- Add focused unit tests for each extracted core service before rewiring callers.
- For version resolution, use table-style tests covering Minecraft version, loader, shader loader, release channel, resource packs, and pinned versions.
- Test install planning separately from file download and state mutation.
- Test update application with download failure, partial success, backup, rollback, and state persistence cases.

## Version Control (git)

This project uses **git** for version control. Development happens on `main`; feature work lives on short-lived branches merged via PR.

- Create branches with `git switch -c feat/issue-XX-<short-description>` (see `.claude/rules/git-workflow.md` for naming conventions)
- Commit in small, reviewable units using Conventional Commits (`type: summary`)
- Keep branches current with `git fetch origin && git rebase origin/main`
- Users handle `git push` and PR creation; AI agents must not push directly
- After merge: `git switch main && git pull --ff-only && git branch -d <branch>`

## Commit & Pull Request Guidelines
- Commit history uses a `type: summary` pattern (example: `docs: add requirement definitions...`).
- Keep commits focused and include the test status in PR descriptions (e.g., `pytest`, `ruff check`).
- For doc-only changes, mention the updated files in the PR summary.

## Configuration Tips
- Local config files are `config.toml` and `projects.toml` (examples in `README.md`).
- State tracking is expected in `.mcpax-state.json` (see `docs/10_summary.md`).
