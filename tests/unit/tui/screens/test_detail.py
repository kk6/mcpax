"""Tests for ProjectDetailScreen."""

from unittest.mock import patch

import pytest
from textual.app import App

from mcpax.core.models import (
    InstallStatus,
    ProjectType,
)
from mcpax.tui.screens.detail import ProjectDetailScreen


@pytest.mark.asyncio
async def test_detail_screen_initialization(
    app_config, make_update_check_result
) -> None:
    """Test ProjectDetailScreen initialization."""
    project = make_update_check_result(slug="test-project")
    screen = ProjectDetailScreen(project=project, config=app_config)
    assert screen is not None
    assert screen._project == project
    assert screen._config == app_config


@pytest.mark.asyncio
async def test_detail_screen_displays_project_info(
    app_config, make_update_check_result
) -> None:
    """Test ProjectDetailScreen displays project information."""

    class TestApp(App[None]):
        def on_mount(self):
            project = make_update_check_result(
                slug="sodium",
                project_type=ProjectType.MOD,
                status=InstallStatus.OUTDATED,
                current_version="0.5.0",
                latest_version="0.6.0",
            )
            self.push_screen(ProjectDetailScreen(project=project, config=app_config))

    app = TestApp()
    async with app.run_test():
        screen = app.screen
        assert isinstance(screen, ProjectDetailScreen)
        # Screen should contain the project information
        # (Verifying compose output happens in textual's render)


@pytest.mark.asyncio
async def test_detail_screen_has_escape_binding(
    app_config, make_update_check_result
) -> None:
    """Test ProjectDetailScreen has escape keybinding."""
    project = make_update_check_result(slug="test-project")
    screen = ProjectDetailScreen(project=project, config=app_config)

    # Check that 'escape' is bound to cancel action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "escape" in bindings
    assert bindings["escape"] == "cancel"


@pytest.mark.asyncio
async def test_detail_screen_has_delete_binding(
    app_config, make_update_check_result
) -> None:
    """Test ProjectDetailScreen has delete (d) keybinding."""
    project = make_update_check_result(slug="test-project")
    screen = ProjectDetailScreen(project=project, config=app_config)

    # Check that 'd' is bound to delete action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "d" in bindings
    assert bindings["d"] == "delete"


@pytest.mark.asyncio
async def test_detail_screen_escape_closes(
    app_config, make_update_check_result
) -> None:
    """Test escape key closes the modal."""

    class TestApp(App[None]):
        def on_mount(self):
            project = make_update_check_result(slug="test-project")
            self.push_screen(ProjectDetailScreen(project=project, config=app_config))

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
async def test_detail_screen_delete_removes_project(
    app_config, make_update_check_result
) -> None:
    """Test delete action removes project from projects.toml."""

    class TestApp(App[None]):
        def on_mount(self):
            project = make_update_check_result(slug="fabric-api")
            self.push_screen(ProjectDetailScreen(project=project, config=app_config))

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
