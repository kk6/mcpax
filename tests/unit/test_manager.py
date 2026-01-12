"""Tests for manager.py."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from pytest_httpx import HTTPXMock

from mcpax.core.api import ModrinthClient
from mcpax.core.exceptions import StateFileError
from mcpax.core.manager import ProjectManager
from mcpax.core.models import (
    AppConfig,
    InstalledFile,
    InstallStatus,
    Loader,
    ProjectConfig,
    ProjectFile,
    ProjectType,
    ReleaseChannel,
    StateFile,
)


def _make_config(minecraft_dir: Path) -> AppConfig:
    """Helper to create AppConfig for tests."""
    return AppConfig(
        minecraft_version="1.21.4",
        loader=Loader.FABRIC,
        minecraft_dir=minecraft_dir,
    )


def _make_installed_file(slug: str, **overrides) -> InstalledFile:
    """Helper to create InstalledFile for tests."""
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


class TestStateManagement:
    """Tests for state file management."""

    async def test_loads_empty_state_when_no_file(self, tmp_path: Path) -> None:
        """Returns empty StateFile when state file doesn't exist."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        # Act
        state = await manager._load_state()

        # Assert
        assert isinstance(state, StateFile)
        assert state.version == 1
        assert state.files == {}

    async def test_loads_existing_state(self, tmp_path: Path) -> None:
        """Loads state from existing file."""
        # Arrange
        config = _make_config(tmp_path)
        state_data = {
            "version": 1,
            "files": {
                "sodium": {
                    "slug": "sodium",
                    "project_type": "mod",
                    "filename": "sodium-fabric-0.6.0+mc1.21.4.jar",
                    "version_id": "ABC123",
                    "version_number": "0.6.0",
                    "sha512": "abc123" * 20,
                    "installed_at": "2024-01-15T10:30:00Z",
                    "file_path": str(
                        tmp_path / "mods" / "sodium-fabric-0.6.0+mc1.21.4.jar"
                    ),
                }
            },
        }
        state_path = tmp_path / ".mcpax-state.json"
        state_path.write_text(json.dumps(state_data))
        manager = ProjectManager(config)

        # Act
        state = await manager._load_state()

        # Assert
        assert state.version == 1
        assert "sodium" in state.files
        assert state.files["sodium"].slug == "sodium"
        assert state.files["sodium"].version_number == "0.6.0"

    async def test_saves_state_to_file(self, tmp_path: Path) -> None:
        """Saves state to JSON file."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        installed = _make_installed_file(
            "sodium",
            file_path=tmp_path / "mods" / "sodium.jar",
        )
        state = StateFile(
            version=1,
            files={"sodium": installed},
        )

        # Act
        await manager._save_state(state)

        # Assert
        state_path = tmp_path / ".mcpax-state.json"
        assert state_path.exists()
        saved_data = json.loads(state_path.read_text())
        assert saved_data["version"] == 1
        assert "sodium" in saved_data["files"]
        assert saved_data["files"]["sodium"]["slug"] == "sodium"

    async def test_raises_on_corrupted_state(self, tmp_path: Path) -> None:
        """Raises StateFileError on corrupted state file."""
        # Arrange
        config = _make_config(tmp_path)
        state_path = tmp_path / ".mcpax-state.json"
        state_path.write_text("invalid json{")
        manager = ProjectManager(config)

        # Act & Assert
        with pytest.raises(StateFileError) as exc_info:
            await manager._load_state()
        assert exc_info.value.path == state_path


class TestGetTargetDirectory:
    """Tests for F-401: get_target_directory."""

    def test_returns_mods_dir_for_mod_type(self, tmp_path: Path) -> None:
        """Returns mods directory for MOD project type."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        # Act
        result = manager.get_target_directory(ProjectType.MOD)

        # Assert
        assert result == tmp_path / "mods"

    def test_returns_shaderpacks_dir_for_shader_type(self, tmp_path: Path) -> None:
        """Returns shaderpacks directory for SHADER project type."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        # Act
        result = manager.get_target_directory(ProjectType.SHADER)

        # Assert
        assert result == tmp_path / "shaderpacks"

    def test_returns_resourcepacks_dir_for_resourcepack_type(
        self, tmp_path: Path
    ) -> None:
        """Returns resourcepacks directory for RESOURCEPACK project type."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        # Act
        result = manager.get_target_directory(ProjectType.RESOURCEPACK)

        # Assert
        assert result == tmp_path / "resourcepacks"

    def test_returns_custom_mods_dir_when_configured(self, tmp_path: Path) -> None:
        """Returns custom mods_dir when specified in config."""
        # Arrange
        custom_mods_dir = tmp_path / "custom_mods"
        config = AppConfig(
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
            minecraft_dir=tmp_path,
            mods_dir=custom_mods_dir,
        )
        manager = ProjectManager(config)

        # Act
        result = manager.get_target_directory(ProjectType.MOD)

        # Assert
        assert result == custom_mods_dir


