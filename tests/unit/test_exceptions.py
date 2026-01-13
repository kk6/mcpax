"""Tests for mcpax.core.exceptions."""

from pathlib import Path

from mcpax.core.exceptions import (
    APIError,
    DownloadError,
    FileOperationError,
    HashMismatchError,
    MCPAXError,
    ProjectNotFoundError,
    RateLimitError,
    StateFileError,
)


class TestMCPAXError:
    """Tests for MCPAXError base class."""

    def test_inherits_from_exception(self) -> None:
        """MCPAXError inherits from Exception."""
        assert issubclass(MCPAXError, Exception)


class TestAPIError:
    """Tests for APIError."""

    def test_stores_status_code(self) -> None:
        """APIError stores status_code."""
        error = APIError("API failed", status_code=500)

        assert str(error) == "API failed"
        assert error.status_code == 500


class TestProjectNotFoundError:
    """Tests for ProjectNotFoundError."""

    def test_sets_slug_and_status(self) -> None:
        """ProjectNotFoundError sets slug and status code."""
        error = ProjectNotFoundError("missing-project")

        assert str(error) == "Project not found: missing-project"
        assert error.slug == "missing-project"
        assert error.status_code == 404


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_message_without_retry_after(self) -> None:
        """RateLimitError uses default message without retry_after."""
        error = RateLimitError()

        assert str(error) == "Rate limit exceeded"
        assert error.retry_after is None
        assert error.status_code == 429

    def test_message_with_retry_after(self) -> None:
        """RateLimitError includes retry_after in message."""
        error = RateLimitError(retry_after=30)

        assert str(error) == "Rate limit exceeded, retry after 30 seconds"
        assert error.retry_after == 30
        assert error.status_code == 429


class TestDownloadError:
    """Tests for DownloadError."""

    def test_stores_url(self) -> None:
        """DownloadError stores the URL."""
        error = DownloadError("Download failed", url="https://example.com/file.jar")

        assert str(error) == "Download failed"
        assert error.url == "https://example.com/file.jar"


class TestHashMismatchError:
    """Tests for HashMismatchError."""

    def test_includes_expected_and_actual_prefixes(self) -> None:
        """HashMismatchError formats message with hash prefixes."""
        expected = "a" * 64
        actual = "b" * 64
        error = HashMismatchError("file.jar", expected=expected, actual=actual)

        assert "file.jar" in str(error)
        assert expected[:16] in str(error)
        assert actual[:16] in str(error)
        assert error.filename == "file.jar"
        assert error.expected == expected
        assert error.actual == actual


class TestStateFileError:
    """Tests for StateFileError."""

    def test_stores_path(self) -> None:
        """StateFileError stores path."""
        path = Path("/tmp/state.json")
        error = StateFileError("State error", path=path)

        assert str(error) == "State error"
        assert error.path == path


class TestFileOperationError:
    """Tests for FileOperationError."""

    def test_stores_path(self) -> None:
        """FileOperationError stores path."""
        path = Path("/tmp/mod.jar")
        error = FileOperationError("File operation failed", path=path)

        assert str(error) == "File operation failed"
        assert error.path == path
