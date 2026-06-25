# 01 · Setup

> Install dependencies, configure env, expose the backend publicly, and run the voice todo board recipe locally. This recipe is **zero-key**: OpenAI is Agora-managed; only Agora credentials and a public tunnel (`ngrok`) are required.

## Prerequisites

- Python 3.10+ (backend runs on 3.10 and 3.13 in CI)
- [Bun](https://bun.sh/) (runs the web app and orchestration scripts)
- [Agora CLI](https://github.com/AgoraIO/cli) (optional; easiest way to mint App ID + Certificate)
- [ngrok](https://ngrok.com/) — the `/mcp` path must be publicly reachable so Agora cloud can call it

## Install

```bash
bun run setup            # installs web deps + creates server/ venv from requirements.txt
```

`setup` runs `setup:env` (copies `server/.env.example` → `server/.env.local` if missing), `setup:server` (recreates `server/venv`, installs `requirements.txt`), and `setup:web` (`bun install`).

## Configure env

Backend env file is `server/.env.local` (template: `server/.env.example`).

| Variable                | Required | Default                    | Notes                                                                            |
| ----------------------- | :------: | -------------------------- | -------------------------------------------------------------------------------- |
| `AGORA_APP_ID`          |    ✅    | —                          | Agora Console → Project → App ID                                                 |
| `AGORA_APP_CERTIFICATE` |    ✅    | —                          | Agora Console → Project → App Certificate                                        |
| `MCP_ENDPOINT`          |    ✅    | —                          | **Public** URL ending in `/mcp` (e.g. `https://<tunnel>/mcp`). Agora cloud calls it; cannot be `localhost`. |
| `OPENAI_MODEL`          |          | `gpt-4o-mini`              | Model name for the managed todo assistant LLM                                    |
| `BOARD_DB_PATH`         |          | `board.db` in server root  | Path to the SQLite board database (`/tmp/board.db` in Docker)                    |
| `OPENAI_API_KEY`        |          | —                          | Optional — Agora manages the key (keyless by default)                            |
| `AGENT_GREETING`        |          | built-in line              | Optional override for the assistant's opening utterance                          |

Fill credentials via the Agora CLI or by hand:

```bash
agora login
agora project use <your-project>
agora project env write server/.env.local   # writes App ID + Certificate
```

Then set `MCP_ENDPOINT` after starting ngrok:

```bash
ngrok http 8000
# Add to server/.env.local:
# MCP_ENDPOINT=https://<your-tunnel>.ngrok-free.dev/mcp
```

> Do **not** add `PORT` to `server/.env.example` — see [07_gotchas](07_gotchas.md).

## Run

```bash
bun run dev              # backend (:8000, also serves /mcp) + web (:3000) via concurrently
```

Open <http://localhost:3000> → **Start Conversation** → say "add buy milk". Backend API docs at <http://localhost:8000/docs>. MCP endpoint at <http://localhost:8000/mcp> (Agora cloud calls this via the tunnel).

## Quick commands

```bash
bun run doctor           # shared prereqs (bun + node_modules); no creds needed
bun run doctor:local     # + .env.local + AGORA_APP_ID/CERTIFICATE/MCP_ENDPOINT present
bun run verify           # web-only gate (doctor + api contracts + web build)
bun run verify:local     # full local gate: backend compile + proxy + web build
bun run clean            # remove venvs and build artifacts
```

Backend unit tests run standalone (no cloud, no creds):

```bash
cd server && pytest tests -v
```

## Related Deep Dives

- None. For what each verify command asserts, see [05_workflows](05_workflows.md) and [06_interfaces](06_interfaces.md).
