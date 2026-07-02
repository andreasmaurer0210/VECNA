"""
VECNA — MCP server for D&D 5e SRD data.

Modules:
  api.py       HTTP client for dnd5eapi.co
  tools.py     MCP tool handlers
  resources.py MCP resource handlers
  prompts.py   MCP prompt templates
  server.py    Async entry point (main())
"""

import asyncio

from vecna.server import main as _main


def main() -> None:
    """Synchronous entry point for the `vecna` CLI command."""
    asyncio.run(_main())


__all__ = ["main"]
