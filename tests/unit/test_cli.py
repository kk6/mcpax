"""Unit tests for CLI application."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from mcpax import __version__
from mcpax.cli.app import app
from mcpax.core.exceptions import ProjectNotFoundError
from mcpax.core.models import ModrinthProject, ProjectType

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


class TestAddCommand:
    """Tests for add command."""

    def test_add_project_success(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that add command successfully adds a project."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine for Minecraft",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url="https://cdn.modrinth.com/...",
            versions=["v1", "v2"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)

            # Act
            result = runner.invoke(app, ["add", "sodium"])

        # Assert
        assert result.exit_code == 0
        assert "Sodium" in result.stdout
        assert "mod" in result.stdout

    def test_add_project_saves_to_projects_toml(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that add command saves project to projects.toml."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)

            # Act
            runner.invoke(app, ["add", "sodium"])

        # Assert
        projects_file = tmp_path / "mcpax" / "projects.toml"
        assert projects_file.exists()
        content = projects_file.read_text()
        assert "sodium" in content

    def test_add_project_with_version_option(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that add command with --version option works."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)

            # Act
            runner.invoke(app, ["add", "sodium", "--version", "0.5.0"])

        # Assert
        projects_file = tmp_path / "mcpax" / "projects.toml"
        content = projects_file.read_text()
        assert "sodium" in content
        assert "0.5.0" in content

    def test_add_project_with_channel_option(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that add command with --channel option works."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)

            # Act
            runner.invoke(app, ["add", "sodium", "--channel", "beta"])

        # Assert
        projects_file = tmp_path / "mcpax" / "projects.toml"
        content = projects_file.read_text()
        assert "sodium" in content
        assert "beta" in content

    def test_add_project_not_found(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that add command shows error when project not found."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(
                side_effect=ProjectNotFoundError("nonexistent")
            )

            # Act
            result = runner.invoke(app, ["add", "nonexistent"])

        # Assert
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
        assert "nonexistent" in result.stdout

    def test_add_project_already_exists(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that add command shows error when project already exists."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)

            # Add first time
            runner.invoke(app, ["add", "sodium"])

            # Act - try to add again
            result = runner.invoke(app, ["add", "sodium"])

        # Assert
        assert result.exit_code == 1
        assert "already" in result.stdout.lower()
        assert "sodium" in result.stdout

    def test_add_project_no_config(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that add command shows error when config.toml not found."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act - try to add without running init
        result = runner.invoke(app, ["add", "sodium"])

        # Assert
        assert result.exit_code == 1
        assert "config.toml not found" in result.stdout or "mcpax init" in result.stdout


class TestRemoveCommand:
    """Tests for remove command."""

    def test_remove_project_not_found(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command shows error when project not in list."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["remove", "nonexistent"], input="y\n")

        # Assert
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "nonexistent" in result.stdout

    def test_remove_project_success(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command successfully removes a project."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)
            runner.invoke(app, ["add", "sodium"])

        # Act
        result = runner.invoke(app, ["remove", "sodium"], input="y\n")

        # Assert
        assert result.exit_code == 0
        projects_file = tmp_path / "mcpax" / "projects.toml"
        content = projects_file.read_text()
        assert "sodium" not in content

    def test_remove_project_confirmation_no(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command does not remove when user says no."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)
            runner.invoke(app, ["add", "sodium"])

        # Act - say "no" to confirmation
        result = runner.invoke(app, ["remove", "sodium"], input="n\n")

        # Assert
        assert result.exit_code == 0
        assert "Cancelled" in result.stdout
        projects_file = tmp_path / "mcpax" / "projects.toml"
        content = projects_file.read_text()
        assert "sodium" in content  # Should still be in the list

    def test_remove_project_skip_confirmation(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command with --yes skips confirmation."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)
            runner.invoke(app, ["add", "sodium"])

        # Act - use --yes to skip confirmation
        result = runner.invoke(app, ["remove", "sodium", "--yes"])

        # Assert
        assert result.exit_code == 0
        assert "Remove" not in result.stdout  # No confirmation prompt
        projects_file = tmp_path / "mcpax" / "projects.toml"
        content = projects_file.read_text()
        assert "sodium" not in content

    def test_remove_project_with_delete_file(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command with --delete-file deletes installed file."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)
            runner.invoke(app, ["add", "sodium"])

        # Mock the file deletion helper
        with patch(
            "mcpax.cli.app._remove_installed_file_with_manager"
        ) as mock_remove_file:
            mock_remove_file.return_value = (True, "sodium-0.5.0.jar")

            # Act
            result = runner.invoke(app, ["remove", "sodium", "--delete-file", "--yes"])

        # Assert
        assert result.exit_code == 0
        mock_remove_file.assert_called_once_with("sodium")
        assert "sodium-0.5.0.jar" in result.stdout

    def test_remove_project_delete_file_not_installed(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command with --delete-file handles not installed case."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)
            runner.invoke(app, ["add", "sodium"])

        # Mock the file deletion helper - returns False (not installed)
        with patch(
            "mcpax.cli.app._remove_installed_file_with_manager"
        ) as mock_remove_file:
            mock_remove_file.return_value = (False, None)

            # Act
            result = runner.invoke(app, ["remove", "sodium", "--delete-file", "--yes"])

        # Assert
        assert result.exit_code == 0
        mock_remove_file.assert_called_once_with("sodium")
        # Should still remove from list but indicate no file was installed
        projects_file = tmp_path / "mcpax" / "projects.toml"
        content = projects_file.read_text()
        assert "sodium" not in content

    def test_remove_project_no_config(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command shows error when config.toml not found."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act - try to remove without running init
        result = runner.invoke(app, ["remove", "sodium"], input="y\n")

        # Assert
        assert result.exit_code == 1
        assert "config.toml not found" in result.stdout or "mcpax init" in result.stdout

    def test_remove_project_combined_flags(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that remove command with -d -y flags works correctly."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(return_value=mock_project)
            runner.invoke(app, ["add", "sodium"])

        # Mock the file deletion helper
        with patch(
            "mcpax.cli.app._remove_installed_file_with_manager"
        ) as mock_remove_file:
            mock_remove_file.return_value = (True, "sodium-0.5.0.jar")

            # Act - use short flags -d -y
            result = runner.invoke(app, ["remove", "sodium", "-d", "-y"])

        # Assert
        assert result.exit_code == 0
        mock_remove_file.assert_called_once_with("sodium")
        assert "sodium-0.5.0.jar" in result.stdout
        projects_file = tmp_path / "mcpax" / "projects.toml"
        content = projects_file.read_text()
        assert "sodium" not in content
