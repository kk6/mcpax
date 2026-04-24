from __future__ import annotations

import json
import logging
from typing import Annotated

import typer

from mcpax.cli.shared import (
    console,
)
from mcpax.core.config import (
    CONFIG_KEY_MAP,
    ConfigAccessor,
    get_all_config_values,
    get_default_config_path,
)

logger = logging.getLogger(__name__)


def path() -> None:
    """Show the path to the config file.

    Example:
        mcpax config path
    """
    config_path = get_default_config_path()
    console.print(str(config_path))


def get(key: Annotated[str, typer.Argument(help="Config key in dot notation")]) -> None:
    """Get a config value by key.

    Example:
        mcpax config get minecraft.version
        mcpax config get download.max_concurrent
    """
    try:
        if key not in CONFIG_KEY_MAP:
            console.print(f"[red]Error:[/red] Unknown config key: '{key}'")
            raise typer.Exit(code=1)

        value = ConfigAccessor().get(key)
        if value is not None:
            console.print(str(value))
        # If value is None for a valid key, it means it's not set.
        # We exit gracefully without printing anything.
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None


def config_list(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """List all configuration settings.

    Example:
        mcpax config list
        mcpax config list --json
    """
    try:
        config_values = get_all_config_values()
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None

    if json_output:
        console.print(json.dumps(config_values, indent=2, ensure_ascii=False))
        return

    # Pretty print the configuration
    config_path = get_default_config_path()
    console.print(f"Configuration ({config_path}):\n")

    # Group by section
    sections: dict[str, list[tuple[str, str | int | bool | None]]] = {}
    for key, value in config_values.items():
        section, field = key.split(".", 1)
        if section not in sections:
            sections[section] = []
        sections[section].append((field, value))

    # Display each section
    for section_name in sorted(sections.keys()):
        console.print(f"\n\\[{section_name}]")
        for field, value in sections[section_name]:
            value_str = str(value) if value is not None else "(not set)"
            console.print(f"  {field:<20} = {value_str}")


def set(
    key: Annotated[str, typer.Argument(help="Config key in dot notation")],
    value: Annotated[str, typer.Argument(help="Value to set")],
) -> None:
    """Set a config value by key.

    Example:
        mcpax config set minecraft.version 1.21.5
        mcpax config set download.max_concurrent 10
        mcpax config set download.verify_hash true
    """
    try:
        ConfigAccessor().set(key, value)
        console.print(f"✓ Set {key} = {value}", style="green")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None
