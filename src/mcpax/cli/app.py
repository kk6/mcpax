"""Typer CLI application."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from mcpax import __version__
from mcpax.core.config import (
    generate_config,
    generate_projects,
    get_config_dir,
    get_default_config_path,
    get_default_projects_path,
)
from mcpax.core.models import Loader

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


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
