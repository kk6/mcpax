"""Tests for mcpax.core.models."""

from datetime import UTC, datetime
from pathlib import Path

from mcpax.core.models import (
    AppConfig,
    Dependency,
    DependencyType,
    DownloadResult,
    DownloadTask,
    InstalledFile,
    InstallStatus,
    Loader,
    ModrinthProject,
    ProjectConfig,
    ProjectFile,
    ProjectType,
    ProjectVersion,
    ReleaseChannel,
    SearchHit,
    SearchResult,
    StateFile,
    UpdateCheckResult,
    UpdateResult,
)


class TestLoader:
    """Tests for Loader enum."""

    def test_loader_values(self) -> None:
        """Loader enum has correct values."""

        assert Loader.FABRIC.value == "fabric"
        assert Loader.FORGE.value == "forge"
        assert Loader.NEOFORGE.value == "neoforge"
        assert Loader.QUILT.value == "quilt"

    def test_loader_is_str(self) -> None:
        """Loader enum values are strings."""

        assert isinstance(Loader.FABRIC, str)
        assert Loader.FABRIC == "fabric"


class TestProjectType:
    """Tests for ProjectType enum."""

    def test_project_type_values(self) -> None:
        """ProjectType enum has correct values."""

        assert ProjectType.MOD.value == "mod"
        assert ProjectType.SHADER.value == "shader"
        assert ProjectType.RESOURCEPACK.value == "resourcepack"

    def test_project_type_is_str(self) -> None:
        """ProjectType enum values are strings."""

        assert isinstance(ProjectType.MOD, str)
        assert ProjectType.MOD == "mod"


class TestReleaseChannel:
    """Tests for ReleaseChannel enum."""

    def test_release_channel_values(self) -> None:
        """ReleaseChannel enum has correct values."""

        assert ReleaseChannel.RELEASE.value == "release"
        assert ReleaseChannel.BETA.value == "beta"
        assert ReleaseChannel.ALPHA.value == "alpha"

    def test_release_channel_is_str(self) -> None:
        """ReleaseChannel enum values are strings."""

        assert isinstance(ReleaseChannel.RELEASE, str)
        assert ReleaseChannel.RELEASE == "release"


class TestDependencyType:
    """Tests for DependencyType enum."""

    def test_dependency_type_values(self) -> None:
        """DependencyType enum has correct values."""

        assert DependencyType.REQUIRED.value == "required"
        assert DependencyType.OPTIONAL.value == "optional"
        assert DependencyType.INCOMPATIBLE.value == "incompatible"
        assert DependencyType.EMBEDDED.value == "embedded"

    def test_dependency_type_is_str(self) -> None:
        """DependencyType enum values are strings."""

        assert isinstance(DependencyType.REQUIRED, str)
        assert DependencyType.REQUIRED == "required"


class TestInstallStatus:
    """Tests for InstallStatus enum."""

    def test_install_status_values(self) -> None:
        """InstallStatus enum has correct values."""

        assert InstallStatus.NOT_INSTALLED.value == "not_installed"
        assert InstallStatus.INSTALLED.value == "installed"
        assert InstallStatus.OUTDATED.value == "outdated"
        assert InstallStatus.NOT_COMPATIBLE.value == "not_compatible"

    def test_install_status_is_str(self) -> None:
        """InstallStatus enum values are strings."""

        assert isinstance(InstallStatus.INSTALLED, str)
        assert InstallStatus.INSTALLED == "installed"


class TestDependency:
    """Tests for Dependency model."""

    def test_create_with_all_fields(self) -> None:
        """Dependency can be created with all fields."""

        dependency = Dependency(
            version_id="ABC123",
            project_id="XYZ789",
            file_name="optional-addon.jar",
            dependency_type=DependencyType.OPTIONAL,
        )

        assert dependency.version_id == "ABC123"
        assert dependency.project_id == "XYZ789"
        assert dependency.file_name == "optional-addon.jar"
        assert dependency.dependency_type == DependencyType.OPTIONAL


