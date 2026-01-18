# mcpax

CLI tool for managing Minecraft MODs/Shaders/Resource Packs via Modrinth API.

## Meta Instructions

**Important**: This CLAUDE.md file should always be written in English for optimal Claude comprehension. However, all responses to the user should be in Japanese.

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
| TUI (Future) | textual |

## Development Workflow

### Development Environment Setup
```bash
uv sync  # Install development dependencies
```

### Issue Workflow
When instructed to work on a GitHub issue (e.g., "issue #X に着手", "work on issue #X"):
1. First, use `gh issue view X` to read the issue details
2. Then, use EnterPlanMode to create an implementation plan
3. After plan approval, proceed with implementation following TDD practices

### TDD (t-wada style)
1. **Red**: Write a failing test
2. **Green**: Write minimal code to pass the test
3. **Refactor**: Refactor the code

Always write tests first. Tests must exist before writing implementation code.

### Code Quality
- Add type hints to all functions and methods
- `ty check src` must pass without errors
- `ruff check src` must pass without errors
- Code must be formatted with `ruff format src`

### Pre-commit Checklist
```bash
uv run ruff format src tests
uv run ruff check src tests --fix
uv run ty check src
uv run pytest
```

### Version Control (jj)

This project's primary development uses **jj (Jujutsu)** for version control. While external contributors may use git, AI agents and the core development team should use jj.

#### Basic Workflow

1. **Create a bookmark for new work**:
   ```bash
   jj bookmark create feat/issue-XX-description
   ```

2. **Record changes with a commit message**:
   ```bash
   jj describe -m "type: description

   Detailed message here.

   Fixes #XX"
   ```

3. **Push to remote** (first time requires tracking):
   ```bash
   jj bookmark track feat/issue-XX-description --remote=origin
   jj git push
   ```

4. **After PR is merged, fetch and start new work**:
   ```bash
   jj git fetch
   jj new main
   ```

#### Common Commands

| Command | Description |
|---------|-------------|
| `jj status` | Show working copy status |
| `jj log` | Show commit history |
| `jj diff` | Show changes |
| `jj new main` | Create a new change on top of main |
| `jj bookmark list` | List all bookmarks |
| `jj git fetch` | Fetch from remote |
| `jj git push` | Push to remote |

## Architecture

```
src/mcpax/
├── __init__.py
├── core/                # Business logic layer
│   ├── __init__.py
│   ├── models.py        # Pydantic data models
│   ├── config.py        # Config file read/write
│   ├── api.py           # Modrinth API client
│   ├── downloader.py    # Download & hash verification
│   └── manager.py       # Project management orchestration
├── cli/                 # CLI interface
│   ├── __init__.py
│   └── app.py           # typer application
└── tui/                 # TUI interface (future)
    └── __init__.py
```

### Design Principles
- **Unix Philosophy**: Each command does one thing well
- **Dependency Direction**: CLI/TUI → core (no reverse dependencies allowed)
- **Testability**: External dependencies (API, filesystem) must be injectable

## Configuration Files

### config.toml
```toml
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
```

### projects.toml
```toml
[[projects]]
slug = "fabric-api"

[[projects]]
slug = "sodium"

[[projects]]
slug = "complementary-unbound"  # shader
```

## CLI Command Structure

```bash
mcpax init                              # Initialize configuration files
mcpax add <slug>                        # Add project
mcpax remove <slug>                     # Remove project
mcpax list [--type TYPE] [--json]       # List registered projects
mcpax search <query> [OPTIONS]          # Search Modrinth
  --type/-t TYPE                        #   Filter by type (mod/modpack/shader/resourcepack)
  --limit/-l N                          #   Number of results (default: 10)
  --json                                #   Output in JSON format
mcpax install [--all]                   # Install projects
mcpax update [OPTIONS]                  # Check/apply updates
  --check/-c                            #   Check for updates without applying them
  --yes/-y                              #   Skip confirmation prompts
mcpax status                            # Show installation status
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

## Implementation Priority

### Phase 1: Core (Current)
1. models.py - Data model definitions
2. config.py - Config file read/write
3. api.py - Modrinth API client
4. downloader.py - Download processing
5. manager.py - Orchestration

### Phase 2: CLI
6. cli/app.py - typer command implementation

### Phase 3: TUI (Future)
7. tui/ - TUI with textual

## Important Notes

### Modrinth API
- Base URL: `https://api.modrinth.com/v2`
- Rate Limit: 300 req/min
- User-Agent header required (format: project-name/version)

### Project Type Detection
Determined by `project_type` field in API response:
- `mod` → `mods/` directory
- `shader` → `shaderpacks/` directory
- `resourcepack` → `resourcepacks/` directory
- `modpack` → Not currently supported for installation (search only)

### Filename Handling
- Use `filename` from API response for downloaded files
- Slug and filename may not match
