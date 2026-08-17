# Agora Conversational AI — Voice Todo Board Recipe (Python)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Bun](https://img.shields.io/badge/bun-latest-black)](https://bun.sh/)

The **voice todo board** recipe in the Agora Conversational AI recipes family. A
managed-keyless OpenAI assistant manages a **3-column kanban** (To Do / In
Progress / Done) through four MCP tools mounted in the same backend process. The
user speaks to add, move, or delete tasks; the web client polls `GET /board` and
the card visibly moves columns in real time. STT (Deepgram) and TTS (MiniMax) are
Agora-managed.

This recipe is **zero-key**: OpenAI is Agora-managed (no `OPENAI_API_KEY` needed,
though you may supply your own). The FastMCP todo server is mounted in-process —
one backend, one port (**:8000**). The full pipeline runs locally with only Agora
credentials and a public tunnel.

**Distinct from `recipe-agent-tool-calling`**: in that recipe tools run inside
the `llm/` endpoint. Here Agora cloud orchestrates them on a **FastMCP server**
mounted inside the API server — Agora cloud calls it directly at `MCP_ENDPOINT`
(`<public-url>/mcp`).

## Prerequisites

- [Python 3.10+](https://www.python.org/)
- [Bun](https://bun.sh/)
- [Agora CLI](https://github.com/AgoraIO/cli) — generates App ID + Certificate
- [ngrok](https://ngrok.com/) — the `/mcp` path must be publicly reachable so
  Agora cloud can call it

The same commands work on macOS, Linux, and Windows. On macOS/Linux, setup uses
`python3`; on Windows, it uses the Python launcher (`py`) or `python`. WSL and
virtualenv activation are not required.

## Run It

```bash
# 1. Install Python venv + web deps
bun run setup

# 2. Add Agora credentials to server/.env.local
agora login
agora project use <your-project>
agora project env write server/.env.local

# 3. Expose the backend publicly — /mcp is served by the same process
ngrok http 8000

# 4. Set MCP_ENDPOINT in server/.env.local (use whatever domain ngrok prints)
#    MCP_ENDPOINT=https://<your-tunnel>.ngrok-free.dev/mcp

# 5. Run backend + frontend
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) → **Start Conversation** →
say "add buy milk" to create a task, or "move buy milk to in progress" to update
it.

### Working from a clone

If you cloned this repo (rather than scaffolding via the Agora CLI), the steps
above are complete as written: `bun run setup` creates the Python venv and
installs web dependencies, then `bun run dev` brings up the backend and
frontend. You still need Agora credentials in `server/.env.local` and a public
`MCP_ENDPOINT` tunnel before a conversation can connect.

Services:

- Frontend — http://localhost:3000
- Backend + MCP todo server — http://localhost:8000
- API docs — http://localhost:8000/docs
- MCP endpoint — http://localhost:8000/mcp

## Deploy

Deploy `web` (Next.js) and `server` (a single publicly reachable FastAPI
backend). Set `AGENT_BACKEND_URL` in the web deployment so the Next rewrites
reach the backend.

The backend must be publicly reachable so Agora cloud can call `/mcp`. A single
Docker image is published to
`ghcr.io/AgoraIO-Conversational-AI/recipe-agent-voice-todo` on `v*` tags. It runs one
process on port 8000 with the FastMCP todo server mounted at `/mcp`.

> **Co-public caveat:** mounting `/mcp` on `:8000` makes the token endpoints
> co-public with the MCP server. The App Certificate is only used to mint tokens
> in-memory and is never sent on the wire, but `/get_config` and `/startAgent`
> are unauthenticated in the dev configuration. Add authentication and
> rate-limiting before exposing the backend on a production URL.

## Environment variables

Backend env file: [`server/.env.example`](server/.env.example).

| Variable | Required | Default | Notes |
| --- | :---: | :---: | --- |
| `AGORA_APP_ID` | Yes | — | Agora Console → Project → App ID |
| `AGORA_APP_CERTIFICATE` | Yes | — | Agora Console → Project → App Certificate |
| `MCP_ENDPOINT` | Yes | — | **Public** URL ending in `/mcp` (e.g. `https://<tunnel>/mcp`). Agora cloud calls it; cannot be `localhost`. |
| `OPENAI_MODEL` | | `gpt-4o-mini` | Model name for the managed todo assistant LLM |
| `BOARD_DB_PATH` | | `board.db` | Path to the SQLite board database (`/tmp/board.db` in Docker) |
| `OPENAI_API_KEY` | | — | Optional — Agora manages the OpenAI key (keyless by default) |
| `AGENT_GREETING` | | built-in | Optional override for the assistant's opening line |
| `AGENT_BACKEND_URL` (web deploy) | Yes (deploy) | — | Required when deploying `web` |

## Commands

```bash
bun run setup            # install web deps + create server/ venv
bun run dev              # run backend (:8000) + web (:3000)

bun run doctor           # prerequisite check (no creds needed)
bun run doctor:local     # + .env.local + credentials + MCP_ENDPOINT checks

bun run verify           # web-only gate (no Agora creds needed)
bun run verify:local     # full local gate: backend compile + web build
bun run clean            # remove venvs and build artifacts
```

Tests run standalone: `pytest` in `server/`, plus `bun run verify` in `web/`.
CI runs them on Linux/macOS/Windows × Python 3.10 & 3.13.

## Architecture

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js  ──rewrite──▶  Agent backend  (server/, localhost:8000)
                          │  starts agent session (todo LLM + mcp_servers)
                          │  also serves /mcp  (FastMCP todo server, in-process)
                          │  also serves GET /board  (kanban snapshot for web UI)
                          ▼
                       Agora ConvoAI Cloud
                          │  user speech → Deepgram STT (managed)
                          │  todo assistant LLM (managed OpenAI, keyless) → emits tool call
                          │  POST <MCP_ENDPOINT>   (streamable-http)
                          ▼
                       FastMCP todo server  (mounted at /mcp, same process)
                          │  public via ngrok tunnel on :8000
                          │  mutates SQLite board → returns post-mutation snapshot
                          ▼
                       Agora ConvoAI Cloud → assistant speaks one-line confirmation
                                          → MiniMax TTS (managed) → user hears speech
                                          → RTM transcript / metrics → web UI
Web client polls GET /api/board (~1 s) → card visibly moves columns in kanban
```

The browser only ever calls Next `/api/*`, which rewrites to the agent backend.
The agent backend owns Agora tokens, agent lifecycle, **and** the FastMCP todo
server — all in one process on port 8000. See [ARCHITECTURE.md](./ARCHITECTURE.md).

## Repo Map

- `web/` — Next.js frontend (:3000); RTC/RTM lifecycle, voice UI, and live
  `TodoBoard` kanban panel that polls `GET /api/board`.
- `server/` — FastAPI agent backend (:8000); Agora tokens, todo assistant agent
  lifecycle, board read/reset endpoints, and the FastMCP todo server (mounted at `/mcp`).
- `server/src/board.py` — pure todo-board store (SQLite, no MCP dependency, fully unit-testable).
- `server/src/mcp_server.py` — FastMCP wrapper exposing the four board tools.
- `ARCHITECTURE.md` — system shape and component boundaries.
- `AGENTS.md` — guide for coding agents working in this repo.

## What You Get

- A **voice todo board** where a managed-LLM assistant manages a 3-column kanban
  — no form to fill out, no drag-and-drop required.
- A managed-LLM assistant that calls **4 self-contained MCP tools**: adding tasks,
  moving tasks between columns, deleting tasks, and listing the board.
- A **live kanban panel** in the web UI that updates automatically as the board
  changes; a "Reset board" button restores the seed tasks.
- **SQLite** backs the board — no external task store or database required.
- **Zero-key**: OpenAI is Agora-managed and the board needs no external
  credentials. The full pipeline runs locally with only Agora credentials and a
  public tunnel.

### Tools

| Tool | When the assistant calls it |
| --- | --- |
| `add_task(title)` | User wants to create or add a task |
| `move_task(title, column)` | User wants to move, start, or finish a task — "done", "finished", or "complete" all map to the Done column |
| `delete_task(title)` | User wants to remove, delete, or drop a task |
| `list_tasks()` | User explicitly asks what's on the board |

Each tool opens its own SQLite connection, mutates the board, and returns a
plain-English string that embeds the post-mutation snapshot. No chaining — one
user utterance maps to at most one tool call.

## How It Works

1. The browser calls `/api/get_config`; the backend mints an Agora token.
2. The browser joins the RTC channel, then calls `/api/startAgent`; the backend
   starts an agent session using the managed `OpenAI` vendor with `mcp_servers`
   pointing at the public `MCP_ENDPOINT` (`<tunnel>/mcp`) and `enable_tools: true`.
3. The user speaks (e.g. "add buy milk"). Agora runs STT (Deepgram) and sends the
   transcript to the managed todo assistant LLM.
4. The assistant decides to call `add_task("buy milk")`. Agora cloud issues a
   streamable-HTTP request to `MCP_ENDPOINT`. The FastMCP server (mounted at
   `/mcp` in the same process) runs the tool, inserts the task into SQLite, and
   returns a result string that embeds the updated board snapshot.
5. Agora feeds the tool result back to the assistant LLM, which speaks a one-line
   confirmation (e.g. "Added buy milk to To Do."). Agora runs TTS (MiniMax) and
   plays it back.
6. The web client is polling `GET /api/board` roughly every second; the new task
   appears in the To Do column without any page refresh.
7. Subsequent commands (`move_task`, `delete_task`) resolve in the same way — each
   tool is **self-contained** (board mutation inside `board.py`, no tool-call
   chaining).
8. `/api/stopAgent` ends the session.

## Replacing the mock board

The board layer is intentionally thin and has no MCP dependency:

- **`server/src/board.py`** — swap SQLite for a real task store (Postgres,
  Notion API, etc.) by replacing `get_db`, `add_task`, `move_task`,
  `delete_task`, `list_tasks`, and `reset`. The only contract the MCP layer
  depends on is that mutating functions return a plain-English string embedding
  the post-mutation snapshot.
- **`server/src/mcp_server.py`** — the tool registry. Add, remove, or rename
  tools here. Keep each tool self-contained (one call → one mutation → one result
  string).

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Assistant greets but never calls a tool | `MCP_ENDPOINT` is not public or the `/mcp` path is wrong. Use your ngrok URL. |
| `doctor:local` warns about localhost | Replace the local URL with your public tunnel URL. |
| Local calls fail under a global proxy | Configure the proxy to send `127.0.0.1` and `localhost` DIRECT. |
| Kanban panel does not update | Check that `GET /api/board` returns 200; confirm the Next rewrite points to the running backend. |

## More Docs

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [AGENTS.md](./AGENTS.md)

## License

Released under the [MIT License](./LICENSE).
