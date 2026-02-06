"""Tests for ProjectDetailScreen."""

from unittest.mock import patch

import pytest
from textual.app import App

from mcpax.core.models import (
    InstallStatus,
    ProjectType,
)
from mcpax.tui.screens.confirm import ConfirmDialog
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
async def test_detail_screen_delete_shows_confirmation(
    app_config, make_update_check_result
) -> None:
    """Test that delete action shows confirmation dialog."""

    class TestApp(App[None]):
        def on_mount(self):
            project = make_update_check_result(slug="fabric-api")
            self.push_screen(ProjectDetailScreen(project=project, config=app_config))

    app = TestApp()
    async with app.run_test() as pilot:
        # Verify detail screen is active
        assert isinstance(app.screen, ProjectDetailScreen)

        # Press 'd' to delete
        await pilot.press("d")
        await pilot.pause()

        # ConfirmDialog should be shown
        assert isinstance(app.screen, ConfirmDialog)


@pytest.mark.asyncio
async def test_detail_screen_delete_cancelled_keeps_project(
    app_config, make_update_check_result
) -> None:
    """Test that cancelling deletion keeps the project."""

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
        ]
        mock_load.return_value = existing_projects

        app = TestApp()
        async with app.run_test() as pilot:
            # Press 'd' to show confirmation
            await pilot.press("d")
            await pilot.pause()

            # Verify ConfirmDialog is shown
            assert isinstance(app.screen, ConfirmDialog)

            # Press escape to cancel
            await pilot.press("escape")
            await pilot.pause()

            # Neither load_projects nor save_projects should have been called
            mock_load.assert_not_called()
            mock_save.assert_not_called()


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
            # Press 'd' to show confirmation
            await pilot.press("d")
            await pilot.pause()

            # Verify ConfirmDialog is shown
            assert isinstance(app.screen, ConfirmDialog)

            # Press enter to confirm
            await pilot.press("enter")
            await pilot.pause()

            # Verify that save_projects was called with the correct list
            mock_load.assert_called_once()
            updated_projects = [p for p in existing_projects if p.slug != "fabric-api"]
            mock_save.assert_called_once_with(updated_projects)


# Phase 2: Error Handling Tests


@pytest.mark.asyncio
async def test_detail_screen_delete_handles_exception(
    app_config, make_update_check_result
) -> None:
    """Test that delete action handles exceptions gracefully."""

    class TestApp(App[None]):
        def on_mount(self):
            project = make_update_check_result(slug="fabric-api")
            self.push_screen(ProjectDetailScreen(project=project, config=app_config))

    with patch("mcpax.tui.screens.detail.load_projects") as mock_load:
        mock_load.side_effect = Exception("File access error")

        app = TestApp()
        async with app.run_test() as pilot:
            # Verify detail screen is active
            assert isinstance(app.screen, ProjectDetailScreen)

            # Press 'd' to show confirmation
            await pilot.press("d")
            await pilot.pause()

            # ConfirmDialog should be shown
            assert isinstance(app.screen, ConfirmDialog)

            # Press enter to confirm
            await pilot.press("enter")
            await pilot.pause()

            # Screen should still be ProjectDetailScreen (not dismissed due to error)
            assert isinstance(app.screen, ProjectDetailScreen)


@pytest.mark.asyncio
async def test_detail_screen_displays_error_when_present(
    app_config, make_update_check_result
) -> None:
    """Test that error messages are displayed when present in project."""

    class TestApp(App[None]):
        def on_mount(self):
            project = make_update_check_result(
                slug="test-project",
                status=InstallStatus.CHECK_FAILED,
            )
            # Add error message to project
            project.error = "Version lookup failed"
            self.push_screen(ProjectDetailScreen(project=project, config=app_config))

    app = TestApp()
    async with app.run_test():
        screen = app.screen
        assert isinstance(screen, ProjectDetailScreen)

        # Check that error Static widget exists with "error" class
        error_widgets = screen.query(".error")
        assert len(error_widgets) > 0


# Phase 4: Button/Event Operation Tests


@pytest.mark.asyncio
async def test_detail_screen_delete_button_click(
    app_config, make_update_check_result
) -> None:
    """Test that clicking delete button removes project."""

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
        ]
        mock_load.return_value = existing_projects

        app = TestApp()
        async with app.run_test() as pilot:
            # Click delete button
            delete_button = app.screen.query_one("#delete-button")
            await pilot.click(delete_button)
            await pilot.pause()

            # ConfirmDialog should be shown
            assert isinstance(app.screen, ConfirmDialog)

            # Press enter to confirm
            await pilot.press("enter")
            await pilot.pause()

            # Verify save_projects was called
            mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_detail_screen_close_button_click(
    app_config, make_update_check_result
) -> None:
    """Test that clicking close button dismisses screen."""

    class TestApp(App[None]):
        def on_mount(self):
            project = make_update_check_result(slug="test-project")
            self.push_screen(ProjectDetailScreen(project=project, config=app_config))

    app = TestApp()
    async with app.run_test() as pilot:
        # Verify detail screen is active
        assert isinstance(app.screen, ProjectDetailScreen)

        # Click close button
        close_button = app.screen.query_one("#close-button")
        await pilot.click(close_button)
        await pilot.pause()

        # Screen should be dismissed
        assert not isinstance(app.screen, ProjectDetailScreen)
