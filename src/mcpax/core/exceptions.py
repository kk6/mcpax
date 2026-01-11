"""Exceptions for mcpax."""


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
