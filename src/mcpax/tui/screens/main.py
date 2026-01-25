"""Main screen for displaying project list."""

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer
from textual.worker import Worker, WorkerState

from mcpax.core.config import ConfigValidationError, load_projects
from mcpax.core.manager import ProjectManager
from mcpax.core.models import AppConfig, ProjectConfig, ProjectType, UpdateCheckResult
from mcpax.tui.screens.detail import ProjectDetailScreen
from mcpax.tui.screens.search import SearchScreen
from mcpax.tui.widgets import ProjectTable, SearchInput, StatusBar


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
            StatusBar, SearchInput, ProjectTable, Footer
        """
        yield StatusBar(config=self._config)
        yield SearchInput()
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
            logging.exception("Unexpected error in _load_and_check_updates")
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
                self.notify("Projects loaded successfully", severity="information")
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
        """View detail of selected project."""
        table = self.query_one(ProjectTable)
        selected = table.selected_project

        if selected:
            self._open_detail(selected)
        else:
            self.notify("No project selected", severity="warning")

    def _open_detail(self, project: UpdateCheckResult) -> None:
        """Open the detail modal for the given project."""
        if isinstance(self.app.screen, ProjectDetailScreen):
            return

        self.app.push_screen(
            ProjectDetailScreen(project=project, config=self._config),
            callback=self._on_detail_dismissed,
        )

    def _on_detail_dismissed(self, deleted: bool | None) -> None:
        """Handle modal dismissal.

        Args:
            deleted: True if project was deleted, False or None otherwise
        """
        if deleted:
            self._load_and_check_updates()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:  # type: ignore[attr-defined]
        """Handle row selection (Enter key or click) in the data table.

        Args:
            event: Row selected event
        """
        table = self.query_one(ProjectTable)
        selected = table.selected_project
        if selected:
            self._open_detail(selected)

    def on_search_input_search_requested(
        self, message: SearchInput.SearchRequested
    ) -> None:
        """Handle search request from SearchInput.

        Args:
            message: SearchRequested message with query and project_type
        """
        query: str = message.query
        project_type: ProjectType | None = message.project_type

        # Only open SearchScreen if query is not empty
        if query:
            self.app.push_screen(
                SearchScreen(query=query, project_type=project_type),
                callback=self._on_search_dismissed,
            )

    def _on_search_dismissed(self, added: bool | None) -> None:
        """Handle search screen dismissal.

        Args:
            added: True if project was added, False or None otherwise
        """
        if added:
            self._load_and_check_updates()
