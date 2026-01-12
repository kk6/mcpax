"""Project management orchestration."""

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import httpx

from mcpax.core.api import ModrinthClient
from mcpax.core.downloader import Downloader, DownloaderConfig
from mcpax.core.exceptions import APIError, FileOperationError, StateFileError
from mcpax.core.models import (
    AppConfig,
    DownloadTask,
    InstalledFile,
    InstallStatus,
    ProjectConfig,
    ProjectFile,
    ProjectType,
    ReleaseChannel,
    StateFile,
    UpdateCheckResult,
    UpdateResult,
)

logger = logging.getLogger(__name__)

# Type alias for update info mapping
UpdateInfo = tuple[UpdateCheckResult, ProjectType]


class ProjectManager:
    """Orchestrates project installation, updates, and state management."""

    STATE_FILE_NAME = ".mcpax-state.json"
    BACKUP_DIR_NAME = ".mcpax-backup"
    STATE_VERSION = 1

    def __init__(
        self,
        config: AppConfig,
        api_client: ModrinthClient | None = None,
        downloader: Downloader | None = None,
    ) -> None:
        """Initialize ProjectManager.

        Args:
            config: Application configuration
            api_client: Optional API client for dependency injection
            downloader: Optional downloader for dependency injection
        """
        self._config = config
        self._api_client = api_client
        self._downloader = downloader
        self._owns_api_client = api_client is None
        self._owns_downloader = downloader is None

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        if self._api_client is None:
            self._api_client = ModrinthClient()
            await self._api_client.__aenter__()
        if self._downloader is None:
            self._downloader = Downloader(
                config=DownloaderConfig(
                    max_concurrent=self._config.max_concurrent_downloads,
                    verify_hash=self._config.verify_hash,
                )
            )
            await self._downloader.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # Cleanup both resources independently to ensure both are attempted
        # even if one fails
        if self._owns_api_client and self._api_client:
            try:
                await self._api_client.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.error("Failed to cleanup API client: %s", e)

        if self._owns_downloader and self._downloader:
            try:
                await self._downloader.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.error("Failed to cleanup downloader: %s", e)

    @property
    def _state_file_path(self) -> Path:
        """Path to state file."""
        return self._config.minecraft_dir / self.STATE_FILE_NAME

    async def _load_state(self) -> StateFile:
        """Load state from file.

        Returns:
            StateFile instance (empty if file doesn't exist)

        Raises:
            StateFileError: If file exists but cannot be parsed
        """
        if not self._state_file_path.exists():
            return StateFile()

        try:
            with open(self._state_file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Convert file entries to InstalledFile
            files = {}
            for slug, file_data in data.get("files", {}).items():
                file_data["file_path"] = Path(file_data["file_path"])
                file_data["project_type"] = ProjectType(file_data["project_type"])
                files[slug] = InstalledFile.model_validate(file_data)

            return StateFile(version=data.get("version", 1), files=files)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise StateFileError(
                f"Failed to parse state file: {e}",
                path=self._state_file_path,
            ) from e

    async def _save_state(self, state: StateFile) -> None:
        """Save state to file.

        Args:
            state: StateFile to save

        Raises:
            StateFileError: If save fails
        """
        try:
            data = {
                "version": state.version,
                "files": {
                    slug: file.model_dump(mode="json")
                    for slug, file in state.files.items()
                },
            }

            self._state_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except OSError as e:
            raise StateFileError(
                f"Failed to save state file: {e}",
                path=self._state_file_path,
            ) from e

    async def _save_installed_file(self, installed: InstalledFile) -> None:
        """Add or update installed file in state.

        Args:
            installed: InstalledFile to save
        """
        state = await self._load_state()
        state.files[installed.slug] = installed
        await self._save_state(state)

    async def _remove_installed_file(self, slug: str) -> None:
        """Remove installed file from state.

        Args:
            slug: Project slug to remove
        """
        state = await self._load_state()
        if slug in state.files:
            del state.files[slug]
            await self._save_state(state)

    # File Management Functions (F-401 to F-404)

    def get_target_directory(self, project_type: ProjectType) -> Path:
        """Map project_type to target directory.

        Args:
            project_type: Type of project (mod, shader, resourcepack)

        Returns:
            Path to target directory
        """
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
        return type_to_dir[project_type]

    async def place_file(self, src: Path, dest_dir: Path) -> Path:
        """Move downloaded file to target directory.

        Args:
            src: Source file path
            dest_dir: Destination directory

        Returns:
            Path to placed file

        Raises:
            FileOperationError: If move fails
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        try:
            shutil.move(str(src), str(dest))
            return dest
        except OSError as e:
            raise FileOperationError(f"Failed to move file: {e}", path=src) from e

    async def backup_file(
        self,
        file_path: Path,
        backup_dir: Path | None = None,
    ) -> Path:
        """Create timestamped backup of file.

        Args:
            file_path: File to backup
            backup_dir: Backup directory (defaults to .mcpax-backup in minecraft_dir)

        Returns:
            Path to backup file

        Raises:
            FileOperationError: If backup fails
        """
        backup_dir = backup_dir or self._config.minecraft_dir / self.BACKUP_DIR_NAME
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name

        try:
            shutil.copy2(str(file_path), str(backup_path))
            return backup_path
        except OSError as e:
            raise FileOperationError(
                f"Failed to backup file: {e}", path=file_path
            ) from e

    async def delete_file(self, file_path: Path) -> bool:
        """Delete specified file.

        Args:
            file_path: File to delete

        Returns:
            True if deleted, False if file didn't exist

        Raises:
            FileOperationError: If deletion fails
        """
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except OSError as e:
            raise FileOperationError(
                f"Failed to delete file: {e}", path=file_path
            ) from e

    # Status Functions (F-405, F-406)

    async def get_installed_file(self, slug: str) -> InstalledFile | None:
        """Get installed file info from state.

        Args:
            slug: Project slug

        Returns:
            InstalledFile if installed, None otherwise
        """
        state = await self._load_state()
        return state.files.get(slug)

    async def get_install_status(
        self,
        slug: str,
        project_config: ProjectConfig | None = None,
    ) -> InstallStatus:
        """Check installation status of a project.

        Args:
            slug: Project slug
            project_config: Optional project config to respect channel settings

        Returns:
            InstallStatus enum value:
            - NOT_INSTALLED: Not in state or file doesn't exist
            - INSTALLED: File exists and matches latest version
            - OUTDATED: File exists but newer version available
            - NOT_COMPATIBLE: No compatible version exists for current config
            - CHECK_FAILED: Could not check status due to API/network error
        """
        installed = await self.get_installed_file(slug)
        if installed is None:
            return InstallStatus.NOT_INSTALLED

        # Check if file still exists
        if not installed.file_path.exists():
            return InstallStatus.NOT_INSTALLED

        # Get latest version to compare
        if self._api_client is None:
            msg = "API client not initialized. Use async context manager."
            raise RuntimeError(msg)

        try:
            versions = await self._api_client.get_versions(slug)
            channel = (
                project_config.channel
                if project_config is not None
                else ReleaseChannel.RELEASE
            )
            latest = self._api_client.get_latest_compatible_version(
                versions,
                self._config.minecraft_version,
                self._config.loader,
                channel=channel,
            )

            if latest is None:
                return InstallStatus.NOT_COMPATIBLE

            # Find primary file hash
            primary_file = next(
                (f for f in latest.files if f.primary),
                latest.files[0] if latest.files else None,
            )
            if (
                primary_file
                and installed.sha512.lower()
                != primary_file.hashes.get("sha512", "").lower()
            ):
                return InstallStatus.OUTDATED

            return InstallStatus.INSTALLED
        except (APIError, httpx.HTTPError):
            logger.exception(
                "Failed to check latest version for slug '%s'; status check failed",
                slug,
            )
            return InstallStatus.CHECK_FAILED

    # Update Management Functions (F-501 to F-503)

    def needs_update(
        self,
        installed: InstalledFile,
        latest: ProjectFile | None,
    ) -> bool:
        """Compare hashes to determine if update needed.

        Args:
            installed: Currently installed file info
            latest: Latest available file info

        Returns:
            True if update is needed
        """
        if latest is None:
            return False

        latest_hash = latest.hashes.get("sha512", "")
        return installed.sha512.lower() != latest_hash.lower()

    async def check_updates(
        self,
        projects: list[ProjectConfig],
    ) -> list[UpdateCheckResult]:
        """Check updates for all projects.

        Args:
            projects: List of project configs to check

        Returns:
            List of UpdateCheckResult for each project
        """
        if self._api_client is None:
            msg = "API client not initialized. Use async context manager."
            raise RuntimeError(msg)

        results = []

        for project in projects:
            try:
                result = await self._check_single_update(project)
                results.append(result)
            except Exception as e:
                logger.warning("Failed to check update for %s: %s", project.slug, e)
                results.append(
                    UpdateCheckResult(
                        slug=project.slug,
                        status=InstallStatus.CHECK_FAILED,
                        current_version=None,
                        current_file=None,
                        latest_version=None,
                        latest_version_id=None,
                        latest_file=None,
                        error=str(e),
                    )
                )

        return results

    async def _check_single_update(self, project: ProjectConfig) -> UpdateCheckResult:
        """Check update for a single project."""
        if self._api_client is None:
            msg = "API client not initialized"
            raise RuntimeError(msg)

        installed = await self.get_installed_file(project.slug)

        # Get latest compatible version
        versions = await self._api_client.get_versions(project.slug)
        latest = self._api_client.get_latest_compatible_version(
            versions,
            self._config.minecraft_version,
            self._config.loader,
            project.channel,
        )

        if latest is None:
            return UpdateCheckResult(
                slug=project.slug,
                status=InstallStatus.NOT_COMPATIBLE,
                current_version=installed.version_number if installed else None,
                current_file=installed,
                latest_version=None,
                latest_version_id=None,
                latest_file=None,
            )

        primary_file = next(
            (f for f in latest.files if f.primary),
            latest.files[0] if latest.files else None,
        )

        if installed is None:
            status = InstallStatus.NOT_INSTALLED
        elif self.needs_update(installed, primary_file):
            status = InstallStatus.OUTDATED
        else:
            status = InstallStatus.INSTALLED

        return UpdateCheckResult(
            slug=project.slug,
            status=status,
            current_version=installed.version_number if installed else None,
            current_file=installed,
            latest_version=latest.version_number,
            latest_version_id=latest.id,
            latest_file=primary_file,
        )

    async def apply_updates(
        self,
        updates: list[UpdateCheckResult],
        backup: bool = True,
    ) -> UpdateResult:
        """Download, backup old, place new, update state.

        Args:
            updates: List of update check results to apply
            backup: Whether to backup old files before update

        Returns:
            UpdateResult with success/failure info
        """
        if self._api_client is None or self._downloader is None:
            msg = "API client or downloader not initialized. Use async context manager."
            raise RuntimeError(msg)

        # Filter to only updates that need action
        to_update = [
            u
            for u in updates
            if u.status in (InstallStatus.NOT_INSTALLED, InstallStatus.OUTDATED)
        ]

        if not to_update:
            return UpdateResult(successful=[], failed=[], backed_up=[])

        result = UpdateResult(successful=[], failed=[], backed_up=[])

        # Load state once at the beginning
        state = await self._load_state()
        state_modified = False

        # Create download tasks
        tasks: list[DownloadTask] = []
        update_info: dict[str, UpdateInfo] = {}

        for update in to_update:
            if update.latest_file is None:
                result.failed.append((update.slug, "No compatible version found"))
                continue

            try:
                project = await self._api_client.get_project(update.slug)
                dest_dir = self._get_temp_download_dir()
                dest_dir.mkdir(parents=True, exist_ok=True)

                task = DownloadTask(
                    url=update.latest_file.url,
                    dest=dest_dir / update.latest_file.filename,
                    expected_hash=update.latest_file.hashes.get("sha512"),
                    slug=update.slug,
                    version_number=update.latest_version or "unknown",
                )
                tasks.append(task)
                update_info[update.slug] = (update, project.project_type)
            except Exception as e:
                result.failed.append((update.slug, str(e)))

        # Download all files
        if tasks:
            download_results = await self._downloader.download_all(tasks)

            for download_result in download_results:
                slug = download_result.task.slug
                if not download_result.success:
                    result.failed.append(
                        (slug, download_result.error or "Download failed")
                    )
                    continue

                update, project_type = update_info[slug]
                final_path: Path | None = None

                try:
                    if update.latest_version_id is None:
                        result.failed.append((slug, "Latest version id is None"))
                        continue

                    # Place new file
                    target_dir = self.get_target_directory(project_type)
                    if download_result.file_path is None:
                        result.failed.append((slug, "Download path is None"))
                        continue

                    final_path = await self.place_file(
                        download_result.file_path, target_dir
                    )

                    # Backup and delete old file after new placement succeeds
                    if (
                        update.current_file
                        and update.current_file.file_path.exists()
                        and update.current_file.file_path != final_path
                    ):
                        if backup:
                            backup_path = await self.backup_file(
                                update.current_file.file_path
                            )
                            result.backed_up.append(backup_path)
                        await self.delete_file(update.current_file.file_path)

                    # Update state
                    if update.latest_file is None:
                        result.failed.append((slug, "Latest file is None"))
                        continue

                    installed_file = InstalledFile(
                        slug=slug,
                        project_type=project_type,
                        filename=final_path.name,
                        version_id=update.latest_version_id,
                        version_number=update.latest_version or "unknown",
                        sha512=update.latest_file.hashes.get("sha512", ""),
                        installed_at=datetime.now(UTC),
                        file_path=final_path,
                    )
                    # Update state in memory
                    state.files[slug] = installed_file
                    state_modified = True
                    result.successful.append(slug)

                except Exception as e:
                    if final_path and final_path.exists():
                        try:
                            await self.delete_file(final_path)
                        except Exception as rollback_error:
                            logger.error(
                                "Failed to rollback new file %s: %s",
                                final_path,
                                rollback_error,
                            )
                    result.failed.append((slug, str(e)))

        # Save state once at the end if modified
        if state_modified:
            await self._save_state(state)

        return result

    def _get_temp_download_dir(self) -> Path:
        """Get temporary download directory."""
        return self._config.minecraft_dir / ".mcpax-downloads"
