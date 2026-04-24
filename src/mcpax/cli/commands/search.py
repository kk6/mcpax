from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated

import typer

from mcpax.cli.shared import (
    VALID_PROJECT_TYPES,
    console,
)
from mcpax.core.api import ModrinthClient
from mcpax.core.exceptions import APIError
from mcpax.core.models import (
    ProjectType,
    SearchHit,
)

logger = logging.getLogger(__name__)


async def _search_projects(
    query: str,
    type_filter: ProjectType | None,
    limit: int,
) -> list[SearchHit]:
    """Search for projects with optional type filtering.

    Args:
        query: Search query string
        type_filter: Optional project type filter
        limit: Maximum number of results to return

    Returns:
        List of search hits

    Raises:
        APIError: For API errors
    """
    facets = None
    if type_filter is not None:
        facets = json.dumps([[f"project_type:{type_filter.value}"]])

    async with ModrinthClient() as client:
        if facets is None:
            result = await client.search(query, limit=limit)
        else:
            result = await client.search(query, limit=limit, facets=facets)

    return result.hits


def search(
    query: Annotated[str, typer.Argument(help="Search keyword")],
    type_filter: Annotated[
        str | None,
        typer.Option(
            "--type", "-t", help="Filter by type (mod/modpack/shader/resourcepack)"
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Number of results to show"),
    ] = 10,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output in JSON format"),
    ] = False,
) -> None:
    """Search for projects on Modrinth.

    Example:
        mcpax search sodium
        mcpax search shader --type shader --limit 5
        mcpax search fabric --json
    """
    # Validate type filter
    project_type_filter: ProjectType | None = None
    if type_filter is not None:
        if type_filter.lower() not in VALID_PROJECT_TYPES:
            console.print(
                f"[red]Error:[/red] Invalid type '{type_filter}'. "
                f"Must be one of: {', '.join(VALID_PROJECT_TYPES)}."
            )
            raise typer.Exit(code=1)
        project_type_filter = ProjectType(type_filter.lower())

    # Search projects
    async def _do_search() -> list[SearchHit]:
        try:
            return await _search_projects(query, project_type_filter, limit)
        except APIError as e:
            console.print(f"[red]Error:[/red] API error: {e}")
            raise typer.Exit(code=1) from None

    hits = asyncio.run(_do_search())

    # Handle no results
    if not hits:
        if json_output:
            console.print("[]")
        else:
            console.print(f"No results found for '{query}'.")
        raise typer.Exit(code=0)

    # Output in JSON format
    if json_output:
        json_data = [
            {
                "slug": h.slug,
                "title": h.title,
                "description": h.description,
                "type": h.project_type.value,
                "downloads": h.downloads,
            }
            for h in hits
        ]
        console.print(json.dumps(json_data, indent=2, ensure_ascii=False))
        raise typer.Exit(code=0)

    # Standard output
    console.print(f"\nSearch results for '{query}':\n")
    for i, hit in enumerate(hits, start=1):
        type_str = hit.project_type.value
        downloads_formatted = f"{hit.downloads:,}"
        console.print(f"{i}. {hit.title} ({type_str})")
        console.print(f"   {hit.description}")
        console.print(f"   Downloads: {downloads_formatted}\n")

    console.print("Run 'mcpax add <slug>' to add a project.")
