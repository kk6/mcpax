"""Filesystem operations for project installation."""

import asyncio
import shutil
from datetime import UTC, datetime
from pathlib import Path

from mcpax.core.exceptions import FileOperationError, UnsupportedProjectTypeError
from mcpax.core.models import AppConfig, ProjectType


class FileService:
    """Handle target path resolution and project file operations."""

    BACKUP_DIR_NAME = ".mcpax-backup"

    def __init__(self, config: AppConfig) -> None:
        """Initialize the file service."""
        self._config = config

    def get_target_directory(self, project_type: ProjectType) -> Path:
        """Map project_type to target directory."""
        type_to_dir = {
            ProjectType.MOD: (
                self._config.mods_dir or self._config.minecraft_dir / "mods"
            ),
            ProjectType.SHADER: (
                self._config.shaders_dir or self._config.minecraft_dir / "shaderpacks"
            ),
            ProjectType.RESOURCEPACK: (
                self._config.resourcepacks_dir
                or self._config.minecraft_dir / "resourcepacks"
            ),
        }
        try:
            return type_to_dir[project_type]
        except KeyError:
            raise UnsupportedProjectTypeError(project_type.value) from None

    async def place_file(self, src: Path, dest_dir: Path) -> Path:
        """Move downloaded file to target directory."""

        def _sync_place() -> Path:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            shutil.move(str(src), str(dest))
            return dest

        try:
            return await asyncio.to_thread(_sync_place)
        except OSError as e:
            raise FileOperationError(f"Failed to move file: {e}", path=src) from e

    async def backup_file(
        self,
        file_path: Path,
        backup_dir: Path | None = None,
    ) -> Path:
        """Create timestamped backup of file."""
        backup_dir = backup_dir or self._config.minecraft_dir / self.BACKUP_DIR_NAME

        def _sync_backup() -> Path:
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = backup_dir / backup_name
            shutil.copy2(str(file_path), str(backup_path))
            return backup_path

        try:
            return await asyncio.to_thread(_sync_backup)
        except OSError as e:
            raise FileOperationError(
                f"Failed to backup file: {e}", path=file_path
            ) from e

    async def delete_file(self, file_path: Path) -> bool:
        """Delete specified file."""

        def _sync_delete() -> bool:
            if file_path.exists():
                file_path.unlink()
                return True
            return False

        try:
            return await asyncio.to_thread(_sync_delete)
        except OSError as e:
            raise FileOperationError(
                f"Failed to delete file: {e}", path=file_path
            ) from e
