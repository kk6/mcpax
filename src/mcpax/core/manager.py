"""Project management orchestration."""

import logging
from pathlib import Path
from types import TracebackType
from typing import Self

from mcpax.core.api import ModrinthClient
from mcpax.core.downloader import Downloader, DownloaderConfig
from mcpax.core.file_service import FileService
from mcpax.core.install_planner import InstallPlanner
from mcpax.core.models import (
    AppConfig,
    InstalledFile,
    InstallStatus,
    ProjectConfig,
    ProjectFile,
    ProjectType,
    StateFile,
    UpdateCheckResult,
    UpdateResult,
)
from mcpax.core.state_store import StateStore
from mcpax.core.update_applier import UpdateApplier
from mcpax.core.update_checker import UpdateChecker
from mcpax.core.version_resolver import VersionResolver

logger = logging.getLogger(__name__)


class ProjectManager:
    """Orchestrates project installation, updates, and state management."""

    STATE_FILE_NAME = ".mcpax-state.json"
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
        self._version_resolver = VersionResolver()
        self._install_planner = InstallPlanner()
        self._file_service = FileService(config)
        self._state_store = StateStore(config)
        self._update_checker: UpdateChecker | None = None
        self._update_applier: UpdateApplier | None = None

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

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
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
        return self._state_store.path

    async def _load_state(self) -> StateFile:
        """Load state from file.

        Returns:
            StateFile instance (empty if file doesn't exist)

        Raises:
            StateFileError: If file exists but cannot be parsed
        """
        return await self._state_store.load()

    async def _save_state(self, state: StateFile) -> None:
        """Save state to file.

        Args:
            state: StateFile to save

        Raises:
            StateFileError: If save fails
        """
        await self._state_store.save(state)

    async def _save_installed_file(self, installed: InstalledFile) -> None:
        """Add or update installed file in state.

        Args:
            installed: InstalledFile to save
        """
        await self._state_store.save_installed_file(installed)

    async def _remove_installed_file(self, slug: str) -> None:
        """Remove installed file from state.

        Args:
            slug: Project slug to remove
        """
        await self._state_store.remove_installed_file(slug)

    # File Management Functions (F-401 to F-404)

    def get_target_directory(self, project_type: ProjectType) -> Path:
        """Map project_type to target directory.

        Args:
            project_type: Type of project (mod, shader, resourcepack)

        Returns:
            Path to target directory

        Raises:
            UnsupportedProjectTypeError: If project_type is not supported
                for installation
        """
        return self._file_service.get_target_directory(project_type)

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

        return await self._file_service.place_file(src, dest_dir)

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
        return await self._file_service.backup_file(file_path, backup_dir)

    async def delete_file(self, file_path: Path) -> bool:
        """Delete specified file.

        Args:
            file_path: File to delete

        Returns:
            True if deleted, False if file didn't exist

        Raises:
            FileOperationError: If deletion fails
        """

        return await self._file_service.delete_file(file_path)

    async def uninstall_project(self, slug: str) -> tuple[bool, str | None]:
        """Uninstall a project by removing its file and state.

        Args:
            slug: Project slug to uninstall

        Returns:
            Tuple of (success, filename) where success is True if file was deleted,
            False if not installed, and filename is the deleted file name or None.

        Raises:
            FileOperationError: If file deletion fails
        """
        installed = await self.get_installed_file(slug)
        if installed is None:
            return (False, None)

        # Delete the file
        await self.delete_file(installed.file_path)

        # Remove from state
        await self._remove_installed_file(slug)

        return (True, installed.filename)

    # Status Functions (F-405, F-406)

    async def get_installed_file(self, slug: str) -> InstalledFile | None:
        """Get installed file info from state.

        Args:
            slug: Project slug

        Returns:
            InstalledFile if installed, None otherwise
        """
        return await self._state_store.get_installed_file(slug)

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
        return await self._get_update_checker().get_install_status(
            slug,
            project_config,
        )

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
        max_concurrency: int = 10,
    ) -> list[UpdateCheckResult]:
        """Check updates for all projects.

        Args:
            projects: List of project configs to check
            max_concurrency: Maximum concurrent API requests

        Returns:
            List of UpdateCheckResult for each project
        """
        return await self._get_update_checker().check_updates(
            projects,
            max_concurrency,
        )

    async def _check_single_update(self, project: ProjectConfig) -> UpdateCheckResult:
        """Check update for a single project."""
        return await self._get_update_checker().check_single_update(project)

    def _get_update_checker(self) -> UpdateChecker:
        """Return an update checker backed by the initialized API client."""
        if self._api_client is None:
            msg = "API client not initialized. Use async context manager."
            raise RuntimeError(msg)

        if self._update_checker is None:
            self._update_checker = UpdateChecker(
                config=self._config,
                api_client=self._api_client,
                state_store=self._state_store,
                version_resolver=self._version_resolver,
            )
        return self._update_checker

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

        return await self._get_update_applier().apply_updates(updates, backup)

    def _get_temp_download_dir(self) -> Path:
        """Get temporary download directory."""
        return self._get_update_applier().get_temp_download_dir()

    def _get_update_applier(self) -> UpdateApplier:
        """Return an update applier backed by the initialized downloader."""
        if self._downloader is None:
            msg = "Downloader not initialized. Use async context manager."
            raise RuntimeError(msg)

        if self._update_applier is None:
            self._update_applier = UpdateApplier(
                minecraft_dir=self._config.minecraft_dir,
                downloader=self._downloader,
                install_planner=self._install_planner,
                file_service=_ProjectManagerFileServiceAdapter(self),
                state_store=self._state_store,
            )
        return self._update_applier


class _ProjectManagerFileServiceAdapter:
    """Route file operations through ProjectManager compatibility methods."""

    def __init__(self, manager: ProjectManager) -> None:
        self._manager = manager

    def get_target_directory(self, project_type: ProjectType) -> Path:
        return self._manager.get_target_directory(project_type)

    async def place_file(self, src: Path, dest_dir: Path) -> Path:
        return await self._manager.place_file(src, dest_dir)

    async def backup_file(
        self,
        file_path: Path,
        backup_dir: Path | None = None,
    ) -> Path:
        return await self._manager.backup_file(file_path, backup_dir)

    async def delete_file(self, file_path: Path) -> bool:
        return await self._manager.delete_file(file_path)
