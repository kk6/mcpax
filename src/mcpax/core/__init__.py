"""Core business logic for mcpax."""

from mcpax.core.api import ModrinthClient, RateLimitInfo
from mcpax.core.exceptions import (
    APIError,
    ConfigError,
    ConfigValidationError,
    MCPAXError,
    ProjectNotFoundError,
    RateLimitError,
    ValidationError,
)
from mcpax.core.file_service import FileService
from mcpax.core.install_planner import InstallPlan, InstallPlanner
from mcpax.core.manager import ProjectManager
from mcpax.core.protocols import ModrinthClientProtocol
from mcpax.core.state_store import StateStore
from mcpax.core.update_applier import UpdateApplier
from mcpax.core.update_checker import UpdateChecker
from mcpax.core.version_resolver import VersionCriteria, VersionResolver

__all__ = [
    "APIError",
    "ConfigError",
    "ConfigValidationError",
    "FileService",
    "InstallPlan",
    "InstallPlanner",
    "MCPAXError",
    "ModrinthClient",
    "ModrinthClientProtocol",
    "ProjectManager",
    "ProjectNotFoundError",
    "RateLimitError",
    "RateLimitInfo",
    "StateStore",
    "UpdateApplier",
    "UpdateChecker",
    "ValidationError",
    "VersionCriteria",
    "VersionResolver",
]
