"""
MCP resource handlers for VECNA.

Resources are data the AI can READ (like files).
VECNA exposes D&D SRD data under URI scheme `dnd://`.

URI patterns:
  dnd://monsters/{index}  → monster data as JSON
  dnd://spells/{index}    → spell data as JSON
"""

import json
import logging
import re

import mcp.types as types

from vecna import api

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# URI routing
# ---------------------------------------------------------------------------
# Match URIs like:
#   dnd://monsters/adult-red-dragon
#   dnd://spells/fireball

MONSTER_RE = re.compile(r"^dnd://monsters/(.+)$")
SPELL_RE = re.compile(r"^dnd://spells/(.+)$")


async def list_resources() -> list[types.Resource]:
    """
    Called when the AI asks 'what data do you have?'
    We dynamically build the list from the API — no hard-coded items.
    """
    resources: list[types.Resource] = []

    # Add monster resources (limit to first 50 to keep listing reasonable)
    monsters = await api.list_monsters()
    for m in monsters[:50]:
        resources.append(
            types.Resource(
                uri=f"dnd://monsters/{m['index']}",
                name=f"{m['name']} — Monster",
                description=f"Full stat block for {m['name']}",
                mimeType="application/json",
            )
        )

    # Add spell resources
    spells = await api.list_spells()
    for s in spells[:50]:
        label = "Cantrip" if s.get("level") == 0 else f"Level {s['level']}"
        resources.append(
            types.Resource(
                uri=f"dnd://spells/{s['index']}",
                name=f"{s['name']} — {label}",
                description=f"Full details for {s['name']}",
                mimeType="application/json",
            )
        )

    return resources


async def read_resource(uri: str) -> str:
    """
    Called when the AI wants to READ a resource.
    `uri` tells us which data to fetch from the API.

    Note: MCP SDK may pass uri as pydantic AnyUrl — convert to str.
    """
    uri_str = str(uri)

    m = MONSTER_RE.match(uri_str)
    if m:
        data = await api.get_monster(m.group(1))
        return json.dumps(data, indent=2)

    m = SPELL_RE.match(uri_str)
    if m:
        data = await api.get_spell(m.group(1))
        return json.dumps(data, indent=2)

    raise ValueError(f"Unknown resource URI: {uri_str}")
