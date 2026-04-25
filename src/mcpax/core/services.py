"""Core service lifecycle composition."""

import logging
from types import TracebackType
from typing import Self

from mcpax.core.api import ModrinthClient
from mcpax.core.downloader import Downloader, DownloaderConfig
from mcpax.core.file_service import FileService
from mcpax.core.install_planner import InstallPlanner
from mcpax.core.models import AppConfig
from mcpax.core.protocols import ModrinthClientProtocol
from mcpax.core.state_store import StateStore
from mcpax.core.update_applier import UpdateApplier
from mcpax.core.update_checker import UpdateChecker
from mcpax.core.version_resolver import VersionResolver

logger = logging.getLogger(__name__)


class ProjectServices:
    """Own and expose core services for one application operation."""

    def __init__(
        self,
        config: AppConfig,
        api_client: ModrinthClientProtocol | None = None,
        downloader: Downloader | None = None,
    ) -> None:
        self.config = config
        self.api_client = api_client
        self.downloader = downloader
        self.owns_api_client = api_client is None
        self.owns_downloader = downloader is None
        self.state_store = StateStore(config)
        self.file_service = FileService(config)
        self.version_resolver = VersionResolver()
        self.install_planner = InstallPlanner()
        self._update_checker: UpdateChecker | None = None
        self._update_applier: UpdateApplier | None = None

    async def __aenter__(self) -> Self:
        entered_api_client = False
        entered_downloader = False

        try:
            if self.api_client is None:
                self.api_client = ModrinthClient()
                await self.api_client.__aenter__()
                entered_api_client = True
            if self.downloader is None:
                self.downloader = Downloader(
                    config=DownloaderConfig(
                        max_concurrent=self.config.max_concurrent_downloads,
                        verify_hash=self.config.verify_hash,
                    )
                )
                await self.downloader.__aenter__()
                entered_downloader = True
        except Exception:
            if entered_downloader and self.owns_downloader and self.downloader:
                try:
                    await self.downloader.__aexit__(None, None, None)
                except Exception:
                    logger.exception(
                        "Failed to cleanup downloader after initialization error"
                    )
            if entered_api_client and self.owns_api_client and self.api_client:
                try:
                    await self.api_client.__aexit__(None, None, None)
                except Exception:
                    logger.exception(
                        "Failed to cleanup API client after initialization error"
                    )
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.owns_api_client and self.api_client:
            try:
                await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
            except Exception:
                logger.exception("Failed to cleanup API client")
        if self.owns_downloader and self.downloader:
            try:
                await self.downloader.__aexit__(exc_type, exc_val, exc_tb)
            except Exception:
                logger.exception("Failed to cleanup downloader")

    @property
    def update_checker(self) -> UpdateChecker:
        if self.api_client is None:
            msg = "API client not initialized. Use async context manager."
            raise RuntimeError(msg)
        if self._update_checker is None:
            self._update_checker = UpdateChecker(
                config=self.config,
                api_client=self.api_client,
                state_store=self.state_store,
                version_resolver=self.version_resolver,
            )
        return self._update_checker

    @property
    def update_applier(self) -> UpdateApplier:
        if self.downloader is None:
            msg = "Downloader not initialized. Use async context manager."
            raise RuntimeError(msg)
        if self._update_applier is None:
            self._update_applier = UpdateApplier(
                minecraft_dir=self.config.minecraft_dir,
                downloader=self.downloader,
                install_planner=self.install_planner,
                file_service=self.file_service,
                state_store=self.state_store,
            )
        return self._update_applier
