"""CLI command callbacks."""

from mcpax.cli.commands.add import add
from mcpax.cli.commands.config import config_list, get, path, set
from mcpax.cli.commands.init import init
from mcpax.cli.commands.install import install
from mcpax.cli.commands.list import list_projects
from mcpax.cli.commands.remove import remove
from mcpax.cli.commands.search import search
from mcpax.cli.commands.tui import tui
from mcpax.cli.commands.update import update

__all__ = [
    "add",
    "config_list",
    "get",
    "init",
    "install",
    "list_projects",
    "path",
    "remove",
    "search",
    "set",
    "tui",
    "update",
]

APP_COMMANDS = (init, add, remove, search, install, update, tui)
CONFIG_COMMANDS = (path, get, set)
