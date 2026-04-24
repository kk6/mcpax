"""Tests for installed file state persistence."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcpax.core.exceptions import StateFileError
from mcpax.core.models import AppConfig, InstalledFile, Loader, ProjectType, StateFile
from mcpax.core.state_store import StateStore


def _make_config(minecraft_dir: Path) -> AppConfig:
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        minecraft_dir=minecraft_dir,
    )


def _make_installed_file(slug: str, **overrides) -> InstalledFile:
    defaults = {
        "slug": slug,
        "project_type": ProjectType.MOD,
        "filename": f"{slug}.jar",
        "version_id": "ABC123",
        "version_number": "1.0.0",
        "sha512": "abc123" * 20,
        "installed_at": datetime.now(UTC),
        "file_path": Path(f"/tmp/{slug}.jar"),
    }
    return InstalledFile(**{**defaults, **overrides})


class TestStateStoreLoadSave:
    """Tests for loading and saving state files."""

    async def test_loads_empty_state_when_no_file(self, tmp_path: Path) -> None:
        state = await StateStore(_make_config(tmp_path)).load()

        assert state.version == 1
        assert state.files == {}

    async def test_loads_existing_state(self, tmp_path: Path) -> None:
        state_data = {
            "version": 1,
            "files": {
                "sodium": {
                    "slug": "sodium",
                    "project_type": "mod",
                    "filename": "sodium.jar",
                    "version_id": "ABC123",
                    "version_number": "1.0.0",
                    "sha512": "abc123" * 20,
                    "installed_at": "2024-01-15T10:30:00Z",
                    "file_path": str(tmp_path / "mods" / "sodium.jar"),
                }
            },
        }
        state_path = tmp_path / ".mcpax-state.json"
        state_path.write_text(json.dumps(state_data))

        state = await StateStore(_make_config(tmp_path)).load()

        assert state.version == 1
        assert state.files["sodium"].slug == "sodium"
        assert state.files["sodium"].project_type == ProjectType.MOD
        assert state.files["sodium"].file_path == tmp_path / "mods" / "sodium.jar"

    async def test_saves_state_to_file(self, tmp_path: Path) -> None:
        store = StateStore(_make_config(tmp_path))
        installed = _make_installed_file(
            "sodium",
            file_path=tmp_path / "mods" / "sodium.jar",
        )

        await store.save(StateFile(version=1, files={"sodium": installed}))

        saved_data = json.loads(store.path.read_text())
        assert saved_data["version"] == 1
        assert saved_data["files"]["sodium"]["slug"] == "sodium"

    async def test_creates_parent_directory_when_saving(self, tmp_path: Path) -> None:
        minecraft_dir = tmp_path / "nested" / ".minecraft"
        store = StateStore(_make_config(minecraft_dir))

        await store.save(StateFile())

        assert store.path.exists()

    async def test_raises_on_corrupted_state(self, tmp_path: Path) -> None:
        state_path = tmp_path / ".mcpax-state.json"
        state_path.write_text("invalid json{")
        store = StateStore(_make_config(tmp_path))

        with pytest.raises(StateFileError) as exc_info:
            await store.load()

        assert exc_info.value.path == state_path


class TestStateStoreInstalledFiles:
    """Tests for installed file helpers."""

    async def test_get_installed_file_returns_file_when_present(
        self,
        tmp_path: Path,
    ) -> None:
        store = StateStore(_make_config(tmp_path))
        installed = _make_installed_file("sodium")
        await store.save(StateFile(files={"sodium": installed}))

        result = await store.get_installed_file("sodium")

        assert result is not None
        assert result.slug == "sodium"

    async def test_get_installed_file_returns_none_when_missing(
        self,
        tmp_path: Path,
    ) -> None:
        result = await StateStore(_make_config(tmp_path)).get_installed_file("sodium")

        assert result is None

    async def test_save_installed_file_adds_file(self, tmp_path: Path) -> None:
        store = StateStore(_make_config(tmp_path))
        installed = _make_installed_file("sodium")

        await store.save_installed_file(installed)

        state = await store.load()
        assert state.files["sodium"].slug == "sodium"

    async def test_remove_installed_file_removes_existing_file(
        self,
        tmp_path: Path,
    ) -> None:
        store = StateStore(_make_config(tmp_path))
        installed = _make_installed_file("sodium")
        await store.save(StateFile(files={"sodium": installed}))

        await store.remove_installed_file("sodium")

        state = await store.load()
        assert "sodium" not in state.files
