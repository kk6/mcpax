from __future__ import annotations

import logging

import typer

from mcpax.cli.shared import (
    console,
)

logger = logging.getLogger(__name__)


def tui() -> None:
    """Launch the TUI interface."""
    try:
        from mcpax.tui import run_tui

        run_tui()
    except ImportError as e:
        console.print(
            "[red]Error:[/red] TUI dependencies not installed. "
            "Run 'uv pip install -e \".\\[tui]\"' to install them."
        )
        raise typer.Exit(1) from e
