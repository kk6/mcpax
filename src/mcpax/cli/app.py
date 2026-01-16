"""Typer CLI application."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mcpax import __version__
from mcpax.core.api import ModrinthClient
from mcpax.core.config import (
    generate_config,
    generate_projects,
    get_config_dir,
    get_default_config_path,
    get_default_projects_path,
    load_config,
    load_projects,
    save_projects,
)
from mcpax.core.exceptions import APIError, ProjectNotFoundError
from mcpax.core.manager import ProjectManager
from mcpax.core.models import Loader, ModrinthProject, ProjectConfig, ReleaseChannel

app = typer.Typer(
    name="mcpax",
    help="Minecraft MOD/Shader/Resource Pack manager via Modrinth API",
    no_args_is_help=True,
)

# Constants
DEFAULT_MINECRAFT_VERSION = "1.21.4"
DEFAULT_MINECRAFT_DIR = Path("~/.minecraft")
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
        loader = Loader.FABRIC
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
                loader = Loader(loader_str.lower())
                break
            except ValueError:
                console.print(
                    "[red]無効なローダーです。"
                    "fabric, forge, neoforge, quilt "
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
            loader=loader,
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


@app.command()
def status() -> None:
    """Show installation status."""
    typer.echo("No projects configured yet. Run 'mcpax init' to get started.")


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
    )

    # Add to list and save
    projects.append(project_config)
    save_projects(projects)

    # Show success message
    project_type_str = project.project_type.value
    console.print(
        f"✓ {project.title} ({project_type_str}) を追加しました", style="green"
    )


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
