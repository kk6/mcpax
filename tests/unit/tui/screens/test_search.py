"""Tests for SearchScreen."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App

from mcpax.core.models import (
    ProjectType,
    SearchHit,
    SearchResult,
)
from mcpax.tui.screens.search import MODRINTH_SEARCH_LIMIT, SearchScreen


def create_test_search_hit(
    slug: str,
    title: str,
    project_type: ProjectType = ProjectType.MOD,
    downloads: int = 1000,
) -> SearchHit:
    """Create a test SearchHit instance."""
    return SearchHit(
        slug=slug,
        title=title,
        description="Test description",
        project_type=project_type,
        downloads=downloads,
        icon_url=None,
    )


@pytest.mark.asyncio
async def test_search_screen_initialization() -> None:
    """Test SearchScreen initialization."""
    screen = SearchScreen(query="sodium", project_type=None)
    assert screen is not None
    assert screen._query == "sodium"
    assert screen._project_type is None


@pytest.mark.asyncio
async def test_search_screen_with_project_type_filter() -> None:
    """Test SearchScreen initialization with project type filter."""
    screen = SearchScreen(query="shader", project_type=ProjectType.SHADER)
    assert screen._query == "shader"
    assert screen._project_type == ProjectType.SHADER


@pytest.mark.asyncio
async def test_search_screen_has_escape_binding() -> None:
    """Test SearchScreen has escape keybinding."""
    screen = SearchScreen(query="test", project_type=None)

    # Check that 'escape' is bound to cancel action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "escape" in bindings
    assert bindings["escape"] == "cancel"


@pytest.mark.asyncio
async def test_search_screen_has_add_binding() -> None:
    """Test SearchScreen has add (a) keybinding."""
    screen = SearchScreen(query="test", project_type=None)

    # Check that 'a' is bound to add_project action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "a" in bindings
    assert bindings["a"] == "add_project"


@pytest.mark.asyncio
async def test_search_screen_executes_search() -> None:
    """Test SearchScreen executes search on mount."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(SearchScreen(query="sodium", project_type=None))

    mock_search_result = SearchResult(
        hits=[
            create_test_search_hit("sodium", "Sodium", ProjectType.MOD, 3000000),
            create_test_search_hit("lithium", "Lithium", ProjectType.MOD, 2000000),
        ],
        total_hits=2,
        offset=0,
        limit=MODRINTH_SEARCH_LIMIT,
    )

    with patch("mcpax.tui.screens.search.ModrinthClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_search_result)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        app = TestApp()
        async with app.run_test():
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Verify search was called
            mock_client.search.assert_called_once_with(
                query="sodium", limit=MODRINTH_SEARCH_LIMIT, facets=None
            )


@pytest.mark.asyncio
async def test_search_screen_with_project_type_facet() -> None:
    """Test SearchScreen applies project_type as facet."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(
                SearchScreen(
                    query="shader",
                    project_type=ProjectType.SHADER,
                )
            )

    mock_search_result = SearchResult(
        hits=[
            create_test_search_hit("iris", "Iris Shaders", ProjectType.SHADER, 2000000),
        ],
        total_hits=1,
        offset=0,
        limit=MODRINTH_SEARCH_LIMIT,
    )

    with patch("mcpax.tui.screens.search.ModrinthClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_search_result)
        mock_client_class.return_value.__aenter__.return_value = mock_client

        app = TestApp()
        async with app.run_test():
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Verify search was called with facets
            expected_facets = json.dumps([["project_type:shader"]])
            mock_client.search.assert_called_once_with(
                query="shader", limit=MODRINTH_SEARCH_LIMIT, facets=expected_facets
            )


@pytest.mark.asyncio
async def test_search_screen_escape_closes() -> None:
    """Test escape key closes the search screen."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(SearchScreen(query="test", project_type=None))

    with patch("mcpax.tui.screens.search.ModrinthClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(
            return_value=SearchResult(
                hits=[], total_hits=0, offset=0, limit=MODRINTH_SEARCH_LIMIT
            )
        )
        mock_client_class.return_value.__aenter__.return_value = mock_client

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Verify search screen is active
            assert isinstance(app.screen, SearchScreen)

            # Press escape to close
            await pilot.press("escape")
            await pilot.pause()

            # Screen should be dismissed
            assert not isinstance(app.screen, SearchScreen)


@pytest.mark.asyncio
async def test_search_screen_add_project() -> None:
    """Test adding a project from search results."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(SearchScreen(query="sodium", project_type=None))

    mock_search_result = SearchResult(
        hits=[
            create_test_search_hit("sodium", "Sodium", ProjectType.MOD, 3000000),
        ],
        total_hits=1,
        offset=0,
        limit=MODRINTH_SEARCH_LIMIT,
    )

    with (
        patch("mcpax.tui.screens.search.ModrinthClient") as mock_client_class,
        patch("mcpax.tui.screens.search.load_projects") as mock_load,
        patch("mcpax.tui.screens.search.save_projects") as mock_save,
    ):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_search_result)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_load.return_value = []

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Press 'a' to add selected project
            await pilot.press("a")
            await pilot.pause()

            # Verify save_projects was called
            mock_save.assert_called_once()
            saved_projects = mock_save.call_args[0][0]
            assert len(saved_projects) == 1
            assert saved_projects[0].slug == "sodium"
            assert saved_projects[0].project_type == ProjectType.MOD


@pytest.mark.asyncio
async def test_search_screen_add_duplicate_project() -> None:
    """Test adding a duplicate project shows warning."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(SearchScreen(query="sodium", project_type=None))

    mock_search_result = SearchResult(
        hits=[
            create_test_search_hit("sodium", "Sodium", ProjectType.MOD, 3000000),
        ],
        total_hits=1,
        offset=0,
        limit=MODRINTH_SEARCH_LIMIT,
    )

    from mcpax.core.models import ProjectConfig, ReleaseChannel

    existing_projects = [
        ProjectConfig(
            slug="sodium",
            project_type=ProjectType.MOD,
            channel=ReleaseChannel.RELEASE,
        ),
    ]

    with (
        patch("mcpax.tui.screens.search.ModrinthClient") as mock_client_class,
        patch("mcpax.tui.screens.search.load_projects") as mock_load,
        patch("mcpax.tui.screens.search.save_projects") as mock_save,
    ):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_search_result)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_load.return_value = existing_projects

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Press 'a' to add selected project
            await pilot.press("a")
            await pilot.pause()

            # Verify save_projects was NOT called (duplicate)
            mock_save.assert_not_called()


@pytest.mark.asyncio
async def test_search_screen_add_project_with_invalid_config() -> None:
    """Test adding a project when projects.toml is invalid shows error."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(SearchScreen(query="sodium", project_type=None))

    mock_search_result = SearchResult(
        hits=[
            create_test_search_hit("sodium", "Sodium", ProjectType.MOD, 3000000),
        ],
        total_hits=1,
        offset=0,
        limit=MODRINTH_SEARCH_LIMIT,
    )

    from mcpax.core.config import ConfigValidationError

    with (
        patch("mcpax.tui.screens.search.ModrinthClient") as mock_client_class,
        patch("mcpax.tui.screens.search.load_projects") as mock_load,
        patch("mcpax.tui.screens.search.save_projects") as mock_save,
    ):
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_search_result)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_load.side_effect = ConfigValidationError("Invalid TOML")

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for worker to complete
            await app.workers.wait_for_complete()

            # Press 'a' to add selected project
            await pilot.press("a")
            await pilot.pause()

            # Verify save_projects was NOT called (config error)
            mock_save.assert_not_called()
