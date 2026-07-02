# VECNA

**V**ault **E**xtensible **C**omputational **N**exus for **A**dventurers

A Python MCP server that provides D&D Beyond character data to AI assistants.

## What is this?

VECNA is an **MCP server**. MCP = Model Context Protocol — an open standard
that lets AI assistants (Claude, OpenCode, etc.) call functions and read data
from external tools, like a USB-C port for AI.

VECNA exposes:
- **Tools** — functions the AI can call (look up characters, roll dice)
- **Resources** — data the AI can read (character sheets as JSON)
- **Prompts** — templates the AI can load (character creation guide)

## Quick start

```bash
# Install dependencies
uv sync

# Run the server (stdio mode — used by AI clients)
uv run vecna
```

## Project structure

```
VECNA/
├── pyproject.toml        # Python project config + dependencies
├── README.md             # This file
├── .gitignore            # Files Git should ignore
└── src/
    └── vecna/
        ├── __init__.py   # Makes "vecna" a Python package
        └── server.py     # The MCP server code (tools, resources, prompts)
```

## Adding a new tool

1. Add a `types.Tool(...)` entry in `handle_list_tools()`
2. Add an `if name == "your_tool":` branch in `handle_call_tool()`
3. Write a handler function (like `_get_character`)

## License

MIT
