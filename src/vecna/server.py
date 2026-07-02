"""
VECNA — Model Context Protocol (MCP) server.

This file is the **entry point** — it wires together modules:
  api.py       → HTTP client for dnd5eapi.co
  tools.py     → Tool definitions + handlers
  resources.py → Resource definitions + handlers
  prompts.py   → Prompt templates

Each module registers handlers with the MCP Server object.
This file just imports them and runs the event loop.

MCP = Model Context Protocol — standard for AI ↔ tool communication.
"""

import asyncio
import logging

import mcp.server.stdio
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    PromptsCapability,
    ResourcesCapability,
    ServerCapabilities,
    ToolsCapability,
)

from vecna import api, prompts, resources, tools

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

server = Server("vecna")


# ---------------------------------------------------------------------------
# Wire MCP handlers from modules
# ---------------------------------------------------------------------------

# ---- Tools ----

@server.list_tools()
async def handle_list_tools():
    return tools.get_tool_definitions()


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    return await tools.handle_call_tool(name, arguments)


# ---- Resources ----

@server.list_resources()
async def handle_list_resources():
    return await resources.list_resources()


@server.read_resource()
async def handle_read_resource(uri: str):
    return await resources.read_resource(uri)


# ---- Prompts ----

@server.list_prompts()
async def handle_list_prompts():
    return await prompts.list_prompts()


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None):
    return await prompts.get_prompt(name, arguments)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """
    Start the MCP server.

    stdio_server() gives two streams:
      - read_stream:  AI sends requests here
      - write_stream: we send responses back

    server.run() connects those streams to the handlers above.
    """
    logger.info("VECNA server starting...")

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
            InitializationOptions(
                server_name="vecna",
                server_version="0.1.1",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(),
                    resources=ResourcesCapability(),
                    prompts=PromptsCapability(),
                ),
            ),
            )
    finally:
        await api.close()
        logger.info("VECNA server shut down.")


if __name__ == "__main__":
    asyncio.run(main())
