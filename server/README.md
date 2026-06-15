# Agora Agent Backend — Voice Todo Board Recipe

FastAPI service that owns Agora token generation, the todo assistant agent
session lifecycle, board read/reset endpoints, and the in-process FastMCP todo
server. It is the service the web client reaches through the Next.js `/api/*`
rewrite proxy (port 8000).

## What's different from the base quickstart

The LLM stage uses the SDK's managed `OpenAI` vendor (keyless — Agora manages
the OpenAI key) with `mcp_servers` pointing at the public `/mcp` todo server and
`enable_tools: true`. When the todo assistant LLM emits a tool call, Agora cloud
POSTs to `MCP_ENDPOINT` (streamable-http transport), receives the board result,
and the assistant speaks a one-line confirmation. There is no `llm/` endpoint in
this recipe. STT (Deepgram) and TTS (MiniMax) remain Agora-managed.

The backend also exposes `GET /board` and `POST /board/reset` so the web client's
live kanban panel can poll the board state independently of the voice session.

## Run

Use the repo-root `README.md` for the full local flow (`bun run dev`). To work
on this module directly:

```bash
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
MCP_ENDPOINT=https://<your-tunnel>/mcp python src/server.py
```

## Environment

`server/.env.example` is the template. Required:

- `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE` — Agora project credentials.
- `MCP_ENDPOINT` — the **public** URL of your `/mcp` todo server (e.g.
  `https://<tunnel>/mcp`). Agora cloud calls this directly, so it cannot be
  `localhost`. Expose port 8000 via ngrok and use the tunnel URL here.

Optional:

- `OPENAI_MODEL` (default `gpt-4o-mini`) — model name for the managed todo
  assistant LLM.
- `BOARD_DB_PATH` (default `board.db` in the server root, `/tmp/board.db` in
  Docker) — path to the SQLite board database.
- `OPENAI_API_KEY` — Agora manages the key by default; set this only if you
  want to supply your own.
- `AGENT_GREETING` — override the assistant's opening line.

## API

- `GET /get_config` — token + channel/UID config
- `POST /startAgent` — start a todo assistant agent session
- `POST /stopAgent` — stop an agent session
- `GET /board` — current kanban snapshot (todo/in_progress/done columns)
- `POST /board/reset` — clear the board and restore the 5 seed tasks

The repo-root `bun run verify:web:api` exercises the token/agent routes through
the Next proxy using a fake agent (`scripts/run_fake_server.py`), so no live
Agora session is required.

## Key files

| File | Purpose |
| --- | --- |
| `src/server.py` | FastAPI app, routes, in-process MCP mount |
| `src/agent.py` | Agent wrapper — todo assistant LLM (OpenAI vendor + mcp_servers) |
| `src/mcp_server.py` | FastMCP wrapper exposing the 4 board tools |
| `src/board.py` | Pure todo-board store (SQLite, no MCP dependency, fully unit-testable) |
| `src/mcp_config.py` | Pure builder for the `mcp_servers` list (testable) |
