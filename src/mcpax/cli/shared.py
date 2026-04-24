"""Shared CLI constants and console."""

from pathlib import Path

from rich.console import Console

DEFAULT_MINECRAFT_VERSION = "1.21.4"
DEFAULT_MINECRAFT_DIR = Path("~/.minecraft")
VALID_PROJECT_TYPES = {"mod", "modpack", "shader", "resourcepack"}
VALID_STATUS_FILTERS = {"installed", "not-installed", "outdated"}
console = Console()
