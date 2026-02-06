"""Tests for ConfirmDialog."""

import pytest
from textual.app import App
from textual.widgets import Button, Static

from mcpax.tui.screens.confirm import ConfirmDialog


@pytest.mark.asyncio
async def test_confirm_dialog_displays_message():
    """Test that the dialog displays the provided message."""
    message = "Are you sure you want to delete this project?"

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(ConfirmDialog(message=message))

    app = TestApp()
    async with app.run_test():
        dialog = app.screen
        assert isinstance(dialog, ConfirmDialog)
        # Check that message is displayed
        msg_widget = dialog.query_one("#confirm-message", Static)
        assert msg_widget.render().plain == message


@pytest.mark.asyncio
async def test_confirm_dialog_confirm_returns_true():
    """Test that clicking confirm button returns True."""
    result = None

    def callback(confirmed: bool) -> None:
        nonlocal result
        result = confirmed

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(ConfirmDialog(message="Test message"), callback=callback)

    app = TestApp()
    async with app.run_test() as pilot:
        # Verify dialog is shown
        assert isinstance(app.screen, ConfirmDialog)

        # Click confirm button
        await pilot.click("#confirm-button")
        await pilot.pause()

        # Dialog should be dismissed
        assert not isinstance(app.screen, ConfirmDialog)
        # Callback should have been called with True
        assert result is True


@pytest.mark.asyncio
async def test_confirm_dialog_cancel_returns_false():
    """Test that clicking cancel button returns False."""
    result = None

    def callback(confirmed: bool) -> None:
        nonlocal result
        result = confirmed

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(ConfirmDialog(message="Test message"), callback=callback)

    app = TestApp()
    async with app.run_test() as pilot:
        # Verify dialog is shown
        assert isinstance(app.screen, ConfirmDialog)

        # Click cancel button
        await pilot.click("#cancel-button")
        await pilot.pause()

        # Dialog should be dismissed
        assert not isinstance(app.screen, ConfirmDialog)
        # Callback should have been called with False
        assert result is False


@pytest.mark.asyncio
async def test_confirm_dialog_escape_returns_false():
    """Test that pressing escape returns False."""
    result = None

    def callback(confirmed: bool) -> None:
        nonlocal result
        result = confirmed

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(ConfirmDialog(message="Test message"), callback=callback)

    app = TestApp()
    async with app.run_test() as pilot:
        # Verify dialog is shown
        assert isinstance(app.screen, ConfirmDialog)

        # Press escape
        await pilot.press("escape")
        await pilot.pause()

        # Dialog should be dismissed
        assert not isinstance(app.screen, ConfirmDialog)
        # Callback should have been called with False
        assert result is False


@pytest.mark.asyncio
async def test_confirm_dialog_enter_confirms():
    """Test that pressing enter returns True."""
    result = None

    def callback(confirmed: bool) -> None:
        nonlocal result
        result = confirmed

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(ConfirmDialog(message="Test message"), callback=callback)

    app = TestApp()
    async with app.run_test() as pilot:
        # Verify dialog is shown
        assert isinstance(app.screen, ConfirmDialog)

        # Press enter
        await pilot.press("enter")
        await pilot.pause()

        # Dialog should be dismissed
        assert not isinstance(app.screen, ConfirmDialog)
        # Callback should have been called with True
        assert result is True


@pytest.mark.asyncio
async def test_confirm_dialog_custom_button_labels():
    """Test that custom button labels are reflected."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(
                ConfirmDialog(
                    message="Test message",
                    confirm_label="Delete",
                    cancel_label="Cancel",
                )
            )

    app = TestApp()
    async with app.run_test():
        dialog = app.screen
        assert isinstance(dialog, ConfirmDialog)
        confirm_btn = dialog.query_one("#confirm-button", Button)
        cancel_btn = dialog.query_one("#cancel-button", Button)
        assert confirm_btn.label.plain == "Delete"
        assert cancel_btn.label.plain == "Cancel"
