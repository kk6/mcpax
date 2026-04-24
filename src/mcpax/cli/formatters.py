"""Shared CLI output formatters and validators."""

import json

from mcpax.cli.shared import VALID_PROJECT_TYPES, VALID_STATUS_FILTERS


def validate_list_options(
    type_filter: str | None,
    status_filter: str | None,
    no_update: bool,
    max_concurrency: int,
) -> str | None:
    """Validate list command options. Returns error message or None if valid."""
    if type_filter is not None and type_filter.lower() not in VALID_PROJECT_TYPES:
        return (
            f"Invalid type '{type_filter}'. "
            f"Must be one of: {', '.join(VALID_PROJECT_TYPES)}."
        )

    if status_filter is not None:
        status_filter_lower = status_filter.lower()
        if status_filter_lower not in VALID_STATUS_FILTERS:
            return (
                f"Invalid status '{status_filter}'. "
                f"Must be one of: {', '.join(VALID_STATUS_FILTERS)}."
            )
        if no_update and status_filter_lower == "outdated":
            return "--status outdated is not supported with --no-update."

    if max_concurrency < 1:
        return "--max-concurrency must be a positive integer."

    return None


def format_list_json(results: list[dict]) -> str:
    """Format list results as a JSON string."""
    json_data = [
        {
            "slug": p["slug"],
            "title": p["title"],
            "type": p["type"].value,
            "status": p["status"].value,
            "current_version": p["current_version"],
            "latest_version": p["latest_version"],
        }
        for p in results
    ]
    return json.dumps(json_data, indent=2, ensure_ascii=False)


_validate_list_options = validate_list_options
_format_list_json = format_list_json
