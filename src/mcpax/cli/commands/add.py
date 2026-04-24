from __future__ import annotations

import asyncio
import logging
from typing import Annotated

import typer

from mcpax.cli.shared import (
    console,
)
from mcpax.core.api import ModrinthClient
from mcpax.core.config import (
    get_default_config_path,
    load_projects,
    save_projects,
)
from mcpax.core.exceptions import APIError, ProjectNotFoundError
from mcpax.core.models import (
    INSTALLABLE_PROJECT_TYPES,
    ModrinthProject,
    ProjectConfig,
    ReleaseChannel,
)

logger = logging.getLogger(__name__)


async def _fetch_project(slug: str) -> ModrinthProject:
    """Fetch project information from Modrinth API.

    Args:
        slug: Project slug

    Returns:
        ModrinthProject instance

    Raises:
        ProjectNotFoundError: If project doesn't exist
        APIError: For other API errors
    """
    async with ModrinthClient() as client:
        return await client.get_project(slug)


def add(
    slug: Annotated[str, typer.Argument(help="Project slug on Modrinth")],
    version: Annotated[
        str | None,
        typer.Option("--version", "-v", help="Pin to specific version"),
    ] = None,
    channel: Annotated[
        str | None,
        typer.Option("--channel", "-c", help="Release channel (release/beta/alpha)"),
    ] = None,
) -> None:
    """Add a project to the managed list.

    Example:
        mcpax add sodium
        mcpax add fabric-api --version 0.92.0
        mcpax add iris --channel beta
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

    # Check if project already exists
    if any(p.slug == slug for p in projects):
        console.print(f"[red]Error:[/red] Project '{slug}' is already in the list.")
        raise typer.Exit(code=1)

    # Validate channel option
    release_channel = ReleaseChannel.RELEASE
    if channel is not None:
        try:
            release_channel = ReleaseChannel(channel.lower())
        except ValueError:
            console.print(
                f"[red]Error:[/red] Invalid channel '{channel}'. "
                f"Must be one of: release, beta, alpha."
            )
            raise typer.Exit(code=1) from None

    # Fetch project from Modrinth
    try:
        project = asyncio.run(_fetch_project(slug))
    except ProjectNotFoundError:
        console.print(f"[red]Error:[/red] Project '{slug}' not found on Modrinth.")
        raise typer.Exit(code=1) from None
    except APIError as e:
        console.print(f"[red]Error:[/red] API error: {e}")
        raise typer.Exit(code=1) from None

    # Check if project type is supported for installation
    if project.project_type not in INSTALLABLE_PROJECT_TYPES:
        console.print(
            f"[red]Error:[/red] Project type '{project.project_type.value}' "
            f"is not supported for installation. "
            f"Modpacks cannot be managed by mcpax."
        )
        raise typer.Exit(code=1)

    # Create project config
    project_config = ProjectConfig(
        slug=slug,
        version=version,
        channel=release_channel,
        project_type=project.project_type,
    )

    # Add to list and save
    projects.append(project_config)
    save_projects(projects)

    # Show success message
    project_type_str = project.project_type.value
    console.print(f"✓ Added {project.title} ({project_type_str})", style="green")
