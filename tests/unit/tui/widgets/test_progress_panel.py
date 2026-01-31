"""Tests for ProgressPanel widget."""

import pytest
from textual.app import App, ComposeResult

from mcpax.tui.widgets.progress_panel import DownloadProgress, ProgressPanel


class TestDownloadProgress:
    """Tests for DownloadProgress dataclass."""

    def test_create_with_defaults(self) -> None:
        """DownloadProgress should initialize with default values."""
        # Arrange & Act
        progress = DownloadProgress(
            task_id="task-1",
            slug="fabric-api",
            version_number="0.100.0",
            total=1024,
        )

        # Assert
        assert progress.task_id == "task-1"
        assert progress.slug == "fabric-api"
        assert progress.version_number == "0.100.0"
        assert progress.total == 1024
        assert progress.completed == 0
        assert progress.status == "downloading"
        assert progress.error is None
        assert isinstance(progress.started_at, float)

    def test_create_with_unknown_size(self) -> None:
        """DownloadProgress should allow None for unknown total size."""
        # Arrange & Act
        progress = DownloadProgress(
            task_id="task-2",
            slug="sodium",
            version_number="0.5.0",
            total=None,
        )

        # Assert
        assert progress.total is None

    def test_update_completed(self) -> None:
        """DownloadProgress should track completed bytes."""
        # Arrange
        progress = DownloadProgress(
            task_id="task-3",
            slug="lithium",
            version_number="0.12.0",
            total=2048,
        )

        # Act
        progress.completed = 1024

        # Assert
        assert progress.completed == 1024

    def test_mark_success(self) -> None:
        """DownloadProgress should track success status."""
        # Arrange
        progress = DownloadProgress(
            task_id="task-4",
            slug="iris",
            version_number="1.7.0",
            total=4096,
        )

        # Act
        progress.status = "success"

        # Assert
        assert progress.status == "success"

    def test_mark_error(self) -> None:
        """DownloadProgress should track error status and message."""
        # Arrange
        progress = DownloadProgress(
            task_id="task-5",
            slug="phosphor",
            version_number="0.8.0",
            total=512,
        )

        # Act
        progress.status = "error"
        progress.error = "Network timeout"

        # Assert
        assert progress.status == "error"
        assert progress.error == "Network timeout"


class TestProgressPanelInitialization:
    """Tests for ProgressPanel initialization."""

    @pytest.mark.asyncio
    async def test_create_progress_panel(self) -> None:
        """ProgressPanel should be mountable in an app."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        # Act & Assert
        async with app.run_test():
            progress_panel = app.query_one(ProgressPanel)
            assert progress_panel is not None

    @pytest.mark.asyncio
    async def test_initial_state_empty(self) -> None:
        """ProgressPanel should start with no active downloads."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        # Act & Assert
        async with app.run_test():
            progress_panel = app.query_one(ProgressPanel)
            assert progress_panel.active_downloads == 0
            assert progress_panel.all_completed is True


