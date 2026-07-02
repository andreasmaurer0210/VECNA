"""
MCP prompt handlers for VECNA.

Prompts are templates the AI can load to help with a task.
"""

import mcp.types as types


async def list_prompts() -> list[types.Prompt]:
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


async def get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    if name == "create_character":
        return _prompt_create_character(arguments)
    raise ValueError(f"Unknown prompt: {name}")


def _prompt_create_character(
    arguments: dict[str, str] | None,
) -> types.GetPromptResult:
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
