"""Apply planned project updates to the filesystem and state."""

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from mcpax.core.exceptions import FileOperationError, UnsupportedProjectTypeError
from mcpax.core.install_planner import InstallPlanner
from mcpax.core.models import (
    DownloadResult,
    DownloadTask,
    FailedUpdate,
    InstalledFile,
    ProjectType,
    UpdateCheckResult,
    UpdateResult,
)
from mcpax.core.state_store import StateStore

logger = logging.getLogger(__name__)


class DownloadBatch(Protocol):
    """Downloader operations needed to apply updates."""

    async def download_all(
        self,
        tasks: list[DownloadTask],
    ) -> list[DownloadResult]: ...


class ProjectFileService(Protocol):
    """File operations needed to apply updates."""

    def get_target_directory(self, project_type: ProjectType) -> Path: ...

    async def place_file(self, src: Path, dest_dir: Path) -> Path: ...

    async def backup_file(
        self,
        file_path: Path,
        backup_dir: Path | None = None,
    ) -> Path: ...

    async def delete_file(self, file_path: Path) -> bool: ...


class UpdateApplier:
    """Download, place, backup, and persist project updates."""

    def __init__(
        self,
        minecraft_dir: Path,
        downloader: DownloadBatch,
        install_planner: InstallPlanner,
        file_service: ProjectFileService,
        state_store: StateStore,
    ) -> None:
        """Initialize the update applier."""
        self._minecraft_dir = minecraft_dir
        self._downloader = downloader
        self._install_planner = install_planner
        self._file_service = file_service
        self._state_store = state_store

    async def apply_updates(
        self,
        updates: list[UpdateCheckResult],
        backup: bool = True,
    ) -> UpdateResult:
        """Download, backup old, place new, and update state."""
        result = UpdateResult(successful=[], failed=[], backed_up=[])
        state = await self._state_store.load()
        state_modified = False

        dest_dir = self.get_temp_download_dir()
        plan = self._install_planner.create_plan(updates, dest_dir)
        result.failed.extend(plan.failed)

        if not plan.has_work:
            return result

        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            download_results = await self._downloader.download_all(plan.tasks)

            for download_result in download_results:
                slug = download_result.task.slug
                if not download_result.success:
                    result.failed.append(
                        FailedUpdate(
                            slug=slug,
                            error=download_result.error or "Download failed",
                        )
                    )
                    continue

                update = plan.check_results[slug]
                final_path: Path | None = None

                try:
                    if update.latest_version_id is None:
                        result.failed.append(
                            FailedUpdate(slug=slug, error="Latest version id is None")
                        )
                        continue

                    target_dir = self._file_service.get_target_directory(
                        update.project_type
                    )
                    if download_result.file_path is None:
                        result.failed.append(
                            FailedUpdate(slug=slug, error="Download path is None")
                        )
                        continue

                    final_path = await self._file_service.place_file(
                        download_result.file_path, target_dir
                    )

                    if (
                        update.current_file
                        and update.current_file.file_path.exists()
                        and update.current_file.file_path != final_path
                    ):
                        if backup:
                            backup_path = await self._file_service.backup_file(
                                update.current_file.file_path
                            )
                            result.backed_up.append(backup_path)
                        await self._file_service.delete_file(
                            update.current_file.file_path
                        )

                    if update.latest_file is None:
                        result.failed.append(
                            FailedUpdate(slug=slug, error="Latest file is None")
                        )
                        continue

                    installed_file = InstalledFile(
                        slug=slug,
                        project_type=update.project_type,
                        filename=final_path.name,
                        version_id=update.latest_version_id,
                        version_number=update.latest_version or "unknown",
                        sha512=update.latest_file.hashes.get("sha512", ""),
                        installed_at=datetime.now(UTC),
                        file_path=final_path,
                    )
                    state.files[slug] = installed_file
                    state_modified = True
                    result.successful.append(slug)

                except (FileOperationError, UnsupportedProjectTypeError, OSError) as e:
                    if final_path and final_path.exists():
                        try:
                            await self._file_service.delete_file(final_path)
                        except (FileOperationError, OSError) as rollback_error:
                            logger.error(
                                "Failed to rollback new file %s: %s",
                                final_path,
                                rollback_error,
                            )
                    result.failed.append(FailedUpdate(slug=slug, error=str(e)))

            if state_modified:
                await self._state_store.save(state)
        finally:
            try:
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
            except OSError:
                logger.warning("Failed to clean up temporary directory: %s", dest_dir)

        return result

    def get_temp_download_dir(self) -> Path:
        """Get temporary download directory."""
        return self._minecraft_dir / ".mcpax-downloads"
