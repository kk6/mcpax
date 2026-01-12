"""Exceptions for mcpax."""

from pathlib import Path


class MCPAXError(Exception):
    """Base exception for all mcpax errors."""


# Backward compatibility alias (deprecated)
McpaxError = MCPAXError


class APIError(MCPAXError):
    """General API error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize APIError.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
        """
        super().__init__(message)
        self.status_code = status_code


class ProjectNotFoundError(APIError):
    """Project does not exist on Modrinth."""

    def __init__(self, slug: str) -> None:
        """Initialize ProjectNotFoundError.

        Args:
            slug: Project slug that was not found
        """
        super().__init__(f"Project not found: {slug}", status_code=404)
        self.slug = slug


class RateLimitError(APIError):
    """Rate limit exceeded."""

    def __init__(self, retry_after: int | None = None) -> None:
        """Initialize RateLimitError.

        Args:
            retry_after: Seconds to wait before retrying
        """
        message = "Rate limit exceeded"
        if retry_after is not None:
            message += f", retry after {retry_after} seconds"
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class DownloadError(MCPAXError):
    """Error during file download."""

    def __init__(self, message: str, url: str | None = None) -> None:
        """Initialize DownloadError.

        Args:
            message: Error message
            url: URL that caused the error
        """
        super().__init__(message)
        self.url = url


class HashMismatchError(DownloadError):
    """File hash does not match expected value."""

    def __init__(
        self,
        filename: str,
        expected: str,
        actual: str,
    ) -> None:
        """Initialize HashMismatchError.

        Args:
            filename: Name of the file
            expected: Expected SHA512 hash
            actual: Actual computed hash
        """
        message = (
            f"Hash mismatch for {filename}: "
            f"expected {expected[:16]}..., got {actual[:16]}..."
        )
        super().__init__(message)
        self.filename = filename
        self.expected = expected
        self.actual = actual


class StateFileError(MCPAXError):
    """Error reading/writing state file."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        """Initialize StateFileError.

        Args:
            message: Error message
            path: Path to state file
        """
        super().__init__(message)
        self.path = path


class FileOperationError(MCPAXError):
    """Error during file operations (move, delete, backup)."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        """Initialize FileOperationError.

        Args:
            message: Error message
            path: Path to file that caused error
        """
        super().__init__(message)
        self.path = path
