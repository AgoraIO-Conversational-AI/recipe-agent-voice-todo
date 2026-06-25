# 03 · Code Map

> Where things live. Two top-level modules: `web/` (Next.js client) and `server/` (FastAPI backend + MCP server + board store). Orchestration is in the root `package.json`.

## Root

| Path                  | Responsibility                                                             |
| --------------------- | -------------------------------------------------------------------------- |
| `package.json`        | Bun workspace; `setup`, `dev`, `doctor*`, `verify*`, `clean` scripts.     |
| `README.md`           | Setup, run modes, env, tools table, troubleshooting.                       |
| `ARCHITECTURE.md`     | System shape, single-process design, API table, auth trust model.          |
| `AGENTS.md`           | Coding-agent handbook + System shape / Routing / Tools / Commands.         |
| `Dockerfile`          | Backend-only image (`:8000`); `BOARD_DB_PATH=/tmp/board.db`.               |
| `.github/workflows/`  | `ci.yml` (backend pytest matrix + web verify), `docker.yml`, `nightly.yml`.|

## `server/` — FastAPI backend (:8000)

| Path                           | Responsibility                                                                                      |
| ------------------------------ | --------------------------------------------------------------------------------------------------- |
| `src/server.py`                | FastAPI app, CORS, route handlers, MCP in-process mount, error mapping, uvicorn entrypoint.        |
| `src/agent.py`                 | `Agent` class: `AsyncAgora` client, cascading STT/LLM/TTS build, `start()`/`stop()`, `_sessions`. |
| `src/mcp_server.py`            | `FastMCP` wrapper exposing the 4 board tools; calls into `board.py`.                               |
| `src/board.py`                 | Pure todo-board store (SQLite, no MCP/agora import, fully unit-testable). Seeds 5 sample tasks.    |
| `src/mcp_config.py`            | `build_mcp_servers(endpoint)` — pure builder for the `mcp_servers` list.                           |
| `scripts/run_fake_server.py`   | Boots `server.app` with a `FakeAgent` for the local FastAPI smoke test.                            |
| `tests/test_board.py`          | 14 unit tests covering the board store in isolation (SQLite, no creds, no MCP).                    |
| `tests/test_board_api.py`      | HTTP-level tests for `/board`, `/board/reset`, `/startAgent`, `/stopAgent`, `/get_config`.         |
| `tests/test_agent_construction.py` | Construction smoke: real `AgoraAgent` built + session faked; asserts result shape.             |
| `tests/test_mcp_tools.py`      | MCP `_run` wrapper tests + AST check that `mcp_server.py` has no agora imports.                    |
| `tests/test_mcp_config.py`     | Unit tests for `build_mcp_servers` transport/name defaults.                                        |
| `tests/conftest.py`            | `fake_env` fixture (monkeypatches dotenv + env), `FakeAgent`, `server_module`, `client` fixtures.  |
| `.env.example`                 | Env template (do not add `PORT`).                                                                   |
| `requirements*.txt`            | Runtime + dev (pytest) deps.                                                                        |

## `server/src/server.py` routes

- `GET /get_config` — token + channel/UID config.
- `POST /startAgent` — start the todo assistant agent session.
- `POST /stopAgent` — stop by `agent_id`.
- `GET /board` — current kanban snapshot.
- `POST /board/reset` — clear board and restore 5 seed tasks.
- `POST /mcp` — FastMCP streamable-HTTP endpoint (called by Agora cloud only).

## `web/` — Next.js client (:3000)

| Path                                           | Responsibility                                                             |
| ---------------------------------------------- | -------------------------------------------------------------------------- |
| `next.config.ts`                               | `/api/*` rewrites to `AGENT_BACKEND_URL`; 5 paths including `/api/board` and `/api/board/reset`. |
| `src/services/api.ts`                          | Browser API client: `getConfig`, `startAgent`, `stopAgent`, `getBoard`, `resetBoard`. |
| `src/lib/board.ts`                             | `useBoardPolling(active, intervalMs)` — polls `GET /api/board` while active. |
| `src/lib/conversation.ts`                      | Transcript normalization, timestamp mapping, visualizer state helpers.     |
| `src/lib/agora.ts`                             | `DEFAULT_AGENT_UID` constant.                                              |
| `src/types/board.ts`                           | `BoardTask` and `BoardSnapshot` TypeScript types.                          |
| `src/components/LandingPage.tsx`               | Entry point: config fetch, agent start, RTM login, `TodoBoard` + `ConversationComponent` layout. |
| `src/components/TodoBoard.tsx`                 | Kanban panel using `useBoardPolling`; "Reset board" button.                |
| `src/components/ConversationComponent.tsx`     | RTC join, mic publish, transcript/metrics/state listeners.                 |
| `src/components/Quickstart*.tsx`               | Pre-call, transcript, metrics, layout panels.                              |
| `scripts/verify-api-contracts.ts`             | Asserts rewrites + client paths + response envelope (no network).          |
| `scripts/verify-local-proxy.ts`               | Stub backend; proxies `/api/*` through the rewrite map.                    |
| `scripts/verify-local-fastapi.ts`             | Spawns real FastAPI with `FakeAgent`; proxies routes end-to-end.           |
| `scripts/doctor.ts`                           | Web prerequisite check.                                                    |

## Related Deep Dives

- None. For runtime flow see [02_architecture](02_architecture.md); for contracts see [06_interfaces](06_interfaces.md).
