from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Annotated

import typer

from mcpax.cli.shared import (
    console,
)
from mcpax.core.config import (
    get_default_config_path,
    load_config,
    load_projects,
)
from mcpax.core.manager import ProjectManager
from mcpax.core.models import (
    InstallStatus,
    UpdateCheckResult,
    UpdateResult,
)

logger = logging.getLogger(__name__)


def update(
    check: Annotated[
        bool,
        typer.Option("--check", "-c", help="Check for updates without applying them"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts"),
    ] = False,
) -> None:
    """Check for and apply updates to registered projects.

    Example:
        mcpax update --check
        mcpax update --yes
    """
    # Check if config.toml exists
    config_path = get_default_config_path()
    if not config_path.exists():
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1)

    # Load config
    try:
        config = load_config()
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None

    # Load projects
    try:
        projects = load_projects()
    except FileNotFoundError:
        console.print(
            "[yellow]Warning:[/yellow] projects.toml not found. No projects to update."
        )
        raise typer.Exit(code=0) from None

    if not projects:
        console.print("No projects to check.")
        return

    # Check for updates and apply if needed - single async context
    console.print("Checking for updates...")

    async def _update_flow() -> tuple[list[UpdateCheckResult], UpdateResult | None]:
        async with ProjectManager(config) as manager:
            # Check for updates
            results = await manager.check_updates(projects)

            # Group results by status
            grouped: dict[InstallStatus, list[UpdateCheckResult]] = defaultdict(list)
            for result in results:
                grouped[result.status].append(result)

            updates_available = (
                grouped[InstallStatus.OUTDATED] + grouped[InstallStatus.NOT_INSTALLED]
            )

            display_groups = [
                ("Updates available", updates_available, "updates"),
                (
                    "Not compatible",
                    grouped[InstallStatus.NOT_COMPATIBLE],
                    "not_compatible",
                ),
                ("Check failed", grouped[InstallStatus.CHECK_FAILED], "check_failed"),
                ("Up to date", grouped[InstallStatus.INSTALLED], "up_to_date"),
            ]

            # Display results (console.print is fast, non-blocking I/O acceptable)
            for title, items, kind in display_groups:
                if not items:
                    continue
                console.print(f"\n{title} ({len(items)}):")
                if kind == "updates":
                    for result in items:
                        current = result.current_version or "not installed"
                        latest = result.latest_version or "unknown"
                        arrow = f"{current} → {latest}"
                        pinned_marker = " [pinned]" if result.pinned else ""
                        console.print(f"  {result.slug:<20} {arrow}{pinned_marker}")
                    continue
                if kind == "up_to_date":
                    slugs = ", ".join(r.slug for r in items)
                    console.print(f"  {slugs}")
                    continue
                note = (
                    "no compatible version"
                    if kind == "not_compatible"
                    else "check failed"
                )
                for result in items:
                    console.print(f"  {result.slug:<20} ({note})")

            # If check-only mode, exit here
            if check:
                if updates_available:
                    console.print("\nRun 'mcpax update' to apply updates.")
                return results, None

            # If no updates available, exit
            if not updates_available:
                console.print("\nAll projects are up to date.")
                return results, None

            # Ask for confirmation unless --yes is specified
            if not yes:
                # Use asyncio.to_thread for blocking I/O (user input)
                confirmed = await asyncio.to_thread(typer.confirm, "\nApply updates?")
                if not confirmed:
                    console.print("Update cancelled.")
                    return results, None

            # Apply updates
            console.print("\nApplying updates...")
            return results, await manager.apply_updates(results)

    results, update_result = asyncio.run(_update_flow())

    # Display results if updates were applied
    if update_result is not None:
        if update_result.failed:
            console.print(
                f"\n[yellow]Updates completed with {len(update_result.failed)} "
                f"errors.[/yellow]"
            )
            for failed in update_result.failed:
                console.print(f"  [red]✗[/red] {failed.slug}: {failed.error}")
        else:
            updated_count = len(update_result.successful)
            console.print(
                f"\n[green]✓[/green] {updated_count} project(s) updated successfully."
            )
