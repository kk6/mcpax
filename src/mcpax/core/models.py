"""Data models for mcpax."""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class Loader(str, Enum):
    """Mod loader types."""

    FABRIC = "fabric"
    FORGE = "forge"
    NEOFORGE = "neoforge"
    QUILT = "quilt"


class ProjectType(str, Enum):
    """Project types on Modrinth."""

    MOD = "mod"
    SHADER = "shader"
    RESOURCEPACK = "resourcepack"


class ReleaseChannel(str, Enum):
    """Release channel types."""

    RELEASE = "release"
    BETA = "beta"
    ALPHA = "alpha"


class InstallStatus(str, Enum):
    """Installation status of a project."""

    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    OUTDATED = "outdated"
    NOT_COMPATIBLE = "not_compatible"


# Local data models


class AppConfig(BaseModel):
    """Application configuration from config.toml."""

    minecraft_version: str
    loader: Loader
    minecraft_dir: Path
    mods_dir: Path | None = None
    shaders_dir: Path | None = None
    resourcepacks_dir: Path | None = None
    max_concurrent_downloads: int = 5
    verify_hash: bool = True


class ProjectConfig(BaseModel):
    """Project configuration from projects.toml."""

    slug: str
    version: str | None = None
    channel: ReleaseChannel = ReleaseChannel.RELEASE


class InstalledFile(BaseModel):
    """Information about an installed file."""

    slug: str
    project_type: ProjectType
    filename: str
    version_id: str
    version_number: str
    sha512: str
    installed_at: datetime
    file_path: Path


# Modrinth API data models


class ModrinthProject(BaseModel):
    """Project information from Modrinth API."""

    id: str
    slug: str
    title: str
    description: str
    project_type: ProjectType
    downloads: int
    icon_url: str | None
    versions: list[str]


class ProjectFile(BaseModel):
    """Downloadable file information from Modrinth API."""

    url: str
    filename: str
    size: int
    sha512: str
    primary: bool


class ProjectVersion(BaseModel):
    """Version information from Modrinth API."""

    id: str
    project_id: str
    version_number: str
    version_type: ReleaseChannel
    game_versions: list[str]
    loaders: list[str]
    files: list[ProjectFile]
    date_published: datetime


class SearchHit(BaseModel):
    """A single search result from Modrinth API."""

    slug: str
    title: str
    description: str
    project_type: ProjectType
    downloads: int
    icon_url: str | None


class SearchResult(BaseModel):
    """Search results from Modrinth API."""

    hits: list[SearchHit]
    total_hits: int
    offset: int
    limit: int


# Internal data models


class UpdateCheckResult(BaseModel):
    """Result of checking for updates."""

    slug: str
    status: InstallStatus
    current_version: str | None
    current_file: InstalledFile | None
    latest_version: str | None
    latest_file: ProjectFile | None


class DownloadTask(BaseModel):
    """A download task."""

    url: str
    dest: Path
    expected_hash: str | None
    slug: str
    version_number: str


class DownloadResult(BaseModel):
    """Result of a download task."""

    task: DownloadTask
    success: bool
    file_path: Path | None
    error: str | None
