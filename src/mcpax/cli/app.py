import typer

from mcpax import __version__
from mcpax.cli import commands

app = typer.Typer(
    name="mcpax",
    help="Minecraft MOD/Shader/Resource Pack manager via Modrinth API",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Manage configuration settings.")


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"mcpax {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Minecraft MOD/Shader/Resource Pack manager via Modrinth API."""


for command in commands.APP_COMMANDS:
    app.command()(command)

app.command(name="list")(commands.list_projects)
for command in commands.CONFIG_COMMANDS:
    config_app.command()(command)
config_app.command(name="list")(commands.config_list)
app.add_typer(config_app, name="config")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
