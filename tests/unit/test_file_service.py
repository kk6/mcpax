"""Tests for file installation operations."""

from pathlib import Path

import pytest

from mcpax.core.exceptions import UnsupportedProjectTypeError
from mcpax.core.file_service import FileService
from mcpax.core.models import AppConfig, Loader, ProjectType


def _make_config(minecraft_dir: Path) -> AppConfig:
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        minecraft_dir=minecraft_dir,
    )


class TestFileServiceTargetDirectory:
    """Tests for target directory resolution."""

    def test_returns_default_directories(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))

        assert service.get_target_directory(ProjectType.MOD) == tmp_path / "mods"
        assert (
            service.get_target_directory(ProjectType.SHADER) == tmp_path / "shaderpacks"
        )
        assert (
            service.get_target_directory(ProjectType.RESOURCEPACK)
            == tmp_path / "resourcepacks"
        )

    def test_returns_custom_directories(self, tmp_path: Path) -> None:
        config = AppConfig(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=tmp_path,
            mods_dir=tmp_path / "custom_mods",
            shaders_dir=tmp_path / "custom_shaders",
            resourcepacks_dir=tmp_path / "custom_resourcepacks",
        )
        service = FileService(config)

        assert service.get_target_directory(ProjectType.MOD) == config.mods_dir
        assert service.get_target_directory(ProjectType.SHADER) == config.shaders_dir
        assert (
            service.get_target_directory(ProjectType.RESOURCEPACK)
            == config.resourcepacks_dir
        )

    def test_raises_for_unsupported_project_type(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))

        with pytest.raises(UnsupportedProjectTypeError) as exc_info:
            service.get_target_directory(ProjectType.MODPACK)

        assert exc_info.value.project_type == "modpack"


class TestFileServicePlaceFile:
    """Tests for placing downloaded files."""

    async def test_moves_file_to_destination(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))
        src_file = tmp_path / "src" / "test.jar"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("test content")
        dest_dir = tmp_path / "dest"

        result = await service.place_file(src_file, dest_dir)

        assert result == dest_dir / "test.jar"
        assert result.exists()
        assert result.read_text() == "test content"
        assert not src_file.exists()

    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))
        src_file = tmp_path / "test.jar"
        src_file.write_text("test content")
        dest_dir = tmp_path / "nested" / "dirs" / "dest"

        result = await service.place_file(src_file, dest_dir)

        assert result.exists()
        assert result.parent == dest_dir
        assert dest_dir.exists()


class TestFileServiceBackupFile:
    """Tests for backup creation."""

    async def test_creates_timestamped_backup(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))
        file_path = tmp_path / "test.jar"
        file_path.write_text("original content")

        backup_path = await service.backup_file(file_path)

        assert backup_path.exists()
        assert backup_path.read_text() == "original content"
        assert backup_path.parent == tmp_path / ".mcpax-backup"
        assert backup_path.stem.startswith("test_")
        assert backup_path.suffix == ".jar"

    async def test_uses_custom_backup_dir(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))
        file_path = tmp_path / "test.jar"
        file_path.write_text("content")
        custom_backup = tmp_path / "custom_backup"

        backup_path = await service.backup_file(file_path, backup_dir=custom_backup)

        assert backup_path.parent == custom_backup
        assert custom_backup.exists()


class TestFileServiceDeleteFile:
    """Tests for deleting files."""

    async def test_deletes_existing_file(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))
        file_path = tmp_path / "test.jar"
        file_path.write_text("content")

        result = await service.delete_file(file_path)

        assert result is True
        assert not file_path.exists()

    async def test_returns_false_for_nonexistent_file(self, tmp_path: Path) -> None:
        service = FileService(_make_config(tmp_path))

        result = await service.delete_file(tmp_path / "nonexistent.jar")

        assert result is False
