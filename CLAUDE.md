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

## Issue Workflow

When instructed to work on a GitHub issue (e.g., "issue #X に着手", "work on issue #X"):
1. First, use `gh issue view X` to read the issue details
2. Then, use EnterPlanMode to create an implementation plan
3. After plan approval, proceed with implementation following TDD practices
