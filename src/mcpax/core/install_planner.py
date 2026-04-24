"""Install planning for update application."""

from pathlib import Path

from pydantic import BaseModel, Field

from mcpax.core.models import (
    DownloadTask,
    FailedUpdate,
    InstallStatus,
    UpdateCheckResult,
)


class InstallPlan(BaseModel):
    """Planned download work and planning-time failures."""

    tasks: list[DownloadTask] = Field(default_factory=list)
    update_info: dict[str, UpdateCheckResult] = Field(default_factory=dict)
    failed: list[FailedUpdate] = Field(default_factory=list)

    @property
    def has_work(self) -> bool:
        """Return whether the plan has download work to execute."""
        return bool(self.tasks)


class InstallPlanner:
    """Create download plans from update check results."""

    _ACTIONABLE_STATUSES = frozenset(
        [InstallStatus.NOT_INSTALLED, InstallStatus.OUTDATED]
    )

    def create_plan(
        self,
        updates: list[UpdateCheckResult],
        dest_dir: Path,
    ) -> InstallPlan:
        """Create an install plan for updates that need action."""
        plan = InstallPlan()

        for update in updates:
            if update.status not in self._ACTIONABLE_STATUSES:
                continue

            if update.latest_file is None:
                plan.failed.append(
                    FailedUpdate(slug=update.slug, error="No compatible version found")
                )
                continue

            task = DownloadTask(
                url=update.latest_file.url,
                dest=dest_dir / update.latest_file.filename,
                expected_hash=update.latest_file.hashes.get("sha512"),
                slug=update.slug,
                version_number=update.latest_version or "unknown",
            )
            plan.tasks.append(task)
            plan.update_info[update.slug] = update

        return plan
