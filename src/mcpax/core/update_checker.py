"""Update checking orchestration."""

import asyncio
import logging
from typing import Protocol

import httpx

from mcpax.core.exceptions import APIError, ProjectNotFoundError
from mcpax.core.models import (
    AppConfig,
    InstalledFile,
    InstallStatus,
    ModrinthProject,
    ProjectConfig,
    ProjectFile,
    ProjectType,
    ProjectVersion,
    ReleaseChannel,
    UpdateCheckResult,
)
from mcpax.core.state_store import StateStore
from mcpax.core.version_resolver import VersionCriteria, VersionResolver

logger = logging.getLogger(__name__)


class ProjectVersionClient(Protocol):
    """API operations needed for update checking."""

    async def get_project(self, slug: str) -> ModrinthProject: ...

    async def get_versions(self, slug: str) -> list[ProjectVersion]: ...


class UpdateChecker:
    """Check configured projects for install and update status."""

    def __init__(
        self,
        config: AppConfig,
        api_client: ProjectVersionClient,
        state_store: StateStore,
        version_resolver: VersionResolver | None = None,
    ) -> None:
        """Initialize the update checker."""
        self._config = config
        self._api_client = api_client
        self._state_store = state_store
        self._version_resolver = version_resolver or VersionResolver()

    async def check_updates(
        self,
        projects: list[ProjectConfig],
        max_concurrency: int = 10,
    ) -> list[UpdateCheckResult]:
        """Check updates for all projects."""
        if max_concurrency < 1:
            msg = "max_concurrency must be a positive integer."
            raise ValueError(msg)

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _check_project(project: ProjectConfig) -> UpdateCheckResult:
            async with semaphore:
                try:
                    return await self.check_single_update(project)
                except Exception as e:
                    logger.exception(
                        "Failed to check update for %s: %s", project.slug, e
                    )
                    return UpdateCheckResult(
                        slug=project.slug,
                        project_type=project.project_type,
                        status=InstallStatus.CHECK_FAILED,
                        current_version=None,
                        current_file=None,
                        latest_version=None,
                        latest_version_id=None,
                        latest_file=None,
                        error=str(e),
                    )

        return await asyncio.gather(*(_check_project(project) for project in projects))

    async def check_single_update(self, project: ProjectConfig) -> UpdateCheckResult:
        """Check update status for a single project."""
        installed = await self._state_store.get_installed_file(project.slug)
        project_type = project.project_type

        title: str | None = None
        try:
            project_info = await self._api_client.get_project(project.slug)
            title = project_info.title
        except (APIError, ProjectNotFoundError) as e:
            logger.warning(
                "Failed to fetch title for project '%s': %s", project.slug, e
            )

        try:
            versions = await self._api_client.get_versions(project.slug)
        except (APIError, httpx.HTTPError) as e:
            logger.warning(
                "Failed to fetch versions for project '%s': %s", project.slug, e
            )
            return UpdateCheckResult(
                slug=project.slug,
                project_type=project_type,
                status=InstallStatus.CHECK_FAILED,
                current_version=installed.version_number if installed else None,
                current_file=installed,
                latest_version=None,
                latest_version_id=None,
                latest_file=None,
                title=title,
                error=str(e),
            )

        if project.version is not None:
            return self.resolve_pinned_version(
                project,
                versions,
                installed,
                project_type,
                title,
            )

        shader_loader = (
            self._config.shader_loader if project_type == ProjectType.SHADER else None
        )
        latest = self._version_resolver.latest_compatible_version(
            versions,
            VersionCriteria(
                minecraft_version=self._config.minecraft_version,
                mod_loader=self._config.mod_loader,
                shader_loader=shader_loader,
                project_type=project_type,
                channel=project.channel,
            ),
        )

        if latest is None:
            return UpdateCheckResult(
                slug=project.slug,
                project_type=project_type,
                status=InstallStatus.NOT_COMPATIBLE,
                current_version=installed.version_number if installed else None,
                current_file=installed,
                latest_version=None,
                latest_version_id=None,
                latest_file=None,
                title=title,
            )

        primary_file = latest.get_primary_file()
        status = self._status_for(installed, primary_file)

        return UpdateCheckResult(
            slug=project.slug,
            project_type=project_type,
            status=status,
            current_version=installed.version_number if installed else None,
            current_file=installed,
            latest_version=latest.version_number,
            latest_version_id=latest.id,
            latest_file=primary_file,
            title=title,
        )

    async def get_install_status(
        self,
        slug: str,
        project_config: ProjectConfig | None = None,
    ) -> InstallStatus:
        """Check installation status for an installed project."""
        installed = await self._state_store.get_installed_file(slug)
        if installed is None:
            return InstallStatus.NOT_INSTALLED

        if not installed.file_path.exists():
            return InstallStatus.NOT_INSTALLED

        try:
            versions = await self._api_client.get_versions(slug)
            channel = (
                project_config.channel
                if project_config is not None
                else ReleaseChannel.RELEASE
            )
            shader_loader = (
                self._config.shader_loader
                if installed.project_type == ProjectType.SHADER
                else None
            )

            criteria = VersionCriteria(
                minecraft_version=self._config.minecraft_version,
                mod_loader=self._config.mod_loader,
                shader_loader=shader_loader,
                project_type=installed.project_type,
                channel=channel,
                pinned_version=project_config.version if project_config else None,
            )

            if project_config is not None and project_config.version is not None:
                pinned_result = self._version_resolver.resolve_pinned_version(
                    versions, criteria
                )
                latest = pinned_result.version
                if latest is None:
                    return InstallStatus.NOT_COMPATIBLE
            else:
                latest = self._version_resolver.latest_compatible_version(
                    versions, criteria
                )

            if latest is None:
                return InstallStatus.NOT_COMPATIBLE

            primary_file = latest.get_primary_file()
            if self.needs_update(installed, primary_file):
                return InstallStatus.OUTDATED

            return InstallStatus.INSTALLED
        except (APIError, httpx.HTTPError):
            logger.exception(
                "Failed to check latest version for slug '%s'; status check failed",
                slug,
            )
            return InstallStatus.CHECK_FAILED

    def get_pinned_compatible_version(
        self,
        versions: list[ProjectVersion],
        version_number: str,
        project_type: ProjectType,
        channel: ReleaseChannel | None = None,
    ) -> tuple[ProjectVersion | None, str | None]:
        """Get pinned version and check compatibility."""
        shader_loader = (
            self._config.shader_loader if project_type == ProjectType.SHADER else None
        )
        result = self._version_resolver.resolve_pinned_version(
            versions,
            VersionCriteria(
                minecraft_version=self._config.minecraft_version,
                mod_loader=self._config.mod_loader,
                shader_loader=shader_loader,
                project_type=project_type,
                channel=channel or ReleaseChannel.RELEASE,
                pinned_version=version_number,
            ),
        )
        return result.version, result.error

    def resolve_pinned_version(
        self,
        project: ProjectConfig,
        versions: list[ProjectVersion],
        installed: InstalledFile | None,
        project_type: ProjectType,
        title: str | None = None,
    ) -> UpdateCheckResult:
        """Resolve pinned version into an update check result."""
        version_number = project.version
        if version_number is None:
            msg = "resolve_pinned_version called without pinned version"
            raise RuntimeError(msg)

        pinned_version, error = self.get_pinned_compatible_version(
            versions, version_number, project_type, project.channel
        )

        if pinned_version is None:
            return UpdateCheckResult(
                slug=project.slug,
                project_type=project_type,
                status=InstallStatus.NOT_COMPATIBLE,
                current_version=installed.version_number if installed else None,
                current_file=installed,
                latest_version=None,
                latest_version_id=None,
                latest_file=None,
                error=error,
                pinned=True,
                title=title,
            )

        primary_file = pinned_version.get_primary_file()
        status = self._status_for(installed, primary_file)

        return UpdateCheckResult(
            slug=project.slug,
            project_type=project_type,
            status=status,
            current_version=installed.version_number if installed else None,
            current_file=installed,
            latest_version=pinned_version.version_number,
            latest_version_id=pinned_version.id,
            latest_file=primary_file,
            pinned=True,
            title=title,
        )

    def needs_update(
        self,
        installed: InstalledFile,
        latest: ProjectFile | None,
    ) -> bool:
        """Compare hashes to determine if update is needed."""
        if latest is None:
            return False

        latest_hash = latest.hashes.get("sha512", "")
        return installed.sha512.lower() != latest_hash.lower()

    def _status_for(
        self,
        installed: InstalledFile | None,
        primary_file: ProjectFile | None,
    ) -> InstallStatus:
        if installed is None:
            return InstallStatus.NOT_INSTALLED
        if self.needs_update(installed, primary_file):
            return InstallStatus.OUTDATED
        return InstallStatus.INSTALLED
