---
recipe_version: 1.0.0
recipe_status: experimental
extension_points:
  - id: api.routes
    name: Browser-facing API routes
  - id: agent.llm-config
    name: OpenAI model, system prompt, greeting, and mcp_servers list
  - id: board.store
    name: SQLite board store implementation (board.py)
  - id: mcp.tools
    name: FastMCP tool registry (mcp_server.py)
  - id: web.board-ui
    name: TodoBoard kanban panel and board polling
  - id: verification.contracts
    name: Contract, proxy, and local FastAPI smoke verification
invariants:
  - id: api.rewrite-boundary
    summary: Browser calls stay on /api/* and Next rewrites to FastAPI; no Route Handlers for agent/token/board logic.
  - id: secrets.server-only
    summary: Agora App Certificate stays in the Python backend; OPENAI_API_KEY is optional but also server-only when set.
  - id: mcp.in-process
    summary: The FastMCP todo server is mounted in-process on the same port as the API backend; it is not a separate process.
  - id: router.before-mount
    summary: app.include_router(router) must run before app.mount("/", _mcp_asgi) so token and board endpoints take precedence.
  - id: board.no-mcp-import
    summary: board.py has no mcp or agora_agent imports; it is a standalone SQLite store testable in isolation.
  - id: token.uid-concrete
    summary: Backend resolves missing, zero, or negative UIDs before issuing a Token007.
stable_contracts:
  - id: env.required
    summary: AGORA_APP_ID, AGORA_APP_CERTIFICATE, and MCP_ENDPOINT are required; AGENT_BACKEND_URL is required by deployed web rewrites.
  - id: api.core-routes
    summary: GET /api/get_config, POST /api/startAgent, POST /api/stopAgent, GET /api/board, and POST /api/board/reset remain the browser-facing contract.
  - id: response.envelope
    summary: Successful backend responses use { code, msg, data }.
  - id: mcp.tools
    summary: The four tools (add_task, move_task, delete_task, list_tasks) each accept the documented params and return a plain-English string embedding the post-mutation board snapshot.
---

# Recipe Contract

This base recipe defines the reusable surface for a Python-backed Agora Conversational AI **voice todo board**: a managed-keyless OpenAI assistant that manages a 3-column kanban through 4 FastMCP tools mounted in-process, with a live polling web client.

## Recipe Role

- Role: `base` recipe (self-contained, clone-and-run; no `Extends` pin).
- Target audience: developers building a voice-driven task-management feature with MCP tool calling, a Python FastAPI backend, and a Next.js web client.
- Reuse model: clone, bind project, set `MCP_ENDPOINT` (public tunnel), run, then customize the board store, tools, or browser UI.

## Recipe Scope

- Python FastAPI token generation and managed agent lifecycle.
- A cascading STT (`DeepgramSTT`) + LLM (`OpenAI`, managed-keyless) + TTS (`MiniMaxTTS`) pipeline with `enable_tools: true` and `mcp_servers` pointing at the public `MCP_ENDPOINT`.
- A FastMCP todo server mounted in-process at `/mcp` (same port 8000), serving 4 board tools via streamable-HTTP transport.
- A pure SQLite board store (`board.py`) with no MCP dependency, fuzzy title matching, and column synonym parsing.
- Board read/reset endpoints (`GET /board`, `POST /board/reset`) for the live kanban web panel.
- Next.js browser UI with RTC audio, RTM transcript/metrics, and a `TodoBoard` kanban panel polling `GET /api/board` at ~1s.
- Rewrite-only `/api/*` browser facade hiding backend placement.
- Contract, proxy, and local FastAPI smoke verification that need no live Agora calls.

## Baseline Implementation Guidance

Use this repo's source and progressive disclosure docs as the starting point, then customize. Do not recreate the Agora ConvoAI integration, MCP wiring, or board store from memory — vendor schemas, SDK builder fields, token behavior, MCP transport conventions, and RTM details drift. Copy verified patterns from this repo.

## Extension Points

| ID | Surface | How to extend | Required follow-up |
| -- | ------- | ------------- | ------------------ |
| `api.routes` | `server/src/server.py`, `web/next.config.ts`, `web/src/services/api.ts` | Add FastAPI route, add rewrite, add browser fetch helper. | Extend `web/scripts/verify-api-contracts.ts`; add proxy coverage if needed. |
| `agent.llm-config` | `server/src/agent.py` | Change `OPENAI_MODEL`, `TODO_PROMPT`, `AGENT_GREETING`, or `mcp_servers`. | Run `verify:backend` + `pytest tests`; document new env in `server/.env.example` (never add `PORT`). |
| `board.store` | `server/src/board.py` | Replace SQLite with Postgres, Notion, etc. Keep `board.py` free of MCP imports; mutating functions must return a result string embedding the snapshot. | Update `server/tests/test_board.py`; keep `snapshot(conn)` returning `{todo, in_progress, done}`. |
| `mcp.tools` | `server/src/mcp_server.py` | Add, remove, or rename `@mcp.tool()` functions. Keep each tool self-contained (one call → one mutation → one result string). | Update `TODO_PROMPT` in `agent.py`; add tests in `test_mcp_tools.py`. |
| `web.board-ui` | `web/src/components/TodoBoard.tsx`, `web/src/lib/board.ts` | Customize the kanban layout, polling interval, or reset behavior. | Preserve `useBoardPolling` active-guard and cancel-on-unmount logic. |
| `verification.contracts` | `web/scripts/*.ts`, root `package.json` | Add checks for new browser/backend boundaries. | Keep checks runnable without live Agora credentials. |

## Invariants

- Browser code calls only `/api/get_config`, `/api/startAgent`, `/api/stopAgent`, `/api/board`, and `/api/board/reset` for the default flow.
- Next.js owns `/api/*` through rewrites only; no `web/app/api/**/route.ts` for agent/token/board logic.
- FastAPI owns token generation, `AGORA_APP_CERTIFICATE`, and agent lifecycle.
- The FastMCP server is mounted in-process via `app.mount("/", _mcp_asgi)` after `app.include_router(router)`.
- `board.py` has no MCP or `agora_agent` imports.
- `MCP_ENDPOINT` is required and must be public; there is no localhost default.

## Stable Contracts

| Contract | Stable shape |
| -------- | ------------ |
| Required backend env | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `MCP_ENDPOINT` |
| Optional backend env | `OPENAI_MODEL`, `OPENAI_API_KEY`, `BOARD_DB_PATH`, `AGENT_GREETING`, `PORT` (env only) |
| Required web deploy env | `AGENT_BACKEND_URL` |
| `GET /api/get_config` | Query `channel?`, `uid?`; returns `data.app_id`, `data.token`, `data.uid`, `data.channel_name`, `data.agent_uid`. |
| `POST /api/startAgent` | Body `{ channelName, rtcUid, userUid, parameters? }`; returns `data.agent_id`, `data.channel_name`, `data.status`. |
| `POST /api/stopAgent` | Body `{ agentId }`; returns `{ code: 0, msg: "success" }`. |
| `GET /api/board` | Returns `data: { todo: [{id, title}], in_progress: [{id, title}], done: [{id, title}] }`. |
| `POST /api/board/reset` | Returns `data` (same shape as board snapshot) after restoring 5 seed tasks. |
| Success envelope | `{ "code": 0, "msg": "success", "data": ... }` where the route has data. |
| MCP tool result | Each tool returns a plain-English string embedding the full post-mutation board snapshot. |
| Verification entry points | `bun run verify:web`, `bun run verify:backend`, `bun run verify:web:proxy`, `bun run verify:local`. |

## Internal / Subject to Change

- Visual layout, component composition, Tailwind classes, and assets under `web/src/components/`.
- Exact model name, system prompt wording, voice, and greeting text, as long as they stay documented extension points.
- In-memory `Agent._sessions` details; the stable behavior is start by channel/user and stop by returned `agent_id`.
- Verification internals under `web/scripts/`; the stable surface is the root script names and what they assert.
- `agora-agents` SDK minor-version behavior; this recipe lower-bounds `>=2.3.0` but does not freeze every field.
- `board.db` SQLite schema internals; the stable behavior is the `snapshot()` shape and the `reset()` post-condition.

## Related Progressive Disclosure Docs

- `L1/01_setup.md` — setup, env, ngrok, and commands.
- `L1/02_architecture.md` — request flow, single-process design, and topology.
- `L1/05_workflows.md` — common modification workflows.
- `L1/06_interfaces.md` — route, rewrite, env, MCP tool, and vendor contracts.
- `L1/L2/mcp_tools_and_board_store.md` — full MCP tool wiring and board store detail.
- `L1/L2/board_state_sync.md` — board polling and reset flow.
