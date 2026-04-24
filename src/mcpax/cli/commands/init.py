from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from mcpax.cli.shared import (
    DEFAULT_MINECRAFT_DIR,
    DEFAULT_MINECRAFT_VERSION,
    console,
)
from mcpax.core.config import (
    generate_config,
    generate_projects,
    get_config_dir,
    get_default_config_path,
    get_default_projects_path,
)
from mcpax.core.models import (
    Loader,
)

logger = logging.getLogger(__name__)


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
                    "[red]Invalid mod loader. "
                    "Enter one of: fabric, forge, neoforge, quilt.[/red]"
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
                    "[red]Invalid shader loader. "
                    "Enter one of: iris, optifine, none.[/red]"
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
        filename = Path(e.filename).name if e.filename else str(e)
        console.print(
            f"[red]Error:[/red] {filename} already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1) from None
