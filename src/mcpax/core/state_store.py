"""State file persistence for installed project tracking."""

import asyncio
import json
from pathlib import Path

from mcpax.core.exceptions import StateFileError
from mcpax.core.models import AppConfig, InstalledFile, ProjectType, StateFile


class StateStore:
    """Load and save mcpax installed file state."""

    STATE_FILE_NAME = ".mcpax-state.json"

    def __init__(self, config: AppConfig) -> None:
        """Initialize the state store."""
        self._config = config

    @property
    def path(self) -> Path:
        """Path to the state file."""
        return self._config.minecraft_dir / self.STATE_FILE_NAME

    async def load(self) -> StateFile:
        """Load state from file, or return an empty state when missing."""
        if not self.path.exists():
            return StateFile()

        def _sync_load() -> dict:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)

        try:
            data = await asyncio.to_thread(_sync_load)

            files = {}
            for slug, file_data in data.get("files", {}).items():
                file_data["file_path"] = Path(file_data["file_path"])
                file_data["project_type"] = ProjectType(file_data["project_type"])
                files[slug] = InstalledFile.model_validate(file_data)

            return StateFile(version=data.get("version", 1), files=files)

        except (
            AttributeError,
            json.JSONDecodeError,
            KeyError,
            OSError,
            TypeError,
            ValueError,
        ) as e:
            raise StateFileError(
                f"Failed to parse state file: {e}",
                path=self.path,
            ) from e

    async def save(self, state: StateFile) -> None:
        """Save state to file."""
        data = {
            "version": state.version,
            "files": {
                slug: file.model_dump(mode="json") for slug, file in state.files.items()
            },
        }

        def _sync_save() -> None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        try:
            await asyncio.to_thread(_sync_save)
        except OSError as e:
            raise StateFileError(
                f"Failed to save state file: {e}",
                path=self.path,
            ) from e

    async def get_installed_file(self, slug: str) -> InstalledFile | None:
        """Get installed file info by slug."""
        state = await self.load()
        return state.files.get(slug)

    async def save_installed_file(self, installed: InstalledFile) -> None:
        """Add or update installed file in state."""
        state = await self.load()
        state.files[installed.slug] = installed
        await self.save(state)

    async def remove_installed_file(self, slug: str) -> None:
        """Remove installed file from state."""
        state = await self.load()
        if slug in state.files:
            del state.files[slug]
            await self.save(state)
