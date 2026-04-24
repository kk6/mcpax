"""Core service protocols."""

from typing import Protocol

from mcpax.core.models import (
    Loader,
    ModrinthProject,
    ProjectType,
    ProjectVersion,
    ReleaseChannel,
    SearchResult,
)


class ModrinthClientProtocol(Protocol):
    """API client operations used by core business logic."""

    async def get_project(self, slug: str) -> ModrinthProject: ...

    async def get_versions(self, slug: str) -> list[ProjectVersion]: ...

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        facets: str | None = None,
    ) -> SearchResult: ...

    def get_latest_compatible_version(
        self,
        versions: list[ProjectVersion],
        minecraft_version: str,
        loader: Loader,
        channel: ReleaseChannel = ReleaseChannel.RELEASE,
        project_type: ProjectType | None = None,
        shader_loader: Loader | None = None,
    ) -> ProjectVersion | None: ...
