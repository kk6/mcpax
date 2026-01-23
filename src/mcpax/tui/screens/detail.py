"""Project detail modal screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from mcpax.core.config import load_projects, save_projects
from mcpax.core.models import AppConfig, UpdateCheckResult


class ProjectDetailScreen(ModalScreen[bool]):
    """Modal screen for displaying project details."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("d", "delete", "Delete"),
    ]

    def __init__(self, project: UpdateCheckResult, config: AppConfig) -> None:
        """Initialize ProjectDetailScreen.

        Args:
            project: Project information to display
            config: Application configuration
        """
        super().__init__()
        self._project = project
        self._config = config

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            Container with project details
        """
        with Container(id="detail-container"), Vertical():
            yield Label("Project Details", id="detail-title")
            yield Static(f"Slug: {self._project.slug}")
            yield Static(f"Type: {self._project.project_type.value}")
            yield Static(f"Status: {self._project.status.value}")
            yield Static(f"Current Version: {self._project.current_version or 'N/A'}")
            yield Static(f"Latest Version: {self._project.latest_version or 'N/A'}")
            if self._project.error:
                yield Static(f"Error: {self._project.error}", classes="error")

            with Container(id="button-container"):
                yield Button("Delete (d)", id="delete-button", variant="error")
                yield Button("Close (ESC)", id="close-button")

    def action_cancel(self) -> None:
        """Close the modal without deleting."""
        self.dismiss(False)

    def action_delete(self) -> None:
        """Delete the project after confirmation."""
        # TODO: Show confirmation dialog
        self._delete_project()

    def _delete_project(self) -> None:
        """Delete the project from projects.toml."""
        try:
            projects = load_projects()
            # Filter out the project to delete
            updated_projects = [p for p in projects if p.slug != self._project.slug]
            save_projects(updated_projects)
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Failed to delete project: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        if event.button.id == "delete-button":
            self.action_delete()
        elif event.button.id == "close-button":
            self.action_cancel()
