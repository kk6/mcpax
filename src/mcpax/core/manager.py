"""Project management compatibility facade."""

from pathlib import Path
from types import TracebackType
from typing import Self

from mcpax.core.downloader import Downloader
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
from mcpax.core.services import ProjectServices
from mcpax.core.state_store import StateStore
from mcpax.core.update_applier import UpdateApplier
from mcpax.core.update_checker import UpdateChecker


class ProjectManager:
    """Compatibility facade over focused core services."""

    STATE_FILE_NAME = StateStore.STATE_FILE_NAME
    STATE_VERSION = 1

    def __init__(
        self,
        config: AppConfig,
        api_client: ModrinthClientProtocol | None = None,
        downloader: Downloader | None = None,
    ) -> None:
        self._services = ProjectServices(
            config, api_client=api_client, downloader=downloader
        )
        self._config = self._services.config
        self._state_store = self._services.state_store
        self._file_service = self._services.file_service

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

    def _get_update_checker(self) -> UpdateChecker:
        return self._services.update_checker

    def _get_update_applier(self) -> UpdateApplier:
        return self._services.update_applier

    async def __aenter__(self) -> Self:
        await self._services.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._services.__aexit__(exc_type, exc_val, exc_tb)

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
        return await self._get_update_applier().apply_updates(updates, backup)

    def _get_temp_download_dir(self) -> Path:
        return self._get_update_applier().get_temp_download_dir()
