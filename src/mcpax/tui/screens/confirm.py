"""Confirmation dialog screen."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmDialog(ModalScreen[bool]):
    """Confirmation dialog modal.

    This modal displays a message and two buttons (confirm/cancel).
    Pressing Enter or clicking the confirm button dismisses with True.
    Pressing Escape or clicking the cancel button dismisses with False.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    def __init__(
        self,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
    ) -> None:
        """Initialize the confirmation dialog.

        Args:
            message: Message to display
            confirm_label: Label for the confirm button
            cancel_label: Label for the cancel button
        """
        super().__init__()
        self.message = message
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label

    def compose(self) -> ComposeResult:
        """Compose the dialog widgets."""
        with Container(id="confirm-container"):
            yield Static(self.message, id="confirm-message")
            with Horizontal(id="confirm-button-row"):
                yield Button(self.confirm_label, id="confirm-button", variant="error")
                yield Button(self.cancel_label, id="cancel-button")

    @on(Button.Pressed, "#confirm-button")
    def handle_confirm(self) -> None:
        """Handle confirm button press."""
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-button")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        self.dismiss(False)

    def action_confirm(self) -> None:
        """Action for confirm (Enter key)."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Action for cancel (Escape key)."""
        self.dismiss(False)
