"""Typer CLI application."""

from typing import Annotated

import typer

from mcpax import __version__

app = typer.Typer(
    name="mcpax",
    help="Minecraft MOD/Shader/Resource Pack manager via Modrinth API",
    no_args_is_help=True,
)


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
def status() -> None:
    """Show installation status."""
    typer.echo("No projects configured yet. Run 'mcpax init' to get started.")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
