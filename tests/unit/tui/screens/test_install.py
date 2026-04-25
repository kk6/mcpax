"""Tests for InstallScreen."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App

from mcpax.core.models import (
    UpdateResult,
)
from mcpax.tui.screens.install import InstallPhase, InstallScreen


@pytest.mark.asyncio
async def test_install_screen_initialization(
    app_config, make_update_check_result
) -> None:
    """Test InstallScreen initialization."""
    updates = [make_update_check_result("sodium")]
    screen = InstallScreen(updates=updates, config=app_config)

    assert screen is not None
    assert screen._updates == updates
    assert screen._config == app_config
    assert screen._phase == InstallPhase.INSTALLING


@pytest.mark.asyncio
async def test_install_screen_has_escape_binding(
    app_config, make_update_check_result
) -> None:
    """Test InstallScreen has escape keybinding for cancel."""
    updates = [make_update_check_result("sodium")]
    screen = InstallScreen(updates=updates, config=app_config)

    # Check that 'escape' is bound to cancel action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "escape" in bindings
    assert bindings["escape"] == "cancel"


@pytest.mark.asyncio
async def test_install_screen_composes_progress_panel(
    app_config, make_update_check_result
) -> None:
    """Test InstallScreen composes ProgressPanel widget."""
    from mcpax.tui.widgets.progress_panel import ProgressPanel

    updates = [make_update_check_result("sodium")]
    screen = InstallScreen(updates=updates, config=app_config)

    # Check that compose() yields ProgressPanel
    widgets = list(screen.compose())
    progress_panels = [w for w in widgets if isinstance(w, ProgressPanel)]
    assert len(progress_panels) == 1


@pytest.mark.asyncio
async def test_install_screen_executes_install_worker(
    app_config, make_update_check_result
) -> None:
    """Test InstallScreen executes install worker on mount."""

    class TestApp(App[None]):
        def on_mount(self):
            updates = [make_update_check_result("sodium")]
            self.push_screen(InstallScreen(updates=updates, config=app_config))

    mock_update_result = UpdateResult(successful=["sodium"], failed=[], backed_up=[])

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectServices") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()
        mock_manager.update_applier.apply_updates = AsyncMock(
            return_value=mock_update_result
        )
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        app = TestApp()
        async with app.run_test():
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Verify apply_updates was called
            mock_manager.update_applier.apply_updates.assert_called_once()


@pytest.mark.asyncio
async def test_install_screen_cancel_during_installation(
    app_config, make_update_check_result
) -> None:
    """Test cancelling installation with escape key."""

    class TestApp(App[None]):
        def on_mount(self):
            updates = [make_update_check_result("sodium")]
            self.push_screen(InstallScreen(updates=updates, config=app_config))

    mock_update_result = UpdateResult(successful=[], failed=[], backed_up=[])

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectServices") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()

        # Block indefinitely so the worker is still running when escape is pressed.
        # worker.cancel() raises CancelledError inside the wait(), ending the task.
        async def blocking_apply_updates(*args, **kwargs):
            await asyncio.Event().wait()
            return mock_update_result

        mock_manager.update_applier.apply_updates = blocking_apply_updates
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        app = TestApp()
        async with app.run_test() as pilot:
            # Verify screen is active
            screen = app.screen
            assert isinstance(screen, InstallScreen)
            assert screen._phase == InstallPhase.INSTALLING

            # Press escape to cancel
            await pilot.press("escape")
            await pilot.pause()

            # Screen should be cancelled and phase should be COMPLETED
            assert screen._cancelled is True
            assert screen._phase == InstallPhase.COMPLETED

            # Verify cancelled message is shown in summary
            from textual.widgets import Static

            summary = screen.query_one("#install-summary", Static)
            assert summary.display is True
            summary_text = str(summary.render())
            assert "Installation was cancelled" in summary_text


@pytest.mark.asyncio
async def test_install_screen_dismiss_after_cancel(
    app_config, make_update_check_result
) -> None:
    """Test that ESC dismisses the screen after cancellation."""

    class TestApp(App[None]):
        def on_mount(self):
            updates = [make_update_check_result("sodium")]
            self.push_screen(InstallScreen(updates=updates, config=app_config))

    mock_update_result = UpdateResult(successful=[], failed=[], backed_up=[])

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectServices") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()

        # Block indefinitely so the worker is still running when escape is pressed.
        # worker.cancel() raises CancelledError inside the wait(), ending the task.
        async def blocking_apply_updates(*args, **kwargs):
            await asyncio.Event().wait()
            return mock_update_result

        mock_manager.update_applier.apply_updates = blocking_apply_updates
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        app = TestApp()
        async with app.run_test() as pilot:
            # Get the install screen
            install_screen = app.screen
            assert isinstance(install_screen, InstallScreen)
            assert install_screen._phase == InstallPhase.INSTALLING

            # Press escape to cancel
            await pilot.press("escape")
            await pilot.pause()

            # Phase should be COMPLETED after cancellation
            assert install_screen._phase == InstallPhase.COMPLETED

            # Press escape again to dismiss the summary
            await pilot.press("escape")
            await pilot.pause()

            # Screen should have been dismissed
            # (The app should no longer be showing the install screen)
            assert app.screen is not install_screen


@pytest.mark.asyncio
async def test_install_screen_successful_installation_summary(
    app_config, make_update_check_result
) -> None:
    """Test successful installation shows proper summary."""

    class TestApp(App[None]):
        def on_mount(self):
            updates = [
                make_update_check_result("sodium"),
                make_update_check_result("lithium"),
            ]
            self.push_screen(InstallScreen(updates=updates, config=app_config))

    from mcpax.core.models import FailedUpdate

    mock_update_result = UpdateResult(
        successful=["sodium"],
        failed=[FailedUpdate(slug="lithium", error="Network timeout")],
        backed_up=["old_sodium.jar"],
    )

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectServices") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()
        mock_manager.update_applier.apply_updates = AsyncMock(
            return_value=mock_update_result
        )
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        app = TestApp()
        async with app.run_test():
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            screen = app.screen
            assert isinstance(screen, InstallScreen)

            # Verify phase is COMPLETED
            assert screen._phase == InstallPhase.COMPLETED

            # Verify result was stored
            assert screen._result == mock_update_result

            # Verify summary is displayed
            from textual.widgets import Static

            summary = screen.query_one("#install-summary", Static)
            assert summary.display is True

            # Verify summary contains expected text
            # Static widget stores the text in its renderable property
            summary_text = str(summary.render())
            assert "Successfully installed 1 project(s)" in summary_text
            assert "sodium" in summary_text
            assert "Failed 1 project(s)" in summary_text
            assert "lithium" in summary_text
            assert "Network timeout" in summary_text
            assert "Backed up 1 file(s)" in summary_text


@pytest.mark.asyncio
async def test_install_screen_error_during_installation(
    app_config, make_update_check_result
) -> None:
    """Test that worker errors show summary with error message."""

    class TestApp(App[None]):
        def on_mount(self):
            updates = [make_update_check_result("sodium")]
            self.push_screen(InstallScreen(updates=updates, config=app_config))

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectServices") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader

        async def async_exit(*args):
            return None

        mock_downloader_class.return_value.__aexit__ = async_exit

        mock_manager = AsyncMock()
        # Simulate a network error during apply_updates
        mock_manager.update_applier.apply_updates = AsyncMock(
            side_effect=RuntimeError("Network connection lost")
        )
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__ = async_exit

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for worker to complete (with error)
            await app.workers.wait_for_complete()

            # Give time for event handlers to process
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, InstallScreen)

            # Verify phase is COMPLETED
            assert screen._phase == InstallPhase.COMPLETED

            # Verify error was stored
            assert screen._error is not None
            assert "Network connection lost" in str(screen._error)

            # Verify summary is displayed
            from textual.widgets import Static

            summary = screen.query_one("#install-summary", Static)
            assert summary.display is True

            # Verify summary contains error message
            summary_text = str(summary.render())
            assert "Installation failed" in summary_text
            assert "Network connection lost" in summary_text

            # Verify progress UI is hidden
            assert screen.query_one("#install-header").display is False
            assert screen.query_one("#install-progress").display is False
