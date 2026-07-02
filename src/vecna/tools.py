"""
MCP tool handlers for VECNA.

Each tool is:
1. A Tool definition (name, description, inputSchema) returned by list_tools()
2. A handler function called by call_tool()

Handlers call api.py functions — no direct HTTP.
"""

import logging

import mcp.types as types

from vecna import api

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def get_tool_definitions() -> list[types.Tool]:
    """Return all tool definitions the server advertises."""
    return [
        # ---- Monster tools ----
        types.Tool(
            name="get_monster",
            description="Get full stats for a D&D monster by name index (e.g. 'adult-red-dragon', 'goblin')",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "string",
                        "description": "Monster index (kebab-case). Use search_monsters to find the right index.",
                    },
                },
                "required": ["index"],
            },
        ),
        types.Tool(
            name="search_monsters",
            description="Search monsters by name keyword. Returns list of matching monsters with name and index.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Name keyword to search for (e.g. 'dragon', 'goblin', 'lich')",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="list_monsters",
            description="List all available monsters in the SRD (334 entries). Returns names and indices.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # ---- Spell tools ----
        types.Tool(
            name="get_spell",
            description="Get full details for a D&D spell by index (e.g. 'fireball', 'magic-missile')",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "string",
                        "description": "Spell index (kebab-case). Use search_spells to find the right index.",
                    },
                },
                "required": ["index"],
            },
        ),
        types.Tool(
            name="search_spells",
            description="Search spells by name keyword. Returns matching spells with name, level, and index.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Name keyword to search for (e.g. 'fire', 'heal', 'fear')",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="list_spells",
            description="List all available spells in the SRD (319 entries). Returns names, levels, and indices.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # ---- Class tools ----
        types.Tool(
            name="get_class",
            description="Get full details for a D&D class by index (e.g. 'fighter', 'wizard', 'paladin')",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "string",
                        "description": "Class index (e.g. 'fighter', 'wizard', 'rogue')",
                    },
                },
                "required": ["index"],
            },
        ),
        types.Tool(
            name="list_classes",
            description="List all available classes (12 total: Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # ---- Other ----
        types.Tool(
            name="roll_dice",
            description="Roll dice in NdN format, e.g. '2d6' = roll two 6-sided dice, '1d20+5' = d20 with +5 modifier",
            inputSchema={
                "type": "object",
                "properties": {
                    "dice_expr": {
                        "type": "string",
                        "description": "Dice expression like '3d8', '1d20', or '2d6+3'",
                    },
                },
                "required": ["dice_expr"],
            },
        ),
    ]