class TestProgressPanelMessages:
    """Tests for ProgressPanel message handling."""

    @pytest.mark.asyncio
    async def test_task_started_message(self) -> None:
        """ProgressPanel should handle TaskStarted message."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)

            # Act
            message = ProgressPanel.TaskStarted(
                task_id="task-1",
                slug="fabric-api",
                version_number="0.100.0",
                total=1024,
            )
            progress_panel.post_message(message)
            await pilot.pause()

            # Assert
            assert progress_panel.active_downloads == 1
            assert progress_panel.all_completed is False

    @pytest.mark.asyncio
    async def test_progress_updated_message(self) -> None:
        """ProgressPanel should handle ProgressUpdated message."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)

            # Start a task first
            start_msg = ProgressPanel.TaskStarted(
                task_id="task-2",
                slug="sodium",
                version_number="0.5.0",
                total=2048,
            )
            progress_panel.post_message(start_msg)
            await pilot.pause()

            # Act
            task_id = list(progress_panel._tasks.keys())[0]
            update_msg = ProgressPanel.ProgressUpdated(
                task_id=task_id,
                completed=1024,
                total=2048,
            )
            progress_panel.post_message(update_msg)
            await pilot.pause()

            # Assert
            task = progress_panel._tasks[task_id]
            assert task.completed == 1024
            assert task.total == 2048

    @pytest.mark.asyncio
    async def test_task_completed_success_message(self) -> None:
        """ProgressPanel should handle TaskCompleted success message."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)

            # Start a task first
            start_msg = ProgressPanel.TaskStarted(
                task_id="task-3",
                slug="lithium",
                version_number="0.12.0",
                total=4096,
            )
            progress_panel.post_message(start_msg)
            await pilot.pause()

            # Act
            task_id = list(progress_panel._tasks.keys())[0]
            complete_msg = ProgressPanel.TaskCompleted(
                task_id=task_id,
                success=True,
                error=None,
            )
            progress_panel.post_message(complete_msg)
            await pilot.pause()

            # Assert
            task = progress_panel._tasks[task_id]
            assert task.status == "success"
            assert task.error is None
            assert progress_panel.active_downloads == 0
            assert progress_panel.all_completed is True

    @pytest.mark.asyncio
    async def test_task_completed_error_message(self) -> None:
        """ProgressPanel should handle TaskCompleted error message."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)

            # Start a task first
            start_msg = ProgressPanel.TaskStarted(
                task_id="task-4",
                slug="phosphor",
                version_number="0.8.0",
                total=512,
            )
            progress_panel.post_message(start_msg)
            await pilot.pause()

            # Act
            task_id = list(progress_panel._tasks.keys())[0]
            complete_msg = ProgressPanel.TaskCompleted(
                task_id=task_id,
                success=False,
                error="Network timeout",
            )
            progress_panel.post_message(complete_msg)
            await pilot.pause()

            # Assert
            task = progress_panel._tasks[task_id]
            assert task.status == "error"
            assert task.error == "Network timeout"
            assert progress_panel.active_downloads == 0
            assert progress_panel.all_completed is True

    @pytest.mark.asyncio
    async def test_multiple_concurrent_downloads(self) -> None:
        """ProgressPanel should handle multiple concurrent downloads."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)

            # Act - Start multiple tasks
            for i, slug in enumerate(["fabric-api", "sodium", "lithium"]):
                start_msg = ProgressPanel.TaskStarted(
                    task_id=f"task-{i}",
                    slug=slug,
                    version_number=f"1.{i}.0",
                    total=1024 * (i + 1),
                )
                progress_panel.post_message(start_msg)
                await pilot.pause()

            # Assert
            assert progress_panel.active_downloads == 3
            assert progress_panel.all_completed is False


class TestProgressPanelCallbacks:
    """Tests for ProgressPanel callback factories."""

    @pytest.mark.asyncio
    async def test_create_task_start_callback(self) -> None:
        """ProgressPanel should provide task start callback for Downloader."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)
            callback = progress_panel.create_task_start_callback()

            # Act
            task_id = callback("fabric-api", "0.100.0", 1024)
            await pilot.pause()

            # Assert
            assert task_id is not None
            assert progress_panel.active_downloads == 1
            task = progress_panel._tasks[task_id]
            assert task.slug == "fabric-api"
            assert task.version_number == "0.100.0"
            assert task.total == 1024

    @pytest.mark.asyncio
    async def test_create_progress_callback(self) -> None:
        """ProgressPanel should provide progress callback for Downloader."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)
            start_callback = progress_panel.create_task_start_callback()
            progress_callback = progress_panel.create_progress_callback()

            # Start a task first
            task_id = start_callback("sodium", "0.5.0", 2048)
            await pilot.pause()

            # Act
            progress_callback(task_id, 1024, 2048)
            await pilot.pause()

            # Assert
            task = progress_panel._tasks[task_id]
            assert task.completed == 1024
            assert task.total == 2048

    @pytest.mark.asyncio
    async def test_create_task_complete_callback_success(self) -> None:
        """ProgressPanel should provide task complete callback for Downloader."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)
            start_callback = progress_panel.create_task_start_callback()
            complete_callback = progress_panel.create_task_complete_callback()

            # Start a task first
            task_id = start_callback("lithium", "0.12.0", 4096)
            await pilot.pause()

            # Act
            complete_callback(task_id, True, None)
            await pilot.pause()

            # Assert
            task = progress_panel._tasks[task_id]
            assert task.status == "success"
            assert task.error is None
            assert progress_panel.all_completed is True

    @pytest.mark.asyncio
    async def test_create_task_complete_callback_error(self) -> None:
        """ProgressPanel should handle task complete callback with error."""

        # Arrange
        class TestApp(App[None]):
            def compose(self) -> ComposeResult:
                yield ProgressPanel()

        app = TestApp()

        async with app.run_test() as pilot:
            progress_panel = app.query_one(ProgressPanel)
            start_callback = progress_panel.create_task_start_callback()
            complete_callback = progress_panel.create_task_complete_callback()

            # Start a task first
            task_id = start_callback("phosphor", "0.8.0", 512)
            await pilot.pause()

            # Act
            complete_callback(task_id, False, "Network timeout")
            await pilot.pause()

            # Assert
            task = progress_panel._tasks[task_id]
            assert task.status == "error"
            assert task.error == "Network timeout"
