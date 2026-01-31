"""TUI screens."""

from .detail import ProjectDetailScreen
from .install import InstallScreen
from .main import MainScreen
from .search import SearchScreen
from .settings import SettingsScreen

__all__ = [
    "MainScreen",
    "ProjectDetailScreen",
    "SearchScreen",
    "InstallScreen",
    "SettingsScreen",
]
