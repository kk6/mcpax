"""TUI screens."""

from .detail import ProjectDetailScreen
from .install import InstallScreen
from .main import MainScreen
from .search import SearchScreen
from .settings import SettingsScreen
from .version_select import (
    VERSION_SELECT_CANCELLED,
    VERSION_SELECT_LATEST,
    VersionSelectScreen,
)

__all__ = [
    "MainScreen",
    "ProjectDetailScreen",
    "SearchScreen",
    "InstallScreen",
    "SettingsScreen",
    "VersionSelectScreen",
    "VERSION_SELECT_CANCELLED",
    "VERSION_SELECT_LATEST",
]
