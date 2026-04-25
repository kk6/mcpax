"""Core service protocols."""

from typing import Protocol

from mcpax.core.models import (
    ModrinthProject,
    ProjectVersion,
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
