"""Unit tests for CLI application."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcpax import __version__
from mcpax.cli.app import app

runner = CliRunner()


class TestVersion:
    """Tests for --version option."""

    def test_version_short_flag(self) -> None:
        """Test that -V shows version."""
        # Arrange & Act
        result = runner.invoke(app, ["-V"])

        # Assert
        assert result.exit_code == 0
        assert f"mcpax {__version__}" in result.stdout

    def test_version_long_flag(self) -> None:
        """Test that --version shows version."""
        # Arrange & Act
        result = runner.invoke(app, ["--version"])

        # Assert
        assert result.exit_code == 0
        assert f"mcpax {__version__}" in result.stdout


class TestStatus:
    """Tests for status command."""

    def test_status_command(self) -> None:
        """Test that status command shows expected message."""
        # Arrange & Act
        result = runner.invoke(app, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "No projects configured yet" in result.stdout


class TestHelp:
    """Tests for help display."""

    def test_no_args_shows_help(self) -> None:
        """Test that running without args shows help (with exit code 2)."""
        # Arrange & Act
        result = runner.invoke(app, [])

        # Assert
        # no_args_is_help=True causes exit code 2 (as per Click/Typer behavior)
        assert result.exit_code == 2
        assert "Minecraft MOD/Shader/Resource Pack manager" in result.stdout

    def test_help_flag(self) -> None:
        """Test that --help shows help."""
        # Arrange & Act
        result = runner.invoke(app, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "Minecraft MOD/Shader/Resource Pack manager" in result.stdout


class TestInitCommand:
    """Tests for init command."""

    def test_init_non_interactive_creates_config_file(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init -y creates config.toml."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["init", "-y"])

        # Assert
        assert result.exit_code == 0
        assert (tmp_path / "mcpax" / "config.toml").exists()

    def test_init_non_interactive_creates_projects_file(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init -y creates projects.toml."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["init", "-y"])

        # Assert
        assert result.exit_code == 0
        assert (tmp_path / "mcpax" / "projects.toml").exists()

    def test_init_non_interactive_uses_default_values(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init -y uses default values in config.toml."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["init", "-y"])

        # Assert
        assert result.exit_code == 0
        config_content = (tmp_path / "mcpax" / "config.toml").read_text()
        assert "1.21.4" in config_content
        assert "fabric" in config_content
        assert "~/.minecraft" in config_content

    def test_init_short_flag_y(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init with short flag -y works."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["init", "-y"])

        # Assert
        assert result.exit_code == 0
        assert (tmp_path / "mcpax" / "config.toml").exists()
        assert (tmp_path / "mcpax" / "projects.toml").exists()

    def test_init_fails_when_config_exists(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init fails when config.toml already exists."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config_dir = tmp_path / "mcpax"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.toml").write_text("")

        # Act
        result = runner.invoke(app, ["init", "-y"])

        # Assert
        assert result.exit_code == 1
        assert "config.toml already exists" in result.stdout
        assert "Use --force to overwrite" in result.stdout

    def test_init_fails_when_projects_exists(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init fails when projects.toml already exists."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config_dir = tmp_path / "mcpax"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "projects.toml").write_text("")

        # Act
        result = runner.invoke(app, ["init", "-y"])

        # Assert
        assert result.exit_code == 1
        assert "projects.toml already exists" in result.stdout
        assert "Use --force to overwrite" in result.stdout

    def test_init_force_overwrites_config(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init --force overwrites existing files."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config_dir = tmp_path / "mcpax"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.toml").write_text("old content")
        (config_dir / "projects.toml").write_text("old content")

        # Act
        result = runner.invoke(app, ["init", "-y", "--force"])

        # Assert
        assert result.exit_code == 0
        assert "old content" not in (config_dir / "config.toml").read_text()
        assert "old content" not in (config_dir / "projects.toml").read_text()

    def test_init_force_short_flag_f(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init -f short flag works."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        config_dir = tmp_path / "mcpax"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.toml").write_text("old")

        # Act
        result = runner.invoke(app, ["init", "-y", "-f"])

        # Assert
        assert result.exit_code == 0
        assert (config_dir / "config.toml").exists()

    def test_init_interactive_prompts_for_values(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init prompts for values in interactive mode."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(
            app, ["init"], input="1.20.1\nforge\n/custom/minecraft\n"
        )

        # Assert
        assert result.exit_code == 0
        config_content = (tmp_path / "mcpax" / "config.toml").read_text()
        assert "1.20.1" in config_content
        assert "forge" in config_content
        assert "/custom/minecraft" in config_content

    def test_init_interactive_uses_defaults_on_empty_input(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init uses defaults when user presses enter."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["init"], input="\n\n\n")

        # Assert
        assert result.exit_code == 0
        config_content = (tmp_path / "mcpax" / "config.toml").read_text()
        assert "1.21.4" in config_content
        assert "fabric" in config_content
        assert "~/.minecraft" in config_content

    def test_init_shows_success_message(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init shows success message."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["init", "-y"])

        # Assert
        assert result.exit_code == 0
        assert "Created" in result.stdout
        assert "config.toml" in result.stdout
        assert "projects.toml" in result.stdout
        assert "Initialization complete!" in result.stdout
        assert "Configuration stored in:" in result.stdout
        assert "mcpax add" in result.stdout
