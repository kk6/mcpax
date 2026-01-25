"""ProgressPanel widget for displaying download progress."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from time import time
from typing import Any, Literal

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.message import Message
from textual.widget import Widget


@dataclass
class DownloadProgress:
    """Data class to track individual download progress."""

    task_id: str
    slug: str
    version_number: str
    total: int | None
    completed: int = 0
    started_at: float = field(default_factory=time)
    status: Literal["downloading", "success", "error"] = "downloading"
    error: str | None = None


class ProgressPanel(Widget):
    """Widget for displaying download progress.

    TODO: This widget needs to be integrated into a TUI screen (e.g., InstallScreen).
    The create_*_callback() methods should be used to wire up Downloader callbacks.
    See issue #68 for integration work.
    """

    COMPONENT_CLASSES = {
        "success-icon",
        "error-icon",
        "downloading-icon",
        "success-bar",
        "error-bar",
        "downloading-bar",
    }

    class TaskStarted(Message):
        """Message emitted when a download task starts."""

        def __init__(
            self, task_id: str, slug: str, version_number: str, total: int | None
        ) -> None:
            """Initialize the TaskStarted message.

            Args:
                task_id: Task identifier
                slug: Project slug
                version_number: Version string
                total: Total size in bytes (None if unknown)
            """
            super().__init__()
            self.task_id = task_id
            self.slug = slug
            self.version_number = version_number
            self.total = total

    class ProgressUpdated(Message):
        """Message emitted when progress is updated."""

        def __init__(self, task_id: str, completed: int, total: int | None) -> None:
            """Initialize the ProgressUpdated message.

            Args:
                task_id: Task identifier
                completed: Bytes downloaded so far
                total: Total bytes to download (None if unknown)
            """
            super().__init__()
            self.task_id = task_id
            self.completed = completed
            self.total = total

    class TaskCompleted(Message):
        """Message emitted when a download task completes."""

        def __init__(self, task_id: str, success: bool, error: str | None) -> None:
            """Initialize the TaskCompleted message.

            Args:
                task_id: Task identifier
                success: Whether the download succeeded
                error: Error message if failed
            """
            super().__init__()
            self.task_id = task_id
            self.success = success
            self.error = error

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the ProgressPanel widget.

        Args:
            **kwargs: Additional arguments passed to Widget
        """
        super().__init__(**kwargs)
        self._tasks: dict[str, DownloadProgress] = {}

    def _render_progress_bar(
        self, completed: int, total: int | None, width: int = 30
    ) -> str:
        """Render a text-based progress bar.

        Args:
            completed: Bytes completed
            total: Total bytes (None if unknown)
            width: Width of the progress bar in characters

        Returns:
            Progress bar string
        """
        if total is None or total == 0:
            # Unknown total - show indeterminate bar
            return "[" + "~" * width + "]"

        ratio = min(completed / total, 1.0)
        filled = int(width * ratio)
        empty = width - filled

        # Use block characters for a nice visual bar
        bar = "█" * filled + "░" * empty
        return f"[{bar}]"

    def render(self) -> RenderableType:
        """Render the progress panel as a Rich table.

        Returns:
            Rich Table with download progress information
        """
        if not self._tasks:
            return Text("No active downloads", style="dim")

        table = Table.grid(padding=(0, 1), expand=True)
        table.add_column("Project", style="bold", width=25)
        table.add_column("Bar", width=34)  # 30 + 2 brackets + padding
        table.add_column("Progress", justify="right", width=20)
        table.add_column("Status", justify="center", width=3)

        for task in self._tasks.values():
            # Format project name
            project_name = f"{task.slug}@{task.version_number}"

            # Render progress bar
            progress_bar = self._render_progress_bar(task.completed, task.total)

            # Calculate progress percentage
            if task.total is not None and task.total > 0:
                percentage = min((task.completed / task.total) * 100, 100.0)
                progress_text = f"{percentage:5.1f}%"
            elif task.completed > 0:
                # Unknown total size
                progress_text = f"{task.completed} bytes"
            else:
                progress_text = "Starting..."

            # Status icon
            if task.status == "success":
                status = Text("✓", style=self.get_component_rich_style("success-icon"))
                progress_bar_colored = Text(
                    progress_bar,
                    style=self.get_component_rich_style("success-bar"),
                )
            elif task.status == "error":
                status = Text("✗", style=self.get_component_rich_style("error-icon"))
                progress_bar_colored = Text(
                    progress_bar,
                    style=self.get_component_rich_style("error-bar"),
                )
                if task.error:
                    project_name = f"{project_name}\n  {task.error}"
            else:  # downloading
                status = Text(
                    "↓", style=self.get_component_rich_style("downloading-icon")
                )
                progress_bar_colored = Text(
                    progress_bar,
                    style=self.get_component_rich_style("downloading-bar"),
                )

            table.add_row(project_name, progress_bar_colored, progress_text, status)

        return table

    def on_progress_panel_task_started(self, message: TaskStarted) -> None:
        """Handle TaskStarted message.

        Args:
            message: TaskStarted message
        """
        self._apply_task_started(
            task_id=message.task_id,
            slug=message.slug,
            version_number=message.version_number,
            total=message.total,
        )

    def on_progress_panel_progress_updated(self, message: ProgressUpdated) -> None:
        """Handle ProgressUpdated message.

        Args:
            message: ProgressUpdated message
        """
        self._apply_progress_updated(
            task_id=message.task_id,
            completed=message.completed,
            total=message.total,
        )

    def on_progress_panel_task_completed(self, message: TaskCompleted) -> None:
        """Handle TaskCompleted message.

        Args:
            message: TaskCompleted message
        """
        self._apply_task_completed(
            task_id=message.task_id,
            success=message.success,
            error=message.error,
        )

    def _apply_task_started(
        self, task_id: str, slug: str, version_number: str, total: int | None
    ) -> None:
        self._tasks[task_id] = DownloadProgress(
            task_id=task_id,
            slug=slug,
            version_number=version_number,
            total=total,
        )
        self.refresh()

    def _apply_progress_updated(
        self, task_id: str, completed: int, total: int | None
    ) -> None:
        if task := self._tasks.get(task_id):
            task.completed = completed
            if total is not None:
                task.total = total
            self.refresh()

    def _apply_task_completed(
        self, task_id: str, success: bool, error: str | None
    ) -> None:
        if task := self._tasks.get(task_id):
            if success:
                task.status = "success"
            else:
                task.status = "error"
                task.error = error
            self.refresh()

    @property
    def active_downloads(self) -> int:
        """Get the number of active downloads.

        Returns:
            Number of downloads in progress
        """
        return sum(1 for task in self._tasks.values() if task.status == "downloading")

    @property
    def all_completed(self) -> bool:
        """Check if all downloads are completed.

        Returns:
            True if all downloads are completed or no downloads exist
        """
        if not self._tasks:
            return True
        return all(task.status != "downloading" for task in self._tasks.values())

    def create_task_start_callback(self) -> "Callable[[str, str, int | None], object]":
        """Create a callback for task start events.

        Returns:
            Callback function compatible with Downloader.TaskStartCallback
        """

        def callback(slug: str, version_number: str, total: int | None) -> object:
            """Callback for task start event.

            Args:
                slug: Project slug
                version_number: Version string
                total: Total size in bytes (None if unknown)

            Returns:
                Task ID for progress tracking
            """
            task_id = str(uuid.uuid4())
            self.post_message(
                ProgressPanel.TaskStarted(
                    task_id=task_id,
                    slug=slug,
                    version_number=version_number,
                    total=total,
                )
            )
            return task_id

        return callback

    def create_progress_callback(self) -> "Callable[[object, int, int | None], None]":
        """Create a callback for progress update events.

        Returns:
            Callback function compatible with Downloader.ProgressCallback
        """

        def callback(task_id: object, completed: int, total: int | None) -> None:
            """Callback for progress update event.

            Args:
                task_id: Task identifier
                completed: Bytes downloaded so far
                total: Total bytes to download (None if unknown)
            """
            task_id_str = str(task_id)
            self.post_message(
                ProgressPanel.ProgressUpdated(
                    task_id=task_id_str,
                    completed=completed,
                    total=total,
                )
            )

        return callback

    def create_task_complete_callback(
        self,
    ) -> "Callable[[object, bool, str | None], None]":
        """Create a callback for task complete events.

        Returns:
            Callback function compatible with Downloader.TaskCompleteCallback
        """

        def callback(task_id: object, success: bool, error: str | None) -> None:
            """Callback for task complete event.

            Args:
                task_id: Task identifier
                success: Whether the download succeeded
                error: Error message if failed
            """
            task_id_str = str(task_id)
            self.post_message(
                ProgressPanel.TaskCompleted(
                    task_id=task_id_str,
                    success=success,
                    error=error,
                )
            )

        return callback
