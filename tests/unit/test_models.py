"""Tests for mcpax.core.models."""

from datetime import UTC, datetime
from pathlib import Path


class TestLoader:
    """Tests for Loader enum."""

    def test_loader_values(self) -> None:
        """Loader enum has correct values."""
        from mcpax.core.models import Loader

        assert Loader.FABRIC.value == "fabric"
        assert Loader.FORGE.value == "forge"
        assert Loader.NEOFORGE.value == "neoforge"
        assert Loader.QUILT.value == "quilt"

    def test_loader_is_str(self) -> None:
        """Loader enum values are strings."""
        from mcpax.core.models import Loader

        assert isinstance(Loader.FABRIC, str)
        assert Loader.FABRIC == "fabric"


class TestProjectType:
    """Tests for ProjectType enum."""

    def test_project_type_values(self) -> None:
        """ProjectType enum has correct values."""
        from mcpax.core.models import ProjectType

        assert ProjectType.MOD.value == "mod"
        assert ProjectType.SHADER.value == "shader"
        assert ProjectType.RESOURCEPACK.value == "resourcepack"

    def test_project_type_is_str(self) -> None:
        """ProjectType enum values are strings."""
        from mcpax.core.models import ProjectType

        assert isinstance(ProjectType.MOD, str)
        assert ProjectType.MOD == "mod"


class TestReleaseChannel:
    """Tests for ReleaseChannel enum."""

    def test_release_channel_values(self) -> None:
        """ReleaseChannel enum has correct values."""
        from mcpax.core.models import ReleaseChannel

        assert ReleaseChannel.RELEASE.value == "release"
        assert ReleaseChannel.BETA.value == "beta"
        assert ReleaseChannel.ALPHA.value == "alpha"

    def test_release_channel_is_str(self) -> None:
        """ReleaseChannel enum values are strings."""
        from mcpax.core.models import ReleaseChannel

        assert isinstance(ReleaseChannel.RELEASE, str)
        assert ReleaseChannel.RELEASE == "release"


class TestInstallStatus:
    """Tests for InstallStatus enum."""

    def test_install_status_values(self) -> None:
        """InstallStatus enum has correct values."""
        from mcpax.core.models import InstallStatus

        assert InstallStatus.NOT_INSTALLED.value == "not_installed"
        assert InstallStatus.INSTALLED.value == "installed"
        assert InstallStatus.OUTDATED.value == "outdated"
        assert InstallStatus.NOT_COMPATIBLE.value == "not_compatible"

    def test_install_status_is_str(self) -> None:
        """InstallStatus enum values are strings."""
        from mcpax.core.models import InstallStatus

        assert isinstance(InstallStatus.INSTALLED, str)
        assert InstallStatus.INSTALLED == "installed"


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_create_with_required_fields(self) -> None:
        """AppConfig can be created with required fields."""
        from mcpax.core.models import AppConfig, Loader

        config = AppConfig(
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
            minecraft_dir=Path("~/.minecraft"),
        )

        assert config.minecraft_version == "1.21.4"
        assert config.loader == Loader.FABRIC
        assert config.minecraft_dir == Path("~/.minecraft")

    def test_default_values(self) -> None:
        """AppConfig has correct default values."""
        from mcpax.core.models import AppConfig, Loader

        config = AppConfig(
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
            minecraft_dir=Path("~/.minecraft"),
        )

        assert config.mods_dir is None
        assert config.shaders_dir is None
        assert config.resourcepacks_dir is None
        assert config.max_concurrent_downloads == 5
        assert config.verify_hash is True

    def test_custom_values(self) -> None:
        """AppConfig accepts custom values."""
        from mcpax.core.models import AppConfig, Loader

        config = AppConfig(
            minecraft_version="1.21.4",
            loader=Loader.FORGE,
            minecraft_dir=Path("/custom/minecraft"),
            mods_dir=Path("/custom/mods"),
            shaders_dir=Path("/custom/shaders"),
            resourcepacks_dir=Path("/custom/resourcepacks"),
            max_concurrent_downloads=10,
            verify_hash=False,
        )

        assert config.loader == Loader.FORGE
        assert config.minecraft_dir == Path("/custom/minecraft")
        assert config.mods_dir == Path("/custom/mods")
        assert config.shaders_dir == Path("/custom/shaders")
        assert config.resourcepacks_dir == Path("/custom/resourcepacks")
        assert config.max_concurrent_downloads == 10
        assert config.verify_hash is False


class TestProjectConfig:
    """Tests for ProjectConfig model."""

    def test_create_with_slug_only(self) -> None:
        """ProjectConfig can be created with slug only."""
        from mcpax.core.models import ProjectConfig, ReleaseChannel

        config = ProjectConfig(slug="sodium")

        assert config.slug == "sodium"
        assert config.version is None
        assert config.channel == ReleaseChannel.RELEASE

    def test_create_with_all_fields(self) -> None:
        """ProjectConfig can be created with all fields."""
        from mcpax.core.models import ProjectConfig, ReleaseChannel

        config = ProjectConfig(
            slug="sodium",
            version="0.6.0",
            channel=ReleaseChannel.BETA,
        )

        assert config.slug == "sodium"
        assert config.version == "0.6.0"
        assert config.channel == ReleaseChannel.BETA


