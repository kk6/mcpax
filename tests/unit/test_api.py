"""Tests for mcpax.core.api."""

from datetime import UTC, datetime

import httpx
import pytest
from pytest_httpx import HTTPXMock

from mcpax.core.api import ModrinthClient
from mcpax.core.exceptions import (
    APIError,
    MCPAXError,
    ProjectNotFoundError,
    RateLimitError,
)
from mcpax.core.models import (
    Loader,
    ModrinthProject,
    ProjectType,
    ProjectVersion,
    ReleaseChannel,
    SearchResult,
)

# === Fixtures ===


@pytest.fixture
def modrinth_project_response() -> dict:
    """Sample Modrinth project API response."""
    return {
        "id": "AANobbMI",
        "slug": "sodium",
        "title": "Sodium",
        "description": "A modern rendering engine for Minecraft",
        "project_type": "mod",
        "downloads": 12345678,
        "icon_url": "https://cdn.modrinth.com/data/AANobbMI/icon.png",
        "versions": ["v1", "v2", "v3"],
    }


@pytest.fixture
def modrinth_version_response() -> dict:
    """Sample Modrinth version API response."""
    return {
        "id": "ABC123",
        "project_id": "AANobbMI",
        "version_number": "0.6.0+mc1.21.4",
        "version_type": "release",
        "game_versions": ["1.21.4", "1.21.3"],
        "loaders": ["fabric", "quilt"],
        "files": [
            {
                "url": "https://cdn.modrinth.com/data/AANobbMI/versions/ABC123/sodium.jar",
                "filename": "sodium-fabric-0.6.0+mc1.21.4.jar",
                "size": 1234567,
                "hashes": {"sha512": "abc123def456", "sha1": "abc123"},
                "primary": True,
            }
        ],
        "dependencies": [],
        "date_published": "2024-01-15T10:00:00Z",
    }


@pytest.fixture
def search_response() -> dict:
    """Sample Modrinth search API response."""
    return {
        "hits": [
            {
                "slug": "sodium",
                "title": "Sodium",
                "description": "A modern rendering engine",
                "project_type": "mod",
                "downloads": 12345678,
                "icon_url": None,
            }
        ],
        "total_hits": 1,
        "offset": 0,
        "limit": 10,
    }


# === Exception Tests ===


class TestMCPAXError:
    """Tests for MCPAXError exception."""

    def test_is_exception(self) -> None:
        """MCPAXError is an Exception."""
        # Arrange & Act
        error = MCPAXError("Test error")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestAPIError:
    """Tests for APIError exception."""

    def test_stores_message_and_status_code(self) -> None:
        """APIError stores message and status code."""
        # Arrange & Act
        error = APIError("Server error", status_code=500)

        # Assert
        assert str(error) == "Server error"
        assert error.status_code == 500

    def test_status_code_defaults_to_none(self) -> None:
        """APIError status_code defaults to None."""
        # Arrange & Act
        error = APIError("Unknown error")

        # Assert
        assert error.status_code is None

    def test_inherits_from_mcpax_error(self) -> None:
        """APIError inherits from MCPAXError."""
        # Arrange & Act
        error = APIError("Test error")

        # Assert
        assert isinstance(error, MCPAXError)