class TestAppConfig:
    """Tests for AppConfig model."""

    def test_create_with_required_fields(self) -> None:
        """AppConfig can be created with required fields."""

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

        config = ProjectConfig(slug="sodium")

        assert config.slug == "sodium"
        assert config.version is None
        assert config.channel == ReleaseChannel.RELEASE

    def test_create_with_all_fields(self) -> None:
        """ProjectConfig can be created with all fields."""

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

        hashes = {"sha512": "abc123def456", "sha1": "def789ghi012"}
        file = ProjectFile(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            filename="sodium-fabric-0.6.0+mc1.21.4.jar",
            size=1234567,
            hashes=hashes,
            primary=True,
        )

        assert file.url == "https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar"
        assert file.filename == "sodium-fabric-0.6.0+mc1.21.4.jar"
        assert file.size == 1234567
        assert file.hashes["sha512"] == "abc123def456"
        assert file.hashes["sha1"] == "def789ghi012"
        assert file.primary is True


class TestProjectVersion:
    """Tests for ProjectVersion model."""

    def test_create_with_all_fields(self) -> None:
        """ProjectVersion can be created with all fields."""

        date_published = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        hashes = {"sha512": "abc123def456", "sha1": "def789ghi012"}
        file = ProjectFile(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            filename="sodium-fabric-0.6.0+mc1.21.4.jar",
            size=1234567,
            hashes=hashes,
            primary=True,
        )
        dependency = Dependency(
            version_id=None,
            project_id="XYZ789",
            file_name=None,
            dependency_type=DependencyType.OPTIONAL,
        )

        version = ProjectVersion(
            id="ABC123",
            project_id="AANobbMI",
            version_number="0.6.0",
            version_type=ReleaseChannel.RELEASE,
            game_versions=["1.21.4", "1.21.3"],
            loaders=["fabric", "quilt"],
            files=[file],
            dependencies=[dependency],
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
        assert version.dependencies == [dependency]
        assert version.date_published == date_published


class TestSearchHit:
    """Tests for SearchHit model."""

    def test_create_with_all_fields(self) -> None:
        """SearchHit can be created with all fields."""

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
        hashes = {"sha512": "new_hash", "sha1": "new_hash_sha1"}
        latest_file = ProjectFile(
            url="https://cdn.modrinth.com/data/xxx/versions/yyy/sodium.jar",
            filename="sodium-fabric-0.6.0+mc1.21.4.jar",
            size=1234567,
            hashes=hashes,
            primary=True,
        )

        result = UpdateCheckResult(
            slug="sodium",
            status=InstallStatus.OUTDATED,
            current_version="0.5.0",
            current_file=current_file,
            latest_version="0.6.0",
            latest_version_id="NEW456",
            latest_file=latest_file,
        )

        assert result.slug == "sodium"
        assert result.status == InstallStatus.OUTDATED
        assert result.current_version == "0.5.0"
        assert result.current_file == current_file
        assert result.latest_version == "0.6.0"
        assert result.latest_version_id == "NEW456"
        assert result.latest_file == latest_file

    def test_create_not_installed(self) -> None:
        """UpdateCheckResult can be created for not installed project."""

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
        assert result.latest_version_id is None


class TestStateFile:
    """Tests for StateFile model."""

    def test_defaults(self) -> None:
        """StateFile defaults to version 1 with empty files."""
        state = StateFile()

        assert state.version == 1
        assert state.files == {}

    def test_create_with_files(self) -> None:
        """StateFile can be created with InstalledFile entries."""
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

        state = StateFile(version=2, files={"sodium": installed})

        assert state.version == 2
        assert state.files["sodium"] == installed


class TestUpdateResult:
    """Tests for UpdateResult model."""

    def test_create_with_results(self) -> None:
        """UpdateResult can be created with success and failure lists."""
        result = UpdateResult(
            successful=["sodium"],
            failed=[("iris", "download failed")],
            backed_up=[Path("/tmp/sodium.jar")],
        )

        assert result.successful == ["sodium"]
        assert result.failed == [("iris", "download failed")]
        assert result.backed_up == [Path("/tmp/sodium.jar")]


class TestDownloadTask:
    """Tests for DownloadTask model."""

    def test_create_with_all_fields(self) -> None:
        """DownloadTask can be created with all fields."""

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
