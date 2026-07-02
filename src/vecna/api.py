"""
HTTP client for the D&D 5e SRD API (https://www.dnd5eapi.co).

Uses sync httpx.Client running in a thread via anyio.to_thread.run_sync.
This avoids event loop conflicts between anyio (MCP SDK) and asyncio (httpx).

API base: https://www.dnd5eapi.co/api/2014/
Endpoints: monsters, spells, classes, ability-scores, equipment, etc.
"""

import logging
from typing import Any

import anyio
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.dnd5eapi.co"
API_PREFIX = "/api/2014"

# Shared sync client (thread-safe for basic GET usage)
_client: httpx.Client | None = None
_lock: anyio.Lock | None = None


def _get_sync_client() -> httpx.Client:
    """Get or create the shared sync HTTP client (called in thread)."""
    global _client
    if _client is None:
        _client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    return _client


async def _ensure_lock() -> anyio.Lock:
    global _lock
    if _lock is None:
        _lock = anyio.Lock()
    return _lock


async def close() -> None:
    """Shut down the HTTP client."""
    global _client
    lock = await _ensure_lock()
    async with lock:
        if _client is not None:
            _client.close()
            _client = None


def _fetch_sync(path: str) -> dict[str, Any]:
    """Sync GET request (runs in thread, not on asyncio loop)."""
    client = _get_sync_client()
    url = f"{API_PREFIX}{path}"
    logger.debug("GET %s", url)
    resp = client.get(url)
    resp.raise_for_status()
    return resp.json()


async def _fetch(path: str) -> dict[str, Any]:
    """Run sync HTTP request in a thread to keep event loop free."""
    lock = await _ensure_lock()
    async with lock:
        try:
            return await anyio.to_thread.run_sync(_fetch_sync, path)
        except httpx.HTTPStatusError as e:
            raise DndApiError(f"API returned {e.response.status_code} for {API_PREFIX}{path}") from e
        except httpx.RequestError as e:
            raise DndApiError(f"Network error fetching {path}: {e}") from e


async def _fetch_list(endpoint: str) -> list[dict[str, Any]]:
    data = await _fetch(endpoint)
    return data.get("results", [])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def list_monsters() -> list[dict[str, Any]]:
    return await _fetch_list("/monsters")


async def get_monster(index: str) -> dict[str, Any]:
    return await _fetch(f"/monsters/{index}")


async def list_spells() -> list[dict[str, Any]]:
    return await _fetch_list("/spells")


async def get_spell(index: str) -> dict[str, Any]:
    return await _fetch(f"/spells/{index}")


async def list_classes() -> list[dict[str, Any]]:
    return await _fetch_list("/classes")


async def get_class(index: str) -> dict[str, Any]:
    return await _fetch(f"/classes/{index}")


async def get_ability_score(index: str) -> dict[str, Any]:
    return await _fetch(f"/ability-scores/{index}")


async def search(endpoint: str, query: str) -> list[dict[str, Any]]:
    items = await _fetch_list(f"/{endpoint}")
    q = query.lower()
    return [item for item in items if q in item["name"].lower()]


# ---------------------------------------------------------------------------
# Custom error
# ---------------------------------------------------------------------------

class DndApiError(Exception):
    """Raised when the D&D API request fails."""
