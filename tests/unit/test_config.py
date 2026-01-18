"""Tests for mcpax.core.config."""

from pathlib import Path

import pytest

from mcpax.core.config import (
    ConfigValidationError,
    ValidationError,
    generate_config,
    generate_projects,
    get_config_dir,
    get_default_config_path,
    get_default_projects_path,
    load_config,
    load_projects,
    resolve_path,
    save_projects,
    validate_config,
)
from mcpax.core.models import (
    AppConfig,
    Loader,
    ProjectConfig,
    ProjectType,
    ReleaseChannel,
)


class TestGetConfigDir:
    """Tests for get_config_dir function."""

    def test_uses_xdg_config_home_when_set(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """get_config_dir uses XDG_CONFIG_HOME when set."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = get_config_dir()

        # Assert
        assert result == tmp_path / "mcpax"

    def test_uses_default_when_xdg_config_home_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_config_dir uses ~/.config/mcpax when XDG_CONFIG_HOME not set."""
        # Arrange
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        # Act
        result = get_config_dir()

        # Assert
        assert result == Path.home() / ".config" / "mcpax"

    def test_uses_default_when_xdg_config_home_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_config_dir uses default when XDG_CONFIG_HOME is empty."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", "")

        # Act
        result = get_config_dir()

        # Assert
        assert result == Path.home() / ".config" / "mcpax"

    def test_uses_default_when_xdg_config_home_whitespace(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_config_dir uses default when XDG_CONFIG_HOME is whitespace."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", "   ")

        # Act
        result = get_config_dir()

        # Assert
        assert result == Path.home() / ".config" / "mcpax"


class TestGetDefaultConfigPath:
    """Tests for get_default_config_path function."""

    def test_returns_config_toml_in_config_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """get_default_config_path returns config.toml in config directory."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = get_default_config_path()

        # Assert
        assert result == tmp_path / "mcpax" / "config.toml"

    def test_uses_default_config_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_default_config_path uses default config directory."""
        # Arrange
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        # Act
        result = get_default_config_path()

        # Assert
        assert result == Path.home() / ".config" / "mcpax" / "config.toml"


