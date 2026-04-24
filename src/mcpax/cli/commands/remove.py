from __future__ import annotations

import asyncio
import logging
from typing import Annotated

import typer

from mcpax.cli.shared import (
    console,
)
from mcpax.core.config import (
    get_default_config_path,
    load_config,
    load_projects,
    save_projects,
)
from mcpax.core.manager import ProjectManager

logger = logging.getLogger(__name__)


async def _remove_installed_file_with_manager(slug: str) -> tuple[bool, str | None]:
    """Remove installed file using ProjectManager.

    Args:
        slug: Project slug

    Returns:
        Tuple of (success, filename) where success is True if file was deleted,
        False if not installed, and filename is the deleted file name or None.
    """
    config = load_config()
    async with ProjectManager(config) as manager:
        return await manager.uninstall_project(slug)


def remove(
    slug: Annotated[str, typer.Argument(help="Project slug to remove")],
    delete_file: Annotated[
        bool,
        typer.Option("--delete-file", "-d", help="Also delete the installed file."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Remove a project from the managed list.

    Example:
        mcpax remove sodium
        mcpax remove sodium --yes
        mcpax remove sodium --delete-file
    """
    # Check if config.toml exists
    config_path = get_default_config_path()
    if not config_path.exists():
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1)

    # Load existing projects
    try:
        projects = load_projects()
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] projects.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None

    # Check if project exists in list
    project_to_remove = next((p for p in projects if p.slug == slug), None)
    if project_to_remove is None:
        console.print(f"[red]Error:[/red] Project '{slug}' not found in the list.")
        raise typer.Exit(code=1)

    # Confirmation prompt
    if not yes:
        confirmed = typer.confirm(f"Remove '{slug}' from the managed list?")
        if not confirmed:
            console.print("Cancelled.")
            raise typer.Exit(code=0)

    # Delete installed file if requested
    deleted_filename: str | None = None
    if delete_file:
        file_deleted, deleted_filename = asyncio.run(
            _remove_installed_file_with_manager(slug)
        )
        if file_deleted and deleted_filename:
            console.print(f"✓ Deleted {deleted_filename}", style="green")
        else:
            console.print(f"[yellow]Note:[/yellow] '{slug}' was not installed.")

    # Remove from list and save
    projects = [p for p in projects if p.slug != slug]
    save_projects(projects)

    console.print(f"✓ Removed '{slug}'", style="green")