class TestPlaceFile:
    """Tests for F-402: place_file."""

    async def test_moves_file_to_destination(self, tmp_path: Path) -> None:
        """place_file moves file to destination directory."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        src_file = tmp_path / "src" / "test.jar"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("test content")
        dest_dir = tmp_path / "dest"

        # Act
        result = await manager.place_file(src_file, dest_dir)

        # Assert
        assert result == dest_dir / "test.jar"
        assert result.exists()
        assert result.read_text() == "test content"
        assert not src_file.exists()

    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """place_file creates parent directories if needed."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        src_file = tmp_path / "test.jar"
        src_file.write_text("test content")
        dest_dir = tmp_path / "nested" / "dirs" / "dest"

        # Act
        result = await manager.place_file(src_file, dest_dir)

        # Assert
        assert result.exists()
        assert result.parent == dest_dir
        assert dest_dir.exists()


class TestBackupFile:
    """Tests for F-403: backup_file."""

    async def test_creates_timestamped_backup(self, tmp_path: Path) -> None:
        """backup_file creates timestamped backup."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        file_path = tmp_path / "test.jar"
        file_path.write_text("original content")

        # Act
        backup_path = await manager.backup_file(file_path)

        # Assert
        assert backup_path.exists()
        assert backup_path.read_text() == "original content"
        assert backup_path.parent == tmp_path / ".mcpax-backup"
        assert backup_path.stem.startswith("test_")
        assert backup_path.suffix == ".jar"

    async def test_uses_default_backup_dir(self, tmp_path: Path) -> None:
        """backup_file uses .mcpax-backup by default."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        file_path = tmp_path / "test.jar"
        file_path.write_text("content")

        # Act
        backup_path = await manager.backup_file(file_path)

        # Assert
        assert backup_path.parent == tmp_path / ".mcpax-backup"

    async def test_uses_custom_backup_dir(self, tmp_path: Path) -> None:
        """backup_file uses custom backup directory when specified."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        file_path = tmp_path / "test.jar"
        file_path.write_text("content")
        custom_backup = tmp_path / "custom_backup"

        # Act
        backup_path = await manager.backup_file(file_path, backup_dir=custom_backup)

        # Assert
        assert backup_path.parent == custom_backup
        assert custom_backup.exists()


class TestDeleteFile:
    """Tests for F-404: delete_file."""

    async def test_deletes_existing_file(self, tmp_path: Path) -> None:
        """delete_file removes existing file."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        file_path = tmp_path / "test.jar"
        file_path.write_text("content")

        # Act
        result = await manager.delete_file(file_path)

        # Assert
        assert result is True
        assert not file_path.exists()

    async def test_returns_false_for_nonexistent_file(self, tmp_path: Path) -> None:
        """delete_file returns False for nonexistent file."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        file_path = tmp_path / "nonexistent.jar"

        # Act
        result = await manager.delete_file(file_path)

        # Assert
        assert result is False


class TestGetInstalledFile:
    """Tests for F-406: get_installed_file."""

    async def test_returns_installed_file_from_state(self, tmp_path: Path) -> None:
        """Returns InstalledFile when slug exists in state."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)
        installed = _make_installed_file(
            "sodium",
            file_path=tmp_path / "mods" / "sodium.jar",
        )
        state = StateFile(version=1, files={"sodium": installed})
        await manager._save_state(state)

        # Act
        result = await manager.get_installed_file("sodium")

        # Assert
        assert result is not None
        assert result.slug == "sodium"
        assert result.version_number == "1.0.0"

    async def test_returns_none_when_not_in_state(self, tmp_path: Path) -> None:
        """Returns None when slug not in state."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        # Act
        result = await manager.get_installed_file("nonexistent")

        # Assert
        assert result is None


class TestGetInstallStatus:
    """Tests for F-405: get_install_status."""

    async def test_returns_not_installed_when_no_state(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns NOT_INSTALLED when not in state."""
        # Arrange
        config = _make_config(tmp_path)

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.NOT_INSTALLED

    async def test_returns_not_installed_when_file_missing(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns NOT_INSTALLED when file no longer exists."""
        # Arrange
        config = _make_config(tmp_path)
        manager_temp = ProjectManager(config)
        installed = _make_installed_file(
            "sodium",
            file_path=tmp_path / "mods" / "missing.jar",  # File doesn't exist
        )
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.NOT_INSTALLED

    async def test_returns_installed_when_hash_matches(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns INSTALLED when hash matches latest."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        test_hash = "abc123" * 20
        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
            sha512=test_hash,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        # Mock API responses
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/sodium/version",
            json=[
                {
                    "id": "version-id",
                    "project_id": "AANobbMI",
                    "version_number": "1.0.0",
                    "version_type": "release",
                    "game_versions": ["1.21.4"],
                    "loaders": ["fabric"],
                    "files": [
                        {
                            "url": "https://cdn.modrinth.com/sodium.jar",
                            "filename": "sodium.jar",
                            "size": 1024,
                            "hashes": {"sha512": test_hash},
                            "primary": True,
                        }
                    ],
                    "dependencies": [],
                    "date_published": "2024-01-15T10:30:00Z",
                }
            ],
        )

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.INSTALLED

    async def test_returns_outdated_when_hash_differs(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns OUTDATED when hash differs from latest."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        old_hash = "old123" * 20
        new_hash = "new456" * 20

        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
            sha512=old_hash,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        # Mock API responses
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/sodium/version",
            json=[
                {
                    "id": "version-id",
                    "project_id": "AANobbMI",
                    "version_number": "1.1.0",
                    "version_type": "release",
                    "game_versions": ["1.21.4"],
                    "loaders": ["fabric"],
                    "files": [
                        {
                            "url": "https://cdn.modrinth.com/sodium.jar",
                            "filename": "sodium.jar",
                            "size": 1024,
                            "hashes": {"sha512": new_hash},
                            "primary": True,
                        }
                    ],
                    "dependencies": [],
                    "date_published": "2024-01-15T10:30:00Z",
                }
            ],
        )

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.OUTDATED

    async def test_returns_not_compatible_when_no_version(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns NOT_COMPATIBLE when no compatible version exists."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        # Mock API responses - incompatible version
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/sodium/version",
            json=[
                {
                    "id": "version-id",
                    "project_id": "AANobbMI",
                    "version_number": "1.0.0",
                    "version_type": "release",
                    "game_versions": ["1.20.0"],  # Wrong Minecraft version
                    "loaders": ["fabric"],
                    "files": [
                        {
                            "url": "https://cdn.modrinth.com/sodium.jar",
                            "filename": "sodium.jar",
                            "size": 1024,
                            "hashes": {"sha512": "abc123" * 20},
                            "primary": True,
                        }
                    ],
                    "dependencies": [],
                    "date_published": "2024-01-15T10:30:00Z",
                }
            ],
        )

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.NOT_COMPATIBLE

    async def test_returns_check_failed_on_api_error(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
        fast_api_client: ModrinthClient,
    ) -> None:
        """Returns CHECK_FAILED when API returns error."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        # Mock API to return 500 error (need to match multiple retries)
        for _ in range(4):  # max_retries + 1
            httpx_mock.add_response(
                url="https://api.modrinth.com/v2/project/sodium/version",
                status_code=500,
            )

        # Act
        async with (
            fast_api_client,
            ProjectManager(config, api_client=fast_api_client) as manager,
        ):
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.CHECK_FAILED

    async def test_returns_check_failed_on_network_error(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns CHECK_FAILED when network error occurs."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        # Mock network timeout (needs 4 times for retries)
        for _ in range(4):  # max_retries (3) + 1
            httpx_mock.add_exception(
                httpx.TimeoutException("Connection timed out"),
                url="https://api.modrinth.com/v2/project/sodium/version",
            )

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.CHECK_FAILED

    async def test_returns_check_failed_on_rate_limit(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns CHECK_FAILED when rate limit exceeded."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        # Mock API to return 429 rate limit
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/sodium/version",
            status_code=429,
            headers={"Retry-After": "60"},
        )

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("sodium")

        # Assert
        assert result == InstallStatus.CHECK_FAILED

    async def test_returns_check_failed_on_project_not_found(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Returns CHECK_FAILED when project no longer exists on Modrinth."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "deleted-mod.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        installed = _make_installed_file(
            "deleted-mod",
            file_path=file_path,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"deleted-mod": installed})
        await manager_temp._save_state(state)

        # Mock API to return 404
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/deleted-mod/version",
            status_code=404,
        )

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status("deleted-mod")

        # Assert
        assert result == InstallStatus.CHECK_FAILED

    async def test_raises_runtime_error_when_not_initialized(
        self,
        tmp_path: Path,
    ) -> None:
        """Raises RuntimeError when API client not initialized."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
        )

        manager = ProjectManager(config)  # NOT using async context manager
        state = StateFile(version=1, files={"sodium": installed})
        await manager._save_state(state)

        # Act & Assert
        with pytest.raises(RuntimeError, match="API client not initialized"):
            await manager.get_install_status("sodium")


class TestGetInstallStatusWithChannel:
    """Tests for get_install_status with project channel."""

    async def test_respects_project_channel(
        self,
        tmp_path: Path,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Uses project channel when selecting latest compatible version."""
        # Arrange
        config = _make_config(tmp_path)
        file_path = tmp_path / "mods" / "sodium.jar"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")

        test_hash = "beta123" * 20
        installed = _make_installed_file(
            "sodium",
            file_path=file_path,
            sha512=test_hash,
        )

        manager_temp = ProjectManager(config)
        state = StateFile(version=1, files={"sodium": installed})
        await manager_temp._save_state(state)

        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/sodium/version",
            json=[
                {
                    "id": "version-id-beta",
                    "project_id": "AANobbMI",
                    "version_number": "1.1.0-beta",
                    "version_type": "beta",
                    "game_versions": ["1.21.4"],
                    "loaders": ["fabric"],
                    "files": [
                        {
                            "url": "https://cdn.modrinth.com/sodium.jar",
                            "filename": "sodium.jar",
                            "size": 1024,
                            "hashes": {"sha512": test_hash},
                            "primary": True,
                        }
                    ],
                    "dependencies": [],
                    "date_published": "2024-01-15T10:30:00Z",
                }
            ],
        )

        project_config = ProjectConfig(slug="sodium", channel=ReleaseChannel.BETA)

        # Act
        async with ProjectManager(config) as manager:
            result = await manager.get_install_status(
                "sodium",
                project_config=project_config,
            )

        # Assert
        assert result == InstallStatus.INSTALLED


