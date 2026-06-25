# 02 · Architecture

> One backend process, three concerns: Agora token generation, kanban board read/reset endpoints, and a FastMCP todo server — all on port 8000. Agora cloud calls the MCP tools at the public `MCP_ENDPOINT`; the web client polls `GET /board` for the live kanban panel.

## Topology

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js (web/)  ──rewrite──▶  Agent backend (server/, :8000)
                                 │  builds AgoraAgent with OpenAI(mcp_servers=[{endpoint: MCP_ENDPOINT}])
                                 │  mounts FastMCP todo server at /mcp (same process, same port)
                                 │  also serves GET /board + POST /board/reset
                                 ▼
                              Agora ConvoAI Cloud
                                 │  user speech → Deepgram STT (managed)
                                 │  managed todo assistant LLM (keyless OpenAI) → emits tool call
                                 │  POST <MCP_ENDPOINT>   (streamable-http transport)
                                 ▼
                              FastMCP todo server (/mcp, same process, public via tunnel)
                                 │  executes tool (add_task / move_task / delete_task / list_tasks)
                                 │  mutates SQLite board → returns plain-English result + board snapshot
                                 ▼
                              Agora ConvoAI Cloud → LLM speaks one-line confirmation
                                                  → MiniMax TTS (managed) → user hears speech
                                                  → RTM transcript / metrics → web UI

Web client polls GET /api/board (~1 s) → card visibly moves columns in live kanban
```

- **`web/`** — Next.js / React / TypeScript. Owns UI plus the RTC/RTM client lifecycle and the live `TodoBoard` kanban panel. Calls only `/api/*`.
- **`server/`** — Python FastAPI (:8000). Owns Agora token generation, agent session lifecycle, board read/reset endpoints, **and** the in-process FastMCP todo server. SDK: `agora-agents>=2.3.0` (`import agora_agent`).
- No `llm/` service — the managed `OpenAI` vendor is keyless; Agora handles the key.

## Request lifecycle

1. Browser `GET /api/get_config` → Next rewrites to backend `/get_config`; backend mints a Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE` and returns channel + UIDs.
2. Browser joins the RTC channel, then `POST /api/startAgent`; backend builds the `OpenAI` LLM vendor with `mcp_servers` pointing at `MCP_ENDPOINT`, sets `enable_tools: true`, and starts an async agent session.
3. User speaks (e.g. "add buy milk"). Agora runs Deepgram STT (managed), sends the transcript to the managed todo assistant LLM.
4. The assistant emits a tool call (`add_task`). Agora cloud issues a streamable-HTTP POST to `MCP_ENDPOINT`. The FastMCP server (same process, same port) executes the tool, mutates the SQLite board, and returns a plain-English result embedding the updated board snapshot.
5. Agora feeds the tool result back; the assistant speaks a one-line confirmation. Agora runs MiniMax TTS (managed) and plays it back.
6. RTM delivers transcript + metrics to the web UI.
7. The web client polls `GET /api/board` roughly every second; the new task appears in the To Do column without any page refresh.
8. `POST /api/stopAgent { agentId }` ends the session.

## Single-process design

The FastMCP server is mounted in-process via `app.mount("/", _mcp_asgi)` in `server/src/server.py`. A shared `_lifespan` manages the MCP session manager. The API router is included **before** the mount so `/get_config`, `/startAgent`, `/stopAgent`, `/board`, and `/board/reset` take precedence over the catch-all MCP mount.

## Key abstractions

- **`Agent`** (`server/src/agent.py`) — builds an `AgoraAgent` with cascading STT/LLM/TTS vendors and `enable_tools: true`; owns `AsyncAgora` client and the in-memory `_sessions` map keyed by `agent_id`.
- **`build_mcp_servers(endpoint)`** (`server/src/mcp_config.py`) — pure builder that returns the `mcp_servers` list with `transport: "streamable_http"` (Agora SDK convention, underscore, not hyphen).
- **`board.py`** (`server/src/board.py`) — pure SQLite board store with no MCP or `agora_agent` imports; fully unit-testable in isolation.
- **`mcp_server.py`** (`server/src/mcp_server.py`) — FastMCP wrapper exposing the 4 board tools; each tool calls into `board.py`.
- **Rewrite proxy** (`web/next.config.ts`) — the only browser→backend boundary for the 5 `/api/*` paths; no Next Route Handlers for agent/token/board logic.

## Tech decisions

- **Managed OpenAI (keyless)** — `OPENAI_API_KEY` is optional; Agora manages it. Cascading STT (`DeepgramSTT`) + LLM (`OpenAI`) + TTS (`MiniMaxTTS`) vendors vs. the `MLLM` path used in `recipe-agent-realtime`.
- **MCP in-process** — one port (8000) and one tunnel handle token endpoints, board read, and MCP tool calls. The downside is a co-public deployment surface; see [07_gotchas](07_gotchas.md).
- **Board polling over RTM push** — the web client polls `GET /board` rather than receiving board updates over RTM. Simple and sufficient for a single-user session model.
- **Self-contained tools** — one utterance maps to at most one tool call; no chaining. Each tool returns the full post-mutation snapshot so the LLM can confirm in one sentence.

## Related Deep Dives

- [mcp_tools_and_board_store](L2/mcp_tools_and_board_store.md) — MCP tool wiring, board store design, fuzzy matching, column synonyms.
- [board_state_sync](L2/board_state_sync.md) — board polling, `useBoardPolling`, reset flow, state model.
