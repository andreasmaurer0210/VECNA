"""
HTTP client for the D&D 5e SRD API (https://www.dnd5eapi.co).

This module handles all communication with the external API.
Other modules (tools.py, resources.py) call these functions —
they never make HTTP requests directly.

API base: https://www.dnd5eapi.co/api/2014/
Endpoints: monsters, spells, classes, ability-scores, equipment, etc.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.dnd5eapi.co"
API_PREFIX = "/api/2014"


# ---------------------------------------------------------------------------
# Shared HTTP client
# ---------------------------------------------------------------------------
# httpx.AsyncClient reuses connections (faster than creating a new one
# per request). We create it once and share it.
_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
    return _client


async def close() -> None:
    """Shut down the HTTP client (call on server shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# ---------------------------------------------------------------------------
# Raw fetch helpers
# ---------------------------------------------------------------------------

async def _fetch(path: str) -> dict[str, Any]:
    """
    GET a JSON resource from the D&D API.

    Raises DndApiError on failure (non-200, network error, bad JSON).
    """
    client = await _get_client()
    url = f"{API_PREFIX}{path}"
    logger.debug("GET %s", url)

    try:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise DndApiError(f"API returned {e.response.status_code} for {url}") from e
    except httpx.RequestError as e:
        raise DndApiError(f"Network error fetching {url}: {e}") from e


async def _fetch_list(endpoint: str) -> list[dict[str, Any]]:
    """
    Fetch a list endpoint and return the `results` array.

    Example: _fetch_list("/monsters") returns
    [{"index": "adult-red-dragon", "name": "Adult Red Dragon", ...}, ...]
    """
    data = await _fetch(endpoint)
    return data.get("results", [])


# ---------------------------------------------------------------------------
# Public API — called by tools & resources
# ---------------------------------------------------------------------------

async def list_monsters() -> list[dict[str, Any]]:
    """Return all monster summaries: [{index, name, url}]."""
    return await _fetch_list("/monsters")


async def get_monster(index: str) -> dict[str, Any]:
    """Return full monster data by index (e.g. 'adult-red-dragon')."""
    return await _fetch(f"/monsters/{index}")


async def list_spells() -> list[dict[str, Any]]:
    """Return all spell summaries: [{index, name, level, url}]."""
    return await _fetch_list("/spells")


async def get_spell(index: str) -> dict[str, Any]:
    """Return full spell data by index (e.g. 'fireball')."""
    return await _fetch(f"/spells/{index}")


async def list_classes() -> list[dict[str, Any]]:
    """Return all class summaries: [{index, name, url}]."""
    return await _fetch_list("/classes")


async def get_class(index: str) -> dict[str, Any]:
    """Return full class data by index (e.g. 'fighter')."""
    return await _fetch(f"/classes/{index}")


async def get_ability_score(index: str) -> dict[str, Any]:
    """Return ability score by index ('str', 'dex', 'con', 'int', 'wis', 'cha')."""
    return await _fetch(f"/ability-scores/{index}")


async def search(
    endpoint: str, query: str
) -> list[dict[str, Any]]:
    """
    Search an endpoint list for items whose name contains `query` (case-insensitive).

    Example: search("monsters", "dragon") → all dragons.
    """
    items = await _fetch_list(f"/{endpoint}")
    q = query.lower()
    return [item for item in items if q in item["name"].lower()]


# ---------------------------------------------------------------------------
# Custom error
# ---------------------------------------------------------------------------

class DndApiError(Exception):
    """Raised when the D&D API request fails."""
