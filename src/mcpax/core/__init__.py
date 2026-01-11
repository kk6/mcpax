"""Core business logic for mcpax."""

from mcpax.core.api import ModrinthClient, RateLimitInfo
from mcpax.core.exceptions import (
    APIError,
    MCPAXError,
    McpaxError,  # Backward compatibility alias
    ProjectNotFoundError,
    RateLimitError,
)

__all__ = [
    "ModrinthClient",
    "RateLimitInfo",
    "APIError",
    "MCPAXError",
    "McpaxError",  # Backward compatibility (deprecated)
    "ProjectNotFoundError",
    "RateLimitError",
]
