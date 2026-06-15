# Architecture — RPG Gaming Recipe

Two processes. The browser talks only to Next.js `/api/*`, which rewrites to
the agent backend. The agent backend owns Agora tokens, agent lifecycle, **and**
the FastMCP game server — all in one process on port 8000.

**MCP multi-tool spike: GO (2026-06-12)** — a live Agora session confirmed `create_character` then `start_encounter` fired as distinct tools with SQLite state persisting across calls; the managed-LLM DM reliably called the tools.

## Request flow

```
Browser
  │  GET /api/get_config            → token + channel/UIDs
  │  POST /api/startAgent           → start Dungeon Master agent session
  ▼
Next.js  (rewrites /api/* → AGENT_BACKEND_URL)
  ▼
Agent backend (server/, :8000)
  │  builds session with OpenAI(mcp_servers=[{endpoint: MCP_ENDPOINT}])
  │  also mounts FastMCP at /mcp (same process, same port)
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT (managed)
  │  managed Dungeon Master LLM (keyless OpenAI) → emits tool call
  │  POST <MCP_ENDPOINT>   (streamable-http transport)
  ▼
FastMCP game server (/mcp, same process as agent backend, public via tunnel)
  │  executes tool (create_character / get_character / start_encounter /
  │                 attack / cast_spell / flee)
  │  → rolls dice, updates SQLite, returns plain-English result
  ▼
Agora ConvoAI Cloud → DM LLM incorporates result → narrates outcome
                     → MiniMax TTS (managed) → user hears speech
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## Single-process design

The FastMCP game server is mounted in-process via `app.mount("/", _mcp_asgi)` in
`server/src/server.py`. A shared lifespan manages the MCP session manager. This
means:

- One port (8000) and one tunnel handle both token endpoints and MCP tool calls.
- Agora cloud calls `<public-url>/mcp` — the same URL the browser reaches for
  `/get_config` and `/startAgent`, just at the `/mcp` path.
- The `server/src/game.py` engine has no MCP dependency and remains fully
  unit-testable in isolation.

## Self-contained tools

Each of the 6 tools resolves a **whole action** in one call. Dice are rolled
inside `game.py`, not by the LLM. This design means:

- The DM never needs to chain multiple tool calls for one player utterance.
- Game outcomes are reproducible with `RPG_SEED`.
- The LLM's only job is narrative; it cannot invent HP values or loot.

## Single-player global state

SQLite state is global (no session id, matching Agora's single-user-per-session
model). The `character`, `enemy`, and `settings` tables each hold at most one
row. `get_character` is the voice-first stat sheet — the player asks the DM,
and the DM reads it aloud via the tool result; there is no character-sheet UI.

## Narrator ↔ combat flow

```
[narration mode]  player: "start a fight"
  → DM calls start_encounter() → enemy spawns, mode → "combat"
[combat mode]     player: "attack"
  → DM calls attack() → dice rolled, damage applied, enemy counterattacks
  → if enemy HP ≤ 0: mode → "narration", loot awarded
  → if player HP ≤ 0: hero deleted, mode → "narration", game over message
  → player: "run away"  → DM calls flee() → enemy cleared, mode → "narration"
```

## Distinct from recipe-agent-tool-calling

In `recipe-agent-tool-calling` the tools run **inside** the `llm/` endpoint:
the agent's custom LLM proxy intercepts tool calls and handles them locally. In
this recipe Agora cloud orchestrates the tools on the **FastMCP server** via the
MCP protocol — the managed OpenAI vendor issues the tool call, Agora invokes
`MCP_ENDPOINT` (served at `/mcp` by the same backend process), and the result
flows back to the DM LLM.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the Dungeon Master agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |
| `/mcp` | POST | FastMCP streamable-HTTP endpoint (called by Agora cloud) |

The browser calls `/get_config`, `/startAgent`, `/stopAgent` as `/api/*`; Next
rewrites them to `AGENT_BACKEND_URL`. Agora cloud calls `/mcp` directly via the
public `MCP_ENDPOINT`.

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007, generated from `AGORA_APP_ID` +
  `AGORA_APP_CERTIFICATE`.
- Agora cloud → FastMCP game server (`/mcp`): streamable-http (no auth on the
  dev server; add it for production use).
- OpenAI: Agora-managed (keyless) — `OPENAI_API_KEY` is optional.
