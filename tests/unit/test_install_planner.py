"""Tests for install planning."""

from pathlib import Path

from mcpax.core.install_planner import InstallPlanner
from mcpax.core.models import (
    InstallStatus,
    ProjectFile,
    ProjectType,
    UpdateCheckResult,
)


def _make_project_file(filename: str = "sodium.jar") -> ProjectFile:
    return ProjectFile(
        url=f"https://cdn.modrinth.com/{filename}",
        filename=filename,
        size=1024,
        hashes={"sha512": "abc123" * 20},
        primary=True,
    )


def _make_update(
    slug: str,
    status: InstallStatus,
    latest_file: ProjectFile | None = None,
    latest_version: str | None = "1.0.0",
) -> UpdateCheckResult:
    return UpdateCheckResult(
        slug=slug,
        project_type=ProjectType.MOD,
        status=status,
        current_version=None,
        current_file=None,
        latest_version=latest_version,
        latest_version_id="VERSIONID",
        latest_file=latest_file,
    )


def test_create_plan_includes_not_installed_and_outdated_updates(
    tmp_path: Path,
) -> None:
    """Creates download tasks for updates that need action."""
    sodium_file = _make_project_file("sodium.jar")
    lithium_file = _make_project_file("lithium.jar")
    updates = [
        _make_update("sodium", InstallStatus.NOT_INSTALLED, sodium_file, "1.0.0"),
        _make_update("lithium", InstallStatus.OUTDATED, lithium_file, "2.0.0"),
    ]

    plan = InstallPlanner().create_plan(updates, tmp_path)

    assert plan.has_work is True
    assert [task.slug for task in plan.tasks] == ["sodium", "lithium"]
    assert plan.tasks[0].url == sodium_file.url
    assert plan.tasks[0].dest == tmp_path / "sodium.jar"
    assert plan.tasks[0].expected_hash == sodium_file.hashes["sha512"]
    assert plan.tasks[0].version_number == "1.0.0"
    assert plan.check_results["sodium"] == updates[0]
    assert plan.failed == []


def test_create_plan_skips_non_actionable_updates(tmp_path: Path) -> None:
    """Does not create tasks for updates that require no install action."""
    updates = [
        _make_update("installed", InstallStatus.INSTALLED, _make_project_file()),
        _make_update("not-compatible", InstallStatus.NOT_COMPATIBLE, None),
        _make_update("failed", InstallStatus.CHECK_FAILED, None),
    ]

    plan = InstallPlanner().create_plan(updates, tmp_path)

    assert plan.has_work is False
    assert plan.tasks == []
    assert plan.check_results == {}
    assert plan.failed == []


def test_create_plan_reports_actionable_update_without_latest_file(
    tmp_path: Path,
) -> None:
    """Reports a planning failure when an actionable update lacks latest_file."""
    updates = [
        _make_update("sodium", InstallStatus.NOT_INSTALLED, None),
    ]

    plan = InstallPlanner().create_plan(updates, tmp_path)

    assert plan.tasks == []
    assert plan.check_results == {}
    assert len(plan.failed) == 1
    assert plan.failed[0].slug == "sodium"
    assert plan.failed[0].error == "No compatible version found"


def test_create_plan_uses_unknown_when_latest_version_is_missing(
    tmp_path: Path,
) -> None:
    """Uses the existing fallback version number for download tasks."""
    update = _make_update(
        "sodium",
        InstallStatus.NOT_INSTALLED,
        _make_project_file("sodium.jar"),
        latest_version=None,
    )

    plan = InstallPlanner().create_plan([update], tmp_path)

    assert plan.tasks[0].version_number == "unknown"
