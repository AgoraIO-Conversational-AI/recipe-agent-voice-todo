# Agent Development Guide

For coding agents working in `recipe-agent-voice-todo`. This repository is the **voice
todo board** recipe in the Agora Conversational AI recipes family. A managed
keyless OpenAI assistant manages a 3-column kanban by calling **MCP board tools**;
the FastMCP todo server is mounted in-process inside the API server at `/mcp`
(served on :8000); `MCP_ENDPOINT` must be public via ngrok.

## How to Load

This repository uses progressive disclosure documentation. Docs live under
`docs/ai/` in three levels.

1. Read [docs/ai/L0_repo_card.md](docs/ai/L0_repo_card.md) to identify the repo.
2. This repo declares `Recipe Role: base`; read [docs/ai/RECIPE.md](docs/ai/RECIPE.md) before changing reusable recipe contracts.
3. Load ALL 8 files in [docs/ai/L1/](docs/ai/L1/). They are small — load all upfront.
4. Follow L2 deep-dive links only when L1 isn't detailed enough. The index is at [docs/ai/L1/L2/_index.md](docs/ai/L1/L2/_index.md).

The sections below remain the canonical contributor handbook for hands-on work;
the `docs/ai/` tree is the structured summary used by AI agents.

## System shape

- **`server/`** — Python FastAPI agent backend (:8000). Owns Agora token
  generation, the todo assistant agent session lifecycle, and the FastMCP todo
  server (mounted at `/mcp`). SDK: `agora-agents>=2.3.0` (`import agora_agent`).
- **`server/src/mcp_server.py`** — FastMCP wrapper exposing 4 board tools.
  Mounted in-process; Agora cloud calls it at `<public-url>/mcp`.
- **`server/src/board.py`** — pure todo-board store (SQLite, no MCP dependency,
  fully unit-testable). All task mutations, fuzzy matching, and column synonym
  parsing live here. Seeds 5 sample tasks on first init.
- **`web/`** — Next.js frontend (:3000), Agora voice UI with a live `TodoBoard`
  kanban panel that polls `GET /api/board` (~1 s) and a "Reset board" button
  (`POST /api/board/reset`).