class TestInstalledFile:
    """Tests for InstalledFile model."""

    def test_create_with_all_fields(self) -> None:
        """InstalledFile can be created with all fields."""
        from mcpax.core.models import InstalledFile, ProjectType

        installed_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        installed = InstalledFile(
            slug="sodium",
            project_type=ProjectType.MOD,
            filename="sodium-fabric-0.6.0+mc1.21.4.jar",
            version_id="ABC123",
            version_number="0.6.0",
            sha512="abc123def456",
            installed_at=installed_at,
            file_path=Path(
                "/home/user/.minecraft/mods/sodium-fabric-0.6.0+mc1.21.4.jar"
            ),
        )

        assert installed.slug == "sodium"
        assert installed.project_type == ProjectType.MOD
        assert installed.filename == "sodium-fabric-0.6.0+mc1.21.4.jar"
        assert installed.version_id == "ABC123"
        assert installed.version_number == "0.6.0"
        assert installed.sha512 == "abc123def456"
        assert installed.installed_at == installed_at
        assert installed.file_path == Path(
            "/home/user/.minecraft/mods/sodium-fabric-0.6.0+mc1.21.4.jar"
        )


class TestModrinthProject:
    """Tests for ModrinthProject model."""

    def test_create_with_all_fields(self) -> None:
        """ModrinthProject can be created with all fields."""
        from mcpax.core.models import ModrinthProject, ProjectType

        project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="A modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=12345678,
            icon_url="https://example.com/icon.png",
            versions=["ABC123", "DEF456"],
        )

        assert project.id == "AANobbMI"
        assert project.slug == "sodium"
        assert project.title == "Sodium"
        assert project.description == "A modern rendering engine"
        assert project.project_type == ProjectType.MOD
        assert project.downloads == 12345678
        assert project.icon_url == "https://example.com/icon.png"
        assert project.versions == ["ABC123", "DEF456"]

    def test_create_without_icon_url(self) -> None:
        """ModrinthProject can be created without icon_url."""
        from mcpax.core.models import ModrinthProject, ProjectType

        project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="A modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=12345678,
            icon_url=None,
            versions=["ABC123"],
        )

        assert project.icon_url is None


class TestProjectFile:
    """Tests for ProjectFile model."""

    def test_create_with_all_fields(self) -> None:
        """ProjectFile can be created with all fields."""
        from mcpax.core.models import ProjectFile

        file = ProjectFile(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            filename="sodium-fabric-0.6.0+mc1.21.4.jar",
            size=1234567,
            sha512="abc123def456",
            primary=True,
        )

        assert file.url == "https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar"
        assert file.filename == "sodium-fabric-0.6.0+mc1.21.4.jar"
        assert file.size == 1234567
        assert file.sha512 == "abc123def456"
        assert file.primary is True


class TestProjectVersion:
    """Tests for ProjectVersion model."""

    def test_create_with_all_fields(self) -> None:
        """ProjectVersion can be created with all fields."""
        from mcpax.core.models import ProjectFile, ProjectVersion, ReleaseChannel

        date_published = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        file = ProjectFile(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            filename="sodium-fabric-0.6.0+mc1.21.4.jar",
            size=1234567,
            sha512="abc123def456",
            primary=True,
        )

        version = ProjectVersion(
            id="ABC123",
            project_id="AANobbMI",
            version_number="0.6.0",
            version_type=ReleaseChannel.RELEASE,
            game_versions=["1.21.4", "1.21.3"],
            loaders=["fabric", "quilt"],
            files=[file],
            date_published=date_published,
        )

        assert version.id == "ABC123"
        assert version.project_id == "AANobbMI"
        assert version.version_number == "0.6.0"
        assert version.version_type == ReleaseChannel.RELEASE
        assert version.game_versions == ["1.21.4", "1.21.3"]
        assert version.loaders == ["fabric", "quilt"]
        assert len(version.files) == 1
        assert version.files[0].filename == "sodium-fabric-0.6.0+mc1.21.4.jar"
        assert version.date_published == date_published