class TestGetDefaultProjectsPath:
    """Tests for get_default_projects_path function."""

    def test_returns_projects_toml_in_config_dir(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """get_default_projects_path returns projects.toml in config directory."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = get_default_projects_path()

        # Assert
        assert result == tmp_path / "mcpax" / "projects.toml"

    def test_uses_default_config_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_default_projects_path uses default config directory."""
        # Arrange
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        # Act
        result = get_default_projects_path()

        # Assert
        assert result == Path.home() / ".config" / "mcpax" / "projects.toml"


class TestResolvePath:
    """Tests for resolve_path function."""

    def test_expand_tilde(self) -> None:
        """resolve_path expands ~ to home directory."""
        # Arrange
        home = Path.home()

        # Act
        result = resolve_path("~")

        # Assert
        assert result == home
        assert result.is_absolute()

    def test_expand_tilde_with_subdirectory(self) -> None:
        """resolve_path expands ~/subdir correctly."""
        # Arrange
        home = Path.home()

        # Act
        result = resolve_path("~/subdir")

        # Assert
        assert result == home / "subdir"
        assert result.is_absolute()

    def test_relative_path_to_absolute(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """resolve_path converts relative path to absolute."""
        # Arrange
        monkeypatch.chdir(tmp_path)

        # Act
        result = resolve_path("./relative")

        # Assert
        assert result == tmp_path / "relative"
        assert result.is_absolute()

    def test_absolute_path_unchanged(self, tmp_path: Path) -> None:
        """resolve_path returns absolute path as-is."""
        # Arrange
        absolute = tmp_path / "absolute"

        # Act
        result = resolve_path(absolute)

        # Assert
        assert result == absolute
        assert result.is_absolute()

    def test_string_input(self) -> None:
        """resolve_path accepts string input."""
        # Arrange
        path_str = "~/test"

        # Act
        result = resolve_path(path_str)

        # Assert
        assert isinstance(result, Path)
        assert result.is_absolute()

    def test_path_input(self) -> None:
        """resolve_path accepts Path input."""
        # Arrange
        path_obj = Path("~/test")

        # Act
        result = resolve_path(path_obj)

        # Assert
        assert isinstance(result, Path)
        assert result.is_absolute()


class TestValidationError:
    """Tests for ValidationError class."""

    def test_stores_field_and_message(self) -> None:
        """ValidationError stores field name and message."""
        # Arrange & Act
        error = ValidationError(field="test_field", message="test message")

        # Assert
        assert error.field == "test_field"
        assert error.message == "test message"


class TestConfigValidationError:
    """Tests for ConfigValidationError class."""

    def test_inherits_from_exception(self) -> None:
        """ConfigValidationError inherits from Exception."""
        # Arrange & Act
        error = ConfigValidationError("test")

        # Assert
        assert isinstance(error, Exception)

    def test_stores_message(self) -> None:
        """ConfigValidationError stores error message."""
        # Arrange & Act
        error = ConfigValidationError("test message")

        # Assert
        assert str(error) == "test message"

    def test_stores_errors_list(self) -> None:
        """ConfigValidationError stores list of validation errors."""
        # Arrange
        errors = [
            ValidationError(field="field1", message="error1"),
            ValidationError(field="field2", message="error2"),
        ]

        # Act
        error = ConfigValidationError("Multiple errors", errors=errors)

        # Assert
        assert error.errors == errors
        assert len(error.errors) == 2

    def test_errors_defaults_to_empty_list(self) -> None:
        """ConfigValidationError errors defaults to empty list."""
        # Arrange & Act
        error = ConfigValidationError("test")

        # Assert
        assert error.errors == []


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, sample_config: Path) -> None:
        """load_config loads valid config.toml successfully."""
        # Arrange & Act
        config = load_config(sample_config)

        # Assert
        assert isinstance(config, AppConfig)
        assert config.minecraft_version == "1.21.4"
        assert config.mod_loader == Loader.FABRIC

    def test_load_config_returns_app_config(self, sample_config: Path) -> None:
        """load_config returns AppConfig instance."""
        # Arrange & Act
        config = load_config(sample_config)

        # Assert
        assert isinstance(config, AppConfig)

    def test_load_config_file_not_found(self, tmp_path: Path) -> None:
        """load_config raises FileNotFoundError for missing file."""
        # Arrange
        nonexistent = tmp_path / "nonexistent.toml"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            load_config(nonexistent)

    def test_load_config_invalid_toml(self, tmp_path: Path) -> None:
        """load_config raises ConfigValidationError for invalid TOML."""
        # Arrange
        invalid_toml = tmp_path / "invalid.toml"
        invalid_toml.write_text("this is not valid TOML {{{")

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_config(invalid_toml)

    def test_load_config_missing_required_fields(self, tmp_path: Path) -> None:
        """load_config raises ConfigValidationError for missing fields."""
        # Arrange
        incomplete = tmp_path / "incomplete.toml"
        incomplete.write_text("[minecraft]\nversion = '1.21.4'\n")

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_config(incomplete)

    def test_load_config_invalid_loader(self, tmp_path: Path) -> None:
        """load_config raises ConfigValidationError for invalid loader."""
        # Arrange
        invalid_loader = tmp_path / "invalid_loader.toml"
        invalid_loader.write_text(
            """
[minecraft]
version = "1.21.4"
mod_loader = "invalid_loader"

[paths]
minecraft_dir = "~/.minecraft"
"""
        )

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_config(invalid_loader)

    def test_load_config_with_download_section(self, tmp_path: Path) -> None:
        """load_config reads download section correctly."""
        # Arrange
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"

[download]
max_concurrent = 10
verify_hash = false
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.max_concurrent_downloads == 10
        assert config.verify_hash is False

    def test_load_config_requires_mod_loader(self, tmp_path: Path) -> None:
        """load_config requires mod_loader field."""
        # Arrange
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[minecraft]
version = "1.21.4"
loader = "fabric"

[paths]
minecraft_dir = "~/.minecraft"
"""
        )

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_config(config_file)

    def test_load_config_expands_paths(self, tmp_path: Path) -> None:
        """load_config expands ~ in paths."""
        # Arrange
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "~/test_minecraft"
"""
        )

        # Act
        config = load_config(config_file)

        # Assert
        assert config.minecraft_dir.is_absolute()
        assert "~" not in str(config.minecraft_dir)


