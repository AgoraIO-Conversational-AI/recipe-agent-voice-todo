# Architecture — Voice Todo Board Recipe

Two processes. The browser talks only to Next.js `/api/*`, which rewrites to
the agent backend. The agent backend owns Agora tokens, agent lifecycle, **and**
the FastMCP todo server — all in one process on port 8000.

**MCP multi-tool spike: GO (2026-06-12)** — a live Agora session confirmed
`add_task` then `move_task` fired as distinct tools with SQLite state persisting
across calls; the managed-LLM todo assistant reliably called the tools and the
web kanban updated in real time.

## Request flow

```
Browser
  │  GET /api/get_config            → token + channel/UIDs
  │  POST /api/startAgent           → start todo assistant agent session
  ▼
Next.js  (rewrites /api/* → AGENT_BACKEND_URL)
  ▼
Agent backend (server/, :8000)
  │  builds session with OpenAI(mcp_servers=[{endpoint: MCP_ENDPOINT}])
  │  also mounts FastMCP at /mcp (same process, same port)
  │  also serves GET /board and POST /board/reset (kanban snapshot endpoints)
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT (managed)
  │  managed todo assistant LLM (keyless OpenAI) → emits tool call
  │  POST <MCP_ENDPOINT>   (streamable-http transport)
  ▼
FastMCP todo server (/mcp, same process as agent backend, public via tunnel)
  │  executes tool (add_task / move_task / delete_task / list_tasks)
  │  → mutates SQLite board, returns plain-English result + board snapshot
  ▼
Agora ConvoAI Cloud → LLM speaks one-line confirmation
                     → MiniMax TTS (managed) → user hears speech
                     → RTM transcript / metrics → web UI

Web client polls GET /api/board (~1 s) → card moves columns in live kanban
```

`POST /api/stopAgent { agentId }` ends the session.

## Single-process design

The FastMCP todo server is mounted in-process via `app.mount("/", _mcp_asgi)` in
`server/src/server.py`. A shared lifespan manages the MCP session manager
(`mcp_server.mcp.session_manager.run()`). The API router is included before the
mount so `/get_config`, `/startAgent`, `/stopAgent`, `/board`, and `/board/reset`
take precedence over the catch-all MCP mount. This means:

- One port (8000) and one tunnel handle token endpoints, board read endpoints,
  and MCP tool calls.
- Agora cloud calls `<public-url>/mcp` — the same host the browser uses for
  `/get_config` and `/startAgent`, just at the `/mcp` path.
- The `server/src/board.py` store has no MCP dependency and remains fully
  unit-testable in isolation.

## One process, three concerns

| Concern | Handler |
| --- | --- |
| Agora token generation + agent lifecycle | `GET /get_config`, `POST /startAgent`, `POST /stopAgent` (router) |
| Kanban read endpoints for the web client | `GET /board`, `POST /board/reset` (router) |
| MCP board tools for Agora cloud | `POST /mcp` (FastMCP mount via `app.mount("/", _mcp_asgi)`) |

## Co-public trade-off

Mounting `/mcp` on the same port as the token endpoints means both are reachable
from the public tunnel. The App Certificate is only used to mint tokens in-memory
and is never transmitted on the wire, but `/get_config` and `/startAgent` are
unauthenticated in the dev configuration. Add authentication and rate-limiting
before exposing the backend on a production URL.

## Self-contained tools

Each of the 4 tools resolves a **whole board mutation** in one call. The board
store (`board.py`) handles fuzzy title matching and column synonym parsing before
writing to SQLite. Each tool returns a plain-English string that embeds the
post-mutation snapshot, so the LLM can confirm what changed in a single
sentence — no tool-call chaining required.

## Board state model

SQLite state is global (no session id, matching Agora's single-user-per-session
model). The `tasks` table holds all kanban cards; the `meta` table records
whether the seed tasks have been inserted (so an empty board after all tasks are
deleted is a valid state, not a trigger for re-seeding). `list_tasks` is the
voice-first board read — the user asks the assistant, and the assistant reads it
aloud via the tool result. The web client uses `GET /board` for the live kanban
panel.

## Distinct from recipe-agent-tool-calling

In `recipe-agent-tool-calling` the tools run **inside** the `llm/` endpoint:
the agent's custom LLM proxy intercepts tool calls and handles them locally. In
this recipe Agora cloud orchestrates the tools on the **FastMCP server** via the
MCP protocol — the managed OpenAI vendor issues the tool call, Agora invokes
`MCP_ENDPOINT` (served at `/mcp` by the same backend process), and the result
flows back to the todo assistant LLM.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the todo assistant agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |
| `/board` | GET | Kanban snapshot for the web client |
| `/board/reset` | POST | Clear the board and restore seed tasks |
| `/mcp` | POST | FastMCP streamable-HTTP endpoint (called by Agora cloud) |

The browser calls `/get_config`, `/startAgent`, `/stopAgent`, `/board`, and
`/board/reset` as `/api/*`; Next rewrites them to `AGENT_BACKEND_URL`. Agora
cloud calls `/mcp` directly via the public `MCP_ENDPOINT`.

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007, generated from `AGORA_APP_ID` +
  `AGORA_APP_CERTIFICATE`.
- Agora cloud → FastMCP todo server (`/mcp`): streamable-http (no auth on the
  dev server; add it for production use).
- OpenAI: Agora-managed (keyless) — `OPENAI_API_KEY` is optional.
