"""Tests for ProjectTable widget."""

import pytest
from textual.app import App, ComposeResult

from mcpax.core.models import InstallStatus, ProjectType, UpdateCheckResult
from mcpax.tui.widgets import ProjectTable


def create_test_update_result(
    slug: str,
    project_type: ProjectType = ProjectType.MOD,
    status: InstallStatus = InstallStatus.INSTALLED,
    current_version: str | None = "1.0.0",
    latest_version: str | None = "1.0.0",
) -> UpdateCheckResult:
    """Create a test UpdateCheckResult instance."""
    return UpdateCheckResult(
        slug=slug,
        project_type=project_type,
        status=status,
        current_version=current_version,
        latest_version=latest_version,
        current_file=None,
        latest_file=None,
    )


@pytest.mark.asyncio
async def test_project_table_initialization() -> None:
    """Test ProjectTable initialization."""
    table = ProjectTable()
    assert table is not None


@pytest.mark.asyncio
async def test_project_table_empty_projects() -> None:
    """Test ProjectTable with empty project list."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects([])

        assert table.projects == []


@pytest.mark.asyncio
async def test_project_table_load_projects() -> None:
    """Test loading projects into the table."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
        create_test_update_result(
            "sodium", ProjectType.MOD, InstallStatus.OUTDATED, "0.5.0", "0.6.0"
        ),
        create_test_update_result(
            "iris", ProjectType.SHADER, InstallStatus.NOT_INSTALLED, None, "1.7.0"
        ),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        assert table.projects == projects
        assert len(table.projects) == 3


@pytest.mark.asyncio
async def test_project_table_selected_project() -> None:
    """Test selected_project property returns the first row by default."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
        create_test_update_result("sodium", ProjectType.MOD, InstallStatus.OUTDATED),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        # By default, DataTable has cursor at first row
        selected = table.selected_project
        assert selected is not None
        assert selected.slug == "fabric-api"


@pytest.mark.asyncio
async def test_project_table_in_app() -> None:
    """Test ProjectTable integration in a minimal app."""

    class TestApp(App[None]):
        """Minimal app for testing ProjectTable."""

        def compose(self) -> ComposeResult:
            yield ProjectTable()

    app = TestApp()
    async with app.run_test():
        # Check that ProjectTable is rendered
        table = app.query_one(ProjectTable)
        assert table is not None


@pytest.mark.asyncio
async def test_project_table_sort_by_slug() -> None:
    """Test sorting by slug column."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result("sodium", ProjectType.MOD, InstallStatus.INSTALLED),
        create_test_update_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
        create_test_update_result("iris", ProjectType.SHADER, InstallStatus.INSTALLED),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        # Sort ascending
        table.sort_by_column("slug")
        assert table.projects[0].slug == "fabric-api"
        assert table.projects[1].slug == "iris"
        assert table.projects[2].slug == "sodium"

        # Sort descending (toggle)
        table.sort_by_column("slug")
        assert table.projects[0].slug == "sodium"
        assert table.projects[1].slug == "iris"
        assert table.projects[2].slug == "fabric-api"


@pytest.mark.asyncio
async def test_project_table_sort_by_status() -> None:
    """Test sorting by status column with priority order."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result("project1", status=InstallStatus.INSTALLED),
        create_test_update_result("project2", status=InstallStatus.OUTDATED),
        create_test_update_result("project3", status=InstallStatus.NOT_INSTALLED),
        create_test_update_result("project4", status=InstallStatus.NOT_COMPATIBLE),
        create_test_update_result("project5", status=InstallStatus.CHECK_FAILED),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        # Sort by status (priority: outdated > not_installed > installed >
        # not_compatible > check_failed)
        table.sort_by_column("status")
        assert table.projects[0].status == InstallStatus.OUTDATED
        assert table.projects[1].status == InstallStatus.NOT_INSTALLED


@pytest.mark.asyncio
async def test_project_table_sort_by_type() -> None:
    """Test sorting by type column."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result("sodium", project_type=ProjectType.MOD),
        create_test_update_result("iris", project_type=ProjectType.SHADER),
        create_test_update_result("vanilla", project_type=ProjectType.RESOURCEPACK),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        # Sort ascending
        table.sort_by_column("type")
        assert table.projects[0].project_type == ProjectType.MOD


@pytest.mark.asyncio
async def test_project_table_sort_by_current_version() -> None:
    """Test sorting by current version column (lexicographic order)."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result("project1", current_version="1.2.0"),
        create_test_update_result("project2", current_version="1.10.0"),
        create_test_update_result("project3", current_version="0.5.0"),
        create_test_update_result("project4", current_version=None),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        # Sort ascending (lexicographic: "" < "0.5.0" < "1.10.0" < "1.2.0")
        table.sort_by_column("current")
        assert table.projects[0].current_version is None
        assert table.projects[1].current_version == "0.5.0"
        assert table.projects[2].current_version == "1.10.0"
        assert table.projects[3].current_version == "1.2.0"

        # Sort descending
        table.sort_by_column("current")
        assert table.projects[0].current_version == "1.2.0"
        assert table.projects[1].current_version == "1.10.0"
        assert table.projects[2].current_version == "0.5.0"
        assert table.projects[3].current_version is None


@pytest.mark.asyncio
async def test_project_table_sort_by_latest_version() -> None:
    """Test sorting by latest version column (lexicographic order)."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result("project1", latest_version="2.0.0"),
        create_test_update_result("project2", latest_version="1.9.0"),
        create_test_update_result("project3", latest_version="1.10.0"),
        create_test_update_result("project4", latest_version=None),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        # Sort ascending (lexicographic: "" < "1.10.0" < "1.9.0" < "2.0.0")
        table.sort_by_column("latest")
        assert table.projects[0].latest_version is None
        assert table.projects[1].latest_version == "1.10.0"
        assert table.projects[2].latest_version == "1.9.0"
        assert table.projects[3].latest_version == "2.0.0"

        # Sort descending
        table.sort_by_column("latest")
        assert table.projects[0].latest_version == "2.0.0"
        assert table.projects[1].latest_version == "1.9.0"
        assert table.projects[2].latest_version == "1.10.0"
        assert table.projects[3].latest_version is None


@pytest.mark.asyncio
async def test_project_table_refresh_project() -> None:
    """Test refreshing a single project in the table."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield ProjectTable()

    projects = [
        create_test_update_result("fabric-api", status=InstallStatus.INSTALLED),
        create_test_update_result("sodium", status=InstallStatus.OUTDATED),
    ]

    app = TestApp()
    async with app.run_test():
        table = app.query_one(ProjectTable)
        table.load_projects(projects)

        # Update one project
        updated_project = create_test_update_result(
            "sodium",
            status=InstallStatus.INSTALLED,
            current_version="0.6.0",
            latest_version="0.6.0",
        )
        table.refresh_project(updated_project)

        # Check that the project was updated
        sodium = next(p for p in table.projects if p.slug == "sodium")
        assert sodium.status == InstallStatus.INSTALLED
        assert sodium.current_version == "0.6.0"
