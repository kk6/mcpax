"""Tests for core service lifecycle composition."""

from types import TracebackType
from typing import Self
from unittest.mock import patch

import pytest

from mcpax.core.models import AppConfig, Loader
from mcpax.core.services import ProjectServices


class _FakeApiClient:
    def __init__(self) -> None:
        self.exited = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.exited = True


class _FailingDownloader:
    async def __aenter__(self) -> Self:
        msg = "downloader failed"
        raise RuntimeError(msg)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        return None


def _make_config(tmp_path) -> AppConfig:
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        minecraft_dir=tmp_path,
    )


async def test_aenter_closes_api_client_if_downloader_enter_fails(tmp_path) -> None:
    api_client = _FakeApiClient()

    with (
        patch("mcpax.core.services.ModrinthClient", return_value=api_client),
        patch("mcpax.core.services.Downloader", return_value=_FailingDownloader()),
    ):
        services = ProjectServices(_make_config(tmp_path))

        with pytest.raises(RuntimeError, match="downloader failed"):
            await services.__aenter__()

    assert api_client.exited is True