async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Dispatch a tool call to the correct handler.

    The TOOL_HANDLERS dict is built lazily inside this function
    so it can reference handler functions defined below.
    """
    # fmt: off
    handlers: dict[str, callable] = {
        "get_monster": _handle_get_monster,
        "search_monsters": _handle_search_monsters,
        "list_monsters": _handle_list_monsters,
        "get_spell": _handle_get_spell,
        "search_spells": _handle_search_spells,
        "list_spells": _handle_list_spells,
        "get_class": _handle_get_class,
        "list_classes": _handle_list_classes,
        "roll_dice": _handle_roll_dice,
    }
    # fmt: on
    handler = handlers.get(name)
    if handler is None:
        raise ValueError(f"Unknown tool: {name}")
    return await handler(arguments)


# ---------------------------------------------------------------------------
# Handler implementations
# ---------------------------------------------------------------------------

async def _handle_get_monster(args: dict | None) -> list[types.TextContent]:
    if not args or "index" not in args:
        raise ValueError("Missing required argument: 'index'")

    data = await api.get_monster(args["index"])

    # Format a readable stat block
    ac = data.get("armor_class", [{}])
    ac_str = ", ".join(f"{a.get('value', '?')} ({a.get('type', '')})" for a in ac) if isinstance(ac, list) else str(ac)

    speed_str = ", ".join(f"{k} {v}" for k, v in data.get("speed", {}).items())

    lines = [
        f"**{data['name']}**",
        f"{data.get('size', '?')} {data.get('type', '?')}, {data.get('alignment', '?')}",
        f"AC: {ac_str}",
        f"HP: {data.get('hit_points', '?')} ({data.get('hit_dice', '')})",
        f"Speed: {speed_str}",
        "",
        f"STR {data.get('strength', '?')}  DEX {data.get('dexterity', '?')}  CON {data.get('constitution', '?')}",
        f"INT {data.get('intelligence', '?')}  WIS {data.get('wisdom', '?')}  CHA {data.get('charisma', '?')}",
        "",
        f"CR: {data.get('challenge_rating', '?')}  XP: {data.get('xp', '?')}  Prof. Bonus: {data.get('proficiency_bonus', '?')}",
    ]

    if data.get("damage_immunities"):
        lines.append(f"Damage Immunities: {', '.join(data['damage_immunities'])}")
    if data.get("damage_resistances"):
        lines.append(f"Damage Resistances: {', '.join(data['damage_resistances'])}")
    if data.get("damage_vulnerabilities"):
        lines.append(f"Damage Vulnerabilities: {', '.join(data['damage_vulnerabilities'])}")
    if data.get("condition_immunities"):
        lines.append(f"Condition Immunities: {', '.join(data['condition_immunities'])}")
    if data.get("senses"):
        senses_str = ", ".join(f"{k} {v}" for k, v in data["senses"].items())
        lines.append(f"Senses: {senses_str}")
    if data.get("languages"):
        lines.append(f"Languages: {data['languages']}")

    if data.get("special_abilities"):
        lines.append("")
        lines.append("**Special Abilities:**")
        for ab in data["special_abilities"]:
            lines.append(f"  • {ab['name']}: {ab.get('desc', '')[:200]}")

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_search_monsters(args: dict | None) -> list[types.TextContent]:
    if not args or "query" not in args:
        raise ValueError("Missing required argument: 'query'")
    results = await api.search("monsters", args["query"])
    if not results:
        return [types.TextContent(type="text", text=f"No monsters found matching '{args['query']}'.")]

    lines = [f"Found {len(results)} monster(s) matching '{args['query']}':", ""]
    for r in results:
        lines.append(f"  • **{r['name']}** — index: `{r['index']}`")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_list_monsters(args: dict | None) -> list[types.TextContent]:
    results = await api.list_monsters()
    lines = [f"**All Monsters ({len(results)} total)**", ""]
    for r in results:
        lines.append(f"  • `{r['index']}` — {r['name']}")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_get_spell(args: dict | None) -> list[types.TextContent]:
    if not args or "index" not in args:
        raise ValueError("Missing required argument: 'index'")

    data = await api.get_spell(args["index"])

    school = data.get("school", {}).get("name", "?")
    classes_str = ", ".join(c["name"] for c in data.get("classes", []))
    components = ", ".join(data.get("components", []))
    material = data.get("material", "")
    if material:
        components += f" ({material})"

    desc = " ".join(data.get("desc", []))
    higher = data.get("higher_level", [])
    higher_str = " ".join(higher) if higher else ""

    damage_info = ""
    if data.get("damage"):
        dmg = data["damage"]
        slot_dmg = dmg.get("damage_at_slot_level", {})
        if slot_dmg:
            damage_info = f"\nDamage: {', '.join(f'slot {k}: {v}' for k, v in slot_dmg.items())}"

    aoe = ""
    if data.get("area_of_effect"):
        aoe_info = data["area_of_effect"]
        aoe = f"\nArea: {aoe_info.get('size', '?')}-ft {aoe_info.get('type', '?')}"

    lines = [
        f"**{data['name']}**",
        f"Level {data.get('level', '?')} {school}",
        f"Casting Time: {data.get('casting_time', '?')}  Range: {data.get('range', '?')}",
        f"Components: {components}  Duration: {data.get('duration', '?')}",
        f"Concentration: {data.get('concentration', False)}  Ritual: {data.get('ritual', False)}",
        f"Classes: {classes_str}",
        "",
        desc,
    ]
    if higher_str:
        lines.extend(["", "**At Higher Levels:**", higher_str])
    if damage_info:
        lines.append(damage_info)
    if aoe:
        lines.append(aoe)

    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_search_spells(args: dict | None) -> list[types.TextContent]:
    if not args or "query" not in args:
        raise ValueError("Missing required argument: 'query'")
    results = await api.search("spells", args["query"])
    if not results:
        return [types.TextContent(type="text", text=f"No spells found matching '{args['query']}'.")]

    lines = [f"Found {len(results)} spell(s) matching '{args['query']}':", ""]
    for r in results:
        level_label = "Cantrip" if r.get("level") == 0 else f"Level {r['level']}"
        lines.append(f"  • **{r['name']}** ({level_label}) — index: `{r['index']}`")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_list_spells(args: dict | None) -> list[types.TextContent]:
    results = await api.list_spells()
    lines = [f"**All Spells ({len(results)} total)**", ""]
    for r in results:
        level_label = "Cantrip" if r.get("level") == 0 else f"Lvl {r['level']}"
        lines.append(f"  • `{r['index']}` — {r['name']} ({level_label})")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_get_class(args: dict | None) -> list[types.TextContent]:
    if not args or "index" not in args:
        raise ValueError("Missing required argument: 'index'")

    data = await api.get_class(args["index"])

    saves = ", ".join(s["name"] for s in data.get("saving_throws", []))
    profs = [p["name"] for p in data.get("proficiencies", [])]
    subclasses = ", ".join(s["name"] for s in data.get("subclasses", []))

    lines = [
        f"**{data['name']}**",
        f"Hit Die: d{data.get('hit_die', '?')}",
        f"Saving Throws: {saves}",
        f"Proficiencies: {', '.join(profs)}",
        f"Subclasses: {subclasses}",
        "",
        "**Starting Equipment:** (choose from options — see class page for details)",
    ]
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_list_classes(args: dict | None) -> list[types.TextContent]:
    results = await api.list_classes()
    lines = ["**All Classes**", ""]
    for r in results:
        lines.append(f"  • `{r['index']}` — {r['name']}")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _handle_roll_dice(args: dict | None) -> list[types.TextContent]:
    """Roll dice from a string like '2d6' or '1d20+5'."""
    if not args or "dice_expr" not in args:
        raise ValueError("Missing required argument: 'dice_expr'")

    import random
    expr: str = args["dice_expr"]

    modifier = 0
    if "+" in expr:
        expr, mod_str = expr.split("+", 1)
        modifier = int(mod_str.strip())
    elif "-" in expr and expr.index("-") > 0:
        expr, mod_str = expr.split("-", 1)
        modifier = -int(mod_str.strip())

    if "d" not in expr:
        raise ValueError("Dice expression must contain 'd' (e.g. '2d6')")

    parts = expr.split("d")
    count = int(parts[0]) if parts[0] else 1
    sides = int(parts[1])

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    detail = " + ".join(str(r) for r in rolls)
    if modifier:
        detail += f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}"

    text = f"[dice] {expr} -> [{detail}] = **{total}**"
    return [types.TextContent(type="text", text=text)]
