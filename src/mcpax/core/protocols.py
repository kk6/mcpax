"""Core service protocols."""

from types import TracebackType
from typing import Protocol, Self

from mcpax.core.models import (
    ModrinthProject,
    ProjectVersion,
    SearchResult,
)


class ModrinthClientProtocol(Protocol):
    """API client operations used by core business logic."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    async def get_project(self, slug: str) -> ModrinthProject: ...

    async def get_versions(self, slug: str) -> list[ProjectVersion]: ...

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        facets: str | None = None,
    ) -> SearchResult: ...