class TestGenerateConfig:
    """Tests for generate_config function."""

    def test_generate_config_creates_file(self, tmp_path: Path) -> None:
        """generate_config creates config.toml."""
        # Arrange
        config_path = tmp_path / "config.toml"

        # Act
        generate_config(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=Path("~/.minecraft"),
            path=config_path,
        )

        # Assert
        assert config_path.exists()

    def test_generate_config_returns_path(self, tmp_path: Path) -> None:
        """generate_config returns path to created file."""
        # Arrange
        config_path = tmp_path / "config.toml"

        # Act
        result = generate_config(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=Path("~/.minecraft"),
            path=config_path,
        )

        # Assert
        assert result == config_path

    def test_generate_config_content_structure(self, tmp_path: Path) -> None:
        """generate_config creates valid TOML structure."""
        # Arrange
        config_path = tmp_path / "config.toml"

        # Act
        generate_config(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=Path("~/.minecraft"),
            path=config_path,
        )

        # Assert
        content = config_path.read_text()
        assert "[minecraft]" in content
        assert "[paths]" in content
        assert "[download]" in content

    def test_generate_config_file_exists_raises_error(self, tmp_path: Path) -> None:
        """generate_config raises FileExistsError if file exists."""
        # Arrange
        config_path = tmp_path / "config.toml"
        config_path.write_text("existing content")

        # Act & Assert
        with pytest.raises(FileExistsError):
            generate_config(
                minecraft_version="1.21.4",
                mod_loader=Loader.FABRIC,
                minecraft_dir=Path("~/.minecraft"),
                path=config_path,
            )

    def test_generate_config_force_overwrites(self, tmp_path: Path) -> None:
        """generate_config with force=True overwrites existing file."""
        # Arrange
        config_path = tmp_path / "config.toml"
        config_path.write_text("existing content")

        # Act
        generate_config(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=Path("~/.minecraft"),
            path=config_path,
            force=True,
        )

        # Assert
        content = config_path.read_text()
        assert "existing content" not in content
        assert "[minecraft]" in content

    def test_generate_config_all_loaders(self, tmp_path: Path) -> None:
        """generate_config accepts all Loader types."""
        # Arrange & Act
        for loader in Loader:
            config_path = tmp_path / f"config_{loader.value}.toml"
            generate_config(
                minecraft_version="1.21.4",
                mod_loader=loader,
                minecraft_dir=Path("~/.minecraft"),
                path=config_path,
            )

            # Assert
            assert config_path.exists()
            content = config_path.read_text()
            assert f'mod_loader = "{loader.value}"' in content

    def test_generate_config_roundtrip(self, tmp_path: Path) -> None:
        """Generated config can be loaded back."""
        # Arrange
        config_path = tmp_path / "config.toml"
        minecraft_dir = tmp_path / "minecraft"
        minecraft_dir.mkdir()

        # Act
        generate_config(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=minecraft_dir,
            path=config_path,
        )
        loaded = load_config(config_path)

        # Assert
        assert loaded.minecraft_version == "1.21.4"
        assert loaded.mod_loader == Loader.FABRIC
        assert loaded.minecraft_dir == minecraft_dir.resolve()


