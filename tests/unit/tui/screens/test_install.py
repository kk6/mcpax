"""Tests for InstallScreen."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App

from mcpax.core.models import (
    AppConfig,
    InstallStatus,
    Loader,
    ProjectType,
    UpdateCheckResult,
    UpdateResult,
)
from mcpax.tui.screens.install import InstallPhase, InstallScreen


def create_test_app_config() -> AppConfig:
    """Create a test AppConfig instance."""
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        minecraft_dir=Path("/tmp/minecraft"),
        max_concurrent_downloads=5,
        verify_hash=True,
    )


def create_test_update_result(
    slug: str,
    status: InstallStatus = InstallStatus.NOT_INSTALLED,
    project_type: ProjectType = ProjectType.MOD,
    latest_version: str = "1.0.0",
) -> UpdateCheckResult:
    """Create a test UpdateCheckResult instance."""
    return UpdateCheckResult(
        slug=slug,
        project_type=project_type,
        status=status,
        current_version=None,
        current_file=None,
        latest_version=latest_version,
        latest_version_id="version-id-123",
        latest_file=None,
    )


@pytest.mark.asyncio
async def test_install_screen_initialization() -> None:
    """Test InstallScreen initialization."""
    config = create_test_app_config()
    updates = [create_test_update_result("sodium")]
    screen = InstallScreen(updates=updates, config=config)

    assert screen is not None
    assert screen._updates == updates
    assert screen._config == config
    assert screen._phase == InstallPhase.INSTALLING


@pytest.mark.asyncio
async def test_install_screen_has_escape_binding() -> None:
    """Test InstallScreen has escape keybinding for cancel."""
    config = create_test_app_config()
    updates = [create_test_update_result("sodium")]
    screen = InstallScreen(updates=updates, config=config)

    # Check that 'escape' is bound to cancel action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "escape" in bindings
    assert bindings["escape"] == "cancel"


@pytest.mark.asyncio
async def test_install_screen_composes_progress_panel() -> None:
    """Test InstallScreen composes ProgressPanel widget."""
    from mcpax.tui.widgets.progress_panel import ProgressPanel

    config = create_test_app_config()
    updates = [create_test_update_result("sodium")]
    screen = InstallScreen(updates=updates, config=config)

    # Check that compose() yields ProgressPanel
    widgets = list(screen.compose())
    progress_panels = [w for w in widgets if isinstance(w, ProgressPanel)]
    assert len(progress_panels) == 1


@pytest.mark.asyncio
async def test_install_screen_executes_install_worker() -> None:
    """Test InstallScreen executes install worker on mount."""

    class TestApp(App[None]):
        def on_mount(self):
            config = create_test_app_config()
            updates = [create_test_update_result("sodium")]
            self.push_screen(InstallScreen(updates=updates, config=config))

    mock_update_result = UpdateResult(successful=["sodium"], failed=[], backed_up=[])

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectManager") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()
        mock_manager.apply_updates = AsyncMock(return_value=mock_update_result)
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        app = TestApp()
        async with app.run_test():
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Verify apply_updates was called
            mock_manager.apply_updates.assert_called_once()


@pytest.mark.asyncio
async def test_install_screen_cancel_during_installation() -> None:
    """Test cancelling installation with escape key."""

    class TestApp(App[None]):
        def on_mount(self):
            config = create_test_app_config()
            updates = [create_test_update_result("sodium")]
            self.push_screen(InstallScreen(updates=updates, config=config))

    mock_update_result = UpdateResult(successful=[], failed=[], backed_up=[])

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectManager") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()

        # Make apply_updates take some time so we can cancel
        async def slow_apply_updates(*args, **kwargs):
            await asyncio.sleep(0.5)
            return mock_update_result

        mock_manager.apply_updates = slow_apply_updates
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
async def test_install_screen_dismiss_after_cancel() -> None:
    """Test that ESC dismisses the screen after cancellation."""

    class TestApp(App[None]):
        def on_mount(self):
            config = create_test_app_config()
            updates = [create_test_update_result("sodium")]
            self.push_screen(InstallScreen(updates=updates, config=config))

    mock_update_result = UpdateResult(successful=[], failed=[], backed_up=[])

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectManager") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()

        # Make apply_updates take some time so we can cancel
        async def slow_apply_updates(*args, **kwargs):
            await asyncio.sleep(0.5)
            return mock_update_result

        mock_manager.apply_updates = slow_apply_updates
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
async def test_install_screen_successful_installation_summary() -> None:
    """Test successful installation shows proper summary."""

    class TestApp(App[None]):
        def on_mount(self):
            config = create_test_app_config()
            updates = [
                create_test_update_result("sodium"),
                create_test_update_result("lithium"),
            ]
            self.push_screen(InstallScreen(updates=updates, config=config))

    from mcpax.core.models import FailedUpdate

    mock_update_result = UpdateResult(
        successful=["sodium"],
        failed=[FailedUpdate(slug="lithium", error="Network timeout")],
        backed_up=["old_sodium.jar"],
    )

    with (
        patch("mcpax.tui.screens.install.Downloader") as mock_downloader_class,
        patch("mcpax.tui.screens.install.ProjectManager") as mock_manager_class,
    ):
        mock_downloader = AsyncMock()
        mock_downloader_class.return_value.__aenter__.return_value = mock_downloader
        mock_downloader_class.return_value.__aexit__.return_value = AsyncMock()

        mock_manager = AsyncMock()
        mock_manager.apply_updates = AsyncMock(return_value=mock_update_result)
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
