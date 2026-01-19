"""Typer CLI application."""

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mcpax import __version__
from mcpax.core.api import ModrinthClient
from mcpax.core.cache import ApiCache
from mcpax.core.config import (
    CONFIG_KEY_MAP,
    generate_config,
    generate_projects,
    get_all_config_values,
    get_config_dir,
    get_config_value,
    get_default_config_path,
    get_default_projects_path,
    load_config,
    load_projects,
    save_projects,
    set_config_value,
)
from mcpax.core.exceptions import APIError, ProjectNotFoundError
from mcpax.core.manager import ProjectManager
from mcpax.core.models import (
    InstallStatus,
    Loader,
    ModrinthProject,
    ProjectConfig,
    ProjectType,
    ReleaseChannel,
    SearchHit,
    UpdateCheckResult,
    UpdateResult,
)

app = typer.Typer(
    name="mcpax",
    help="Minecraft MOD/Shader/Resource Pack manager via Modrinth API",
    no_args_is_help=True,
)

# Config subcommand group
config_app = typer.Typer(help="Manage configuration settings.")
app.add_typer(config_app, name="config")

# Constants
DEFAULT_MINECRAFT_VERSION = "1.21.4"
DEFAULT_MINECRAFT_DIR = Path("~/.minecraft")
VALID_PROJECT_TYPES = {"mod", "modpack", "shader", "resourcepack"}
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"mcpax {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Minecraft MOD/Shader/Resource Pack manager via Modrinth API."""