class TestLoadProjects:
    """Tests for load_projects function."""

    def test_load_valid_projects(self, sample_projects: Path) -> None:
        """load_projects loads valid projects.toml successfully."""
        # Arrange & Act
        projects = load_projects(sample_projects)

        # Assert
        assert len(projects) == 3
        assert projects[0].slug == "fabric-api"
        assert projects[1].slug == "sodium"
        assert projects[2].slug == "complementary-unbound"

    def test_load_projects_returns_list(self, sample_projects: Path) -> None:
        """load_projects returns list of ProjectConfig."""
        # Arrange & Act
        projects = load_projects(sample_projects)

        # Assert
        assert isinstance(projects, list)
        assert all(isinstance(p, ProjectConfig) for p in projects)

    def test_load_projects_file_not_found(self, tmp_path: Path) -> None:
        """load_projects raises FileNotFoundError for missing file."""
        # Arrange
        nonexistent = tmp_path / "nonexistent.toml"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            load_projects(nonexistent)

    def test_load_projects_empty_file(self, tmp_path: Path) -> None:
        """load_projects returns empty list for empty projects."""
        # Arrange
        empty_file = tmp_path / "empty.toml"
        empty_file.write_text("")

        # Act
        projects = load_projects(empty_file)

        # Assert
        assert projects == []

    def test_load_projects_with_version(self, tmp_path: Path) -> None:
        """load_projects parses version field."""
        # Arrange
        projects_file = tmp_path / "projects.toml"
        projects_file.write_text(
            """
[[projects]]
slug = "fabric-api"
project_type = "mod"
version = "0.100.0"
"""
        )

        # Act
        projects = load_projects(projects_file)

        # Assert
        assert len(projects) == 1
        assert projects[0].version == "0.100.0"

    def test_load_projects_with_channel(self, tmp_path: Path) -> None:
        """load_projects parses channel field."""
        # Arrange
        projects_file = tmp_path / "projects.toml"
        projects_file.write_text(
            """
[[projects]]
slug = "sodium"
project_type = "mod"
channel = "beta"
"""
        )

        # Act
        projects = load_projects(projects_file)

        # Assert
        assert len(projects) == 1
        assert projects[0].channel == ReleaseChannel.BETA

    def test_load_projects_default_channel(self, tmp_path: Path) -> None:
        """load_projects uses release as default channel."""
        # Arrange
        projects_file = tmp_path / "projects.toml"
        projects_file.write_text(
            """
[[projects]]
slug = "fabric-api"
project_type = "mod"
"""
        )

        # Act
        projects = load_projects(projects_file)

        # Assert
        assert len(projects) == 1
        assert projects[0].channel == ReleaseChannel.RELEASE

    def test_load_projects_invalid_toml(self, tmp_path: Path) -> None:
        """load_projects raises ConfigValidationError for invalid TOML."""
        # Arrange
        invalid_toml = tmp_path / "invalid.toml"
        invalid_toml.write_text("this is not valid TOML {{{")

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_projects(invalid_toml)

    def test_load_projects_missing_slug(self, tmp_path: Path) -> None:
        """load_projects raises ConfigValidationError for missing slug."""
        # Arrange
        projects_file = tmp_path / "projects.toml"
        projects_file.write_text(
            """
[[projects]]
version = "0.100.0"
"""
        )

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_projects(projects_file)

    def test_load_projects_invalid_channel(self, tmp_path: Path) -> None:
        """load_projects raises ConfigValidationError for invalid channel."""
        # Arrange
        projects_file = tmp_path / "projects.toml"
        projects_file.write_text(
            """
[[projects]]
slug = "fabric-api"
project_type = "mod"
channel = "invalid_channel"
"""
        )

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_projects(projects_file)

    def test_load_projects_with_project_type(self, tmp_path: Path) -> None:
        """load_projects parses project_type field."""
        # Arrange
        projects_file = tmp_path / "projects.toml"
        projects_file.write_text(
            """
[[projects]]
slug = "sodium"
project_type = "mod"
"""
        )

        # Act
        projects = load_projects(projects_file)

        # Assert
        assert len(projects) == 1
        assert projects[0].project_type == ProjectType.MOD

    def test_load_projects_requires_project_type(self, tmp_path: Path) -> None:
        """load_projects requires project_type."""
        # Arrange
        projects_file = tmp_path / "projects.toml"
        projects_file.write_text(
            """
[[projects]]
slug = "sodium"
"""
        )

        # Act & Assert
        with pytest.raises(ConfigValidationError):
            load_projects(projects_file)


class TestGenerateProjects:
    """Tests for generate_projects function."""

    def test_generate_projects_creates_file(self, tmp_path: Path) -> None:
        """generate_projects creates projects.toml."""
        # Arrange
        projects_path = tmp_path / "projects.toml"

        # Act
        generate_projects(path=projects_path)

        # Assert
        assert projects_path.exists()

    def test_generate_projects_returns_path(self, tmp_path: Path) -> None:
        """generate_projects returns path to created file."""
        # Arrange
        projects_path = tmp_path / "projects.toml"

        # Act
        result = generate_projects(path=projects_path)

        # Assert
        assert result == projects_path

    def test_generate_projects_empty_content(self, tmp_path: Path) -> None:
        """generate_projects creates file with comments."""
        # Arrange
        projects_path = tmp_path / "projects.toml"

        # Act
        generate_projects(path=projects_path)

        # Assert
        content = projects_path.read_text()
        # Should have comments but no actual projects
        assert "#" in content or content.strip() == ""

    def test_generate_projects_file_exists_raises_error(self, tmp_path: Path) -> None:
        """generate_projects raises FileExistsError if file exists."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects_path.write_text("existing content")

        # Act & Assert
        with pytest.raises(FileExistsError):
            generate_projects(path=projects_path)

    def test_generate_projects_force_overwrites(self, tmp_path: Path) -> None:
        """generate_projects with force=True overwrites existing file."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects_path.write_text("existing content")

        # Act
        generate_projects(path=projects_path, force=True)

        # Assert
        content = projects_path.read_text()
        assert "existing content" not in content


