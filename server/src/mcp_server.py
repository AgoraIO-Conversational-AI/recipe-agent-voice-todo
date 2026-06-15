"""Todo-board MCP server (streamable-HTTP). Agora cloud calls these tools when the
assistant LLM acts on the board. Each tool is self-contained — one call performs a
whole board mutation and returns the post-mutation snapshot, so the recipe never
depends on the LLM chaining tool calls."""
import os

from mcp.server.fastmcp import FastMCP

import board

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
mcp = FastMCP("recipe-agent-voice-todo", host="0.0.0.0", port=MCP_PORT)


def _run(fn, *args) -> str:
    conn = board.get_db()
    try:
        result = fn(conn, *args)
    finally:
        conn.close()
    print(f"[MCP TOOL] {fn.__name__}{args} -> {result}", flush=True)
    return result


@mcp.tool()
def add_task(title: str) -> str:
    """Add a new task to the To Do column. `title` is the task text the user said.
    Call this when the user wants to create or add a task."""
    return _run(board.add_task, title)


@mcp.tool()
def move_task(title: str, column: str) -> str:
    """Move a task to a column. `title` is roughly what the user called the task
    (fuzzy-matched). `column` must be one of: 'to do', 'in progress', 'done'. Use
    this whenever the user wants to move, start, or finish a task — e.g. 'mark the
    milk done' -> move_task('milk', 'done')."""
    return _run(board.move_task, title, column)


@mcp.tool()
def delete_task(title: str) -> str:
    """Delete a task from the board. `title` is roughly what the user called it.
    Call this when the user wants to remove, delete, or drop a task."""
    return _run(board.delete_task, title)


@mcp.tool()
def list_tasks() -> str:
    """Return the whole board (all tasks grouped by column). Call this only when
    the user explicitly asks what's on the board or to list their tasks."""
    return _run(board.list_tasks)


if __name__ == "__main__":
    print(f"Starting Todo MCP server (streamable-http) on :{MCP_PORT}/mcp", flush=True)
    mcp.run(transport="streamable-http")
