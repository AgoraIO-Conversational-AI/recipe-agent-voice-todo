# Deep Dive — MCP Tools and Board Store

> **When to Read This:** You are adding, removing, or changing an MCP tool; swapping the SQLite board store for a different backing system; debugging why the assistant greets but never calls a tool; or understanding the wiring between Agora cloud, FastMCP, and `board.py`. For the high-level picture, start at [02_architecture](../02_architecture.md).

The voice todo board recipe wires together three layers: the Agora SDK agent (in `agent.py`), the FastMCP server (in `mcp_server.py`), and the pure board store (in `board.py`). They are intentionally decoupled so `board.py` can be tested in isolation.

## How Agora calls the tools

In `Agent.start()`, the `OpenAI` LLM vendor is built with:

```python
llm = OpenAI(
    api_key=self.openai_api_key,          # optional — Agora-managed when absent
    model=self.openai_model,              # OPENAI_MODEL, default gpt-4o-mini
    system_messages=[{"role": "system", "content": TODO_PROMPT}],
    mcp_servers=build_mcp_servers(self.mcp_endpoint),  # [{name, endpoint, transport}]
    greeting_message=self.greeting,
)
```

`build_mcp_servers(endpoint)` in `mcp_config.py` returns:

```python
[{"name": "todo", "endpoint": endpoint, "transport": "streamable_http"}]
```

Note: `"streamable_http"` (underscore) is the Agora SDK's convention. The FastMCP server uses `"streamable-http"` (hyphen) in its own transport — do not unify them.

When the todo assistant LLM decides to call a tool, Agora cloud issues a streamable-HTTP POST to `MCP_ENDPOINT` (the public tunnel URL). The FastMCP server, mounted in-process at `/mcp`, receives the request and calls the matching `@mcp.tool()` function.

## The 4 tool functions

```python
@mcp.tool()
def add_task(title: str) -> str: ...
    # Calls board.add_task(conn, title) via _run

@mcp.tool()
def move_task(title: str, column: str) -> str: ...
    # Calls board.move_task(conn, title, column) via _run

@mcp.tool()
def delete_task(title: str) -> str: ...
    # Calls board.delete_task(conn, title) via _run

@mcp.tool()
def list_tasks() -> str: ...
    # Calls board.list_tasks(conn) via _run
```

The `_run(fn, *args)` wrapper opens a DB connection, calls `fn(conn, *args)`, closes the connection, and prints a debug log. This pattern means each tool call has its own DB lifecycle — safe for SQLite's check-same-thread model.

**Tool docstrings are load-bearing.** Agora's managed LLM reads the docstring when deciding which tool to call. Keep them accurate and concise.

## Board store design (`board.py`)

`board.py` has **no MCP or `agora_agent` imports** — it is a pure SQLite store. This means all 14+ board unit tests run without any network or cloud dependency.

### Schema

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL,       -- 'todo' | 'in_progress' | 'done'
    created_at REAL NOT NULL
);
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
```

`meta` records whether seed tasks have been inserted (`key='seeded'`). Seeding happens exactly once at first `get_db()` — deleting all tasks does not re-seed on the next connection.

### Fuzzy title matching (`find_task`)

`find_task(conn, title)` resolves the spoken title to a stored task via three passes:
1. Exact match, case-insensitive.
2. Substring match in either direction.
3. Token overlap (most shared words wins).

This means "milk" matches "Buy milk", and "the dog walking one" matches "Walk dog". If no match is found, the tool returns a message asking the user to clarify — the LLM relays this verbally.

### Column synonym parsing (`parse_column`)

`parse_column(text)` maps free speech to a canonical column key (`"todo"`, `"in_progress"`, `"done"`). Synonyms include "doing", "wip", "started", "finished", "complete", "backlog", etc. The longest phrase wins to avoid the substring collision between "to do" and "done" (e.g. "move to done" resolves to `"done"`, not `"todo"`).

### Self-grounding result strings

Every mutating function returns a string like:

```
Added "Buy milk" to To Do. Board now: To Do — Buy milk, Walk dog; In Progress — Email Bob; Done — Pay rent.
```

This embeds the post-mutation snapshot. The LLM can confirm what changed in one sentence (`"Added 'buy milk' to your To Do list."`) without a second tool call.

## How to add a new tool

1. Add the board operation to `board.py` (returns a result string embedding the snapshot; no MCP imports).
2. Add the `@mcp.tool()` wrapper in `mcp_server.py`; keep the docstring accurate.
3. Add a line to `TODO_PROMPT` in `agent.py` so the LLM knows when to call it.
4. Add tests to `test_board.py` and `test_mcp_tools.py`.
5. Verify: `bun run verify:backend` + `cd server && pytest tests -v`.

## How to swap the board store

Replace the functions in `board.py` (`get_db`, `add_task`, `move_task`, `delete_task`, `list_tasks`, `reset`) with your backing store. The only contract `mcp_server.py` depends on is:
- `get_db()` returns a connection-like object.
- Mutating functions accept `(conn, *args)` and return a plain-English result string.
- `snapshot(conn)` returns `{ "todo": [...], "in_progress": [...], "done": [...] }` for the board API.

Keep `board.py` free of `mcp` and `agora_agent` imports.

## Related L1

- [02_architecture](../02_architecture.md) · [04_conventions](../04_conventions.md) · [06_interfaces](../06_interfaces.md) · [07_gotchas](../07_gotchas.md)
