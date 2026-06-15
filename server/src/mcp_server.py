"""RPG game-mechanics MCP server (streamable-HTTP). Agora cloud calls these tools
when the Dungeon Master LLM resolves an action. Each tool is self-contained — one
call resolves a whole action (dice rolled internally inside game.py)."""
import os

from mcp.server.fastmcp import FastMCP

import game

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
mcp = FastMCP("recipe-agent-rpg", host="0.0.0.0", port=MCP_PORT)


def _run(fn, *args) -> str:
    conn = game.get_db()
    try:
        result = fn(conn, *args)
    finally:
        conn.close()
    print(f"[MCP TOOL] {fn.__name__}{args} -> {result}", flush=True)
    return result


@mcp.tool()
def create_character(char_class: str) -> str:
    """Create the player's hero (also starts a NEW game, resetting progress).
    char_class must be one of: warrior, mage, rogue, cleric. Call this when the
    player chooses or changes their class."""
    return _run(game.create_character, char_class)


@mcp.tool()
def get_character() -> str:
    """Return the hero's class, HP, gold, inventory, and current mode. Call this
    when the player asks about their character, stats, or inventory."""
    return _run(game.get_character)


@mcp.tool()
def start_encounter() -> str:
    """Begin a combat encounter with a random enemy. Call this when the player
    goes looking for a fight or the story leads into danger."""
    return _run(game.start_encounter)


@mcp.tool()
def attack() -> str:
    """Resolve one attack against the current enemy (rolls dice, applies damage,
    enemy counterattacks, handles defeat + loot). Call this when the player attacks."""
    return _run(game.attack)


@mcp.tool()
def cast_spell(name: str) -> str:
    """Cast the hero's class spell at the current enemy (rolls dice, resolves the
    exchange). Call this when the player casts a spell. `name` is the spell name."""
    return _run(game.cast_spell, name)


@mcp.tool()
def flee() -> str:
    """Flee the current combat back to exploration. Call this when the player runs."""
    return _run(game.flee)


if __name__ == "__main__":
    print(f"Starting RPG MCP server (streamable-http) on :{MCP_PORT}/mcp", flush=True)
    mcp.run(transport="streamable-http")
