"""
VECNA — Model Context Protocol (MCP) server.

What this file does:
An MCP server is a program that lets AI assistants (like Claude or OpenCode)
run functions ("tools") and read data ("resources") on demand.
This server exposes D&D Beyond character data to AI assistants.

MCP = Model Context Protocol — a standard for AI ↔ tool communication.
Think of it as "USB-C for AI": one plug that connects AI to any tool.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
# Libraries are pre-written code you can borrow. Python puts them in
# "modules" (files) and "packages" (folders of modules).
import asyncio          # Python's async I/O — lets multiple things wait at once
import logging          # Prints timestamped messages for debugging
from dataclasses import dataclass  # Shortcut to make simple data containers

import httpx                     # For making HTTP requests (fetch web pages)
import mcp.server.stdio          # MCP's stdio transport (reads/writes over stdin/stdout)
import mcp.types as types        # MCP type definitions (Tool, Resource, etc.)
from mcp.server import Server    # The main MCP server class
from mcp.server.models import InitializationOptions  # Server identity sent to client


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
# logging prints messages so you can see what the server is doing.
# %(levelname)s = INFO / WARN / ERROR, %(message)s = the actual message.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data store
# ---------------------------------------------------------------------------
# A simple in-memory "database". In a real app this would be a real database
# or an API call. For now it's just a Python dictionary.
# key = character name (str), value = Character object.
characters: dict[str, "Character"] = {}


@dataclass
class Character:
    """
    Holds one D&D character's stats.

    @dataclass auto-generates __init__, __repr__, and __eq__ so we don't
    have to write boilerplate like:
        def __init__(self, name, level, ...):
            self.name = name
            ...
    """
    name: str
    level: int
    class_name: str
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


# Seed some example data so the server isn't empty on first run.
characters["Ardeus Solis"] = Character(
    name="Ardeus Solis",
    level=5,
    class_name="Paladin",
    strength=15, dexterity=10, constitution=14,
    intelligence=8, wisdom=10, charisma=16,
)


# ---------------------------------------------------------------------------
# MCP primitives — what the server can do
# ---------------------------------------------------------------------------
# MCP has 3 core concepts:
#   Tools   — functions the AI can CALL (e.g. "roll a dice")
#   Resources — data the AI can READ (e.g. "show me a character sheet")
#   Prompts — templates the AI can USE (e.g. "generate a new character")

# Create the server instance. The name "vecna" identifies it to the client.
server = Server("vecna")


# ---- Tools ----------------------------------------------------------------
# Tools = actions the AI assistant can trigger.
# The AI decides when to call a tool based on the user's request.

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Called when the AI asks "what tools do you have?"
    We return a list of Tool objects describing each tool's name, purpose,
    and what arguments it expects (its "input schema").

    The input schema uses JSON Schema — a standard way to describe JSON data.
    { "type": "object" } means the argument is a JSON object/dict.
    "properties" lists each argument's name, type, and description.
    "required" lists which arguments the AI MUST provide.
    """
    return [
        types.Tool(
            name="get_character",
            description="Look up a D&D character by name and return their stats",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The character's full name",
                    },
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="roll_dice",
            description="Roll dice in NdN format, e.g. '2d6' = roll two 6-sided dice",
            inputSchema={
                "type": "object",
                "properties": {
                    "dice_expr": {
                        "type": "string",
                        "description": "Dice expression like '3d8' or '1d20+5'",
                    },
                },
                "required": ["dice_expr"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """
    Called when the AI WANTS TO USE a tool.
    `name` tells us which tool, `arguments` has the values the AI provided.

    We must return a list of TextContent objects (the "answer").
    MCP supports other content types too (images, embedded resources),
    but text is the simplest.
    """
    if name == "get_character":
        return await _get_character(arguments)
    elif name == "roll_dice":
        return await _roll_dice(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _get_character(arguments: dict | None) -> list[types.TextContent]:
    """Look up a character in our in-memory store."""
    if not arguments or "name" not in arguments:
        raise ValueError("Missing required argument: 'name'")

    char_name: str = arguments["name"]
    char = characters.get(char_name)

    if char is None:
        return [types.TextContent(
            type="text",
            text=f"Character '{char_name}' not found. Known characters: {list(characters.keys())}",
        )]

    # Format the character data as readable text.
    text = (
        f"**{char.name}** — Level {char.level} {char.class_name}\n\n"
        f"STR {char.strength}  DEX {char.dexterity}  CON {char.constitution}\n"
        f"INT {char.intelligence}  WIS {char.wisdom}  CHA {char.charisma}"
    )
    return [types.TextContent(type="text", text=text)]


async def _roll_dice(arguments: dict | None) -> list[types.TextContent]:
    """
    Roll dice from a string like "2d6" or "1d20+5".

    This is intentionally NOT using roll20 or any API — just Python's random
    module to show how tools run real code.

    NdN format:
        "2d6"  → roll 2 six-sided dice, sum the results
        "1d20" → roll 1 twenty-sided die
    """
    if not arguments or "dice_expr" not in arguments:
        raise ValueError("Missing required argument: 'dice_expr'")

    import random
    expr: str = arguments["dice_expr"]

    # Parse "2d6+3" into count=2, sides=6, modifier=3
    # This is a simplified parser — it works for basic cases.
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

    # Roll each die
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier

    result_parts = [str(r) for r in rolls]
    detail = " + ".join(result_parts)
    if modifier:
        detail += f" + {modifier}" if modifier > 0 else f" - {abs(modifier)}"

    text = f"🎲 {expr} → [{detail}] = **{total}**"
    return [types.TextContent(type="text", text=text)]


# ---- Resources ------------------------------------------------------------
# Resources = data the AI can READ (like files on a hard drive).
# Each resource has a URI (unique address) and a MIME type (what format).

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    Called when the AI asks "what data do you have?"
    We return a Resource for each character in our store.
    """
    resources: list[types.Resource] = []
    for name in characters:
        resources.append(
            types.Resource(
                uri=f"character://{name.lower().replace(' ', '_')}/stats",
                name=f"{name} — Stats",
                description=f"Ability scores for {name}",
                mimeType="application/json",
            )
        )
    return resources


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """
    Called when the AI wants to READ a resource's content.
    `uri` is the resource address (e.g. "character://ardeus_solis/stats").
    We return the data as a string.
    """
    # Convert URI back to a character name
    # "character://ardeus_solis/stats" → "Ardeus Solis"
    path = uri.replace("character://", "").replace("/stats", "")
    name = path.replace("_", " ").title()

    char = characters.get(name)
    if char is None:
        return f'{{"error": "Character not found: {name}"}}'

    return (
        '{\n'
        f'  "name": "{char.name}",\n'
        f'  "level": {char.level},\n'
        f'  "class": "{char.class_name}",\n'
        f'  "strength": {char.strength},\n'
        f'  "dexterity": {char.dexterity},\n'
        f'  "constitution": {char.constitution},\n'
        f'  "intelligence": {char.intelligence},\n'
        f'  "wisdom": {char.wisdom},\n'
        f'  "charisma": {char.charisma}\n'
        '}'
    )


# ---- Prompts --------------------------------------------------------------
# Prompts = pre-written templates the AI can load to help with a task.

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="create_character",
            description="Guide for creating a new D&D character",
            arguments=[
                types.PromptArgument(
                    name="class_name",
                    description="Character class (Fighter, Wizard, Paladin, etc.)",
                    required=False,
                ),
            ],
        ),
    ]


@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name == "create_character":
        return _prompt_create_character(arguments)
    raise ValueError(f"Unknown prompt: {name}")


def _prompt_create_character(
    arguments: dict[str, str] | None,
) -> types.GetPromptResult:
    """Return a prompt template for character creation."""
    class_name = (arguments or {}).get("class_name", "Fighter")
    return types.GetPromptResult(
        description=f"Create a new {class_name} character",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=(
                        f"I want to create a new level 1 {class_name} character.\n"
                        "Help me choose:\n"
                        "1. A name\n"
                        "2. Ability scores (point buy or standard array?)\n"
                        "3. A background\n"
                        "4. Equipment\n"
                        "5. Personality traits\n"
                    ),
                ),
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
# "Entry point" = the function that runs when you start the program.
# async = this function can pause and let other tasks run while waiting
# (e.g. waiting for the AI to send a request).

async def main() -> None:
    """
    Start the MCP server.

    stdio_server() gives us two streams:
      - read_stream:  where the AI sends us requests
      - write_stream: where we send back responses

    server.run() connects those streams to our handler functions above.
    """
    logger.info("VECNA server starting...")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="vecna",
                server_version="0.1.0",
            ),
        )


# This guard ensures main() only runs when this file is executed directly
# (python server.py), not when imported as a module (from server import ...).
if __name__ == "__main__":
    asyncio.run(main())
