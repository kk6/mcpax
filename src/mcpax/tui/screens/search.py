"""Search screen for displaying Modrinth search results."""

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static
from textual.worker import Worker, WorkerState

from mcpax.core.api import ModrinthClient
from mcpax.core.config import (
    ConfigValidationError,
    load_config,
    load_projects,
    save_projects,
)
from mcpax.core.models import (
    INSTALLABLE_PROJECT_TYPES,
    ProjectConfig,
    ProjectType,
    SearchHit,
    SearchResult,
)
from mcpax.tui.widgets.search_result_table import SearchResultTable

MODRINTH_SEARCH_LIMIT = 50


class SearchScreen(Screen[bool]):
    """Screen for displaying search results and adding projects."""

    BINDINGS = [
        Binding("escape", "cancel", "Back"),
        Binding("a", "add_project", "Add"),
    ]

    def __init__(self, query: str, project_type: ProjectType | None) -> None:
        """Initialize SearchScreen.

        Args:
            query: Search query string
            project_type: Optional project type filter
        """
        super().__init__()
        self._query = query
        self._project_type = project_type
        self._added = False

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            Screen widgets
        """
        yield Static(f"Search: '{self._query}'", id="search-header")
        yield SearchResultTable(id="search-results")
        yield Footer()

    def on_mount(self) -> None:
        """Execute search when screen is mounted."""
        self.run_worker(self._search_worker(), exclusive=True)

    async def _search_worker(self) -> SearchResult:
        """Execute Modrinth search.

        Returns:
            SearchResult from API
        """
        facets = None
        if self._project_type:
            facets = json.dumps([[f"project_type:{self._project_type.value}"]])

        async with ModrinthClient() as client:
            return await client.search(
                query=self._query, limit=MODRINTH_SEARCH_LIMIT, facets=facets
            )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes.

        Args:
            event: Worker state change event
        """
        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if isinstance(result, SearchResult):
                table = self.query_one(SearchResultTable)
                table.load_results(result.hits)

                if not result.hits:
                    self.notify("No results found", severity="warning")
        elif event.state == WorkerState.ERROR:
            self.notify(f"Search failed: {event.worker.error}", severity="error")

    def action_cancel(self) -> None:
        """Close the search screen."""
        self.dismiss(self._added)

    def action_add_project(self) -> None:
        """Add the selected project to projects.toml."""
        table = self.query_one(SearchResultTable)
        selected = table.selected_result

        if not selected:
            self.notify("No project selected", severity="warning")
            return

        # Show version selection screen
        self.run_worker(self._show_version_select(selected), exclusive=False)

    async def _show_version_select(self, hit: SearchHit) -> None:
        """Show version selection screen and add project.

        Args:
            hit: Selected search hit
        """
        # Check if project type is supported for installation
        if hit.project_type not in INSTALLABLE_PROJECT_TYPES:
            self.notify(
                f"'{hit.project_type.value}' type is not supported for installation",
                severity="error",
            )
            return

        from mcpax.tui.screens.version_select import (
            VERSION_SELECT_CANCELLED,
            VERSION_SELECT_LATEST,
            VersionSelectScreen,
        )

        try:
            # Load config to get minecraft version and mod loader
            config = load_config()
        except (FileNotFoundError, ConfigValidationError) as e:
            self.notify(f"Failed to load config: {e}", severity="error")
            return

        # Push version selection screen
        version_select_screen = VersionSelectScreen(
            slug=hit.slug,
            project_type=hit.project_type,
            minecraft_version=config.minecraft_version,
            mod_loader=config.mod_loader.value,
        )

        selected_version = await self.app.push_screen_wait(version_select_screen)

        # Handle version selection result
        if selected_version == VERSION_SELECT_CANCELLED:
            return  # User cancelled, don't add project
        elif selected_version == VERSION_SELECT_LATEST:
            self._add_project_to_config(hit, version=None)  # No version pinning
        else:
            self._add_project_to_config(hit, version=selected_version)

    def _add_project_to_config(
        self, hit: SearchHit, version: str | None = None
    ) -> None:
        """Add project to projects.toml.

        Args:
            hit: Selected search hit to add
            version: Optional version to pin
        """
        try:
            projects = load_projects()
        except FileNotFoundError:
            projects = []
        except ConfigValidationError as e:
            self.notify(f"Failed to load configuration: {e}", severity="error")
            return

        # Check for duplicates
        if any(p.slug == hit.slug for p in projects):
            self.notify(f"'{hit.slug}' is already in the list", severity="warning")
            return

        # Add new project
        projects.append(
            ProjectConfig(slug=hit.slug, project_type=hit.project_type, version=version)
        )
        save_projects(projects)
        self._added = True

        if version:
            self.notify(
                f"Added '{hit.slug}' (pinned to {version})", severity="information"
            )
        else:
            self.notify(f"Added '{hit.slug}' (latest)", severity="information")