class TestSearchHit:
    """Tests for SearchHit model."""

    def test_create_with_all_fields(self) -> None:
        """SearchHit can be created with all fields."""
        from mcpax.core.models import ProjectType, SearchHit

        hit = SearchHit(
            slug="sodium",
            title="Sodium",
            description="A modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=12345678,
            icon_url="https://example.com/icon.png",
        )

        assert hit.slug == "sodium"
        assert hit.title == "Sodium"
        assert hit.description == "A modern rendering engine"
        assert hit.project_type == ProjectType.MOD
        assert hit.downloads == 12345678
        assert hit.icon_url == "https://example.com/icon.png"


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_with_hits(self) -> None:
        """SearchResult can be created with hits."""
        from mcpax.core.models import ProjectType, SearchHit, SearchResult

        hit = SearchHit(
            slug="sodium",
            title="Sodium",
            description="A modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=12345678,
            icon_url=None,
        )

        result = SearchResult(
            hits=[hit],
            total_hits=100,
            offset=0,
            limit=10,
        )

        assert len(result.hits) == 1
        assert result.hits[0].slug == "sodium"
        assert result.total_hits == 100
        assert result.offset == 0
        assert result.limit == 10


class TestUpdateCheckResult:
    """Tests for UpdateCheckResult model."""

    def test_create_with_update_available(self) -> None:
        """UpdateCheckResult can be created with update available."""
        from mcpax.core.models import (
            InstalledFile,
            InstallStatus,
            ProjectFile,
            ProjectType,
            UpdateCheckResult,
        )

        installed_at = datetime(2024, 1, 10, 10, 0, 0, tzinfo=UTC)
        current_file = InstalledFile(
            slug="sodium",
            project_type=ProjectType.MOD,
            filename="sodium-fabric-0.5.0+mc1.21.4.jar",
            version_id="OLD123",
            version_number="0.5.0",
            sha512="old_hash",
            installed_at=installed_at,
            file_path=Path(
                "/home/user/.minecraft/mods/sodium-fabric-0.5.0+mc1.21.4.jar"
            ),
        )
        latest_file = ProjectFile(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            filename="sodium-fabric-0.6.0+mc1.21.4.jar",
            size=1234567,
            sha512="new_hash",
            primary=True,
        )

        result = UpdateCheckResult(
            slug="sodium",
            status=InstallStatus.OUTDATED,
            current_version="0.5.0",
            current_file=current_file,
            latest_version="0.6.0",
            latest_file=latest_file,
        )

        assert result.slug == "sodium"
        assert result.status == InstallStatus.OUTDATED
        assert result.current_version == "0.5.0"
        assert result.current_file == current_file
        assert result.latest_version == "0.6.0"
        assert result.latest_file == latest_file

    def test_create_not_installed(self) -> None:
        """UpdateCheckResult can be created for not installed project."""
        from mcpax.core.models import InstallStatus, UpdateCheckResult

        result = UpdateCheckResult(
            slug="sodium",
            status=InstallStatus.NOT_INSTALLED,
            current_version=None,
            current_file=None,
            latest_version="0.6.0",
            latest_file=None,
        )

        assert result.status == InstallStatus.NOT_INSTALLED
        assert result.current_version is None
        assert result.current_file is None


class TestDownloadTask:
    """Tests for DownloadTask model."""

    def test_create_with_all_fields(self) -> None:
        """DownloadTask can be created with all fields."""
        from mcpax.core.models import DownloadTask

        task = DownloadTask(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            dest=Path("/tmp/sodium.jar"),
            expected_hash="abc123def456",
            slug="sodium",
            version_number="0.6.0",
        )

        assert task.url == "https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar"
        assert task.dest == Path("/tmp/sodium.jar")
        assert task.expected_hash == "abc123def456"
        assert task.slug == "sodium"
        assert task.version_number == "0.6.0"

    def test_create_without_expected_hash(self) -> None:
        """DownloadTask can be created without expected_hash."""
        from mcpax.core.models import DownloadTask

        task = DownloadTask(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            dest=Path("/tmp/sodium.jar"),
            expected_hash=None,
            slug="sodium",
            version_number="0.6.0",
        )

        assert task.expected_hash is None


class TestDownloadResult:
    """Tests for DownloadResult model."""

    def test_create_success(self) -> None:
        """DownloadResult can be created for successful download."""
        from mcpax.core.models import DownloadResult, DownloadTask

        task = DownloadTask(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            dest=Path("/tmp/sodium.jar"),
            expected_hash="abc123def456",
            slug="sodium",
            version_number="0.6.0",
        )

        result = DownloadResult(
            task=task,
            success=True,
            file_path=Path("/tmp/sodium.jar"),
            error=None,
        )

        assert result.task == task
        assert result.success is True
        assert result.file_path == Path("/tmp/sodium.jar")
        assert result.error is None

    def test_create_failure(self) -> None:
        """DownloadResult can be created for failed download."""
        from mcpax.core.models import DownloadResult, DownloadTask

        task = DownloadTask(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            dest=Path("/tmp/sodium.jar"),
            expected_hash="abc123def456",
            slug="sodium",
            version_number="0.6.0",
        )

        result = DownloadResult(
            task=task,
            success=False,
            file_path=None,
            error="Hash mismatch",
        )

        assert result.task == task
        assert result.success is False
        assert result.file_path is None
        assert result.error == "Hash mismatch"