class TestProjectNotFoundError:
    """Tests for ProjectNotFoundError exception."""

    def test_stores_slug(self) -> None:
        """ProjectNotFoundError stores project slug."""
        # Arrange & Act
        error = ProjectNotFoundError("sodium")

        # Assert
        assert error.slug == "sodium"
        assert error.status_code == 404
        assert "sodium" in str(error)

    def test_inherits_from_api_error(self) -> None:
        """ProjectNotFoundError inherits from APIError."""
        # Arrange & Act
        error = ProjectNotFoundError("sodium")

        # Assert
        assert isinstance(error, APIError)


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_stores_retry_after(self) -> None:
        """RateLimitError stores retry_after value."""
        # Arrange & Act
        error = RateLimitError(retry_after=60)

        # Assert
        assert error.retry_after == 60
        assert error.status_code == 429
        assert "60" in str(error)

    def test_retry_after_defaults_to_none(self) -> None:
        """RateLimitError retry_after defaults to None."""
        # Arrange & Act
        error = RateLimitError()

        # Assert
        assert error.retry_after is None
        assert "Rate limit exceeded" in str(error)

    def test_inherits_from_api_error(self) -> None:
        """RateLimitError inherits from APIError."""
        # Arrange & Act
        error = RateLimitError()

        # Assert
        assert isinstance(error, APIError)


# === Client Initialization Tests ===


class TestModrinthClientInit:
    """Tests for ModrinthClient initialization."""

    def test_default_values(self) -> None:
        """ModrinthClient uses correct default values."""
        # Arrange & Act
        client = ModrinthClient()

        # Assert
        assert client.max_retries == 3
        assert client.backoff_factor == 1.0

    def test_custom_values(self) -> None:
        """ModrinthClient accepts custom values."""
        # Arrange & Act
        client = ModrinthClient(max_retries=5, backoff_factor=2.0)

        # Assert
        assert client.max_retries == 5
        assert client.backoff_factor == 2.0

    def test_headers_include_user_agent(self) -> None:
        """ModrinthClient headers include User-Agent."""
        # Arrange
        client = ModrinthClient()

        # Act
        headers = client._headers

        # Assert
        assert "User-Agent" in headers
        assert headers["User-Agent"] == "mcpax/0.1.0"


# === Context Manager Tests ===


class TestModrinthClientContextManager:
    """Tests for ModrinthClient context manager."""

    async def test_creates_client_on_enter(self) -> None:
        """Context manager creates httpx client on enter."""
        # Arrange
        client = ModrinthClient()

        # Act
        async with client as c:
            # Assert
            assert c._client is not None
            assert isinstance(c._client, httpx.AsyncClient)

    async def test_closes_client_on_exit(self) -> None:
        """Context manager closes httpx client on exit."""
        # Arrange
        client = ModrinthClient()

        # Act
        async with client:
            pass

        # Assert
        assert client._client.is_closed

    async def test_uses_injected_client(self) -> None:
        """Context manager uses injected httpx client."""
        # Arrange
        injected_client = httpx.AsyncClient()
        client = ModrinthClient(client=injected_client)

        # Act
        async with client as c:
            # Assert
            assert c._client is injected_client

        # Cleanup
        await injected_client.aclose()


# === Rate Limit Tests ===


