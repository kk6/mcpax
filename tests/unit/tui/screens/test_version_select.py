"""Tests for version selection screen."""

from datetime import UTC, datetime

from mcpax.core.models import ProjectFile, ProjectType, ProjectVersion, ReleaseChannel
from mcpax.tui.screens.version_select import VersionSelectScreen


class TestVersionSelectScreen:
    """Tests for VersionSelectScreen."""

    def test_screen_initialization(self) -> None:
        """Screen can be initialized with required parameters."""
        screen = VersionSelectScreen(
            slug="sodium",
            project_type=ProjectType.MOD,
            minecraft_version="1.21.4",
            mod_loader="fabric",
        )

        assert screen._slug == "sodium"
        assert screen._project_type == ProjectType.MOD
        assert screen._minecraft_version == "1.21.4"
        assert screen._mod_loader == "fabric"

    def test_screen_has_correct_bindings(self) -> None:
        """Screen has correct key bindings."""
        screen = VersionSelectScreen(
            slug="sodium",
            project_type=ProjectType.MOD,
            minecraft_version="1.21.4",
            mod_loader="fabric",
        )

        # Check bindings exist
        binding_keys = [b.key for b in screen.BINDINGS]
        assert "escape" in binding_keys
        assert "enter" in binding_keys
        assert "l" in binding_keys

    def test_populate_table_with_duplicate_version_numbers(self) -> None:
        """Table handles versions with duplicate numbers (different loaders)."""
        from textual.widgets import DataTable

        screen = VersionSelectScreen(
            slug="test-mod",
            project_type=ProjectType.MOD,
            minecraft_version="1.20.1",
            mod_loader="fabric",
        )

        # Create versions with same version number but different loaders
        versions = [
            ProjectVersion(
                id="version-fabric",
                project_id="test-mod",
                version_number="1.0.0",
                version_type=ReleaseChannel.RELEASE,
                game_versions=["1.20.1"],
                loaders=["fabric"],
                files=[
                    ProjectFile(
                        url="https://example.com/fabric.jar",
                        filename="mod-fabric.jar",
                        size=1000,
                        hashes={"sha512": "abc123"},
                        primary=True,
                    )
                ],
                dependencies=[],
                date_published=datetime.now(tz=UTC),
            ),
            ProjectVersion(
                id="version-forge",
                project_id="test-mod",
                version_number="1.0.0",
                version_type=ReleaseChannel.RELEASE,
                game_versions=["1.20.1"],
                loaders=["forge"],
                files=[
                    ProjectFile(
                        url="https://example.com/forge.jar",
                        filename="mod-forge.jar",
                        size=2000,
                        hashes={"sha512": "def456"},
                        primary=True,
                    )
                ],
                dependencies=[],
                date_published=datetime.now(tz=UTC),
            ),
        ]

        # Create a mock DataTable
        from unittest.mock import MagicMock

        mock_table = MagicMock(spec=DataTable)
        screen.query_one = MagicMock(return_value=mock_table)  # type: ignore[assignment]

        # Populate table should not raise DuplicateKey error
        screen._populate_table(versions)

        # Verify table.add_row was called twice with different keys
        assert mock_table.add_row.call_count == 2

        # Verify that keys are different (version IDs)
        calls = mock_table.add_row.call_args_list
        key1 = calls[0][1]["key"]
        key2 = calls[1][1]["key"]
        assert key1 != key2
        assert key1 == "version-fabric"
        assert key2 == "version-forge"

        # Verify versions mapping is populated
        assert len(screen._versions) == 2
        assert "version-fabric" in screen._versions
        assert "version-forge" in screen._versions

    def test_shader_loader_parameter_is_stored(self) -> None:
        """Screen stores shader_loader parameter correctly."""
        screen = VersionSelectScreen(
            slug="complementary-shaders",
            project_type=ProjectType.SHADER,
            minecraft_version="1.21.4",
            mod_loader="fabric",
            shader_loader="iris",
        )

        assert screen._shader_loader == "iris"

    def test_shader_loader_parameter_defaults_to_none(self) -> None:
        """Screen defaults shader_loader to None when not provided."""
        screen = VersionSelectScreen(
            slug="sodium",
            project_type=ProjectType.MOD,
            minecraft_version="1.21.4",
            mod_loader="fabric",
        )

        assert screen._shader_loader is None
