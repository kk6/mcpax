"""Project management facade."""

import logging
from pathlib import Path
from types import TracebackType
from typing import Self, cast

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
from mcpax.core.protocols import ModrinthClientProtocol
from mcpax.core.state_store import StateStore
from mcpax.core.update_applier import UpdateApplier
from mcpax.core.update_checker import UpdateChecker
from mcpax.core.version_resolver import VersionResolver

logger = logging.getLogger(__name__)


class _StateFacade:
    _state_store: StateStore

    @property
    def _state_file_path(self) -> Path:
        return self._state_store.path

    async def _load_state(self) -> StateFile:
        return await self._state_store.load()

    async def _save_state(self, state: StateFile) -> None:
        await self._state_store.save(state)

    async def _save_installed_file(self, installed: InstalledFile) -> None:
        await self._state_store.save_installed_file(installed)

    async def _remove_installed_file(self, slug: str) -> None:
        await self._state_store.remove_installed_file(slug)

    async def get_installed_file(self, slug: str) -> InstalledFile | None:
        return await self._state_store.get_installed_file(slug)


class _FileFacade(_StateFacade):
    _file_service: FileService

    def get_target_directory(self, project_type: ProjectType) -> Path:
        return self._file_service.get_target_directory(project_type)

    async def place_file(self, src: Path, dest_dir: Path) -> Path:
        return await self._file_service.place_file(src, dest_dir)

    async def backup_file(
        self, file_path: Path, backup_dir: Path | None = None
    ) -> Path:
        return await self._file_service.backup_file(file_path, backup_dir)

    async def delete_file(self, file_path: Path) -> bool:
        return await self._file_service.delete_file(file_path)


class _ServiceFactory(_FileFacade):
    _api_client: ModrinthClientProtocol | None
    _config: AppConfig
    _downloader: Downloader | None
    _install_planner: InstallPlanner
    _update_applier: UpdateApplier | None
    _update_checker: UpdateChecker | None
    _version_resolver: VersionResolver

    def _get_update_checker(self) -> UpdateChecker:
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

    def _get_update_applier(self) -> UpdateApplier:
        if self._downloader is None:
            msg = "Downloader not initialized. Use async context manager."
            raise RuntimeError(msg)
        if self._update_applier is None:
            self._update_applier = UpdateApplier(
                minecraft_dir=self._config.minecraft_dir,
                downloader=self._downloader,
                install_planner=self._install_planner,
                file_service=self._file_service,
                state_store=self._state_store,
            )
        return self._update_applier


class ProjectManager(_ServiceFactory):
    """Compatibility facade over focused core services."""

    STATE_FILE_NAME = StateStore.STATE_FILE_NAME
    STATE_VERSION = 1

    def __init__(
        self,
        config: AppConfig,
        api_client: ModrinthClientProtocol | None = None,
        downloader: Downloader | None = None,
    ) -> None:
        self._config = config
        self._api_client = api_client
        self._downloader = downloader
        self._owns_api_client = api_client is None
        self._owns_downloader = downloader is None
        self._state_store = StateStore(config)
        self._file_service = FileService(config)
        self._version_resolver = VersionResolver()
        self._install_planner = InstallPlanner()
        self._update_checker: UpdateChecker | None = None
        self._update_applier: UpdateApplier | None = None

    async def __aenter__(self) -> Self:
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
        if self._owns_api_client and self._api_client:
            try:
                await cast(ModrinthClient, self._api_client).__aexit__(
                    exc_type, exc_val, exc_tb
                )
            except Exception as e:
                logger.error("Failed to cleanup API client: %s", e)
        if self._owns_downloader and self._downloader:
            try:
                await self._downloader.__aexit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.error("Failed to cleanup downloader: %s", e)

    async def get_install_status(
        self, slug: str, project_config: ProjectConfig | None = None
    ) -> InstallStatus:
        return await self._get_update_checker().get_install_status(slug, project_config)

    def needs_update(
        self, installed: InstalledFile, latest: ProjectFile | None
    ) -> bool:
        if latest is None:
            return False
        return installed.sha512.lower() != latest.hashes.get("sha512", "").lower()

    async def check_updates(
        self, projects: list[ProjectConfig], max_concurrency: int = 10
    ) -> list[UpdateCheckResult]:
        return await self._get_update_checker().check_updates(projects, max_concurrency)

    async def _check_single_update(self, project: ProjectConfig) -> UpdateCheckResult:
        return await self._get_update_checker().check_single_update(project)

    async def apply_updates(
        self, updates: list[UpdateCheckResult], backup: bool = True
    ) -> UpdateResult:
        if self._api_client is None or self._downloader is None:
            msg = "API client or downloader not initialized. Use async context manager."
            raise RuntimeError(msg)
        return await self._get_update_applier().apply_updates(updates, backup)

    def _get_temp_download_dir(self) -> Path:
        return self._get_update_applier().get_temp_download_dir()
