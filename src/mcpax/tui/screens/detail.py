"""Project detail modal screen."""

from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from mcpax.core.config import load_projects, save_projects
from mcpax.core.models import AppConfig, ProjectConfig, UpdateCheckResult
from mcpax.tui.screens.confirm import ConfirmDialog


class ProjectDetailScreen(ModalScreen[bool]):
    """Modal screen for displaying project details."""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("d", "delete", "Delete"),
    ]

    def __init__(
        self,
        project: UpdateCheckResult,
        config: AppConfig,
        load_projects_func: Callable[[], list[ProjectConfig]] | None = None,
        save_projects_func: Callable[[list[ProjectConfig]], object] | None = None,
    ) -> None:
        """Initialize ProjectDetailScreen.

        Args:
            project: Project information to display
            config: Application configuration
        """
        super().__init__()
        self._project = project
        self._config = config
        self._load_projects = load_projects_func or load_projects
        self._save_projects = save_projects_func or save_projects

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
        """Show confirmation dialog before deleting."""
        message = f"Are you sure you want to delete '{self._project.slug}'?"
        self.app.push_screen(
            ConfirmDialog(
                message=message,
                confirm_label="Delete",
                cancel_label="Cancel",
            ),
            callback=self._on_confirm_dismissed,
        )

    def _on_confirm_dismissed(self, confirmed: bool | None) -> None:
        """Handle confirmation dialog result.

        Args:
            confirmed: True if user confirmed deletion, False or None otherwise.
        """
        if confirmed:
            self._delete_project()

    def _delete_project(self) -> None:
        """Delete the project from projects.toml."""
        try:
            projects = self._load_projects()
            # Filter out the project to delete
            updated_projects = [p for p in projects if p.slug != self._project.slug]
            self._save_projects(updated_projects)
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
