"""Tests for project uninstall operations."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcpax.core.exceptions import FileOperationError
from mcpax.core.file_service import FileService
from mcpax.core.models import AppConfig, InstalledFile, Loader, ProjectType, StateFile
from mcpax.core.state_store import StateStore
from mcpax.core.uninstaller import ProjectUninstaller


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


def _make_uninstaller(config: AppConfig) -> tuple[ProjectUninstaller, StateStore]:
    state_store = StateStore(config)
    return ProjectUninstaller(state_store, FileService(config)), state_store


class _FailingFileService(FileService):
    async def delete_file(self, file_path: Path) -> bool:
        raise FileOperationError("permission denied", path=file_path)


class TestProjectUninstaller:
    """Tests for explicit project uninstall use case."""

    async def test_uninstalls_existing_project(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        uninstaller, state_store = _make_uninstaller(config)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("content")

        installed = _make_installed_file(
            "sodium",
            filename="sodium.jar",
            file_path=file_path,
        )
        await state_store.save(StateFile(version=1, files={"sodium": installed}))

        success, filename = await uninstaller.uninstall_project("sodium")

        assert success is True
        assert filename == "sodium.jar"
        assert not file_path.exists()
        result_state = await state_store.load()
        assert "sodium" not in result_state.files

    async def test_returns_false_for_not_installed(self, tmp_path: Path) -> None:
        uninstaller, _ = _make_uninstaller(_make_config(tmp_path))

        success, filename = await uninstaller.uninstall_project("nonexistent")

        assert success is False
        assert filename is None

    async def test_removes_stale_state_if_file_missing(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        uninstaller, state_store = _make_uninstaller(config)
        file_path = tmp_path / "mods" / "sodium.jar"
        installed = _make_installed_file(
            "sodium",
            filename="sodium.jar",
            file_path=file_path,
        )
        await state_store.save(StateFile(version=1, files={"sodium": installed}))

        success, filename = await uninstaller.uninstall_project("sodium")

        assert success is False
        assert filename == "sodium.jar"
        result_state = await state_store.load()
        assert "sodium" not in result_state.files

    async def test_keeps_state_if_file_delete_fails(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        state_store = StateStore(config)
        uninstaller = ProjectUninstaller(state_store, _FailingFileService(config))
        file_path = tmp_path / "mods" / "sodium.jar"
        installed = _make_installed_file(
            "sodium",
            filename="sodium.jar",
            file_path=file_path,
        )
        await state_store.save(StateFile(version=1, files={"sodium": installed}))

        with pytest.raises(FileOperationError):
            await uninstaller.uninstall_project("sodium")

        result_state = await state_store.load()
        assert result_state.files["sodium"] == installed
