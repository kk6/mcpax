# Project Structure

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

## Design Principles

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
mcpax list [--type TYPE] [--json]       # List registered projects (includes install status/filters)
mcpax search <query> [OPTIONS]          # Search Modrinth
  --type/-t TYPE                        #   Filter by type (mod/modpack/shader/resourcepack)
  --limit/-l N                          #   Number of results (default: 10)
  --json                                #   Output in JSON format
mcpax install [--all]                   # Install projects
mcpax update [OPTIONS]                  # Check/apply updates
  --check/-c                            #   Check for updates without applying them
  --yes/-y                              #   Skip confirmation prompts
```

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
