from __future__ import annotations

import asyncio
import logging
from typing import Annotated

import typer

from mcpax.cli.shared import (
    console,
)
from mcpax.core.config import (
    load_config,
    load_projects,
)
from mcpax.core.models import (
    InstallStatus,
)
from mcpax.core.services import ProjectServices

logger = logging.getLogger(__name__)


def install(
    slug: Annotated[str | None, typer.Argument(help="Project slug to install")] = None,
    all_projects: Annotated[
        bool,
        typer.Option("--all", help="Install all projects from the list."),
    ] = False,
) -> None:
    """Install projects from the managed list.

    Example:
        mcpax install sodium
        mcpax install --all
    """
    # Load config
    try:
        config = load_config()
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None

    # Load existing projects
    try:
        projects = load_projects()
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] projects.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None

    # Determine target projects
    if all_projects and slug is not None:
        console.print(
            "[red]Error:[/red] Cannot use --all with a specific project slug."
        )
        raise typer.Exit(code=1)
    if not all_projects and slug is None:
        console.print("[red]Error:[/red] Specify a project slug or use --all.")
        raise typer.Exit(code=1)

    target_projects = projects if all_projects else []

    if slug is not None:
        # Find the specific project
        project_config = next((p for p in projects if p.slug == slug), None)
        if project_config is None:
            console.print(f"[red]Error:[/red] Project '{slug}' not found in the list.")
            raise typer.Exit(code=1)
        target_projects = [project_config]

    if not target_projects:
        console.print("[yellow]No projects to install.[/yellow]")
        raise typer.Exit(code=0)

    # Install projects
    async def _install_projects() -> None:
        async with ProjectServices(config) as services:
            # Check updates
            updates = await services.update_checker.check_updates(target_projects)

            # Filter out compatible versions and show warnings
            for update in updates:
                if update.status == InstallStatus.NOT_COMPATIBLE:
                    console.print(
                        f"[yellow]Warning:[/yellow] No compatible version found "
                        f"for '{update.slug}'."
                    )
                elif update.status == InstallStatus.INSTALLED:
                    console.print(
                        f"[blue]Info:[/blue] '{update.slug}' is already up to date."
                    )

            # Apply updates
            result = await services.update_applier.apply_updates(updates, backup=True)

            # Show results
            if result.successful:
                for slug_success in result.successful:
                    console.print(f"✓ Installed '{slug_success}'", style="green")

            if result.failed:
                for failed in result.failed:
                    console.print(
                        f"[red]Error:[/red] Failed to install "
                        f"'{failed.slug}': {failed.error}"
                    )

    asyncio.run(_install_projects())
