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

    Exposes:
      POST/GET /mcp  — MCP Streamable HTTP transport (for AI clients)
      GET /api/...   — REST JSON endpoints (for the browser frontend)
      GET /api/health

    Configure via env vars:
      VECNA_HOST (default 0.0.0.0)
      VECNA_PORT (default 8000)
    """
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    # Render (and most PaaS) inject $PORT; honor it, then VECNA_PORT, then default.
    host = os.environ.get("VECNA_HOST", "0.0.0.0")
    port = int(os.environ.get("VECNA_PORT") or os.environ.get("PORT") or "8000")

    session_manager = StreamableHTTPSessionManager(app=server, stateless=True)

    # ── REST helpers ─────────────────────────────────────────────────────

    _LIST_FNS = {
        "monsters": api.list_monsters,
        "spells":   api.list_spells,
        "classes":  api.list_classes,
    }
    _GET_FNS = {
        "monsters": api.get_monster,
        "spells":   api.get_spell,
        "classes":  api.get_class,
    }

    async def rest_health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": "vecna"})

    async def rest_list(request: Request) -> JSONResponse:
        endpoint = request.path_params["endpoint"]
        fn = _LIST_FNS.get(endpoint)
        if not fn:
            return JSONResponse({"error": f"Unknown endpoint: {endpoint}"}, status_code=404)
        q = request.query_params.get("q")
        try:
            if q:
                results = await api.search(endpoint, q)
            else:
                results = await fn()
            return JSONResponse({"results": results})
        except Exception as exc:
            logger.exception("REST list error for %s", endpoint)
            return JSONResponse({"error": str(exc)}, status_code=500)

    async def rest_get(request: Request) -> JSONResponse:
        endpoint = request.path_params["endpoint"]
        index    = request.path_params["index"]
        fn = _GET_FNS.get(endpoint)
        if not fn:
            return JSONResponse({"error": f"Unknown endpoint: {endpoint}"}, status_code=404)
        try:
            data = await fn(index)
            return JSONResponse(data)
        except Exception as exc:
            logger.exception("REST get error for %s/%s", endpoint, index)
            return JSONResponse({"error": str(exc)}, status_code=500)

    # ── Lifespan ──────────────────────────────────────────────────────────

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette):
        logger.info("VECNA server starting (http transport) on %s:%s ...", host, port)
        async with session_manager.run():
            try:
                yield
            finally:
                await api.close()
                logger.info("VECNA server shut down.")

    # ── Starlette app ─────────────────────────────────────────────────────

    app = Starlette(
        routes=[
            Mount("/mcp", app=session_manager.handle_request),
            Route("/api/health",              rest_health),
            Route("/api/{endpoint}",          rest_list),
            Route("/api/{endpoint}/{index}",  rest_get),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*", "null"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    logger.info("REST API available at http://%s:%s/api/", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    if os.environ.get("VECNA_TRANSPORT", "stdio").lower() == "http":
        run_http()
    else:
        asyncio.run(run_stdio())
