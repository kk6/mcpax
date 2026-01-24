"""Tests for ProjectDetailScreen."""

from pathlib import Path
from unittest.mock import patch

import pytest
from textual.app import App

from mcpax.core.models import (
    AppConfig,
    InstallStatus,
    Loader,
    ProjectType,
    UpdateCheckResult,
)
from mcpax.tui.screens.detail import ProjectDetailScreen


def create_test_config() -> AppConfig:
    """Create a test AppConfig instance."""
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        shader_loader=Loader.IRIS,
        minecraft_dir=Path("/tmp/.minecraft"),
    )


def create_test_update_result(
    slug: str = "fabric-api",
    project_type: ProjectType = ProjectType.MOD,
    status: InstallStatus = InstallStatus.INSTALLED,
    current_version: str | None = "1.0.0",
    latest_version: str | None = "1.0.0",
    error: str | None = None,
) -> UpdateCheckResult:
    """Create a test UpdateCheckResult instance."""
    return UpdateCheckResult(
        slug=slug,
        project_type=project_type,
        status=status,
        current_version=current_version,
        latest_version=latest_version,
        current_file=None,
        latest_file=None,
        error=error,
    )


@pytest.mark.asyncio
async def test_detail_screen_initialization() -> None:
    """Test ProjectDetailScreen initialization."""
    config = create_test_config()
    project = create_test_update_result()
    screen = ProjectDetailScreen(project=project, config=config)
    assert screen is not None
    assert screen._project == project
    assert screen._config == config


@pytest.mark.asyncio
async def test_detail_screen_displays_project_info() -> None:
    """Test ProjectDetailScreen displays project information."""

    class TestApp(App[None]):
        def on_mount(self):
            project = create_test_update_result(
                slug="sodium",
                project_type=ProjectType.MOD,
                status=InstallStatus.OUTDATED,
                current_version="0.5.0",
                latest_version="0.6.0",
            )
            self.push_screen(
                ProjectDetailScreen(project=project, config=create_test_config())
            )

    app = TestApp()
    async with app.run_test():
        screen = app.screen
        assert isinstance(screen, ProjectDetailScreen)
        # Screen should contain the project information
        # (Verifying compose output happens in textual's render)


@pytest.mark.asyncio
async def test_detail_screen_has_escape_binding() -> None:
    """Test ProjectDetailScreen has escape keybinding."""
    config = create_test_config()
    project = create_test_update_result()
    screen = ProjectDetailScreen(project=project, config=config)

    # Check that 'escape' is bound to cancel action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "escape" in bindings
    assert bindings["escape"] == "cancel"


@pytest.mark.asyncio
async def test_detail_screen_has_delete_binding() -> None:
    """Test ProjectDetailScreen has delete (d) keybinding."""
    config = create_test_config()
    project = create_test_update_result()
    screen = ProjectDetailScreen(project=project, config=config)

    # Check that 'd' is bound to delete action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "d" in bindings
    assert bindings["d"] == "delete"


@pytest.mark.asyncio
async def test_detail_screen_escape_closes() -> None:
    """Test escape key closes the modal."""

    class TestApp(App[None]):
        def on_mount(self):
            project = create_test_update_result()
            self.push_screen(
                ProjectDetailScreen(project=project, config=create_test_config())
            )

    app = TestApp()
    async with app.run_test() as pilot:
        # Verify detail screen is active
        assert isinstance(app.screen, ProjectDetailScreen)

        # Press escape to close
        await pilot.press("escape")
        await pilot.pause()

        # Modal should be dismissed (no longer the active screen)
        assert not isinstance(app.screen, ProjectDetailScreen)


@pytest.mark.asyncio
async def test_detail_screen_delete_removes_project() -> None:
    """Test delete action removes project from projects.toml."""

    class TestApp(App[None]):
        def on_mount(self):
            project = create_test_update_result(slug="fabric-api")
            self.push_screen(
                ProjectDetailScreen(project=project, config=create_test_config())
            )

    with (
        patch("mcpax.tui.screens.detail.load_projects") as mock_load,
        patch("mcpax.tui.screens.detail.save_projects") as mock_save,
    ):
        from mcpax.core.models import ProjectConfig, ReleaseChannel

        # Mock existing projects
        existing_projects = [
            ProjectConfig(
                slug="fabric-api",
                project_type=ProjectType.MOD,
                channel=ReleaseChannel.RELEASE,
            ),
            ProjectConfig(
                slug="sodium",
                project_type=ProjectType.MOD,
                channel=ReleaseChannel.RELEASE,
            ),
        ]
        mock_load.return_value = existing_projects

        app = TestApp()
        async with app.run_test() as pilot:
            # Press 'd' to delete
            await pilot.press("d")
            await pilot.pause()

            # Verify that save_projects was called with the correct list
            mock_load.assert_called_once()
            updated_projects = [p for p in existing_projects if p.slug != "fabric-api"]
            mock_save.assert_called_once_with(updated_projects)
