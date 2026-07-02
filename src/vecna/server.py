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
import contextlib
import logging
import os

import mcp.server.stdio
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
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

INIT_OPTIONS = InitializationOptions(
    server_name="vecna",
    server_version="0.1.1",
    capabilities=ServerCapabilities(
        tools=ToolsCapability(),
        resources=ResourcesCapability(),
        prompts=PromptsCapability(),
    ),
)


async def run_stdio() -> None:
    """
    Start the MCP server over stdio.

    stdio_server() gives two streams:
      - read_stream:  AI sends requests here
      - write_stream: we send responses back

    server.run() connects those streams to the handlers above.
    """
    logger.info("VECNA server starting (stdio transport)...")

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, INIT_OPTIONS)
    finally:
        await api.close()
        logger.info("VECNA server shut down.")


def run_http() -> None:
    """
    Start the MCP server over Streamable HTTP.

    Exposes the MCP endpoint at POST/GET /mcp on the given host/port.
    Configure via env vars:
      VECNA_HOST (default 0.0.0.0)
      VECNA_PORT (default 8000)
    """
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Mount

    host = os.environ.get("VECNA_HOST", "0.0.0.0")
    port = int(os.environ.get("VECNA_PORT", "8000"))

    session_manager = StreamableHTTPSessionManager(app=server, stateless=True)

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette):
        logger.info("VECNA server starting (http transport) on %s:%s ...", host, port)
        async with session_manager.run():
            try:
                yield
            finally:
                await api.close()
                logger.info("VECNA server shut down.")

    app = Starlette(
        routes=[Mount("/mcp", app=session_manager.handle_request)],
        lifespan=lifespan,
    )

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    if os.environ.get("VECNA_TRANSPORT", "stdio").lower() == "http":
        run_http()
    else:
        asyncio.run(run_stdio())