class TestSaveProjects:
    """Tests for save_projects function."""

    def test_save_projects_creates_file(self, tmp_path: Path) -> None:
        """save_projects creates projects.toml."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects = [ProjectConfig(slug="fabric-api", project_type=ProjectType.MOD)]

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        assert projects_path.exists()

    def test_save_projects_returns_path(self, tmp_path: Path) -> None:
        """save_projects returns path to created file."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects = [ProjectConfig(slug="fabric-api", project_type=ProjectType.MOD)]

        # Act
        result = save_projects(projects, path=projects_path)

        # Assert
        assert result == projects_path

    def test_save_projects_content_structure(self, tmp_path: Path) -> None:
        """save_projects creates valid TOML structure."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects = [
            ProjectConfig(slug="fabric-api", project_type=ProjectType.MOD),
            ProjectConfig(slug="sodium", project_type=ProjectType.MOD),
        ]

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        content = projects_path.read_text()
        assert "[[projects]]" in content
        assert 'slug = "fabric-api"' in content
        assert 'slug = "sodium"' in content
        assert 'project_type = "mod"' in content

    def test_save_projects_empty_list(self, tmp_path: Path) -> None:
        """save_projects handles empty list."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects: list[ProjectConfig] = []

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        assert projects_path.exists()
        loaded = load_projects(projects_path)
        assert loaded == []

    def test_save_projects_with_version(self, tmp_path: Path) -> None:
        """save_projects includes version when specified."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects = [
            ProjectConfig(
                slug="fabric-api", project_type=ProjectType.MOD, version="0.100.0"
            )
        ]

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        content = projects_path.read_text()
        assert 'version = "0.100.0"' in content

    def test_save_projects_with_channel(self, tmp_path: Path) -> None:
        """save_projects includes channel when not release."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects = [
            ProjectConfig(
                slug="sodium", project_type=ProjectType.MOD, channel=ReleaseChannel.BETA
            )
        ]

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        content = projects_path.read_text()
        assert 'channel = "beta"' in content

    def test_save_projects_omits_default_channel(self, tmp_path: Path) -> None:
        """save_projects omits channel when release (default)."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects = [
            ProjectConfig(
                slug="fabric-api",
                project_type=ProjectType.MOD,
                channel=ReleaseChannel.RELEASE,
            )
        ]

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        content = projects_path.read_text()
        assert "channel" not in content

    def test_save_projects_with_project_type(self, tmp_path: Path) -> None:
        """save_projects includes project_type."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects = [ProjectConfig(slug="sodium", project_type=ProjectType.MOD)]

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        content = projects_path.read_text()
        assert 'project_type = "mod"' in content

    def test_save_projects_roundtrip(self, tmp_path: Path) -> None:
        """Saved projects can be loaded back."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        original = [
            ProjectConfig(slug="fabric-api", project_type=ProjectType.MOD),
            ProjectConfig(slug="sodium", version="0.6.0", project_type=ProjectType.MOD),
            ProjectConfig(
                slug="some-mod",
                project_type=ProjectType.MOD,
                channel=ReleaseChannel.BETA,
            ),
        ]

        # Act
        save_projects(original, path=projects_path)
        loaded = load_projects(projects_path)

        # Assert
        assert len(loaded) == 3
        assert loaded[0].slug == "fabric-api"
        assert loaded[1].slug == "sodium"
        assert loaded[1].version == "0.6.0"
        assert loaded[1].project_type == ProjectType.MOD
        assert loaded[2].slug == "some-mod"
        assert loaded[2].channel == ReleaseChannel.BETA

    def test_save_projects_overwrites_existing(self, tmp_path: Path) -> None:
        """save_projects overwrites existing file."""
        # Arrange
        projects_path = tmp_path / "projects.toml"
        projects_path.write_text("old content")
        projects = [ProjectConfig(slug="new-project", project_type=ProjectType.MOD)]

        # Act
        save_projects(projects, path=projects_path)

        # Assert
        content = projects_path.read_text()
        assert "old content" not in content
        assert 'slug = "new-project"' in content


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config_returns_empty_list(self, tmp_path: Path) -> None:
        """validate_config returns empty list for valid config."""
        # Arrange
        minecraft_dir = tmp_path / "minecraft"
        minecraft_dir.mkdir()
        config = AppConfig(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=minecraft_dir,
        )

        # Act
        errors = validate_config(config)

        # Assert
        assert errors == []

    def test_invalid_minecraft_version_format(self) -> None:
        """validate_config detects invalid minecraft_version format."""
        # Arrange
        config = AppConfig(
            minecraft_version="invalid",
            mod_loader=Loader.FABRIC,
            minecraft_dir=Path("/tmp"),
        )

        # Act
        errors = validate_config(config)

        # Assert
        assert len(errors) > 0
        assert any(e.field == "minecraft_version" for e in errors)

    def test_valid_minecraft_version_formats(self, tmp_path: Path) -> None:
        """validate_config accepts valid version formats."""
        # Arrange
        minecraft_dir = tmp_path / "minecraft"
        minecraft_dir.mkdir()
        valid_versions = ["1.21.4", "1.21", "1.21.4-pre1", "1.20.1"]

        # Act & Assert
        for version in valid_versions:
            config = AppConfig(
                minecraft_version=version,
                mod_loader=Loader.FABRIC,
                minecraft_dir=minecraft_dir,
            )
            errors = validate_config(config)
            version_errors = [e for e in errors if e.field == "minecraft_version"]
            assert len(version_errors) == 0, f"Version {version} should be valid"

    def test_minecraft_dir_not_exists(self, tmp_path: Path) -> None:
        """validate_config detects non-existent minecraft_dir."""
        # Arrange
        nonexistent_dir = tmp_path / "nonexistent"
        config = AppConfig(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=nonexistent_dir,
        )

        # Act
        errors = validate_config(config)

        # Assert
        assert len(errors) > 0
        assert any(e.field == "minecraft_dir" for e in errors)

    def test_minecraft_dir_exists(self, tmp_path: Path) -> None:
        """validate_config passes for existing minecraft_dir."""
        # Arrange
        minecraft_dir = tmp_path / "minecraft"
        minecraft_dir.mkdir()
        config = AppConfig(
            minecraft_version="1.21.4",
            mod_loader=Loader.FABRIC,
            minecraft_dir=minecraft_dir,
        )

        # Act
        errors = validate_config(config)

        # Assert
        dir_errors = [e for e in errors if e.field == "minecraft_dir"]
        assert len(dir_errors) == 0

    def test_multiple_errors(self, tmp_path: Path) -> None:
        """validate_config returns all errors."""
        # Arrange
        config = AppConfig(
            minecraft_version="invalid",
            mod_loader=Loader.FABRIC,
            minecraft_dir=tmp_path / "nonexistent",
        )

        # Act
        errors = validate_config(config)

        # Assert
        assert len(errors) == 2
        fields = {e.field for e in errors}
        assert "minecraft_version" in fields
        assert "minecraft_dir" in fields

    def test_error_includes_field_name(self, tmp_path: Path) -> None:
        """ValidationError includes field name."""
        # Arrange
        config = AppConfig(
            minecraft_version="invalid",
            mod_loader=Loader.FABRIC,
            minecraft_dir=tmp_path,
        )

        # Act
        errors = validate_config(config)

        # Assert
        assert len(errors) > 0
        assert all(isinstance(e.field, str) for e in errors)
        assert all(e.field != "" for e in errors)

    def test_error_includes_message(self, tmp_path: Path) -> None:
        """ValidationError includes descriptive message."""
        # Arrange
        config = AppConfig(
            minecraft_version="invalid",
            mod_loader=Loader.FABRIC,
            minecraft_dir=tmp_path,
        )

        # Act
        errors = validate_config(config)

        # Assert
        assert len(errors) > 0
        assert all(isinstance(e.message, str) for e in errors)
        assert all(e.message != "" for e in errors)
