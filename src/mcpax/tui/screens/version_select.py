"""Version selection screen for pinning a specific version."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Label, Static
from textual.worker import Worker, WorkerState

from mcpax.core.api import ModrinthClient
from mcpax.core.models import Loader, ProjectType, ProjectVersion, ReleaseChannel

# Version selection result constants
VERSION_SELECT_CANCELLED: None = None
VERSION_SELECT_LATEST: str = "__LATEST__"


class VersionSelectScreen(Screen[str | None]):
    """Screen for selecting a version to pin."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
        Binding("l", "select_latest", "Latest (no pin)"),
    ]

    def __init__(
        self,
        slug: str,
        project_type: ProjectType,
        minecraft_version: str,
        mod_loader: str,
        shader_loader: str | None = None,
    ) -> None:
        """Initialize VersionSelectScreen.

        Args:
            slug: Project slug
            project_type: Project type
            minecraft_version: Minecraft version for filtering
            mod_loader: Mod loader for filtering
            shader_loader: Shader loader for filtering (optional)
        """
        super().__init__()
        self._slug = slug
        self._project_type = project_type
        self._minecraft_version = minecraft_version
        self._mod_loader = mod_loader
        self._shader_loader = shader_loader
        self._versions: dict[str, ProjectVersion] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            Screen widgets
        """
        yield Container(
            Static(f"Select version for '{self._slug}'", id="version-header"),
            Label(
                "Press [b]Enter[/b] to pin selected version, "
                "[b]L[/b] for latest (no pin), [b]Esc[/b] to cancel"
            ),
            Vertical(
                DataTable(id="version-table", cursor_type="row"),
                id="version-container",
            ),
            Footer(),
        )

    def on_mount(self) -> None:
        """Fetch versions when screen is mounted."""
        table = self.query_one(DataTable)
        table.add_column("Version", key="version")
        table.add_column("Type", key="type")
        table.add_column("Loaders", key="loaders")
        table.add_column("Game Versions", key="game_versions")
        table.add_column("Date", key="date")

        self.run_worker(self._fetch_versions(), exclusive=True)

    async def _fetch_versions(self) -> list[ProjectVersion]:
        """Fetch versions from Modrinth API.

        Returns:
            List of project versions
        """
        async with ModrinthClient() as client:
            return await client.get_versions(self._slug)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes.

        Args:
            event: Worker state change event
        """
        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if isinstance(result, list):
                self._populate_table(result)
        elif event.state == WorkerState.ERROR:
            self.notify(
                f"Failed to fetch versions: {event.worker.error}", severity="error"
            )
            self.dismiss(None)

    def _populate_table(self, versions: list[ProjectVersion]) -> None:
        """Populate table with versions.

        Args:
            versions: List of versions to display
        """
        table = self.query_one(DataTable)

        if not versions:
            self.notify("No versions found", severity="warning")
            self.dismiss(None)
            return

        # Store versions mapping for later retrieval
        self._versions = {version.id: version for version in versions}

        client = ModrinthClient()
        loader = Loader(self._mod_loader)
        shader_loader_enum = (
            Loader(self._shader_loader) if self._shader_loader else None
        )
        compatible_versions = client.filter_compatible_versions(
            versions=versions,
            minecraft_version=self._minecraft_version,
            loader=loader,
            channel=ReleaseChannel.ALPHA,  # TUI shows all channels
            project_type=self._project_type,
            shader_loader=shader_loader_enum,
        )
        compatible_ids = {v.id for v in compatible_versions}
        compatible = [v for v in versions if v.id in compatible_ids]
        incompatible = [v for v in versions if v.id not in compatible_ids]

        # Add compatible versions first (highlighted)
        for version in compatible:
            game_versions = ", ".join(version.game_versions[:3])
            if len(version.game_versions) > 3:
                game_versions += "..."

            loaders = ", ".join(version.loaders)

            table.add_row(
                version.version_number,
                version.version_type,
                loaders,
                game_versions,
                version.date_published.strftime("%Y-%m-%d"),
                key=version.id,
            )

        # Add incompatible versions (dimmed)
        for version in incompatible:
            game_versions = ", ".join(version.game_versions[:3])
            if len(version.game_versions) > 3:
                game_versions += "..."

            loaders = ", ".join(version.loaders)

            table.add_row(
                f"[dim]{version.version_number}[/dim]",
                f"[dim]{version.version_type}[/dim]",
                f"[dim]{loaders}[/dim]",
                f"[dim]{game_versions}[/dim]",
                f"[dim]{version.date_published.strftime('%Y-%m-%d')}[/dim]",
                key=version.id,
            )

        if compatible:
            # Select first compatible version by default
            table.move_cursor(row=0)

    def action_cancel(self) -> None:
        """Cancel version selection."""
        self.dismiss(VERSION_SELECT_CANCELLED)

    def action_select_latest(self) -> None:
        """Select latest version (no pinning)."""
        self.dismiss(VERSION_SELECT_LATEST)

    def action_select(self) -> None:
        """Select the currently highlighted version."""
        table = self.query_one(DataTable)
        if table.cursor_row is None:
            self.notify("No version selected", severity="warning")
            return

        # Get the version ID from the row key
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        if row_key:
            self._dismiss_with_version_id(str(row_key.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection via Enter key on DataTable.

        Args:
            event: Row selection event
        """
        # Get the version ID from the row key
        if event.row_key:
            self._dismiss_with_version_id(str(event.row_key.value))

    def _dismiss_with_version_id(self, version_id: str) -> None:
        """Dismiss the screen with the version number for the given version ID.

        Args:
            version_id: Version ID to dismiss with
        """
        version = self._versions.get(version_id)
        if version:
            self.dismiss(version.version_number)
