from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Annotated

import typer

from mcpax.cli.formatters import _format_list_json, _validate_list_options
from mcpax.cli.shared import (
    console,
)
from mcpax.core.api import ModrinthClient
from mcpax.core.cache import ApiCache
from mcpax.core.config import (
    get_config_dir,
    load_config,
    load_projects,
)
from mcpax.core.exceptions import APIError, ProjectNotFoundError
from mcpax.core.models import (
    InstallStatus,
    ProjectConfig,
    ProjectType,
    UpdateCheckResult,
)
from mcpax.core.services import ProjectServices

logger = logging.getLogger(__name__)


def list_projects(
    type_filter: Annotated[
        str | None,
        typer.Option(
            "--type", "-t", help="Filter by type (mod/modpack/shader/resourcepack)"
        ),
    ] = None,
    status_filter: Annotated[
        str | None,
        typer.Option(
            "--status", "-s", help="Filter by status (installed/not-installed/outdated)"
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
    no_update: Annotated[
        bool,
        typer.Option(
            "--no-update",
            "--fast",
            help="Skip update checks; show installed/not-installed only.",
        ),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            help="Bypass API cache for this command.",
        ),
    ] = False,
    max_concurrency: Annotated[
        int,
        typer.Option(
            "--max-concurrency",
            help="Maximum concurrent API requests when fetching project info.",
        ),
    ] = 10,
) -> None:
    """List managed projects with their installation status.

    Example:
        mcpax list
        mcpax list --type mod
        mcpax list --status installed
        mcpax list --json
        mcpax list --no-update
        mcpax list --no-cache
        mcpax list --max-concurrency 5
    """
    # Load config
    try:
        config = load_config()
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None

    # Validate options
    validation_error = _validate_list_options(
        type_filter, status_filter, no_update, max_concurrency
    )
    if validation_error is not None:
        console.print(f"[red]Error:[/red] {validation_error}")
        raise typer.Exit(code=1)

    # Load existing projects
    try:
        projects = load_projects()
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] projects.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None

    # Early return if no projects
    if not projects:
        console.print(
            "No projects configured yet. Run 'mcpax add <slug>' to add projects."
        )
        raise typer.Exit(code=0)

    cache = None if no_cache else ApiCache(get_config_dir() / "api_cache.json")

    # Fetch installation status and project types
    async def _get_project_info(
        max_concurrency: int,
        no_update: bool,
    ) -> list[dict]:
        async with ModrinthClient(cache=cache) as client:
            async with ProjectServices(config, api_client=client) as services:
                # Get installation status
                if no_update:
                    # In no-update mode, we still need to fetch project info for titles
                    semaphore = asyncio.Semaphore(max_concurrency)

                    async def _local_update(
                        project: ProjectConfig,
                    ) -> UpdateCheckResult:
                        installed = await services.state_store.get_installed_file(
                            project.slug
                        )
                        # Fetch project info to get title
                        title: str | None = None
                        async with semaphore:
                            try:
                                project_info = await client.get_project(project.slug)
                                title = project_info.title
                            except (ProjectNotFoundError, APIError) as e:
                                logger.warning(
                                    "Failed to fetch title for project '%s': %s",
                                    project.slug,
                                    e,
                                )

                        if installed is None or not installed.file_path.exists():
                            return UpdateCheckResult(
                                slug=project.slug,
                                project_type=project.project_type,
                                status=InstallStatus.NOT_INSTALLED,
                                current_version=None,
                                current_file=None,
                                latest_version=None,
                                latest_version_id=None,
                                latest_file=None,
                                title=title,
                            )
                        return UpdateCheckResult(
                            slug=project.slug,
                            project_type=project.project_type,
                            status=InstallStatus.INSTALLED,
                            current_version=installed.version_number,
                            current_file=installed,
                            latest_version=None,
                            latest_version_id=None,
                            latest_file=None,
                            title=title,
                        )

                    updates = await asyncio.gather(
                        *(_local_update(project) for project in projects)
                    )
                else:
                    updates = await services.update_checker.check_updates(
                        projects,
                        max_concurrency=max_concurrency,
                    )

            # Convert UpdateCheckResult to dict, using title from the result
            project_info_list = [
                {
                    "slug": update.slug,
                    # Fallback to slug if title is None
                    "title": update.title or update.slug,
                    "type": update.project_type,
                    "status": update.status,
                    "current_version": update.current_version,
                    "latest_version": update.latest_version,
                }
                for update in updates
            ]

        return project_info_list

    project_info_list = asyncio.run(_get_project_info(max_concurrency, no_update))

    # Apply filters
    if type_filter is not None:
        project_info_list = [
            p for p in project_info_list if p["type"].value == type_filter.lower()
        ]

    if status_filter is not None:
        status_map = {
            "installed": InstallStatus.INSTALLED,
            "not-installed": InstallStatus.NOT_INSTALLED,
            "outdated": InstallStatus.OUTDATED,
        }
        target_status = status_map[status_filter.lower()]
        project_info_list = [
            p for p in project_info_list if p["status"] == target_status
        ]

    # Output in JSON format
    if json_output:
        console.print(_format_list_json(project_info_list))
        raise typer.Exit(code=0)

    # Group by project type
    grouped: dict[ProjectType, list[dict]] = defaultdict(list)
    for p in project_info_list:
        grouped[p["type"]].append(p)

    # Status icons
    status_icons = {
        InstallStatus.INSTALLED: "✓",
        InstallStatus.NOT_INSTALLED: "○",
        InstallStatus.OUTDATED: "⚠",
        InstallStatus.NOT_COMPATIBLE: "✗",
        InstallStatus.CHECK_FAILED: "?",
    }

    # Display grouped output
    for project_type in sorted(grouped.keys(), key=lambda x: x.value):
        if project_type == ProjectType.RESOURCEPACK:
            type_name = "Resource Pack"
        elif project_type == ProjectType.MODPACK:
            type_name = "Mod Pack"
        else:
            type_name = project_type.value.upper()
        count = len(grouped[project_type])
        console.print(f"\n[bold]{type_name} ({count}):[/bold]")

        for p in grouped[project_type]:
            icon = status_icons.get(p["status"], "?")
            status_str = p["status"].value.replace("_", " ")

            # Format version info
            if p["status"] == InstallStatus.OUTDATED:
                version_str = f"{p['current_version']} → {p['latest_version']}"
            elif p["status"] == InstallStatus.INSTALLED:
                version_str = p["current_version"] or "-"
            elif p["status"] == InstallStatus.NOT_INSTALLED:
                version_str = "-"
            else:
                version_str = "-"

            console.print(f"  {icon} {p['slug']:<30} {version_str:<20} {status_str}")
