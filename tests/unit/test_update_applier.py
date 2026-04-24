"""Tests for applying planned updates."""

from datetime import UTC, datetime
from pathlib import Path

from mcpax.core.file_service import FileService
from mcpax.core.install_planner import InstallPlanner
from mcpax.core.models import (
    AppConfig,
    DownloadResult,
    DownloadTask,
    InstalledFile,
    InstallStatus,
    Loader,
    ProjectFile,
    ProjectType,
    StateFile,
    UpdateCheckResult,
)
from mcpax.core.state_store import StateStore
from mcpax.core.update_applier import UpdateApplier


def _make_config(minecraft_dir: Path) -> AppConfig:
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        minecraft_dir=minecraft_dir,
    )


def _make_file(filename: str = "sodium.jar") -> ProjectFile:
    return ProjectFile(
        url=f"https://cdn.modrinth.com/{filename}",
        filename=filename,
        size=1024,
        hashes={"sha512": "abc123" * 20},
        primary=True,
    )


def _make_update(
    slug: str = "sodium",
    latest_file: ProjectFile | None = None,
    current_file: InstalledFile | None = None,
) -> UpdateCheckResult:
    status = (
        InstallStatus.NOT_INSTALLED if current_file is None else InstallStatus.OUTDATED
    )
    return UpdateCheckResult(
        slug=slug,
        project_type=ProjectType.MOD,
        status=status,
        current_version=current_file.version_number if current_file else None,
        current_file=current_file,
        latest_version="1.1.0",
        latest_version_id="NEWID",
        latest_file=latest_file or _make_file(),
    )


def _make_installed_file(slug: str, file_path: Path) -> InstalledFile:
    return InstalledFile(
        slug=slug,
        project_type=ProjectType.MOD,
        filename=file_path.name,
        version_id="OLDID",
        version_number="1.0.0",
        sha512="oldhash" * 20,
        installed_at=datetime.now(UTC),
        file_path=file_path,
    )


class DummyDownloader:
    """Downloader stub returning predefined results."""

    def __init__(self, results: list[DownloadResult]) -> None:
        self._results = results

    async def download_all(
        self,
        tasks: list[DownloadTask],
    ) -> list[DownloadResult]:
        return self._results


async def test_apply_updates_places_file_and_updates_state(tmp_path: Path) -> None:
    """Successful downloads are placed and written to state."""
    config = _make_config(tmp_path)
    state_store = StateStore(config)
    latest_file = _make_file("sodium-new.jar")
    download_file = tmp_path / ".mcpax-downloads" / latest_file.filename
    download_file.parent.mkdir(parents=True)
    download_file.write_text("new")
    task = DownloadTask(
        url=latest_file.url,
        dest=download_file,
        expected_hash=latest_file.hashes["sha512"],
        slug="sodium",
        version_number="1.1.0",
    )
    applier = UpdateApplier(
        minecraft_dir=tmp_path,
        downloader=DummyDownloader(
            [
                DownloadResult(
                    task=task,
                    success=True,
                    file_path=download_file,
                    error=None,
                )
            ]
        ),
        install_planner=InstallPlanner(),
        file_service=FileService(config),
        state_store=state_store,
    )

    result = await applier.apply_updates([_make_update(latest_file=latest_file)])

    assert result.successful == ["sodium"]
    assert (tmp_path / "mods" / latest_file.filename).exists()
    state = await state_store.load()
    assert state.files["sodium"].version_id == "NEWID"


async def test_apply_updates_backs_up_and_removes_old_file(tmp_path: Path) -> None:
    """Outdated installs are backed up before old file deletion."""
    config = _make_config(tmp_path)
    state_store = StateStore(config)
    old_file = tmp_path / "mods" / "sodium-old.jar"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("old")
    installed = _make_installed_file("sodium", old_file)
    await state_store.save(StateFile(files={"sodium": installed}))
    latest_file = _make_file("sodium-new.jar")
    download_file = tmp_path / ".mcpax-downloads" / latest_file.filename
    download_file.parent.mkdir(parents=True)
    download_file.write_text("new")
    task = DownloadTask(
        url=latest_file.url,
        dest=download_file,
        expected_hash=latest_file.hashes["sha512"],
        slug="sodium",
        version_number="1.1.0",
    )
    applier = UpdateApplier(
        minecraft_dir=tmp_path,
        downloader=DummyDownloader(
            [
                DownloadResult(
                    task=task,
                    success=True,
                    file_path=download_file,
                    error=None,
                )
            ]
        ),
        install_planner=InstallPlanner(),
        file_service=FileService(config),
        state_store=state_store,
    )

    result = await applier.apply_updates(
        [_make_update(latest_file=latest_file, current_file=installed)]
    )

    assert result.backed_up
    assert not old_file.exists()
    assert (tmp_path / "mods" / latest_file.filename).exists()
