"""Tests for SearchInput widget."""

import pytest
from textual.app import App, ComposeResult

from mcpax.core.models import ProjectType


@pytest.mark.asyncio
async def test_search_input_initialization() -> None:
    """Test SearchInput initialization with default parameters."""
    from mcpax.tui.widgets.search_input import SearchInput

    search_input = SearchInput()

    # SearchInput should be instantiated
    assert search_input is not None


@pytest.mark.asyncio
async def test_search_input_in_app() -> None:
    """Test SearchInput integration in a minimal app."""
    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def compose(self) -> ComposeResult:
            yield SearchInput()

    app = TestApp()
    async with app.run_test():
        # Check that SearchInput is rendered
        search_input = app.query_one(SearchInput)
        assert search_input is not None


@pytest.mark.asyncio
async def test_search_input_has_input_and_select() -> None:
    """Test SearchInput contains Input and Select widgets."""
    from textual.widgets import Input, Select

    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def compose(self) -> ComposeResult:
            yield SearchInput()

    app = TestApp()
    async with app.run_test():
        search_input = app.query_one(SearchInput)

        # SearchInput should contain an Input widget
        input_widget = search_input.query_one(Input)
        assert input_widget is not None

        # SearchInput should contain a Select widget
        select_widget = search_input.query_one(Select)
        assert select_widget is not None


@pytest.mark.asyncio
async def test_search_input_emits_search_requested_on_enter() -> None:
    """Test SearchInput emits SearchRequested message only on Enter key."""
    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def __init__(self) -> None:
            super().__init__()
            self.messages: list[tuple[str, ProjectType | None]] = []

        def compose(self) -> ComposeResult:
            yield SearchInput()

        def on_search_input_search_requested(
            self, message: SearchInput.SearchRequested
        ) -> None:
            """Handle SearchRequested message."""
            self.messages.append((message.query, message.project_type))

    app = TestApp()
    async with app.run_test() as pilot:
        search_input = app.query_one(SearchInput)
        input_widget = search_input.query_one("Input")

        # Type a query
        input_widget.focus()
        await pilot.press(*"sodium")
        await pilot.pause(0.1)

        # Should NOT have received a message yet (no Enter pressed)
        assert len(app.messages) == 0

        # Press Enter
        await pilot.press("enter")
        await pilot.pause(0.1)

        # Now should have received a message
        assert len(app.messages) == 1
        assert app.messages[0] == ("sodium", None)


@pytest.mark.asyncio
async def test_search_input_includes_type_filter() -> None:
    """Test SearchInput includes type filter in SearchRequested message."""
    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def __init__(self) -> None:
            super().__init__()
            self.messages: list[tuple[str, ProjectType | None]] = []

        def compose(self) -> ComposeResult:
            yield SearchInput()

        def on_search_input_search_requested(
            self, message: SearchInput.SearchRequested
        ) -> None:
            """Handle SearchRequested message."""
            self.messages.append((message.query, message.project_type))

    app = TestApp()
    async with app.run_test() as pilot:
        search_input = app.query_one(SearchInput)
        from textual.widgets import Input, Select

        input_widget = search_input.query_one(Input)
        select_widget = search_input.query_one(Select)

        # Type a query
        input_widget.focus()
        await pilot.press(*"sodium")
        await pilot.pause(0.1)

        # Change type filter to Mod
        select_widget.value = ProjectType.MOD
        await pilot.pause(0.1)

        # Should NOT have received a message yet (no Enter pressed)
        assert len(app.messages) == 0

        # Press Enter
        await pilot.press("enter")
        await pilot.pause(0.1)

        # Should have received a message with Mod type
        assert len(app.messages) == 1
        assert app.messages[0] == ("sodium", ProjectType.MOD)


@pytest.mark.asyncio
async def test_search_input_query_property() -> None:
    """Test SearchInput query property."""
    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def compose(self) -> ComposeResult:
            yield SearchInput()

    app = TestApp()
    async with app.run_test():
        search_input = app.query_one(SearchInput)

        # Initial query should be empty
        assert search_input.search_query == ""

        # Set input value
        input_widget = search_input.query_one("Input")
        input_widget.value = "sodium"

        # Query property should reflect the input value
        assert search_input.search_query == "sodium"


@pytest.mark.asyncio
async def test_search_input_project_type_property() -> None:
    """Test SearchInput project_type property."""
    from textual.widgets import Select

    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def compose(self) -> ComposeResult:
            yield SearchInput()

    app = TestApp()
    async with app.run_test():
        search_input = app.query_one(SearchInput)

        # Initial project_type should be None (All Types)
        assert search_input.project_type is None

        # Change select value
        select_widget = search_input.query_one(Select)
        select_widget.value = ProjectType.MOD

        # Project_type property should reflect the select value
        assert search_input.project_type == ProjectType.MOD
