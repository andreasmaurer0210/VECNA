"""
VECNA — MCP server for D&D 5e SRD data.

Modules:
  api.py       HTTP client for dnd5eapi.co
  tools.py     MCP tool handlers
  resources.py MCP resource handlers
  prompts.py   MCP prompt templates
  server.py    Entry point (main())
"""

from vecna.server import main

__all__ = ["main"]
