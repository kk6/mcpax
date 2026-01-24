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
async def test_search_input_custom_debounce() -> None:
    """Test SearchInput initialization with custom debounce delay."""
    from mcpax.tui.widgets.search_input import SearchInput

    search_input = SearchInput(debounce_delay=0.5)

    # SearchInput should be instantiated with custom debounce
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
async def test_search_input_emits_search_requested() -> None:
    """Test SearchInput emits SearchRequested message."""
    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def __init__(self) -> None:
            super().__init__()
            self.messages: list[tuple[str, ProjectType | None]] = []

        def compose(self) -> ComposeResult:
            yield SearchInput(debounce_delay=0.0)

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
        await pilot.pause(0.1)  # Wait for debounce

        # Should have received a message
        assert len(app.messages) >= 1
        assert app.messages[-1] == ("sodium", None)


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
            yield SearchInput(debounce_delay=0.0)

        def on_search_input_search_requested(
            self, message: SearchInput.SearchRequested
        ) -> None:
            """Handle SearchRequested message."""
            self.messages.append((message.query, message.project_type))

    app = TestApp()
    async with app.run_test() as pilot:
        search_input = app.query_one(SearchInput)
        from textual.widgets import Select

        select_widget = search_input.query_one(Select)

        # Change type filter to Mod
        select_widget.value = ProjectType.MOD
        await pilot.pause(0.1)

        # Should have received a message with Mod type
        assert len(app.messages) >= 1
        # Find message with Mod type
        mod_messages = [msg for msg in app.messages if msg[1] == ProjectType.MOD]
        assert len(mod_messages) >= 1


@pytest.mark.asyncio
async def test_search_input_debounce_delays_event() -> None:
    """Test SearchInput debounce delays event emission."""
    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def __init__(self) -> None:
            super().__init__()
            self.messages: list[tuple[str, ProjectType | None]] = []

        def compose(self) -> ComposeResult:
            yield SearchInput(debounce_delay=0.2)

        def on_search_input_search_requested(
            self, message: SearchInput.SearchRequested
        ) -> None:
            """Handle SearchRequested message."""
            self.messages.append((message.query, message.project_type))

    app = TestApp()
    async with app.run_test() as pilot:
        search_input = app.query_one(SearchInput)
        input_widget = search_input.query_one("Input")

        # Clear initial messages (focus may trigger events)
        app.messages.clear()

        # Type a query
        input_widget.focus()
        await pilot.press("a")
        await pilot.pause(0.05)  # Wait less than debounce delay

        # Should not have received a message yet (still debouncing)
        # Note: may have initial message, so check for growth
        initial_count = len(app.messages)

        # Wait for debounce to complete
        await pilot.pause(0.2)

        # Now should have received at least one more message
        assert len(app.messages) > initial_count


@pytest.mark.asyncio
async def test_search_input_debounce_resets_on_new_input() -> None:
    """Test SearchInput debounce timer resets on new input."""
    from mcpax.tui.widgets.search_input import SearchInput

    class TestApp(App[None]):
        """Minimal app for testing SearchInput."""

        def __init__(self) -> None:
            super().__init__()
            self.messages: list[tuple[str, ProjectType | None]] = []

        def compose(self) -> ComposeResult:
            yield SearchInput(debounce_delay=0.2)

        def on_search_input_search_requested(
            self, message: SearchInput.SearchRequested
        ) -> None:
            """Handle SearchRequested message."""
            self.messages.append((message.query, message.project_type))

    app = TestApp()
    async with app.run_test() as pilot:
        search_input = app.query_one(SearchInput)
        input_widget = search_input.query_one("Input")

        # Clear initial messages
        app.messages.clear()

        # Type characters one by one
        input_widget.focus()
        await pilot.press("a")
        await pilot.pause(0.1)  # Wait less than debounce
        await pilot.press("b")
        await pilot.pause(0.1)  # Wait less than debounce

        # Should not have received many messages yet (still debouncing)
        initial_count = len(app.messages)

        # Wait for debounce to complete
        await pilot.pause(0.2)

        # Should have received at least one more message with final query
        assert len(app.messages) > initial_count
        # Last message should contain "ab"
        assert "ab" in app.messages[-1][0]


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
