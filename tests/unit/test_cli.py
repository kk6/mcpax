"""Unit tests for CLI application."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from mcpax import __version__
from mcpax.cli.app import app
from mcpax.core.exceptions import APIError, ProjectNotFoundError
from mcpax.core.models import (
    InstalledFile,
    ModrinthProject,
    ProjectType,
    SearchHit,
    SearchResult,
)

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
            app, ["init"], input="1.20.1\nforge\noptifine\n/custom/minecraft\n"
        )

        # Assert
        assert result.exit_code == 0
        config_content = (tmp_path / "mcpax" / "config.toml").read_text()
        assert "1.20.1" in config_content
        assert "forge" in config_content
        assert "optifine" in config_content
        assert "/custom/minecraft" in config_content

    def test_init_interactive_uses_defaults_on_empty_input(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that init uses defaults when user presses enter."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["init"], input="\n\n\n\n")

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


class TestInstallCommand:
    """Tests for install command."""

    def test_install_single_project_success(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install command successfully installs a single project."""
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

        # Mock ProjectManager for install
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_result = UpdateCheckResult(
                slug="sodium",
                status=InstallStatus.NOT_INSTALLED,
                current_version=None,
                current_file=None,
                latest_version="0.5.0",
                latest_version_id="v0.5.0",
                latest_file=None,
            )
            mock_manager_instance.check_updates = AsyncMock(
                return_value=[mock_check_result]
            )

            from mcpax.core.models import UpdateResult

            mock_update_result = UpdateResult(
                successful=["sodium"], failed=[], backed_up=[]
            )
            mock_manager_instance.apply_updates = AsyncMock(
                return_value=mock_update_result
            )

            # Act
            result = runner.invoke(app, ["install", "sodium"])

        # Assert
        assert result.exit_code == 0
        assert "sodium" in result.stdout.lower()

    def test_install_all_projects_success(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install --all installs all projects."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_project_sodium = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_project_lithium = ModrinthProject(
            id="gvQqBUqZ",
            slug="lithium",
            title="Lithium",
            description="Performance mod",
            project_type=ProjectType.MOD,
            downloads=30000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(
                side_effect=[mock_project_sodium, mock_project_lithium]
            )
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "lithium"])

        # Mock ProjectManager for install
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.NOT_INSTALLED,
                    current_version=None,
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="lithium",
                    status=InstallStatus.NOT_INSTALLED,
                    current_version=None,
                    current_file=None,
                    latest_version="0.11.0",
                    latest_version_id="v0.11.0",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            from mcpax.core.models import UpdateResult

            mock_update_result = UpdateResult(
                successful=["sodium", "lithium"], failed=[], backed_up=[]
            )
            mock_manager_instance.apply_updates = AsyncMock(
                return_value=mock_update_result
            )

            # Act
            result = runner.invoke(app, ["install", "--all"])

        # Assert
        assert result.exit_code == 0

    def test_install_no_args_shows_error(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install without slug or --all shows error."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["install"])

        # Assert
        assert result.exit_code != 0

    def test_install_slug_with_all_shows_error(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install with slug and --all shows error."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["install", "sodium", "--all"])

        # Assert
        assert result.exit_code == 1
        assert "Cannot use --all" in result.stdout

    def test_install_project_not_in_list(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install shows error when project not in projects.toml."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["install", "nonexistent"])

        # Assert
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "nonexistent" in result.stdout

    def test_install_no_compatible_version(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install handles no compatible version gracefully."""
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

        # Mock ProjectManager to return NOT_COMPATIBLE
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_result = UpdateCheckResult(
                slug="sodium",
                status=InstallStatus.NOT_COMPATIBLE,
                current_version=None,
                current_file=None,
                latest_version=None,
                latest_version_id=None,
                latest_file=None,
            )
            mock_manager_instance.check_updates = AsyncMock(
                return_value=[mock_check_result]
            )

            # Act
            result = runner.invoke(app, ["install", "sodium"])

        # Assert
        assert result.exit_code == 0  # Should complete but show warning
        assert "compatible" in result.stdout.lower() or "sodium" in result.stdout

    def test_install_already_installed_skips(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install skips already installed projects."""
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

        # Mock ProjectManager to return INSTALLED
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_result = UpdateCheckResult(
                slug="sodium",
                status=InstallStatus.INSTALLED,
                current_version="0.5.0",
                current_file=None,
                latest_version="0.5.0",
                latest_version_id="v0.5.0",
                latest_file=None,
            )
            mock_manager_instance.check_updates = AsyncMock(
                return_value=[mock_check_result]
            )

            from mcpax.core.models import UpdateResult

            mock_update_result = UpdateResult(successful=[], failed=[], backed_up=[])
            mock_manager_instance.apply_updates = AsyncMock(
                return_value=mock_update_result
            )

            # Act
            result = runner.invoke(app, ["install", "sodium"])

        # Assert
        assert result.exit_code == 0
        # Should indicate already installed
        assert (
            "installed" in result.stdout.lower() or "already" in result.stdout.lower()
        )

    def test_install_no_config(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that install shows error when config.toml not found."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act - try to install without running init
        result = runner.invoke(app, ["install", "sodium"])

        # Assert
        assert result.exit_code == 1
        assert "config.toml not found" in result.stdout or "mcpax init" in result.stdout


class TestListCommand:
    """Tests for list command."""

    def test_list_no_config(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list command shows error when config.toml not found."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        # Act
        result = runner.invoke(app, ["list"])

        # Assert
        assert result.exit_code == 1
        assert "config.toml not found" in result.stdout or "mcpax init" in result.stdout

    def test_list_empty_projects(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list command shows message when no projects configured."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["list"])

        # Assert
        assert result.exit_code == 0
        assert "No projects configured" in result.stdout

    def test_list_shows_projects(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list command shows project list."""
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

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_result = UpdateCheckResult(
                slug="sodium",
                status=InstallStatus.INSTALLED,
                current_version="0.5.0",
                current_file=None,
                latest_version="0.5.0",
                latest_version_id="v0.5.0",
                latest_file=None,
            )
            mock_manager_instance.check_updates = AsyncMock(
                return_value=[mock_check_result]
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(return_value=mock_project)

                # Act
                result = runner.invoke(app, ["list"])

        # Assert
        assert result.exit_code == 0
        assert "sodium" in result.stdout.lower() or "Sodium" in result.stdout

    def test_list_groups_by_type(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list command groups projects by type."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_mod = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_shader = ModrinthProject(
            id="HVnmMxH1",
            slug="complementary-unbound",
            title="Complementary Unbound",
            description="Shader pack",
            project_type=ProjectType.SHADER,
            downloads=10000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(side_effect=[mock_mod, mock_shader])
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "complementary-unbound"])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="complementary-unbound",
                    status=InstallStatus.INSTALLED,
                    current_version="r5.2",
                    current_file=None,
                    latest_version="r5.2",
                    latest_version_id="v5.2",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(
                    side_effect=[mock_mod, mock_shader]
                )

                # Act
                result = runner.invoke(app, ["list"])

        # Assert
        assert result.exit_code == 0
        assert "mod" in result.stdout.lower() or "MOD" in result.stdout
        assert "shader" in result.stdout.lower() or "Shader" in result.stdout

    def test_list_filter_type_mod(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --type mod filters to show only mods."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_mod = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_shader = ModrinthProject(
            id="HVnmMxH1",
            slug="complementary-unbound",
            title="Complementary Unbound",
            description="Shader pack",
            project_type=ProjectType.SHADER,
            downloads=10000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(side_effect=[mock_mod, mock_shader])
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "complementary-unbound"])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="complementary-unbound",
                    status=InstallStatus.INSTALLED,
                    current_version="r5.2",
                    current_file=None,
                    latest_version="r5.2",
                    latest_version_id="v5.2",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(
                    side_effect=[mock_mod, mock_shader]
                )

                # Act
                result = runner.invoke(app, ["list", "--type", "mod"])

        # Assert
        assert result.exit_code == 0
        assert "sodium" in result.stdout.lower() or "Sodium" in result.stdout
        assert (
            "complementary" not in result.stdout.lower()
        )  # Shader should not be shown

    def test_list_filter_type_shader(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --type shader filters to show only shaders."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_mod = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_shader = ModrinthProject(
            id="HVnmMxH1",
            slug="complementary-unbound",
            title="Complementary Unbound",
            description="Shader pack",
            project_type=ProjectType.SHADER,
            downloads=10000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(side_effect=[mock_mod, mock_shader])
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "complementary-unbound"])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="complementary-unbound",
                    status=InstallStatus.INSTALLED,
                    current_version="r5.2",
                    current_file=None,
                    latest_version="r5.2",
                    latest_version_id="v5.2",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(
                    side_effect=[mock_mod, mock_shader]
                )

                # Act
                result = runner.invoke(app, ["list", "--type", "shader"])

        # Assert
        assert result.exit_code == 0
        assert (
            "complementary" in result.stdout.lower() or "Complementary" in result.stdout
        )
        assert "sodium" not in result.stdout.lower()  # Mod should not be shown

    def test_list_filter_status_installed(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --status installed filters to show only installed projects."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_sodium = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_lithium = ModrinthProject(
            id="gvQqBUqZ",
            slug="lithium",
            title="Lithium",
            description="Performance mod",
            project_type=ProjectType.MOD,
            downloads=30000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(
                side_effect=[mock_sodium, mock_lithium]
            )
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "lithium"])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="lithium",
                    status=InstallStatus.NOT_INSTALLED,
                    current_version=None,
                    current_file=None,
                    latest_version="0.11.0",
                    latest_version_id="v0.11.0",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(
                    side_effect=[mock_sodium, mock_lithium]
                )

                # Act
                result = runner.invoke(app, ["list", "--status", "installed"])

        # Assert
        assert result.exit_code == 0
        assert "sodium" in result.stdout.lower() or "Sodium" in result.stdout
        assert (
            "lithium" not in result.stdout.lower()
        )  # Not installed should not be shown

    def test_list_filter_status_not_installed(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --status not-installed filters to show only not installed."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_sodium = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_lithium = ModrinthProject(
            id="gvQqBUqZ",
            slug="lithium",
            title="Lithium",
            description="Performance mod",
            project_type=ProjectType.MOD,
            downloads=30000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(
                side_effect=[mock_sodium, mock_lithium]
            )
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "lithium"])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="lithium",
                    status=InstallStatus.NOT_INSTALLED,
                    current_version=None,
                    current_file=None,
                    latest_version="0.11.0",
                    latest_version_id="v0.11.0",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(
                    side_effect=[mock_sodium, mock_lithium]
                )

                # Act
                result = runner.invoke(app, ["list", "--status", "not-installed"])

        # Assert
        assert result.exit_code == 0
        assert "lithium" in result.stdout.lower() or "Lithium" in result.stdout
        assert "sodium" not in result.stdout.lower()  # Installed should not be shown

    def test_list_filter_status_outdated(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --status outdated filters to show only outdated projects."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_sodium = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_lithium = ModrinthProject(
            id="gvQqBUqZ",
            slug="lithium",
            title="Lithium",
            description="Performance mod",
            project_type=ProjectType.MOD,
            downloads=30000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(
                side_effect=[mock_sodium, mock_lithium]
            )
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "lithium"])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="lithium",
                    status=InstallStatus.OUTDATED,
                    current_version="0.10.0",
                    current_file=None,
                    latest_version="0.11.0",
                    latest_version_id="v0.11.0",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(
                    side_effect=[mock_sodium, mock_lithium]
                )

                # Act
                result = runner.invoke(app, ["list", "--status", "outdated"])

        # Assert
        assert result.exit_code == 0
        assert "lithium" in result.stdout.lower() or "Lithium" in result.stdout
        assert "sodium" not in result.stdout.lower()  # Up-to-date should not be shown

    def test_list_json_output(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --json outputs JSON format."""
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

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_result = UpdateCheckResult(
                slug="sodium",
                status=InstallStatus.INSTALLED,
                current_version="0.5.0",
                current_file=None,
                latest_version="0.5.0",
                latest_version_id="v0.5.0",
                latest_file=None,
            )
            mock_manager_instance.check_updates = AsyncMock(
                return_value=[mock_check_result]
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(return_value=mock_project)

                # Act
                result = runner.invoke(app, ["list", "--json"])

        # Assert
        assert result.exit_code == 0
        # Should be valid JSON
        import json

        try:
            json_data = json.loads(result.stdout)
            assert isinstance(json_data, list)
            assert len(json_data) > 0
            assert json_data[0]["slug"] == "sodium"
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.stdout}")

    def test_list_invalid_type_filter(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --type with invalid value shows error."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["list", "--type", "invalid"])

        # Assert
        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower() or "type" in result.stdout.lower()

    def test_list_invalid_status_filter(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --status with invalid value shows error."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["list", "--status", "invalid"])

        # Assert
        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower() or "status" in result.stdout.lower()

    def test_list_no_update_rejects_outdated_status(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --no-update rejects outdated status filter."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        # Act
        result = runner.invoke(app, ["list", "--no-update", "--status", "outdated"])

        # Assert
        assert result.exit_code == 1
        assert (
            "no-update" in result.stdout.lower() or "outdated" in result.stdout.lower()
        )

    def test_list_no_update_skips_check_updates(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list --no-update skips update checks."""
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

        mods_dir = tmp_path / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        file_path = mods_dir / "sodium.jar"
        file_path.write_text("dummy")

        installed = InstalledFile(
            slug="sodium",
            project_type=ProjectType.MOD,
            filename="sodium.jar",
            version_id="v0.5.0",
            version_number="0.5.0",
            sha512="abc123",
            installed_at=datetime.now(UTC),
            file_path=file_path,
        )

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            mock_manager_instance.get_installed_file = AsyncMock(return_value=installed)
            mock_manager_instance.check_updates = AsyncMock()

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(return_value=mock_project)

                # Act
                result = runner.invoke(app, ["list", "--no-update"])

        # Assert
        assert result.exit_code == 0
        mock_manager_instance.check_updates.assert_not_called()
        assert "sodium" in result.stdout.lower() or "Sodium" in result.stdout

    def test_list_respects_max_concurrency(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list respects the max concurrency limit."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_projects = [
            ModrinthProject(
                id="AANobbMI",
                slug="sodium",
                title="Sodium",
                description="Modern rendering engine",
                project_type=ProjectType.MOD,
                downloads=50000000,
                icon_url=None,
                versions=["v1"],
            ),
            ModrinthProject(
                id="gvQqBUqZ",
                slug="lithium",
                title="Lithium",
                description="Performance mod",
                project_type=ProjectType.MOD,
                downloads=30000000,
                icon_url=None,
                versions=["v1"],
            ),
            ModrinthProject(
                id="HVnmMxH1",
                slug="complementary-unbound",
                title="Complementary Unbound",
                description="Shader pack",
                project_type=ProjectType.SHADER,
                downloads=10000000,
                icon_url=None,
                versions=["v1"],
            ),
        ]
        project_map = {project.slug: project for project in mock_projects}

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(side_effect=mock_projects)
            for project in mock_projects:
                runner.invoke(app, ["add", project.slug])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="lithium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.11.0",
                    current_file=None,
                    latest_version="0.11.0",
                    latest_version_id="v0.11.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="complementary-unbound",
                    status=InstallStatus.INSTALLED,
                    current_version="r5.2",
                    current_file=None,
                    latest_version="r5.2",
                    latest_version_id="v5.2",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            current = 0
            max_seen = 0

            async def tracked_get_project(slug: str) -> ModrinthProject:
                nonlocal current, max_seen
                current += 1
                if current > max_seen:
                    max_seen = current
                await asyncio.sleep(0.01)
                current -= 1
                return project_map[slug]

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(side_effect=tracked_get_project)

                # Act
                result = runner.invoke(app, ["list", "--max-concurrency", "1"])

        # Assert
        assert result.exit_code == 0
        assert max_seen == 1

    def test_list_shows_status_icons(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list command shows status icons."""
        # Arrange
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        runner.invoke(app, ["init", "-y"])

        mock_sodium = ModrinthProject(
            id="AANobbMI",
            slug="sodium",
            title="Sodium",
            description="Modern rendering engine",
            project_type=ProjectType.MOD,
            downloads=50000000,
            icon_url=None,
            versions=["v1"],
        )

        mock_lithium = ModrinthProject(
            id="gvQqBUqZ",
            slug="lithium",
            title="Lithium",
            description="Performance mod",
            project_type=ProjectType.MOD,
            downloads=30000000,
            icon_url=None,
            versions=["v1"],
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.get_project = AsyncMock(
                side_effect=[mock_sodium, mock_lithium]
            )
            runner.invoke(app, ["add", "sodium"])
            runner.invoke(app, ["add", "lithium"])

        # Mock ProjectManager for listing
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_results = [
                UpdateCheckResult(
                    slug="sodium",
                    status=InstallStatus.INSTALLED,
                    current_version="0.5.0",
                    current_file=None,
                    latest_version="0.5.0",
                    latest_version_id="v0.5.0",
                    latest_file=None,
                ),
                UpdateCheckResult(
                    slug="lithium",
                    status=InstallStatus.NOT_INSTALLED,
                    current_version=None,
                    current_file=None,
                    latest_version="0.11.0",
                    latest_version_id="v0.11.0",
                    latest_file=None,
                ),
            ]
            mock_manager_instance.check_updates = AsyncMock(
                return_value=mock_check_results
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(
                    side_effect=[mock_sodium, mock_lithium]
                )

                # Act
                result = runner.invoke(app, ["list"])

        # Assert
        assert result.exit_code == 0
        # Check for status icons (✓ for installed, ○ for not installed)
        assert "✓" in result.stdout or "○" in result.stdout

    def test_list_shows_version_update_arrow(
        self, tmp_path: "Path", monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Test that list command shows arrow for version updates."""
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

        # Mock ProjectManager for listing with outdated status
        with patch("mcpax.cli.app.ProjectManager") as MockManager:
            mock_manager_instance = MockManager.return_value.__aenter__.return_value
            from mcpax.core.models import InstallStatus, UpdateCheckResult

            mock_check_result = UpdateCheckResult(
                slug="sodium",
                status=InstallStatus.OUTDATED,
                current_version="0.5.0",
                current_file=None,
                latest_version="0.6.0",
                latest_version_id="v0.6.0",
                latest_file=None,
            )
            mock_manager_instance.check_updates = AsyncMock(
                return_value=[mock_check_result]
            )

            with patch("mcpax.cli.app.ModrinthClient") as MockClient2:
                mock_instance2 = MockClient2.return_value.__aenter__.return_value
                mock_instance2.get_project = AsyncMock(return_value=mock_project)

                # Act
                result = runner.invoke(app, ["list"])

        # Assert
        assert result.exit_code == 0
        # Check for arrow indicator showing version update
        assert "→" in result.stdout or "0.5.0" in result.stdout


class TestSearchCommand:
    """Tests for search command."""

    def test_search_basic_query(self) -> None:
        """Test that search command returns results for a basic query."""
        # Arrange
        mock_result = SearchResult(
            hits=[
                SearchHit(
                    slug="sodium",
                    title="Sodium",
                    description="Modern rendering engine for Minecraft",
                    project_type=ProjectType.MOD,
                    downloads=50000000,
                    icon_url="https://cdn.modrinth.com/...",
                )
            ],
            total_hits=1,
            offset=0,
            limit=10,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "sodium"])

        # Assert
        assert result.exit_code == 0
        assert "sodium" in result.stdout.lower() or "Sodium" in result.stdout

    def test_search_shows_numbered_results(self) -> None:
        """Test that search command shows numbered results."""
        # Arrange
        mock_result = SearchResult(
            hits=[
                SearchHit(
                    slug="sodium",
                    title="Sodium",
                    description="Modern rendering engine",
                    project_type=ProjectType.MOD,
                    downloads=50000000,
                    icon_url=None,
                ),
                SearchHit(
                    slug="lithium",
                    title="Lithium",
                    description="Performance mod",
                    project_type=ProjectType.MOD,
                    downloads=30000000,
                    icon_url=None,
                ),
            ],
            total_hits=2,
            offset=0,
            limit=10,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "performance"])

        # Assert
        assert result.exit_code == 0
        # Check for numbered list
        assert "1." in result.stdout or "1)" in result.stdout

    def test_search_displays_downloads_formatted(self) -> None:
        """Test that search command formats download numbers with commas."""
        # Arrange
        mock_result = SearchResult(
            hits=[
                SearchHit(
                    slug="sodium",
                    title="Sodium",
                    description="Modern rendering engine",
                    project_type=ProjectType.MOD,
                    downloads=12345678,
                    icon_url=None,
                )
            ],
            total_hits=1,
            offset=0,
            limit=10,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "sodium"])

        # Assert
        assert result.exit_code == 0
        # Check for comma-separated downloads
        assert "12,345,678" in result.stdout

    def test_search_shows_add_hint(self) -> None:
        """Test that search command shows hint about adding projects."""
        # Arrange
        mock_result = SearchResult(
            hits=[
                SearchHit(
                    slug="sodium",
                    title="Sodium",
                    description="Modern rendering engine",
                    project_type=ProjectType.MOD,
                    downloads=50000000,
                    icon_url=None,
                )
            ],
            total_hits=1,
            offset=0,
            limit=10,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "sodium"])

        # Assert
        assert result.exit_code == 0
        # Check for hint about mcpax add command
        assert "mcpax add" in result.stdout

    def test_search_limit_option(self) -> None:
        """Test that search command respects --limit option."""
        # Arrange
        mock_result = SearchResult(
            hits=[
                SearchHit(
                    slug=f"project-{i}",
                    title=f"Project {i}",
                    description="Description",
                    project_type=ProjectType.MOD,
                    downloads=1000 * i,
                    icon_url=None,
                )
                for i in range(5)
            ],
            total_hits=100,
            offset=0,
            limit=5,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "test", "--limit", "5"])

        # Assert
        assert result.exit_code == 0
        mock_instance.search.assert_called_once_with("test", limit=5)

    def test_search_type_filter_mod(self) -> None:
        """Test that search command with --type mod filters to mods."""
        # Arrange
        mock_result = SearchResult(
            hits=[
                SearchHit(
                    slug="sodium",
                    title="Sodium",
                    description="Modern rendering engine",
                    project_type=ProjectType.MOD,
                    downloads=50000000,
                    icon_url=None,
                ),
            ],
            total_hits=2,
            offset=0,
            limit=10,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "test", "--type", "mod"])

        # Assert
        assert result.exit_code == 0
        facets = json.dumps([[f"project_type:{ProjectType.MOD.value}"]])
        mock_instance.search.assert_called_once_with("test", limit=10, facets=facets)
        assert "sodium" in result.stdout.lower() or "Sodium" in result.stdout

    def test_search_json_output(self) -> None:
        """Test that search command with --json outputs JSON format."""
        # Arrange
        mock_result = SearchResult(
            hits=[
                SearchHit(
                    slug="sodium",
                    title="Sodium",
                    description="Modern rendering engine",
                    project_type=ProjectType.MOD,
                    downloads=50000000,
                    icon_url=None,
                )
            ],
            total_hits=1,
            offset=0,
            limit=10,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "sodium", "--json"])

        # Assert
        assert result.exit_code == 0
        # Should be valid JSON
        try:
            json_data = json.loads(result.stdout)
            assert isinstance(json_data, list)
            assert len(json_data) == 1
            assert json_data[0]["slug"] == "sodium"
            assert json_data[0]["type"] == "mod"
            assert json_data[0]["downloads"] == 50000000
        except json.JSONDecodeError:
            pytest.fail(f"Output is not valid JSON: {result.stdout}")

    def test_search_no_results(self) -> None:
        """Test that search command handles no results gracefully."""
        # Arrange
        mock_result = SearchResult(
            hits=[],
            total_hits=0,
            offset=0,
            limit=10,
        )

        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(return_value=mock_result)

            # Act
            result = runner.invoke(app, ["search", "nonexistent-query-xyz"])

        # Assert
        assert result.exit_code == 0
        assert "No results" in result.stdout or "0" in result.stdout

    def test_search_api_error(self) -> None:
        """Test that search command handles API errors gracefully."""
        # Arrange
        with patch("mcpax.cli.app.ModrinthClient") as MockClient:
            mock_instance = MockClient.return_value.__aenter__.return_value
            mock_instance.search = AsyncMock(side_effect=APIError("API error"))

            # Act
            result = runner.invoke(app, ["search", "test"])

        # Assert
        assert result.exit_code == 1
        assert "error" in result.stdout.lower() or "Error" in result.stdout

    def test_search_invalid_type_filter(self) -> None:
        """Test that search command rejects invalid type filter."""
        # Arrange & Act
        result = runner.invoke(app, ["search", "test", "--type", "invalid"])

        # Assert
        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower() or "type" in result.stdout.lower()
