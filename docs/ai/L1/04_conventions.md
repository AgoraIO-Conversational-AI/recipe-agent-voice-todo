# 04 · Conventions

> Coding patterns shared across `server/` and `web/`. Follow these to keep the board store, MCP layer, and web client correctly decoupled.

## Boundary ownership

- Browser code calls only `/api/*`. Backend placement is hidden behind Next rewrites (`web/next.config.ts`).
- **Never** add `web/app/api/**/route.ts` for agent/token/board logic — `verify-api-contracts.ts` fails the build if a `route.ts` appears under `app/api`.
- Token generation and the App Certificate stay in `server/`.
- The MCP board tools and the board store both stay in `server/`; do not move them to a separate process or expose them from `web/`.

## Backend (Python / FastAPI)

- Async throughout: route handlers are `async def`; the agent uses `AsyncAgora` and `create_async_session`.
- Request bodies are Pydantic models (`StartAgentRequest`, `StopAgentRequest`). Field names are **camelCase** (`channelName`, `rtcUid`, `userUid`) to match the browser client.
- Error mapping is centralized: `_to_http_error()` maps `ValueError → 400`, `RuntimeError → 500`, else 500. `_log_route_error()` logs with safe context + traceback. Raise plain `ValueError`/`RuntimeError`; let the route convert.
- Logging via `logging.getLogger("uvicorn.error")`.
- Env read with `os.getenv`; `.env.local` then `.env` loaded with `override=True`.

## Response envelope

All backend JSON responses use:

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` is present only when the route returns a payload. The browser client treats `code !== 0` (or missing `data`) as an error.

## Board store isolation

`server/src/board.py` has **no MCP or `agora_agent` imports** — it is a standalone SQLite board store. This keeps it fully unit-testable in isolation. The MCP layer (`mcp_server.py`) calls into `board.py` through the `_run` wrapper which opens and closes a DB connection per call. Do not import from `mcp_server` or `agora_agent` inside `board.py`.

## MCP tool shape

Each of the 4 tools is **self-contained**:

- One tool call performs exactly one board mutation (or read).
- The board mutation and snapshot embedding happen inside `board.py` — the MCP layer calls `_run(board.<op>, ...)` and returns the result string verbatim.
- The result string embeds the post-mutation board snapshot (`"Board now: To Do — X; In Progress — Y; Done — Z"`). This lets the LLM confirm what changed in one sentence without a second tool call.
- Do not add tool-call chaining — one utterance maps to at most one tool call.

## MCP transport convention

The Agora SDK uses `"streamable_http"` (underscore) in `mcp_servers[].transport`. The FastMCP server uses `"streamable-http"` (hyphen) in its run call. These are different SDK conventions and must not be unified — see `server/src/mcp_config.py`.

## Web (TypeScript / Next.js)

- Lint/format with Biome (`bun run lint`, `bun run lint:fix` in `web/`).
- RTC client creation must be StrictMode-safe (strict mode is on).
- Transcript speaker mapping: `normalizeTranscript` maps `uid === '0'` to the local UID. Do not heuristically guess speakers.
- API client lives in `src/services/api.ts`; UI never calls `fetch` to the backend directly.
- Board polling lives in `src/lib/board.ts` (`useBoardPolling`); it only polls while `active` (a conversation is connected).

## Testing approach

- Backend: `pytest` in `server/`, standalone — `conftest.py` fakes env and SDK session, so no cloud or real creds are needed.
- Web: contract/proxy/fastapi smoke scripts under `web/scripts/` run without live Agora calls.
- Run the **narrowest** relevant verify command before finishing (see [05_workflows](05_workflows.md)).

## Doc upkeep

When you change request/response contracts, env vars, MCP tools, or workflow steps, update the web client, backend, contract checks, README, **and** the matching `docs/ai/L1/` file together, then bump `Last Reviewed` in [L0](../L0_repo_card.md).

## Related Deep Dives

- [mcp_tools_and_board_store](L2/mcp_tools_and_board_store.md) — MCP tool wiring and board store design in detail.