@app.command()
def init(
    non_interactive: Annotated[
        bool,
        typer.Option(
            "--non-interactive",
            "-y",
            help="Use default values without prompting.",
        ),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Overwrite existing configuration files.",
        ),
    ] = False,
) -> None:
    """Initialize configuration files (config.toml and projects.toml).

    Configuration files are created in XDG Base Directory compliant location:
    - $XDG_CONFIG_HOME/mcpax/ (if XDG_CONFIG_HOME is set)
    - ~/.config/mcpax/ (default)
    """
    # Get configuration values
    if non_interactive:
        minecraft_version = DEFAULT_MINECRAFT_VERSION
        mod_loader = Loader.FABRIC
        shader_loader: Loader | None = Loader.IRIS
        minecraft_dir = DEFAULT_MINECRAFT_DIR
    else:
        minecraft_version = typer.prompt(
            "Minecraft version", default=DEFAULT_MINECRAFT_VERSION
        )
        while True:
            loader_str = typer.prompt(
                "Mod loader (fabric/forge/neoforge/quilt)", default="fabric"
            )
            try:
                mod_loader = Loader(loader_str.lower())
                break
            except ValueError:
                console.print(
                    "[red]無効なローダーです。"
                    "fabric, forge, neoforge, quilt "
                    "のいずれかを入力してください。[/red]"
                )
        while True:
            shader_loader_str = typer.prompt(
                "Shader loader (iris/optifine/none)", default="iris"
            )
            if shader_loader_str.lower() in ("none", ""):
                shader_loader = None
                break
            try:
                shader_loader = Loader(shader_loader_str.lower())
                break
            except ValueError:
                console.print(
                    "[red]無効なシェーダーローダーです。"
                    "iris, optifine, none "
                    "のいずれかを入力してください。[/red]"
                )
        minecraft_dir_str = typer.prompt(
            "Minecraft directory", default=str(DEFAULT_MINECRAFT_DIR)
        )
        minecraft_dir = Path(minecraft_dir_str)

    # Generate config files
    try:
        config_path = generate_config(
            minecraft_version=minecraft_version,
            mod_loader=mod_loader,
            shader_loader=shader_loader,
            minecraft_dir=minecraft_dir,
            path=get_default_config_path(),
            force=force,
        )
        console.print(f"✓ Created {config_path}", style="green")

        projects_path = generate_projects(path=get_default_projects_path(), force=force)
        console.print(f"✓ Created {projects_path}", style="green")

        console.print("\n[bold]Initialization complete![/bold]")
        console.print(f"Configuration stored in: {get_config_dir()}")
        console.print("Run 'mcpax add <slug>' to add projects.")

    except FileExistsError as e:
        filename = Path(str(e).split(":", 1)[1].strip()).name
        console.print(
            f"[red]Error:[/red] {filename} already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1) from None


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


async def _search_projects(
    query: str,
    type_filter: ProjectType | None,
    limit: int,
) -> list[SearchHit]:
    """Search for projects with optional type filtering.

    Args:
        query: Search query string
        type_filter: Optional project type filter
        limit: Maximum number of results to return

    Returns:
        List of search hits

    Raises:
        APIError: For API errors
    """
    facets = None
    if type_filter is not None:
        facets = json.dumps([[f"project_type:{type_filter.value}"]])

    async with ModrinthClient() as client:
        if facets is None:
            result = await client.search(query, limit=limit)
        else:
            result = await client.search(query, limit=limit, facets=facets)

    return result.hits


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


@app.command()
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

    console.print(f"✓ '{slug}' を削除しました", style="green")


@app.command()
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
    console.print(
        f"✓ {project.title} ({project_type_str}) を追加しました", style="green"
    )


@app.command()
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
        async with ProjectManager(config) as manager:
            # Check updates
            updates = await manager.check_updates(target_projects)

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
            result = await manager.apply_updates(updates, backup=True)

            # Show results
            if result.successful:
                for slug_success in result.successful:
                    console.print(
                        f"✓ '{slug_success}' をインストールしました", style="green"
                    )

            if result.failed:
                for failed in result.failed:
                    console.print(
                        f"[red]Error:[/red] Failed to install "
                        f"'{failed.slug}': {failed.error}"
                    )

    asyncio.run(_install_projects())


@app.command(name="list")
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

    # Validate type filter
    if type_filter is not None and type_filter.lower() not in VALID_PROJECT_TYPES:
        console.print(
            f"[red]Error:[/red] Invalid type '{type_filter}'. "
            f"Must be one of: {', '.join(VALID_PROJECT_TYPES)}."
        )
        raise typer.Exit(code=1)

    # Validate status filter
    valid_statuses = {"installed", "not-installed", "outdated"}
    if status_filter is not None and status_filter.lower() not in valid_statuses:
        console.print(
            f"[red]Error:[/red] Invalid status '{status_filter}'. "
            f"Must be one of: {', '.join(valid_statuses)}."
        )
        raise typer.Exit(code=1)

    if no_update and status_filter is not None and status_filter.lower() == "outdated":
        console.print(
            "[red]Error:[/red] --status outdated is not supported with --no-update."
        )
        raise typer.Exit(code=1)

    if max_concurrency < 1:
        console.print("[red]Error:[/red] --max-concurrency must be a positive integer.")
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
            async with ProjectManager(config, api_client=client) as manager:
                # Get installation status
                if no_update:

                    async def _local_update(
                        project: ProjectConfig,
                    ) -> UpdateCheckResult:
                        installed = await manager.get_installed_file(project.slug)
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
                        )

                    updates = await asyncio.gather(
                        *(_local_update(project) for project in projects)
                    )
                else:
                    updates = await manager.check_updates(
                        projects,
                        max_concurrency=max_concurrency,
                    )

            # Fetch project types from API (bounded concurrency to avoid rate limits).
            semaphore = asyncio.Semaphore(max_concurrency)

            async def fetch_project(update: UpdateCheckResult) -> dict | None:
                async with semaphore:
                    try:
                        project = await client.get_project(update.slug)
                        return {
                            "slug": update.slug,
                            "title": project.title,
                            "type": project.project_type,
                            "status": update.status,
                            "current_version": update.current_version,
                            "latest_version": update.latest_version,
                        }
                    except (ProjectNotFoundError, APIError):
                        # If project cannot be fetched, skip it
                        return None

            results = await asyncio.gather(
                *(fetch_project(update) for update in updates)
            )
            project_info_list = [result for result in results if result is not None]

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
        json_data = [
            {
                "slug": p["slug"],
                "title": p["title"],
                "type": p["type"].value,
                "status": p["status"].value,
                "current_version": p["current_version"],
                "latest_version": p["latest_version"],
            }
            for p in project_info_list
        ]
        console.print(json.dumps(json_data, indent=2, ensure_ascii=False))
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


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search keyword")],
    type_filter: Annotated[
        str | None,
        typer.Option(
            "--type", "-t", help="Filter by type (mod/modpack/shader/resourcepack)"
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Number of results to show"),
    ] = 10,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """Search for projects on Modrinth.

    Example:
        mcpax search sodium
        mcpax search shader --type shader --limit 5
        mcpax search fabric --json
    """
    # Validate type filter
    project_type_filter: ProjectType | None = None
    if type_filter is not None:
        if type_filter.lower() not in VALID_PROJECT_TYPES:
            console.print(
                f"[red]Error:[/red] Invalid type '{type_filter}'. "
                f"Must be one of: {', '.join(VALID_PROJECT_TYPES)}."
            )
            raise typer.Exit(code=1)
        project_type_filter = ProjectType(type_filter.lower())

    # Search projects
    async def _do_search() -> list[SearchHit]:
        try:
            return await _search_projects(query, project_type_filter, limit)
        except APIError as e:
            console.print(f"[red]Error:[/red] API error: {e}")
            raise typer.Exit(code=1) from None

    hits = asyncio.run(_do_search())

    # Handle no results
    if not hits:
        if json_output:
            console.print("[]")
        else:
            console.print(f"No results found for '{query}'.")
        raise typer.Exit(code=0)

    # Output in JSON format
    if json_output:
        json_data = [
            {
                "slug": h.slug,
                "title": h.title,
                "description": h.description,
                "type": h.project_type.value,
                "downloads": h.downloads,
            }
            for h in hits
        ]
        console.print(json.dumps(json_data, indent=2, ensure_ascii=False))
        raise typer.Exit(code=0)

    # Standard output
    console.print(f"\nSearch results for '{query}':\n")
    for i, hit in enumerate(hits, start=1):
        type_str = hit.project_type.value
        downloads_formatted = f"{hit.downloads:,}"
        console.print(f"{i}. {hit.title} ({type_str})")
        console.print(f"   {hit.description}")
        console.print(f"   Downloads: {downloads_formatted}\n")

    console.print("Run 'mcpax add <slug>' to add a project.")


@app.command()
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

    # Check for updates
    console.print("Checking for updates...")

    async def _check_updates() -> list[UpdateCheckResult]:
        async with ProjectManager(config) as manager:
            return await manager.check_updates(projects)

    results = asyncio.run(_check_updates())

    # Group results by status
    grouped: dict[InstallStatus, list[UpdateCheckResult]] = defaultdict(list)
    for result in results:
        grouped[result.status].append(result)

    updates_available = (
        grouped[InstallStatus.OUTDATED] + grouped[InstallStatus.NOT_INSTALLED]
    )

    display_groups = [
        ("Updates available", updates_available, "updates"),
        ("Not compatible", grouped[InstallStatus.NOT_COMPATIBLE], "not_compatible"),
        ("Check failed", grouped[InstallStatus.CHECK_FAILED], "check_failed"),
        ("Up to date", grouped[InstallStatus.INSTALLED], "up_to_date"),
    ]

    # Display results
    for title, items, kind in display_groups:
        if not items:
            continue
        console.print(f"\n{title} ({len(items)}):")
        if kind == "updates":
            for result in items:
                current = result.current_version or "not installed"
                latest = result.latest_version or "unknown"
                arrow = f"{current} → {latest}"
                console.print(f"  {result.slug:<20} {arrow}")
            continue
        if kind == "up_to_date":
            slugs = ", ".join(r.slug for r in items)
            console.print(f"  {slugs}")
            continue
        note = "no compatible version" if kind == "not_compatible" else "check failed"
        for result in items:
            console.print(f"  {result.slug:<20} ({note})")

    # If check-only mode, exit here
    if check:
        if updates_available:
            console.print("\nRun 'mcpax update' to apply updates.")
        return

    # If no updates available, exit
    if not updates_available:
        console.print("\nAll projects are up to date.")
        return

    # Ask for confirmation unless --yes is specified
    if not yes:
        confirmed = typer.confirm("\nApply updates?")
        if not confirmed:
            console.print("Update cancelled.")
            return

    # Apply updates
    console.print("\nApplying updates...")

    async def _apply_updates() -> UpdateResult:
        async with ProjectManager(config) as manager:
            return await manager.apply_updates(results)

    update_result = asyncio.run(_apply_updates())

    # Display results
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


@config_app.command()
def path() -> None:
    """Show the path to the config file.

    Example:
        mcpax config path
    """
    config_path = get_default_config_path()
    console.print(str(config_path))


@config_app.command()
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

        value = get_config_value(key)
        if value is not None:
            console.print(str(value))
        # If value is None for a valid key, it means it's not set.
        # We exit gracefully without printing anything.
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None


@config_app.command(name="list")
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


@config_app.command()
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
        set_config_value(key, value)
        console.print(f"✓ Set {key} = {value}", style="green")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] config.toml not found. Run 'mcpax init' first."
        )
        raise typer.Exit(code=1) from None


@app.command()
def tui() -> None:
    """Launch the TUI interface."""
    try:
        from mcpax.tui import run_tui

        run_tui()
    except ImportError as e:
        console.print(
            "[red]Error:[/red] TUI dependencies not installed. "
            "Run 'uv pip install -e \".\\[tui]\"' to install them."
        )
        raise typer.Exit(1) from e


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
