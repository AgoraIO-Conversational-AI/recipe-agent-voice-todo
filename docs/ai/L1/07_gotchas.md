# 07 · Gotchas

> Non-obvious pitfalls specific to the voice todo board recipe. Read before changing the agent, MCP server, env, or verify scripts.

## `MCP_ENDPOINT` must be public (not localhost)

`MCP_ENDPOINT` is validated at `Agent.__init__` — the server will fail to start if it is missing. Even when present, a `localhost` or LAN URL will cause the assistant to greet but never call a tool: Agora cloud (not the backend process) issues the POST to `MCP_ENDPOINT`. Use a public tunnel (ngrok) and paste the tunnel URL. `doctor:local` warns when `MCP_ENDPOINT` points at `localhost` or `127.0.0.1`.

## Router must be included before the MCP mount

`app.include_router(router)` must run before `app.mount("/", _mcp_asgi)` in `server/src/server.py`. FastAPI route matching is first-match; reversing the order routes `/get_config`, `/startAgent`, `/stopAgent`, `/board`, and `/board/reset` into the MCP catch-all instead of the API handlers.

## `mcp_servers` transport uses underscore; FastMCP uses hyphen

`build_mcp_servers()` passes `"streamable_http"` (underscore) — that is the Agora SDK's convention. The FastMCP server uses `"streamable-http"` (hyphen) in its own run call. Do not unify them; the SDK and FastMCP use different naming.

## `OPENAI_API_KEY` is optional — Agora manages it

Unlike `recipe-agent-realtime`, this recipe is zero-key: the managed `OpenAI` vendor does not require `OPENAI_API_KEY`. You can supply one if you prefer your own key; Agora uses it when present.

## Board state is global (no session isolation)

SQLite state has no per-session partitioning. If two sessions run against the same backend instance, they share the same board. This matches Agora's single-user-per-session model and is intentional for a demo recipe; add session-keyed partitioning before multi-tenant use.

## Do not put `PORT` in `server/.env.example`

`verify:local:fastapi` (`web/scripts/verify-local-fastapi.ts`) injects a random `PORT` and loads env with `load_dotenv(override=True)`. A `PORT` line in `.env.example` (copied to `.env.local`) would clobber the injected port and break the smoke test.

## Keep `/api/*` ownership in rewrites

Adding `web/app/api/**/route.ts` for agent/token/board logic breaks the boundary — `verify-api-contracts.ts` explicitly fails if a `route.ts` exists under `app/api`. Token and board logic belongs in `server/`.

## camelCase request fields

`StartAgentRequest` uses `channelName`, `rtcUid`, `userUid` (camelCase) to match the browser client. Renaming one side without the other breaks the contract tests.

## Do not seed on every empty connection

The board is seeded exactly once (via `meta` table). After all tasks are deleted, an empty board is a valid state — reconnecting to the DB must NOT re-seed. The `_seed_once` guard in `board.py` enforces this. Use `POST /board/reset` to explicitly restore seed tasks.

## Local calls under a global proxy

Global proxies (Clash, etc.) can break `localhost`/RFC-1918 traffic. Configure the proxy to send `127.0.0.1`, `localhost`, and private ranges DIRECT, or use `socksio` (in `requirements.txt`) plus `all_proxy` to route the backend through SOCKS.

## Co-public deployment surface

Port 8000 serves both the unauthenticated token endpoints (`/get_config`, `/startAgent`) and the MCP server (`/mcp`). This is intentional for a dev/demo recipe. Add authentication and rate-limiting before exposing the backend on a production URL.

## Related Deep Dives

- [mcp_tools_and_board_store](L2/mcp_tools_and_board_store.md) — correct MCP tool and board store wiring.
