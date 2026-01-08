"""Unit tests for CLI application."""

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
