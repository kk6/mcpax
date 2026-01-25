"""Tests for SearchResultTable widget."""

import pytest
from textual.app import App, ComposeResult

from mcpax.core.models import ProjectType, SearchHit
from mcpax.tui.widgets.search_result_table import SearchResultTable


def create_test_search_hit(
    slug: str,
    title: str,
    project_type: ProjectType = ProjectType.MOD,
    downloads: int = 1000,
    description: str = "Test description",
) -> SearchHit:
    """Create a test SearchHit instance."""
    return SearchHit(
        slug=slug,
        title=title,
        description=description,
        project_type=project_type,
        downloads=downloads,
        icon_url=None,
    )


@pytest.mark.asyncio
async def test_search_result_table_initialization() -> None:
    """Test SearchResultTable initialization."""
    table = SearchResultTable()
    assert table is not None


@pytest.mark.asyncio
async def test_search_result_table_empty_results() -> None:
    """Test SearchResultTable with empty results."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield SearchResultTable()

    app = TestApp()
    async with app.run_test():
        table = app.query_one(SearchResultTable)
        table.load_results([])

        assert table.results == []


@pytest.mark.asyncio
async def test_search_result_table_load_results() -> None:
    """Test loading search results into the table."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield SearchResultTable()

    results = [
        create_test_search_hit("fabric-api", "Fabric API", ProjectType.MOD, 5000000),
        create_test_search_hit("sodium", "Sodium", ProjectType.MOD, 3000000),
        create_test_search_hit("iris", "Iris Shaders", ProjectType.SHADER, 2000000),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(SearchResultTable)
        table.load_results(results)

        assert table.results == results
        assert len(table.results) == 3


@pytest.mark.asyncio
async def test_search_result_table_selected_result() -> None:
    """Test selected_result property returns the first row by default."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield SearchResultTable()

    results = [
        create_test_search_hit("fabric-api", "Fabric API", ProjectType.MOD),
        create_test_search_hit("sodium", "Sodium", ProjectType.MOD),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(SearchResultTable)
        table.load_results(results)

        # By default, DataTable has cursor at first row
        selected = table.selected_result
        assert selected is not None
        assert selected.slug == "fabric-api"


@pytest.mark.asyncio
async def test_search_result_table_in_app() -> None:
    """Test SearchResultTable integration in a minimal app."""

    class TestApp(App[None]):
        """Minimal app for testing SearchResultTable."""

        def compose(self) -> ComposeResult:
            yield SearchResultTable()

    app = TestApp()
    async with app.run_test():
        # Check that SearchResultTable is rendered
        table = app.query_one(SearchResultTable)
        assert table is not None


@pytest.mark.asyncio
async def test_search_result_table_format_downloads() -> None:
    """Test download count formatting (e.g., 1.2M, 500K)."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield SearchResultTable()

    results = [
        create_test_search_hit("project1", "Project 1", downloads=1234567),  # 1.2M
        create_test_search_hit("project2", "Project 2", downloads=500000),  # 500.0K
        create_test_search_hit("project3", "Project 3", downloads=999),  # 999
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(SearchResultTable)
        table.load_results(results)

        # Verify the table was populated and downloads are formatted
        assert len(table.results) == 3
        # Column index 3 is downloads
        assert table.get_cell_at((0, 3)) == "1.2M"
        assert table.get_cell_at((1, 3)) == "500.0K"
        assert table.get_cell_at((2, 3)) == "999"
