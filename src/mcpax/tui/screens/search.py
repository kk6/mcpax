"""Search screen for displaying Modrinth search results."""

import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static
from textual.worker import Worker, WorkerState

from mcpax.core.api import ModrinthClient
from mcpax.core.config import ConfigValidationError, load_projects, save_projects
from mcpax.core.models import (
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

        self._add_project_to_config(selected)

    def _add_project_to_config(self, hit: SearchHit) -> None:
        """Add project to projects.toml.

        Args:
            hit: Selected search hit to add
        """
        try:
            projects = load_projects()
        except FileNotFoundError:
            projects = []
        except ConfigValidationError as e:
            self.notify(f"設定ファイルの読み込みに失敗しました: {e}", severity="error")
            return

        # Check for duplicates
        if any(p.slug == hit.slug for p in projects):
            self.notify(f"'{hit.slug}' は既に登録済みです", severity="warning")
            return

        # Add new project
        projects.append(ProjectConfig(slug=hit.slug, project_type=hit.project_type))
        save_projects(projects)
        self._added = True
        self.notify(f"'{hit.slug}' を追加しました", severity="information")
