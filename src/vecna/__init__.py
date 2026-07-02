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
import os

from vecna.server import run_http, run_stdio


def main() -> None:
    """
    Synchronous entry point for the `vecna` CLI command.

    Transport is selected via the VECNA_TRANSPORT env var:
      "stdio" (default) - local stdio transport
      "http"             - Streamable HTTP transport (see VECNA_HOST/VECNA_PORT)
    """
    if os.environ.get("VECNA_TRANSPORT", "stdio").lower() == "http":
        run_http()
    else:
        asyncio.run(run_stdio())


__all__ = ["main"]
