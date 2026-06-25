# 08 · Security

> Trust boundaries, secret handling, and auth for the voice todo board recipe.

## Trust boundaries

| Hop                                    | Auth                                                                              |
| -------------------------------------- | --------------------------------------------------------------------------------- |
| Browser → agent backend                | None in local dev (the `/api/*` rewrite is same-origin).                          |
| Agent backend → Agora cloud            | Token007, generated from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.                |
| Agora cloud → FastMCP todo server (`/mcp`) | Streamable-HTTP (no auth on the dev server; add it for production use).       |
| Agora cloud → OpenAI                   | Agora-managed key (keyless). Optional: supply `OPENAI_API_KEY` to use your own.   |

## Secret handling

- **Server-only secrets:** `AGORA_APP_CERTIFICATE` lives only in `server/.env.local` and never reaches the browser. The browser receives a short-lived token, never the certificate.
- `OPENAI_API_KEY` is optional; if supplied, it is kept in `server/.env.local` and passed to the managed `OpenAI` vendor — it never leaves the backend.
- `server/.env.local` is gitignored; `server/.env.example` ships placeholders only.
- Tokens (`generate_convo_ai_token`) expire after 3600s and are minted per `get_config` call for a concrete non-zero UID.

## Co-public port

Port 8000 serves both the browser-facing token/agent endpoints and the FastMCP todo server (`/mcp`). In local dev, the ngrok tunnel makes both paths reachable from the public internet. In production, `/get_config` and `/startAgent` are unauthenticated. **Add authentication and rate-limiting before exposing the backend on a production URL.**

## CORS

The backend sets `CORSMiddleware` with `allow_origins=["*"]` — open by design for a local/dev recipe. **Lock this down to known origins before any production deployment.**

## Validation

- `Agent.__init__` raises `ValueError` for missing `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, or `MCP_ENDPOINT` at startup.
- `Agent.start()` rejects empty `channel_name` and non-positive `agent_uid`/`user_uid` before issuing tokens or starting a session.
- Route errors are sanitized: `_log_route_error` logs only non-`None` context; SDK exceptions map to 400/500 without leaking internals to the client beyond the message.

## MCP endpoint exposure

The FastMCP todo server at `/mcp` is mounted in-process on port 8000. It is designed to be called by Agora cloud (it needs public access for tool calls), but in dev configuration there is no auth on the `/mcp` path. The board state (SQLite) is a demo store — there are no user secrets in it, but the endpoint can be called by anyone with the tunnel URL. Add transport-level auth before production use.

## Deployment notes

- Set `AGENT_BACKEND_URL` only to a backend you control; the rewrite forwards browser requests there verbatim.
- The published Docker image is **backend-only** (`:8000`); it does not bundle secrets. The SQLite board is stored at `/tmp/board.db` in the container (set `BOARD_DB_PATH` to persist it outside the container).

## Related Deep Dives

- None.
