# mcpax

CLI tool for managing Minecraft MODs/Shaders/Resource Packs via Modrinth API.

## Meta Instructions

**Important**: This CLAUDE.md file should always be written in English for optimal Claude comprehension. Messages shown by AI chat assistants (e.g., Claude Code, Codex) to their users must be in Japanese. This rule applies to AI chat responses only and does not set the language for mcpax CLI/TUI output.

**Source Code Language Rule**: All user-facing strings in the source code (`src/` and `tests/`) MUST be written in **English only**. This includes CLI output, TUI labels/messages, error messages, log messages, button labels, dialog text, and test assertions for these strings. Never use Japanese or any other non-English language in source code strings.

## Project Overview

### Problem Statement
Automate the manual update process when managing approximately 30 Minecraft projects across multiple versions.

### Key Features
- Define managed projects in TOML configuration files
- Automatically fetch compatible versions via Modrinth API
- Secure downloads with SHA512 hash verification
- Automatic placement based on project type (mod/modpack/shader/resourcepack)

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.13+ |
| Package Manager | uv |
| Type Checker | ty |
| Linter/Formatter | ruff |
| Testing | pytest, pytest-asyncio, pytest-httpx |
| HTTP Client | httpx |
| CLI Framework | typer |
| Output Decoration | rich |
| TUI | textual |

## TUI Architecture

- Entry point: `mcpax tui` -> `mcpax.tui.run_tui()` -> `McpaxApp`
- App loads config from default paths; if missing/invalid, exits with an error message
- Screens:
  - `MainScreen`: project list + search input + status (bindings: quit/refresh/install/settings/detail)
  - `SearchScreen`: Modrinth search results; add selected project to `projects.toml`
  - `ProjectDetailScreen`: project detail modal with delete action
  - `InstallScreen`: apply updates with progress + summary
  - `SettingsScreen`: edit `config.toml` values
- Widgets: `ProjectTable`, `SearchInput`, `SearchResultTable`, `ProgressPanel`, `StatusBar`
- Core integration:
  - `ProjectManager` for update checks and installs
  - `ModrinthClient` for search
  - `core.config` for reading/writing config + projects
- Dependency: TUI is provided via optional extra `.[tui]` (Textual)

## Issue Workflow

When instructed to work on a GitHub issue (e.g., "issue #X に着手", "work on issue #X"):
1. First, use `gh issue view X` to read the issue details
2. Then, use EnterPlanMode to create an implementation plan
3. After plan approval, proceed with implementation following TDD practices
