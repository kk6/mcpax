"""Install/Update screen for managing project installations."""

import logging
from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Static
from textual.worker import Worker, WorkerState

from mcpax.core.downloader import Downloader, DownloaderConfig
from mcpax.core.manager import ProjectManager
from mcpax.core.models import AppConfig, UpdateCheckResult, UpdateResult
from mcpax.tui.widgets.progress_panel import ProgressPanel

logger = logging.getLogger(__name__)


class InstallPhase(str, Enum):
    """Installation phase."""

    INSTALLING = "installing"
    COMPLETED = "completed"


class InstallScreen(Screen[UpdateResult | None]):
    """Screen for installing/updating projects with progress display."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    _phase: reactive[InstallPhase] = reactive(InstallPhase.INSTALLING)

    def __init__(self, updates: list[UpdateCheckResult], config: AppConfig) -> None:
        """Initialize InstallScreen.

        Args:
            updates: List of update check results to install/update
            config: Application configuration
        """
        super().__init__()
        self._updates = updates
        self._config = config
        self._result: UpdateResult | None = None
        self._cancelled = False

    def compose(self) -> ComposeResult:
        """Create child widgets.

        Yields:
            Screen widgets
        """
        yield Static(
            f"Installing {len(self._updates)} project(s)...",
            id="install-header",
        )
        yield ProgressPanel(id="install-progress")
        yield Static("", id="install-summary")
        yield Button("Close (ESC)", id="install-close-button")
        yield Footer()

    def on_mount(self) -> None:
        """Execute installation when screen is mounted."""
        # Hide summary and close button initially
        self.query_one("#install-summary").display = False
        self.query_one("#install-close-button").display = False
        self.run_worker(self._install_worker(), exclusive=True)

    async def _install_worker(self) -> UpdateResult:
        """Execute installation/update process.

        Returns:
            UpdateResult from apply_updates
        """
        progress_panel = self.query_one(ProgressPanel)

        downloader = Downloader(
            config=DownloaderConfig(
                max_concurrent=self._config.max_concurrent_downloads,
                verify_hash=self._config.verify_hash,
            ),
            on_task_start=progress_panel.create_task_start_callback(),
            on_progress=progress_panel.create_progress_callback(),
            on_task_complete=progress_panel.create_task_complete_callback(),
        )

        async with (
            downloader,
            ProjectManager(self._config, downloader=downloader) as manager,
        ):
            return await manager.apply_updates(self._updates)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes.

        Args:
            event: Worker state change event
        """
        if event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if isinstance(result, UpdateResult):
                self._result = result
                self._phase = InstallPhase.COMPLETED
                self._show_summary()
        elif event.state == WorkerState.ERROR:
            self.notify(
                f"Installation failed: {event.worker.error}",
                severity="error",
            )
            self._phase = InstallPhase.COMPLETED

    def _show_summary(self) -> None:
        """Show installation summary."""
        # Hide progress UI
        self.query_one("#install-header").display = False
        self.query_one("#install-progress").display = False

        # Show summary and close button
        self.query_one("#install-summary").display = True
        self.query_one("#install-close-button").display = True

        # Build summary text
        summary_lines = ["=== Installation Summary ===", ""]

        # Handle cancellation first
        if self._cancelled:
            summary_lines.append("[yellow]Installation was cancelled[/yellow]")
            summary_lines.append("")

        # If no result, show early message
        if not self._result:
            if not self._cancelled:
                summary_lines.append("No results available")
            summary_text = "\n".join(summary_lines)
            self.query_one("#install-summary", Static).update(summary_text)
            return

        success_count = len(self._result.successful)
        failed_count = len(self._result.failed)
        backup_count = len(self._result.backed_up)

        # Log detailed results
        if self._result.successful:
            logger.info("Successfully installed: %s", self._result.successful)
        if self._result.failed:
            logger.error("Failed installations:")
            for failed in self._result.failed:
                logger.error("  %s: %s", failed.slug, failed.error)

        if self._result.successful:
            summary_lines.append(
                f"[green]Successfully installed {success_count} project(s):[/green]"
            )
            for slug in self._result.successful:
                summary_lines.append(f"  ✓ {slug}")
            summary_lines.append("")

        if self._result.failed:
            summary_lines.append(f"[red]Failed {failed_count} project(s):[/red]")
            for failed in self._result.failed:
                summary_lines.append(f"  ✗ {failed.slug}")
                summary_lines.append(f"    Error: {failed.error}")
            summary_lines.append("")

        if self._result.backed_up:
            summary_lines.append(f"[cyan]Backed up {backup_count} file(s)[/cyan]")

        summary_text = "\n".join(summary_lines)
        self.query_one("#install-summary", Static).update(summary_text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "install-close-button":
            self.dismiss(self._result)

    def action_cancel(self) -> None:
        """Cancel the installation or close the summary."""
        if self._phase == InstallPhase.INSTALLING:
            self._cancelled = True
            self.workers.cancel_all()
            self._phase = InstallPhase.COMPLETED
            self._show_summary()
        elif self._phase == InstallPhase.COMPLETED:
            # Close the summary screen
            self.dismiss(self._result)
