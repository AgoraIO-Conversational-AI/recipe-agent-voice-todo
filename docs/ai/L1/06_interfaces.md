# 06 · Interfaces

> Boundary contracts: backend routes, the `/api/*` rewrite map, env vars, the response envelope, MCP tool signatures, and `mcp_servers` config.

## Backend routes (port 8000)

The browser calls these as `/api/<name>`; Next rewrites to the backend `/<name>`. Agora cloud calls `/mcp` directly via the public `MCP_ENDPOINT`.

### `GET /get_config`

- Query (optional): `channel?: string`, `uid?: int` (≤ 0 or missing → backend generates one).
- Returns `data`: `{ app_id, token, uid (string), channel_name, agent_uid (string) }`.
- Token is a Token007 RTC+RTM token, expiry 3600s, for a concrete non-zero UID.

### `POST /startAgent`

- Body: `{ channelName: string, rtcUid: int, userUid: int, parameters?: object }`.
  - `parameters.output_audio_codec?: string` is the only honored parameter field.
- Returns `data`: `{ agent_id, channel_name, status: "started" }`.
- 400 if `channelName`/`rtcUid`/`userUid` invalid; 500 if `Agent` is not configured.

### `POST /stopAgent`

- Body: `{ agentId: string }`.
- Returns `{ code: 0, msg: "success" }` (no `data`).

### `GET /board`

- No query params.
- Returns `data`: `{ todo: [{id, title}], in_progress: [{id, title}], done: [{id, title}] }`.
- Reads the live SQLite board. Does not require an active agent session.

### `POST /board/reset`

- No body.
- Returns `data`: the board snapshot after clearing and restoring the 5 seed tasks.

## Response envelope

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` omitted when the route has no payload. Non-zero `code` or missing `data` = error on the client side.

## Rewrite map (`web/next.config.ts`)

| Browser path          | Backend destination   |
| --------------------- | --------------------- |
| `/api/get_config`     | `/get_config`         |
| `/api/startAgent`     | `/startAgent`         |
| `/api/stopAgent`      | `/stopAgent`          |
| `/api/board`          | `/board`              |
| `/api/board/reset`    | `/board/reset`        |

`rewrites()` returns `[]` when `AGENT_BACKEND_URL` is unset. The contract is asserted by `verify-api-contracts.ts` and exercised by `verify-local-proxy.ts`.

## Browser API client (`web/src/services/api.ts`)

- `getConfig({ channel?, uid? }) → GetConfigResponse`
- `startAgent(channelName, rtcUid, userUid) → agent_id`
- `stopAgent(agentId) → void`
- `getBoard() → BoardSnapshot`
- `resetBoard() → BoardSnapshot`

## Environment variables

| Variable                | Scope              | Required | Default               |
| ----------------------- | ------------------ | :------: | --------------------- |
| `AGORA_APP_ID`          | backend            |    ✅    | —                     |
| `AGORA_APP_CERTIFICATE` | backend            |    ✅    | —                     |
| `MCP_ENDPOINT`          | backend            |    ✅    | — (validated at init) |
| `OPENAI_MODEL`          | backend            |          | `gpt-4o-mini`         |
| `BOARD_DB_PATH`         | backend            |          | `board.db` in server root |
| `OPENAI_API_KEY`        | backend            |          | — (Agora-managed; optional) |
| `AGENT_GREETING`        | backend            |          | built-in line         |
| `AGENT_BACKEND_URL`     | web (deploy)       |    ✅\*  | `http://localhost:8000` (dev) |
| `PORT`                  | backend (env only) |          | `8000` — do **not** put in `.env.example` |

\* Required wherever the web app is deployed; rewrites are empty without it.

## MCP tool signatures

Agora cloud calls these at `MCP_ENDPOINT` (streamable-http transport). Tool docstrings are read by the managed LLM.

| Tool                                | Parameter(s)                        | Result string includes             |
| ----------------------------------- | ----------------------------------- | ---------------------------------- |
| `add_task(title: str)`              | `title` — the task text spoken      | Confirmation + full board snapshot |
| `move_task(title: str, column: str)`| fuzzy title; column free-text       | Confirmation + full board snapshot |
| `delete_task(title: str)`           | fuzzy title                         | Confirmation + full board snapshot |
| `list_tasks()`                      | none                                | Full board snapshot by column      |

`column` accepts free-text (e.g. "done", "finished", "in progress", "wip") — parsed to a canonical key in `board.py`.

## `mcp_servers` config (`server/src/mcp_config.py`)

`build_mcp_servers(endpoint, name="todo")` returns:

```python
[{"name": "todo", "endpoint": endpoint, "transport": "streamable_http"}]
```

Note the underscore in `"streamable_http"` — this is the Agora SDK convention. The FastMCP server itself uses `"streamable-http"` (hyphen) in its run transport. Do not unify them.

## `Agent` vendor config (`server/src/agent.py`)

`Agent.start()` builds:

- `OpenAI(api_key=..., model=OPENAI_MODEL, system_messages=[TODO_PROMPT], mcp_servers=..., greeting_message=...)`
- `DeepgramSTT(model="nova-3", language="en")`
- `MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")`
- `advanced_features={"enable_rtm": True, "enable_tools": True}` on `AgoraAgent`

## Related Deep Dives

- [mcp_tools_and_board_store](L2/mcp_tools_and_board_store.md) — full tool wiring and board store detail.
