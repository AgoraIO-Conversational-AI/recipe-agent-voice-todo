# 05 · Workflows

> Step-by-step guides for the common changes in this recipe. Each ends with the narrowest verify command to run.

## Add or change a browser-facing route

1. Add the FastAPI handler in `server/src/server.py` (return the `{ code, msg, data }` envelope).
2. Add the `/api/<name>` → `/<name>` mapping in `web/next.config.ts` `rewrites()`.
3. Add a client helper in `web/src/services/api.ts`.
4. Extend `web/scripts/verify-api-contracts.ts` with the new path + envelope assertions.
5. Verify: `bun run verify:web` (and `bun run verify:web:proxy` if the route should round-trip through the rewrite map).

## Add or rename a board tool

1. Add or rename the `@mcp.tool()` function in `server/src/mcp_server.py`.
2. If the new tool needs a new board operation, add it in `server/src/board.py` (no MCP imports). Ensure it returns a plain-English string embedding the post-mutation snapshot.
3. Update the tool's docstring — Agora's managed LLM reads the docstring when choosing tools.
4. Update the `TODO_PROMPT` in `server/src/agent.py` to reference the new tool behavior.
5. Add tests in `server/tests/test_mcp_tools.py` (wrapper call) and `server/tests/test_board.py` (board logic).
6. Verify: `bun run verify:backend` + `cd server && pytest tests -v`.

## Change the LLM model or prompt

1. Model: set `OPENAI_MODEL` (default `gpt-4o-mini`).
2. System prompt: edit `TODO_PROMPT` in `server/src/agent.py`.
3. Greeting: set `AGENT_GREETING` (env) or edit `AGENT_GREETING` default in `server/src/agent.py`.
4. Verify: `bun run verify:backend`.

## Swap the board store (replace SQLite)

1. Replace the `get_db`, `add_task`, `move_task`, `delete_task`, `list_tasks`, and `reset` functions in `server/src/board.py` with your backing store. The only MCP contract: mutating functions must return a plain-English string embedding the post-mutation snapshot.
2. Keep `board.py` free of `mcp` and `agora_agent` imports.
3. Update `server/tests/test_board.py` for your new store.
4. Verify: `cd server && pytest tests -v`.

## Run / debug locally

```bash
bun run dev              # both processes
bun run doctor:local     # check creds + .env.local + MCP_ENDPOINT before a live call
```

## Verify before finishing

| Change touches…                  | Run                                                              |
| -------------------------------- | ---------------------------------------------------------------- |
| Web only                         | `bun run verify:web`                                             |
| Backend logic / MCP tools        | `bun run verify:backend` + `cd server && pytest tests -v`        |
| Route/proxy boundary             | `bun run verify:web:proxy`                                       |
| Anything end-to-end (local)      | `bun run verify:local`                                           |

## Deploy

1. Expose port 8000 publicly (e.g. ngrok or a deployed host). The backend must be reachable by Agora cloud for `/mcp` calls.
2. Set `MCP_ENDPOINT=<public-url>/mcp` in `server/.env.local` (or as a deploy env var).
3. Deploy `web/` as a Next.js app; set `AGENT_BACKEND_URL` so rewrites reach the backend.
4. Deploy `server/` (or the backend-only Docker image: `ghcr.io/AgoraIO-Conversational-AI/recipe-agent-voice-todo` on `v*` tags).

## Related Deep Dives

- [mcp_tools_and_board_store](L2/mcp_tools_and_board_store.md) — MCP tool wiring and board store details.
- [board_state_sync](L2/board_state_sync.md) — board polling and reset flow.
