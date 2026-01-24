"""SearchResultTable widget for displaying search results."""

from typing import Any

from textual.widgets import DataTable

from mcpax.core.models import SearchHit


class SearchResultTable(DataTable[str]):
    """DataTable widget for displaying search results."""

    COLUMNS = [
        ("slug", "Slug", 20),
        ("title", "Title", 25),
        ("type", "Type", 12),
        ("downloads", "Downloads", 12),
    ]

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the SearchResultTable.

        Args:
            **kwargs: Additional arguments passed to DataTable
        """
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self._results: list[SearchHit] = []

    def on_mount(self) -> None:
        """Set up the table when mounted."""
        self._setup_columns()

    def _setup_columns(self) -> None:
        """Set up table columns."""
        for col_id, label, width in self.COLUMNS:
            self.add_column(label, key=col_id, width=width)

    @property
    def results(self) -> list[SearchHit]:
        """Get the current list of search results.

        Returns:
            List of SearchHit objects
        """
        return self._results

    @property
    def selected_result(self) -> SearchHit | None:
        """Get the currently selected search result.

        Returns:
            Selected SearchHit or None if nothing is selected
        """
        if not self.cursor_coordinate:
            return None

        row_index = self.cursor_coordinate.row
        if 0 <= row_index < len(self._results):
            return self._results[row_index]

        return None

    def load_results(self, results: list[SearchHit]) -> None:
        """Load search results into the table.

        Args:
            results: List of SearchHit objects to display
        """
        self._results = results
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the table with search result data."""
        self.clear()

        for result in self._results:
            self.add_row(
                result.slug,
                result.title,
                result.project_type.value,
                self._format_downloads(result.downloads),
                key=result.slug,
            )

    def _format_downloads(self, downloads: int) -> str:
        """Format download count for display.

        Args:
            downloads: Download count

        Returns:
            Formatted string (e.g., "1.2M", "500.0K", "999")
        """
        if downloads >= 1_000_000:
            return f"{downloads / 1_000_000:.1f}M"
        elif downloads >= 1_000:
            return f"{downloads / 1_000:.1f}K"
        else:
            return str(downloads)
