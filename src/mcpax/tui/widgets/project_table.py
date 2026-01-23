"""ProjectTable widget for displaying project list."""

from typing import Any

from rich.text import Text
from textual.widgets import DataTable

from mcpax.core.models import InstallStatus, UpdateCheckResult


class ProjectTable(DataTable[str]):
    """DataTable widget for displaying project information."""

    COLUMNS = [
        ("slug", "Slug", 25),
        ("type", "Type", 12),
        ("status", "Status", 15),
        ("current", "Current", 12),
        ("latest", "Latest", 12),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ProjectTable.

        Args:
            **kwargs: Additional arguments passed to DataTable
        """
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self._projects: list[UpdateCheckResult] = []
        self._sort_column: str | None = None
        self._sort_reverse: bool = False

    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self._setup_columns()

    def _setup_columns(self) -> None:
        """Set up table columns."""
        for col_id, label, width in self.COLUMNS:
            self.add_column(label, key=col_id, width=width)

    @property
    def projects(self) -> list[UpdateCheckResult]:
        """Get the current list of projects.

        Returns:
            List of UpdateCheckResult objects
        """
        return self._projects

    @property
    def selected_project(self) -> UpdateCheckResult | None:
        """Get the currently selected project.

        Returns:
            Selected UpdateCheckResult or None if nothing is selected
        """
        if not self.cursor_coordinate:
            return None

        row_index = self.cursor_coordinate.row
        if 0 <= row_index < len(self._projects):
            return self._projects[row_index]

        return None

    def load_projects(self, projects: list[UpdateCheckResult]) -> None:
        """Load projects into the table.

        Args:
            projects: List of UpdateCheckResult objects to display
        """
        self._projects = projects
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the table with project data."""
        self.clear()

        for project in self._projects:
            self.add_row(
                project.slug,
                project.project_type.value,
                self._render_status_cell(project.status),  # type: ignore[arg-type]
                project.current_version or "-",
                project.latest_version or "-",
                key=project.slug,
            )

    def _render_status_cell(self, status: InstallStatus) -> Text:
        """Render status cell with icon and color.

        Args:
            status: Installation status

        Returns:
            Rich Text object with styled status
        """
        status_map = {
            InstallStatus.INSTALLED: ("✓", "green"),
            InstallStatus.NOT_INSTALLED: ("○", "white"),
            InstallStatus.OUTDATED: ("⚠", "yellow"),
            InstallStatus.NOT_COMPATIBLE: ("✗", "red"),
            InstallStatus.CHECK_FAILED: ("?", "red"),
        }

        icon, color = status_map.get(status, ("?", "white"))
        status_text = status.value.replace("_", " ").title()

        return Text(f"{icon} {status_text}", style=color)

    def refresh_project(self, project: UpdateCheckResult) -> None:
        """Refresh a single project in the table.

        Args:
            project: Updated project information
        """
        # Find and update the project in the list
        for i, p in enumerate(self._projects):
            if p.slug == project.slug:
                self._projects[i] = project
                break

        # Refresh the table display
        self._populate_table()

    def sort_by_column(self, column: str, reverse: bool | None = None) -> None:
        """Sort table by column.

        Args:
            column: Column key to sort by
            reverse: Sort direction (True for descending, False for ascending).
                    If None, toggle if same column, else ascending.
        """
        # Determine sort direction
        if reverse is None:
            if self._sort_column == column:
                # Toggle direction
                self._sort_reverse = not self._sort_reverse
            else:
                # New column, start ascending
                self._sort_reverse = False
        else:
            self._sort_reverse = reverse

        self._sort_column = column

        # Define status priority for sorting
        status_priority = {
            InstallStatus.OUTDATED: 0,
            InstallStatus.NOT_INSTALLED: 1,
            InstallStatus.INSTALLED: 2,
            InstallStatus.NOT_COMPATIBLE: 3,
            InstallStatus.CHECK_FAILED: 4,
        }

        # Sort by the specified column
        if column == "slug":
            self._projects.sort(key=lambda p: p.slug, reverse=self._sort_reverse)
        elif column == "type":
            self._projects.sort(
                key=lambda p: p.project_type.value,
                reverse=self._sort_reverse,
            )
        elif column == "status":
            self._projects.sort(
                key=lambda p: status_priority.get(p.status, 99),
                reverse=self._sort_reverse,
            )
        elif column == "current":
            self._projects.sort(
                key=lambda p: p.current_version or "",
                reverse=self._sort_reverse,
            )
        elif column == "latest":
            self._projects.sort(
                key=lambda p: p.latest_version or "",
                reverse=self._sort_reverse,
            )

        # Refresh the table display
        self._populate_table()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle header click for sorting.

        Args:
            event: Header selected event
        """
        column_key = str(event.column_key)
        self.sort_by_column(column_key)