class TestRateLimitTracking:
    """Tests for rate limit tracking."""

    def test_rate_limit_info_initially_none(self) -> None:
        """Rate limit info is None initially."""
        # Arrange
        client = ModrinthClient()

        # Act
        info = client.rate_limit_info

        # Assert
        assert info is None

    async def test_updates_from_response_headers(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Rate limit info is updated from response headers."""
        # Arrange
        httpx_mock.add_response(
            json={"test": "data"},
            headers={
                "X-Ratelimit-Remaining": "299",
                "X-Ratelimit-Limit": "300",
                "X-Ratelimit-Reset": "1704067200",
            },
        )

        # Act
        async with ModrinthClient() as client:
            await client._request("GET", "/test")
            info = client.rate_limit_info

        # Assert
        assert info is not None
        assert info.remaining == 299
        assert info.limit == 300
        assert info.reset == 1704067200

    async def test_handles_missing_rate_limit_headers(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Rate limit info remains None if headers are missing."""
        # Arrange
        httpx_mock.add_response(json={"test": "data"})

        # Act
        async with ModrinthClient() as client:
            await client._request("GET", "/test")
            info = client.rate_limit_info

        # Assert
        assert info is None


# === Error Response Handling Tests ===


class TestErrorResponseHandling:
    """Tests for error response handling."""

    async def test_raises_project_not_found_for_404(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Raises ProjectNotFoundError for 404 responses."""
        # Arrange
        httpx_mock.add_response(status_code=404)

        # Act & Assert
        async with ModrinthClient() as client:
            with pytest.raises(ProjectNotFoundError):
                await client._request("GET", "/project/nonexistent")

    async def test_raises_rate_limit_error_for_429(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Raises RateLimitError for 429 responses."""
        # Arrange
        httpx_mock.add_response(
            status_code=429,
            headers={"Retry-After": "60"},
        )

        # Act & Assert
        async with ModrinthClient() as client:
            with pytest.raises(RateLimitError) as exc_info:
                await client._request("GET", "/project/test")
            assert exc_info.value.retry_after == 60

    async def test_raises_api_error_for_500(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Raises APIError for 500 responses."""
        # Arrange
        # Add responses for initial request + retries
        for _ in range(4):  # max_retries (3) + 1
            httpx_mock.add_response(status_code=500, text="Server Error")

        # Act & Assert (use small backoff_factor for fast tests)
        async with ModrinthClient(backoff_factor=0.001) as client:
            with pytest.raises(APIError) as exc_info:
                await client._request("GET", "/project/test")
            assert exc_info.value.status_code == 500

    async def test_success_response_does_not_raise(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Success responses do not raise exceptions."""
        # Arrange
        httpx_mock.add_response(json={"success": True})

        # Act
        async with ModrinthClient() as client:
            response = await client._request("GET", "/project/test")

        # Assert
        assert response.status_code == 200


# === Retry Logic Tests ===


class TestRetryLogic:
    """Tests for retry logic."""

    async def test_retries_on_500_error(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Client retries request on 500 error."""
        # Arrange
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(status_code=500)
        httpx_mock.add_response(json={"success": True})

        # Act (use small backoff_factor for fast tests)
        async with ModrinthClient(max_retries=3, backoff_factor=0.001) as client:
            response = await client._request("GET", "/test")

        # Assert
        assert response.status_code == 200
        assert len(httpx_mock.get_requests()) == 3

    async def test_retries_on_503_error(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Client retries request on 503 error."""
        # Arrange
        httpx_mock.add_response(status_code=503)
        httpx_mock.add_response(json={"success": True})

        # Act (use small backoff_factor for fast tests)
        async with ModrinthClient(max_retries=3, backoff_factor=0.001) as client:
            response = await client._request("GET", "/test")

        # Assert
        assert response.status_code == 200
        assert len(httpx_mock.get_requests()) == 2

    async def test_raises_after_max_retries(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Client raises APIError after max retries exceeded."""
        # Arrange
        for _ in range(4):  # max_retries + 1
            httpx_mock.add_response(status_code=503)

        # Act & Assert (use small backoff_factor for fast tests)
        async with ModrinthClient(max_retries=3, backoff_factor=0.001) as client:
            with pytest.raises(APIError) as exc_info:
                await client._request("GET", "/test")

        assert exc_info.value.status_code == 503
        assert len(httpx_mock.get_requests()) == 4  # initial + 3 retries

    async def test_does_not_retry_on_404(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Client does not retry on 404 error."""
        # Arrange
        httpx_mock.add_response(status_code=404)

        # Act & Assert
        async with ModrinthClient(max_retries=3) as client:
            with pytest.raises(ProjectNotFoundError):
                await client._request("GET", "/project/test")

        # Only one request should have been made
        assert len(httpx_mock.get_requests()) == 1

    async def test_does_not_retry_on_429(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Client does not retry on 429 error."""
        # Arrange
        httpx_mock.add_response(status_code=429)

        # Act & Assert
        async with ModrinthClient(max_retries=3) as client:
            with pytest.raises(RateLimitError):
                await client._request("GET", "/test")

        # Only one request should have been made
        assert len(httpx_mock.get_requests()) == 1


# === Get Project Tests ===


class TestGetProject:
    """Tests for get_project method."""

    async def test_returns_modrinth_project(
        self,
        httpx_mock: HTTPXMock,
        modrinth_project_response: dict,
    ) -> None:
        """get_project returns ModrinthProject instance."""
        # Arrange
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/sodium",
            json=modrinth_project_response,
        )

        # Act
        async with ModrinthClient() as client:
            project = await client.get_project("sodium")

        # Assert
        assert isinstance(project, ModrinthProject)
        assert project.slug == "sodium"
        assert project.title == "Sodium"
        assert project.project_type == ProjectType.MOD
        assert project.downloads == 12345678

    async def test_raises_project_not_found_for_404(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """get_project raises ProjectNotFoundError for 404."""
        # Arrange
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/nonexistent",
            status_code=404,
        )

        # Act & Assert
        async with ModrinthClient() as client:
            with pytest.raises(ProjectNotFoundError) as exc_info:
                await client.get_project("nonexistent")

        assert exc_info.value.slug == "nonexistent"


# === Get Versions Tests ===


class TestGetVersions:
    """Tests for get_versions method."""

    async def test_returns_version_list(
        self,
        httpx_mock: HTTPXMock,
        modrinth_version_response: dict,
    ) -> None:
        """get_versions returns list of ProjectVersion."""
        # Arrange
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/sodium/version",
            json=[modrinth_version_response],
        )

        # Act
        async with ModrinthClient() as client:
            versions = await client.get_versions("sodium")

        # Assert
        assert isinstance(versions, list)
        assert len(versions) == 1
        assert isinstance(versions[0], ProjectVersion)
        assert versions[0].version_number == "0.6.0+mc1.21.4"
        assert versions[0].version_type == ReleaseChannel.RELEASE
        assert "1.21.4" in versions[0].game_versions
        assert "fabric" in versions[0].loaders

    async def test_returns_empty_list_for_no_versions(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        """get_versions returns empty list when no versions exist."""
        # Arrange
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/project/new-project/version",
            json=[],
        )

        # Act
        async with ModrinthClient() as client:
            versions = await client.get_versions("new-project")

        # Assert
        assert versions == []


# === Search Tests ===


class TestSearch:
    """Tests for search method."""

    async def test_returns_search_result(
        self,
        httpx_mock: HTTPXMock,
        search_response: dict,
    ) -> None:
        """search returns SearchResult instance."""
        # Arrange
        httpx_mock.add_response(
            url="https://api.modrinth.com/v2/search?query=sodium&limit=10&offset=0",
            json=search_response,
        )

        # Act
        async with ModrinthClient() as client:
            result = await client.search("sodium")

        # Assert
        assert isinstance(result, SearchResult)
        assert result.total_hits == 1
        assert len(result.hits) == 1
        assert result.hits[0].slug == "sodium"
        assert result.hits[0].title == "Sodium"
        assert result.limit == 10
        assert result.offset == 0

    async def test_pagination_parameters(
        self,
        httpx_mock: HTTPXMock,
        search_response: dict,
    ) -> None:
        """search uses pagination parameters."""
        # Arrange
        httpx_mock.add_response(json=search_response)

        # Act
        async with ModrinthClient() as client:
            await client.search("sodium", limit=20, offset=10)

        # Assert
        request = httpx_mock.get_request()
        assert "query=sodium" in str(request.url)
        assert "limit=20" in str(request.url)
        assert "offset=10" in str(request.url)


# === Version Filtering Tests ===


class TestFilterCompatibleVersions:
    """Tests for filter_compatible_versions method."""

    def test_filters_by_minecraft_version(self) -> None:
        """Filters versions by Minecraft version."""
        # Arrange
        versions = [
            _make_version("1.0", game_versions=["1.21.4"]),
            _make_version("0.9", game_versions=["1.21.3"]),
        ]
        client = ModrinthClient()

        # Act
        result = client.filter_compatible_versions(
            versions,
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
        )

        # Assert
        assert len(result) == 1
        assert result[0].version_number == "1.0"

    def test_filters_by_loader(self) -> None:
        """Filters versions by loader."""
        # Arrange
        versions = [
            _make_version("1.0", game_versions=["1.21.4"], loaders=["fabric"]),
            _make_version("0.9", game_versions=["1.21.4"], loaders=["forge"]),
        ]
        client = ModrinthClient()

        # Act
        result = client.filter_compatible_versions(
            versions,
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
        )

        # Assert
        assert len(result) == 1
        assert result[0].version_number == "1.0"

    def test_filters_by_channel(self) -> None:
        """Filters versions by release channel."""
        # Arrange
        versions = [
            _make_version(
                "1.0",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                version_type=ReleaseChannel.RELEASE,
            ),
            _make_version(
                "1.1-beta",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                version_type=ReleaseChannel.BETA,
            ),
            _make_version(
                "1.2-alpha",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                version_type=ReleaseChannel.ALPHA,
            ),
        ]
        client = ModrinthClient()

        # Act - release only
        result = client.filter_compatible_versions(
            versions,
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
            channel=ReleaseChannel.RELEASE,
        )

        # Assert
        assert len(result) == 1
        assert result[0].version_number == "1.0"

    def test_channel_hierarchy(self) -> None:
        """Beta channel includes beta and release versions."""
        # Arrange
        versions = [
            _make_version(
                "1.0",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                version_type=ReleaseChannel.RELEASE,
            ),
            _make_version(
                "1.1-beta",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                version_type=ReleaseChannel.BETA,
            ),
            _make_version(
                "1.2-alpha",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                version_type=ReleaseChannel.ALPHA,
            ),
        ]
        client = ModrinthClient()

        # Act - beta includes release and beta
        result = client.filter_compatible_versions(
            versions,
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
            channel=ReleaseChannel.BETA,
        )

        # Assert
        assert len(result) == 2
        assert {v.version_number for v in result} == {"1.0", "1.1-beta"}


class TestGetLatestCompatibleVersion:
    """Tests for get_latest_compatible_version method."""

    def test_returns_latest_version(self) -> None:
        """Returns the latest compatible version."""
        # Arrange
        versions = [
            _make_version(
                "1.0",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                date_published=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            _make_version(
                "1.1",
                game_versions=["1.21.4"],
                loaders=["fabric"],
                date_published=datetime(2024, 1, 15, tzinfo=UTC),
            ),
        ]
        client = ModrinthClient()

        # Act
        result = client.get_latest_compatible_version(
            versions,
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
        )

        # Assert
        assert result is not None
        assert result.version_number == "1.1"

    def test_returns_none_when_no_compatible(self) -> None:
        """Returns None when no compatible version exists."""
        # Arrange
        versions = [
            _make_version("1.0", game_versions=["1.20.1"], loaders=["fabric"]),
        ]
        client = ModrinthClient()

        # Act
        result = client.get_latest_compatible_version(
            versions,
            minecraft_version="1.21.4",
            loader=Loader.FABRIC,
        )

        # Assert
        assert result is None


# === Test Helpers ===


def _make_version(
    version_number: str,
    game_versions: list[str] | None = None,
    loaders: list[str] | None = None,
    version_type: ReleaseChannel = ReleaseChannel.RELEASE,
    date_published: datetime | None = None,
) -> ProjectVersion:
    """Helper to create ProjectVersion for tests."""
    return ProjectVersion(
        id=f"id-{version_number}",
        project_id="test-project",
        version_number=version_number,
        version_type=version_type,
        game_versions=game_versions or ["1.21.4"],
        loaders=loaders or ["fabric"],
        files=[],
        dependencies=[],
        date_published=date_published or datetime.now(UTC),
    )
