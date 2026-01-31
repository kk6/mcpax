"""SearchInput widget for search query and type filter."""

from typing import Any, cast

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Select

from mcpax.core.models import ProjectType


class SearchInput(Widget):
    """SearchInput widget for entering search queries and type filters."""

    class SearchRequested(Message):
        """Message emitted when a search is requested."""

        def __init__(self, query: str, project_type: ProjectType | None) -> None:
            """Initialize the SearchRequested message.

            Args:
                query: Search query string
                project_type: Project type filter (None for all types)
            """
            super().__init__()
            self.query = query
            self.project_type = project_type

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the SearchInput widget.

        Args:
            **kwargs: Additional arguments passed to Widget
        """
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        """Compose the SearchInput widget.

        Yields:
            Input widget for search query
            Select widget for project type filter
        """
        yield Input(placeholder="Search projects...")
        yield Select[ProjectType | None](
            options=[
                ("All Types", None),
                ("Mod", ProjectType.MOD),
                ("Shader", ProjectType.SHADER),
                ("Resource Pack", ProjectType.RESOURCEPACK),
            ],
            value=None,
        )

    def _emit_search_requested(self) -> None:
        """Emit SearchRequested message with current query and filter."""
        input_widget = self.query_one(Input)
        select_widget: Select[ProjectType | None] = self.query_one(Select)

        query = input_widget.value
        project_type: ProjectType | None = (
            None
            if (v := select_widget.value) is Select.BLANK
            else cast(ProjectType | None, v)
        )

        self.post_message(self.SearchRequested(query, project_type))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Input.Submitted event (Enter key pressed).

        Args:
            event: Input.Submitted event
        """
        self._emit_search_requested()

    @property
    def search_query(self) -> str:
        """Get the current search query.

        Returns:
            Current search query string
        """
        input_widget = self.query_one(Input)
        return input_widget.value

    @property
    def project_type(self) -> ProjectType | None:
        """Get the current project type filter.

        Returns:
            Current project type filter (None for all types)
        """
        select_widget: Select[ProjectType | None] = self.query_one(Select)
        return (
            None
            if (v := select_widget.value) is Select.BLANK
            else cast(ProjectType | None, v)
        )
