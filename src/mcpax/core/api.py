"""Modrinth API client."""

import asyncio
from dataclasses import dataclass
from typing import Self

import httpx

from mcpax import __version__
from mcpax.core.exceptions import APIError, ProjectNotFoundError, RateLimitError
from mcpax.core.models import (
    Loader,
    ModrinthProject,
    ProjectVersion,
    ReleaseChannel,
    SearchResult,
)


@dataclass
class RateLimitInfo:
    """Rate limit tracking information."""

    remaining: int
    limit: int
    reset: int  # Unix timestamp


class ModrinthClient:
    """Async client for Modrinth API v2."""

    BASE_URL = "https://api.modrinth.com/v2"
    DEFAULT_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 1.0

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        """Initialize the client.

        Args:
            client: Optional httpx.AsyncClient for dependency injection.
                If provided, it must be pre-configured with base_url and headers.
                The client will not be automatically configured or closed.
            max_retries: Maximum retry attempts for 5xx errors
            backoff_factor: Base factor for exponential backoff

        Note:
            When injecting a custom client, ensure it has:
            - base_url set to BASE_URL or similar
            - User-Agent header configured
            - Appropriate timeout settings
        """
        self._client = client
        self._owns_client = client is None
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._rate_limit_info: RateLimitInfo | None = None

    @property
    def _headers(self) -> dict[str, str]:
        """Default headers for API requests."""
        return {"User-Agent": f"mcpax/{__version__}"}

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self._headers,
                timeout=self.DEFAULT_TIMEOUT,
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._owns_client and self._client:
            await self._client.aclose()

    @property
    def rate_limit_info(self) -> RateLimitInfo | None:
        """Current rate limit information."""
        return self._rate_limit_info

    def _update_rate_limit(self, response: httpx.Response) -> None:
        """Update rate limit info from response headers.

        Args:
            response: HTTP response with rate limit headers
        """
        remaining_str = response.headers.get("X-Ratelimit-Remaining")
        limit_str = response.headers.get("X-Ratelimit-Limit")
        reset_str = response.headers.get("X-Ratelimit-Reset")

        if remaining_str and limit_str and reset_str:
            self._rate_limit_info = RateLimitInfo(
                remaining=int(remaining_str),
                limit=int(limit_str),
                reset=int(reset_str),
            )

    async def _handle_error_response(
        self, response: httpx.Response, slug: str | None = None
    ) -> None:
        """Handle error responses and raise appropriate exceptions.

        Args:
            response: HTTP response to check
            slug: Optional project slug for better error messages

        Raises:
            ProjectNotFoundError: For 404 responses
            RateLimitError: For 429 responses
            APIError: For other error responses
        """
        if response.status_code == 404:
            # Use provided slug or extract from path
            if slug is None:
                # Try to extract slug from path (e.g., /project/{slug})
                import re

                match = re.search(r"/project/([^/]+)", str(response.url.path))
                slug = match.group(1) if match else "unknown"
            raise ProjectNotFoundError(slug)

        if response.status_code == 429:
            retry_after_str = response.headers.get("Retry-After")
            retry_after = int(retry_after_str) if retry_after_str else None
            raise RateLimitError(retry_after=retry_after)

        if response.status_code >= 400:
            raise APIError(
                f"API request failed: {response.status_code}",
                status_code=response.status_code,
            )

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        slug: str | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: Query parameters
            slug: Optional project slug for better error messages

        Returns:
            httpx.Response object

        Raises:
            ProjectNotFoundError: For 404 responses
            RateLimitError: For 429 responses
            APIError: For other error responses
        """
        if self._client is None:
            msg = "Client not initialized. Use async with context manager."
            raise RuntimeError(msg)

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, path, params=params)
                self._update_rate_limit(response)

                # Check for errors
                await self._handle_error_response(response, slug=slug)

                return response

            except APIError as e:
                # Don't retry on client errors (4xx except 429)
                if e.status_code and 400 <= e.status_code < 500:
                    raise

                # Retry on 5xx errors
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue

                # Max retries exceeded
                raise

        # This should never be reached due to raise in the loop,
        # but is needed for type checker
        msg = "Unexpected code path"
        raise RuntimeError(msg)  # pragma: no cover

    # --- Public API Methods ---

    async def get_project(self, slug: str) -> ModrinthProject:
        """Get project information by slug.

        Args:
            slug: Project slug (e.g., "sodium")

        Returns:
            ModrinthProject instance

        Raises:
            ProjectNotFoundError: If project doesn't exist
            APIError: For other API errors
        """
        response = await self._request("GET", f"/project/{slug}", slug=slug)
        return ModrinthProject.model_validate(response.json())

    async def get_versions(self, slug: str) -> list[ProjectVersion]:
        """Get all versions for a project.

        Args:
            slug: Project slug

        Returns:
            List of ProjectVersion instances

        Raises:
            ProjectNotFoundError: If project doesn't exist
            APIError: For other API errors
        """
        response = await self._request("GET", f"/project/{slug}/version", slug=slug)
        versions_data = response.json()
        return [ProjectVersion.model_validate(v) for v in versions_data]

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchResult:
        """Search for projects.

        Args:
            query: Search query string
            limit: Maximum results (default 10, max 100)
            offset: Pagination offset

        Returns:
            SearchResult instance

        Raises:
            APIError: For API errors
        """
        params = {
            "query": query,
            "limit": str(limit),
            "offset": str(offset),
        }
        response = await self._request("GET", "/search", params=params)
        return SearchResult.model_validate(response.json())

    # --- Version Filtering ---

    def filter_compatible_versions(
        self,
        versions: list[ProjectVersion],
        minecraft_version: str,
        loader: Loader,
        channel: ReleaseChannel = ReleaseChannel.RELEASE,
    ) -> list[ProjectVersion]:
        """Filter versions compatible with given criteria.

        Args:
            versions: List of versions to filter
            minecraft_version: Target Minecraft version
            loader: Target mod loader
            channel: The most unstable release channel to include. For example,
                `BETA` will include `BETA` and `RELEASE` versions, but exclude
                `ALPHA`. `ALPHA` includes all channels.

        Returns:
            Filtered list of compatible versions (newest first)
        """
        # Channel hierarchy: RELEASE < BETA < ALPHA
        channel_order = {
            ReleaseChannel.RELEASE: 0,
            ReleaseChannel.BETA: 1,
            ReleaseChannel.ALPHA: 2,
        }
        min_channel_value = channel_order[channel]

        compatible = []
        for version in versions:
            # Check Minecraft version
            if minecraft_version not in version.game_versions:
                continue

            # Check loader (case-insensitive)
            loader_str = loader.value.lower()
            if not any(loader_str == name.lower() for name in version.loaders):
                continue

            # Check release channel
            version_channel_value = channel_order[version.version_type]
            if version_channel_value > min_channel_value:
                continue

            compatible.append(version)

        # Sort by date (newest first)
        compatible.sort(key=lambda v: v.date_published, reverse=True)

        return compatible

    def get_latest_compatible_version(
        self,
        versions: list[ProjectVersion],
        minecraft_version: str,
        loader: Loader,
        channel: ReleaseChannel = ReleaseChannel.RELEASE,
    ) -> ProjectVersion | None:
        """Get the latest compatible version.

        Args:
            versions: List of versions to filter
            minecraft_version: Target Minecraft version
            loader: Target mod loader
            channel: Minimum release channel

        Returns:
            Latest compatible ProjectVersion or None
        """
        compatible = self.filter_compatible_versions(
            versions, minecraft_version, loader, channel
        )
        return compatible[0] if compatible else None
