"""Configuration file handling."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomlkit

from .models import AppConfig, Loader, ProjectConfig, ReleaseChannel

# Constants
DEFAULT_CONFIG_PATH = Path("./config.toml")
DEFAULT_PROJECTS_PATH = Path("./projects.toml")
MINECRAFT_VERSION_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?(-\w+)?$")


@dataclass
class ValidationError:
    """A single validation error."""

    field: str
    message: str


class ConfigValidationError(Exception):
    """Configuration validation failed."""

    def __init__(self, message: str, errors: list[ValidationError] | None = None):
        super().__init__(message)
        self.errors = errors or []


def resolve_path(path: str | Path) -> Path:
    """Expand ~ and relative paths to absolute.

    Args:
        path: Path string or Path object

    Returns:
        Absolute Path object
    """
    return Path(path).expanduser().resolve()


def load_config(path: Path | None = None) -> AppConfig:
    """Load config.toml and return AppConfig.

    Args:
        path: Path to config file (defaults to ./config.toml)

    Returns:
        AppConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ConfigValidationError: If config is invalid
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigValidationError(f"Invalid TOML: {e}") from e

    # Extract values from TOML structure
    minecraft = data.get("minecraft", {})
    paths = data.get("paths", {})
    download = data.get("download", {})

    try:
        return AppConfig(
            minecraft_version=minecraft["version"],
            loader=Loader(minecraft["loader"]),
            minecraft_dir=resolve_path(paths["minecraft_dir"]),
            mods_dir=(
                resolve_path(paths["mods_dir"]) if paths.get("mods_dir") else None
            ),
            shaders_dir=(
                resolve_path(paths["shaders_dir"]) if paths.get("shaders_dir") else None
            ),
            resourcepacks_dir=(
                resolve_path(paths["resourcepacks_dir"])
                if paths.get("resourcepacks_dir")
                else None
            ),
            max_concurrent_downloads=download.get("max_concurrent", 5),
            verify_hash=download.get("verify_hash", True),
        )
    except KeyError as e:
        raise ConfigValidationError(f"Missing required field: {e}") from e
    except ValueError as e:
        raise ConfigValidationError(f"Invalid value: {e}") from e


def generate_config(
    minecraft_version: str,
    loader: Loader,
    minecraft_dir: Path,
    path: Path | None = None,
    force: bool = False,
) -> Path:
    """Generate config.toml.

    Args:
        minecraft_version: Minecraft version (e.g., "1.21.4")
        loader: Mod loader type
        minecraft_dir: Path to .minecraft directory
        path: Output path (defaults to ./config.toml)
        force: Overwrite existing file

    Returns:
        Path to created config file

    Raises:
        FileExistsError: If file exists and force=False
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if config_path.exists() and not force:
        raise FileExistsError(f"Config file already exists: {config_path}")

    doc = tomlkit.document()

    minecraft = tomlkit.table()
    minecraft.add("version", minecraft_version)
    minecraft.add("loader", loader.value)
    doc.add("minecraft", minecraft)

    paths = tomlkit.table()
    paths.add("minecraft_dir", str(minecraft_dir))
    doc.add("paths", paths)

    download = tomlkit.table()
    download.add("max_concurrent", 5)
    download.add("verify_hash", True)
    doc.add("download", download)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))

    return config_path


def load_projects(path: Path | None = None) -> list[ProjectConfig]:
    """Load projects.toml and return list of ProjectConfig.

    Args:
        path: Path to projects file (defaults to ./projects.toml)

    Returns:
        List of ProjectConfig instances

    Raises:
        FileNotFoundError: If projects file doesn't exist
        ConfigValidationError: If projects file is invalid
    """
    projects_path = path or DEFAULT_PROJECTS_PATH

    if not projects_path.exists():
        raise FileNotFoundError(f"Projects file not found: {projects_path}")

    try:
        with open(projects_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigValidationError(f"Invalid TOML: {e}") from e

    projects_data = data.get("projects", [])
    try:
        return [
            ProjectConfig(
                slug=p["slug"],
                version=p.get("version"),
                channel=ReleaseChannel(p.get("channel", "release")),
            )
            for p in projects_data
        ]
    except KeyError as e:
        raise ConfigValidationError(f"Missing required field in project: {e}") from e
    except ValueError as e:
        raise ConfigValidationError(f"Invalid value in project: {e}") from e


def generate_projects(path: Path | None = None, force: bool = False) -> Path:
    """Generate empty projects.toml.

    Args:
        path: Output path (defaults to ./projects.toml)
        force: Overwrite existing file

    Returns:
        Path to created projects file

    Raises:
        FileExistsError: If file exists and force=False
    """
    projects_path = path or DEFAULT_PROJECTS_PATH

    if projects_path.exists() and not force:
        raise FileExistsError(f"Projects file already exists: {projects_path}")

    doc = tomlkit.document()
    doc.add(tomlkit.comment("Managed projects"))
    doc.add(tomlkit.nl())
    doc.add(tomlkit.comment("Example:"))
    doc.add(tomlkit.comment("[[projects]]"))
    doc.add(tomlkit.comment('slug = "fabric-api"'))

    with open(projects_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))

    return projects_path


def save_projects(projects: list[ProjectConfig], path: Path | None = None) -> Path:
    """Save list of ProjectConfig to projects.toml.

    Args:
        projects: List of ProjectConfig instances
        path: Output path (defaults to ./projects.toml)

    Returns:
        Path to saved projects file
    """
    projects_path = path or DEFAULT_PROJECTS_PATH

    doc = tomlkit.document()

    if projects:
        aot = tomlkit.aot()
        for project in projects:
            table = tomlkit.table()
            table.add("slug", project.slug)
            if project.version is not None:
                table.add("version", project.version)
            if project.channel != ReleaseChannel.RELEASE:
                table.add("channel", project.channel.value)

            aot.append(table)

        doc.add("projects", aot)

    with open(projects_path, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(doc))

    return projects_path


def validate_config(config: AppConfig) -> list[ValidationError]:
    """Validate AppConfig values.

    Args:
        config: AppConfig instance to validate

    Returns:
        List of ValidationError (empty if valid)
    """
    errors: list[ValidationError] = []

    # Validate minecraft_version format
    if not MINECRAFT_VERSION_PATTERN.match(config.minecraft_version):
        errors.append(
            ValidationError(
                field="minecraft_version",
                message=f"Invalid version format: {config.minecraft_version}",
            )
        )

    # Validate minecraft_dir exists
    if not config.minecraft_dir.exists():
        errors.append(
            ValidationError(
                field="minecraft_dir",
                message=f"Directory does not exist: {config.minecraft_dir}",
            )
        )

    return errors