class TestNeedsUpdate:
    """Tests for F-502: needs_update."""

    def test_returns_true_when_hashes_differ(self, tmp_path: Path) -> None:
        """Returns True when installed hash differs from latest."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        installed = _make_installed_file("sodium", sha512="old123" * 20)
        latest = ProjectFile(
            url="https://example.com/sodium.jar",
            filename="sodium.jar",
            size=1024,
            hashes={"sha512": "new456" * 20},
            primary=True,
        )

        # Act
        result = manager.needs_update(installed, latest)

        # Assert
        assert result is True

    def test_returns_false_when_hashes_match(self, tmp_path: Path) -> None:
        """Returns False when hashes match."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        same_hash = "abc123" * 20
        installed = _make_installed_file("sodium", sha512=same_hash)
        latest = ProjectFile(
            url="https://example.com/sodium.jar",
            filename="sodium.jar",
            size=1024,
            hashes={"sha512": same_hash},
            primary=True,
        )

        # Act
        result = manager.needs_update(installed, latest)

        # Assert
        assert result is False

    def test_returns_false_when_latest_is_none(self, tmp_path: Path) -> None:
        """Returns False when latest is None."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        installed = _make_installed_file("sodium")

        # Act
        result = manager.needs_update(installed, None)

        # Assert
        assert result is False

    def test_case_insensitive_hash_comparison(self, tmp_path: Path) -> None:
        """Hash comparison is case-insensitive."""
        # Arrange
        config = _make_config(tmp_path)
        manager = ProjectManager(config)

        installed = _make_installed_file("sodium", sha512="ABC123" * 20)
        latest = ProjectFile(
            url="https://example.com/sodium.jar",
            filename="sodium.jar",
            size=1024,
            hashes={"sha512": "abc123" * 20},  # lowercase
            primary=True,
        )

        # Act
        result = manager.needs_update(installed, latest)

        # Assert
        assert result is False