- Auth: Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`. OpenAI is
  Agora-managed (keyless). `OPENAI_API_KEY` is optional.

## Routing / ownership

- UI and RTC/RTM lifecycle live in `web/`.
- Browser-facing `/api/*` paths are Next rewrites (`web/next.config.ts`) to the
  agent backend; do not add `web/app/api/**/route.ts` for agent/token logic.
- Token generation and agent lifecycle live in `server/src/`.
- All 4 MCP board tools live in `server/src/mcp_server.py`; pure board store in
  `server/src/board.py` (no MCP import, fully unit-testable).
- The FastMCP server is mounted at `/mcp` inside `server/src/server.py` via
  `app.mount("/", _mcp_asgi)` with a shared lifespan. The API router is included
  before the mount so token and board endpoints take precedence.

## The 4 tools

| Tool | Purpose |
| --- | --- |
| `add_task(title)` | Add a new task to the To Do column |
| `move_task(title, column)` | Move a task to To Do, In Progress, or Done (fuzzy-matched title; "done/finished/complete" all map to Done) |
| `delete_task(title)` | Remove a task from the board (fuzzy-matched title) |
| `list_tasks()` | Return the whole board grouped by column — call only when the user explicitly asks |

Each tool is **self-contained** — the board mutation and snapshot embedding
happen inside `board.py`. One user utterance maps to at most one tool call.

## Supported modes

- **Local:** `bun run dev` starts `server` (:8000, serving token endpoints,
  board endpoints, and `/mcp`) and `web` (:3000). The web app calls `/api/*`;
  Next rewrites to `AGENT_BACKEND_URL=http://localhost:8000`. The backend must be
  exposed publicly (ngrok) so Agora cloud can reach `/mcp`.
- **Deploy:** deploy `web` (Next) + `server` (a single publicly reachable FastAPI
  process that also serves `/mcp` and `/board`). Set `AGENT_BACKEND_URL` in the
  web deployment.

## Key env vars

| Variable | Notes |
| --- | --- |
| `MCP_ENDPOINT` | Required, public ngrok URL ending in `/mcp` (e.g. `https://<tunnel>/mcp`) |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `BOARD_DB_PATH` | Default `board.db` in server root; `/tmp/board.db` in Docker |
| `OPENAI_API_KEY` | Optional — Agora manages it (keyless) |

## Patterns

- Keep the web client calling `/api/*`; hide backend placement behind Next rewrites.
- Keep token generation and the App Certificate in `server/`.
- Keep `server/src/board.py` free of MCP imports — it is a standalone board store.
- `MCP_ENDPOINT` is required and must be public; there is no localhost default.
- `OPENAI_API_KEY` is optional — Agora manages it (keyless).
- Tools are self-contained — do not add tool-call chaining (the LLM resolves
  one utterance with at most one tool call).
- Every mutating board operation must return a string that embeds the
  post-mutation snapshot (so the LLM can confirm what changed in one sentence).

## Anti-patterns

- Do not reintroduce Next Route Handlers for agent/token logic.
- Do not separate `mcp_server.py` and `board.py` into a standalone process.
- Do not default `MCP_ENDPOINT` to localhost.
- Do not put MCP imports in `board.py` — it must remain independently testable.
- Do not put `PORT` in `server/.env.example` (it would clobber the random port
  that `verify:local:fastapi` injects via `load_dotenv(override=True)`).
- Do not change `server/src/board.py`, `server/src/mcp_server.py`, or
  `server/src/agent.py` without reading the full file first.

## Commands

```bash
bun run setup
bun run dev
bun run doctor
bun run doctor:local
bun run verify         # web-only, no creds
bun run verify:local   # full local gate
```

Narrower checks: `bun run verify:backend`, `bun run verify:web:proxy`.

## Done criteria

1. Run the narrowest relevant verification command.
2. Web-affecting changes: `bun run verify:web` passes.
3. Backend-affecting changes: `bun run verify:local` (or the narrower
   `verify:backend`) passes.
4. If you change required env vars or setup steps, update the root README, the
   relevant module README, and `server/.env.example` together.

## Git Conventions

### Commit messages — conventional commits

- **Format:** `type: description` or `type(scope): description`
- **Types:** `feat:` (new feature), `fix:` (bug fix), `chore:` (maintenance, version bumps), `test:` (test additions/changes), `docs:` (documentation)
- **Scoped variant:** `feat(scope):`, `fix(scope):` — e.g. `fix(server): validate mcp endpoint`
- **Lowercase after prefix** — `feat: add feature`, not `feat: Add feature`
- **Present tense** — "add feature", not "added feature"

### Branch names

- **Format:** `type/short-description` — lowercase, hyphen-separated
- **Types match commit types:** `feat/`, `fix/`, `chore/`, `test/`, `docs/`
- **Examples:** `feat/add-board-tool`, `fix/mcp-endpoint-validation`, `docs/progressive-disclosure`

### General rules

- **Repo-local `AGENTS.md` is the authoritative source for repo conventions.**
- **No AI tool names** — never mention claude, cursor, copilot, cody, aider, gemini, codex, chatgpt, or gpt-3/4 in commit messages or PR descriptions.
- **No Co-Authored-By trailers** — omit AI attribution lines.
- **No `--no-verify`** — let git hooks run normally.
- **No git config changes** — do not modify `user.name` or `user.email`.

## Doc Commands

| Command       | When to use                                                                  |
| ------------- | ---------------------------------------------------------------------------- |
| generate docs | No `docs/ai/` directory exists yet                                           |
| update docs   | Code changed since the `Last Reviewed` date in L0                            |
| test docs     | Verify docs give agents the right context (writes `docs/ai/test-results.md`) |
| fix docs      | Close findings from a docs review or test run                                |

See the [progressive disclosure standard](https://github.com/AgoraIO-Community/ai-devkit/blob/main/docs/standard/progressive-disclosure-standard.md) and [workflows](https://github.com/AgoraIO-Community/ai-devkit/blob/main/docs/workflows/progressive-disclosure-docs.md) for the full specification.
