"""Remove installed project files and state entries."""

from mcpax.core.file_service import FileService
from mcpax.core.state_store import StateStore


class ProjectUninstaller:
    """Uninstall tracked project files."""

    def __init__(self, state_store: StateStore, file_service: FileService) -> None:
        self._state_store = state_store
        self._file_service = file_service

    async def uninstall_project(self, slug: str) -> tuple[bool, str | None]:
        """Delete an installed project file and remove its state entry.

        Returns a tuple of (file_deleted, filename). The state entry is removed
        when the tracked file was deleted or was already missing.
        """
        installed = await self._state_store.get_installed_file(slug)
        if installed is None:
            return (False, None)

        file_deleted = await self._file_service.delete_file(installed.file_path)
        await self._state_store.remove_installed_file(slug)
        return (file_deleted, installed.filename)
