"""Main screen for displaying project list."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer
from textual.worker import Worker, WorkerState

from mcpax.core.config import ConfigValidationError, load_projects
from mcpax.core.manager import ProjectManager
from mcpax.core.models import AppConfig, ProjectConfig, UpdateCheckResult
from mcpax.tui.widgets import ProjectTable, StatusBar


class MainScreen(Screen[None]):
    """Main screen for displaying project list."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "view_detail", "View Detail"),
    ]

    def __init__(self, config: AppConfig) -> None:
        """Initialize MainScreen.

        Args:
            config: Application configuration
        """
        super().__init__()
        self._config = config
        self._projects: list[ProjectConfig] = []

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            StatusBar, ProjectTable, Footer
        """
        yield StatusBar(config=self._config)
        yield ProjectTable()
        yield Footer()

    def on_mount(self) -> None:
        """Load projects when screen is mounted."""
        self._load_and_check_updates()

    def _load_and_check_updates(self) -> None:
        """Load projects and check for updates."""
        try:
            self._projects = load_projects()
            # Start background worker to check updates
            self.run_worker(self._check_updates_worker(), exclusive=True)
        except (FileNotFoundError, ConfigValidationError) as e:
            self.notify(f"Error loading projects: {e}", severity="error")
        except Exception as e:
            self.notify(f"Unexpected error: {e}", severity="error")

    async def _check_updates_worker(self) -> list[UpdateCheckResult]:
        """Background worker to check for updates.

        Returns:
            List of update check results
        """
        async with ProjectManager(self._config) as manager:
            return await manager.check_updates(self._projects)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes.

        Args:
            event: Worker state change event
        """
        if event.state == WorkerState.SUCCESS:
            # Update the project table with results
            table = self.query_one(ProjectTable)
            result = event.worker.result
            if isinstance(result, list):
                table.load_projects(result)
                self.notify(
                    "Projects loaded successfully", severity="information"
                )
        elif event.state == WorkerState.ERROR:
            self.notify(
                f"Failed to check updates: {event.worker.error}",
                severity="error",
            )

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()

    def action_refresh(self) -> None:
        """Refresh project list."""
        self._load_and_check_updates()

    def action_view_detail(self) -> None:
        """View detail of selected project (stub for future)."""
        table = self.query_one(ProjectTable)
        selected = table.selected_project

        if selected:
            self.notify(
                f"Detail view for {selected.slug} (coming soon)",
                severity="information",
            )
        else:
            self.notify("No project selected", severity="warning")
