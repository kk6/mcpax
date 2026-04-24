"""Tests for update checking orchestration."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcpax.core.models import (
    AppConfig,
    InstalledFile,
    InstallStatus,
    Loader,
    ModrinthProject,
    ProjectConfig,
    ProjectFile,
    ProjectType,
    ProjectVersion,
    ReleaseChannel,
    StateFile,
)
from mcpax.core.state_store import StateStore
from mcpax.core.update_checker import UpdateChecker


def _make_config(minecraft_dir: Path) -> AppConfig:
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        minecraft_dir=minecraft_dir,
    )


def _make_file(filename: str = "sodium.jar", sha512: str = "abc123") -> ProjectFile:
    return ProjectFile(
        url=f"https://cdn.modrinth.com/{filename}",
        filename=filename,
        size=1024,
        hashes={"sha512": sha512},
        primary=True,
    )


def _make_version(
    version_number: str,
    version_id: str = "VERSIONID",
    sha512: str = "abc123",
    game_versions: list[str] | None = None,
) -> ProjectVersion:
    return ProjectVersion(
        id=version_id,
        project_id="PROJECTID",
        version_number=version_number,
        version_type=ReleaseChannel.RELEASE,
        game_versions=game_versions or ["1.21.4"],
        loaders=["fabric"],
        files=[_make_file(sha512=sha512)],
        dependencies=[],
        date_published=datetime(2024, 1, 1, tzinfo=UTC),
    )


def _make_installed_file(slug: str, **overrides) -> InstalledFile:
    defaults = {
        "slug": slug,
        "project_type": ProjectType.MOD,
        "filename": f"{slug}.jar",
        "version_id": "OLDID",
        "version_number": "1.0.0",
        "sha512": "oldhash",
        "installed_at": datetime.now(UTC),
        "file_path": Path(f"/tmp/{slug}.jar"),
    }
    return InstalledFile(**{**defaults, **overrides})


class DummyApiClient:
    """API client stub for update checker tests."""

    def __init__(
        self,
        versions: list[ProjectVersion],
        title: str = "Sodium",
    ) -> None:
        self._versions = versions
        self._title = title

    async def get_project(self, slug: str) -> ModrinthProject:
        return ModrinthProject(
            id="PROJECTID",
            slug=slug,
            title=self._title,
            description="A project",
            project_type=ProjectType.MOD,
            downloads=1,
            icon_url=None,
            versions=[version.id for version in self._versions],
        )

    async def get_versions(self, slug: str) -> list[ProjectVersion]:
        return self._versions


async def test_check_single_update_detects_outdated_project(tmp_path: Path) -> None:
    """Returns OUTDATED when installed hash differs from latest hash."""
    state_store = StateStore(_make_config(tmp_path))
    await state_store.save(
        StateFile(files={"sodium": _make_installed_file("sodium", sha512="oldhash")})
    )
    checker = UpdateChecker(
        config=_make_config(tmp_path),
        api_client=DummyApiClient([_make_version("1.1.0", sha512="newhash")]),
        state_store=state_store,
    )

    result = await checker.check_single_update(
        ProjectConfig(slug="sodium", project_type=ProjectType.MOD)
    )

    assert result.status == InstallStatus.OUTDATED
    assert result.latest_version == "1.1.0"
    assert result.title == "Sodium"


async def test_check_single_update_handles_pinned_version(tmp_path: Path) -> None:
    """Returns pinned update result when project config pins a version."""
    checker = UpdateChecker(
        config=_make_config(tmp_path),
        api_client=DummyApiClient([_make_version("1.5.0", version_id="PINNED")]),
        state_store=StateStore(_make_config(tmp_path)),
    )

    result = await checker.check_single_update(
        ProjectConfig(
            slug="sodium",
            project_type=ProjectType.MOD,
            version="1.5.0",
        )
    )

    assert result.status == InstallStatus.NOT_INSTALLED
    assert result.pinned is True
    assert result.latest_version_id == "PINNED"


def test_needs_update_is_case_insensitive(tmp_path: Path) -> None:
    """Hash comparison is case-insensitive."""
    checker = UpdateChecker(
        config=_make_config(tmp_path),
        api_client=DummyApiClient([]),
        state_store=StateStore(_make_config(tmp_path)),
    )
    installed = _make_installed_file("sodium", sha512="ABC123")
    latest = _make_file(sha512="abc123")

    assert checker.needs_update(installed, latest) is False


async def test_check_updates_rejects_invalid_concurrency(tmp_path: Path) -> None:
    """max_concurrency must be positive."""
    checker = UpdateChecker(
        config=_make_config(tmp_path),
        api_client=DummyApiClient([]),
        state_store=StateStore(_make_config(tmp_path)),
    )

    with pytest.raises(ValueError, match="max_concurrency"):
        await checker.check_updates([], max_concurrency=0)
