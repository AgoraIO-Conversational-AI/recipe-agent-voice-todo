# Progressive Disclosure — Test Results

> Test run for `recipe-agent-voice-todo` progressive disclosure docs.
> Date: 2026-06-25 · Standard: AgoraIO-Community/ai-devkit progressive-disclosure.

## Step 1 — Structural checks

| Check                                                            | Result       |
| ---------------------------------------------------------------- | ------------ |
| `L0_repo_card.md` ≤ 50 lines                                     | Pass (36)    |
| All 8 L1 files present                                           | Pass         |
| Each L1 has purpose blockquote + Related Deep Dives              | Pass         |
| L1 line counts in 80–200 target                                  | **Below target** (46–116) — see note |
| L2 `_index.md` present                                           | Pass         |
| Each L2 opens with "When to Read This" callout                   | Pass (2/2)   |
| Relative links resolve (`docs/ai/` tree)                         | Pass (35/35, 0 broken) |
| AGENTS.md has How to Load / Git Conventions / Doc Commands       | Pass         |

**Note on L1 line counts:** files are table-dense and information-complete but
run 46–116 lines. `01_setup.md` (78) and `06_interfaces.md` (116) approach or
reach the target. Lower files are concise by design rather than padded.
Accepted deviation; revisit if a section needs more depth.

## Step 2/3 — Question runs

Questions span the five standard categories. Each answer was checked against the
repo source before being marked Pass. "Level" is the lowest disclosure level
that fully answers the question.

### Setup & Build

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 1 | How do I install and run it locally? | `bun run setup`, start ngrok, set `MCP_ENDPOINT`, `bun run dev` (backend :8000 + web :3000). | `L1/01_setup.md` ↔ `package.json`, `README.md` | L1 | Pass |
| 2 | Which env vars are required? | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `MCP_ENDPOINT`. | `L1/01_setup.md`, `06_interfaces.md` ↔ `agent.py`, `.env.example` | L1 | Pass |
| 3 | Is this zero-key? | Yes — OpenAI is Agora-managed; `OPENAI_API_KEY` is optional. | `L1/01_setup.md`, `07_gotchas.md` ↔ `README.md`, `agent.py` | L1 | Pass |

### Test & Run

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 4 | How do I run backend tests without cloud creds? | `cd server && pytest tests -v`; `conftest.py` fakes env + SDK session; board tests use tmp SQLite. | `L1/04_conventions.md`, `01_setup.md` ↔ `tests/conftest.py` | L1 | Pass (ran: 26 passed) |
| 5 | What's the narrowest gate for a web-only change? | `bun run verify:web`. | `L1/05_workflows.md` ↔ `package.json` | L1 | Pass |
| 6 | What does `verify:local:fastapi` do? | Spawns real FastAPI with `FakeAgent` via `scripts/run_fake_server.py`; proxies routes through the rewrite map. | `L1/03_code_map.md`, `05_workflows.md` ↔ `web/scripts/verify-local-fastapi.ts` | L1 | Pass |

### Conventions

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 7 | What response shape do backend routes use? | `{ code, msg, data }`; `data` only when there's a payload. | `L1/04_conventions.md`, `06_interfaces.md` ↔ `server.py` | L1 | Pass |
| 8 | Why must `board.py` have no MCP imports? | So the board store is independently unit-testable without MCP or agora_agent in scope. | `L1/04_conventions.md` ↔ `board.py`, `tests/test_mcp_tools.py` AST check | L1 | Pass |
| 9 | What are the commit/branch conventions? | Conventional commits `type: description`; branches `type/short-description`; no AI tool names; no Co-Authored-By. | `AGENTS.md` Git Conventions | L0 | Pass |

### Development

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 10 | How do I add a new board tool? | Add board op to `board.py` (no MCP imports) → add `@mcp.tool()` to `mcp_server.py` → update `TODO_PROMPT` in `agent.py` → add tests. | `L1/05_workflows.md` ↔ source files | L1 | Pass |
| 11 | Why does the router need to come before the MCP mount? | FastAPI first-match routing: `app.include_router(router)` before `app.mount("/", _mcp_asgi)` ensures `/get_config`, `/board`, etc. aren't caught by the MCP catch-all. | `L1/07_gotchas.md` ↔ `server.py` | L1 | Pass |
| 12 | Where does token generation live, and where is the MCP endpoint called from? | Token: `server/src/server.py` (`generate_convo_ai_token`). MCP calls: Agora cloud POSTs to the public `MCP_ENDPOINT`; the browser never calls `/mcp`. | `L1/02_architecture.md`, `08_security.md` ↔ `server.py`, `ARCHITECTURE.md` | L1 | Pass |

### Deep Dive

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 13 | How does fuzzy title matching work in `move_task`? | `find_task(conn, title)` does exact → substring → token-overlap passes; `parse_column` uses longest-phrase-first synonym matching to avoid "to do" swallowing "done". | `L2/mcp_tools_and_board_store.md` ↔ `board.py`, `tests/test_board.py` | L2 | Pass |
| 14 | Why does the web client poll `GET /board` instead of receiving RTM push updates? | RTM events are per-turn, not per-mutation. Polling is simpler and keeps the board store decoupled from RTM channels. | `L2/board_state_sync.md` ↔ `web/src/lib/board.ts`, `README.md` | L2 | Pass |
| 15 | What is the `mcp_servers` transport convention mismatch? | Agora SDK uses `"streamable_http"` (underscore); FastMCP uses `"streamable-http"` (hyphen). They must not be unified — see `mcp_config.py`. | `L1/07_gotchas.md`, `L2/mcp_tools_and_board_store.md` ↔ `mcp_config.py`, `mcp_server.py` | L1+L2 | Pass |

## Step 4 — Analysis

- All 15 questions answered at the expected disclosure level (12 at L1, 3 requiring L2).
  No "correct but needed L2 unnecessarily" or "wrong/missing L2" cases.
- No missing-coverage findings; no broken relative links in `docs/ai/`.
- One soft deviation: L1 line counts below the 80–200 target for most files (accepted; table-dense and complete).
- `pytest` ran against a throwaway venv `/tmp/v_voice_todo`; venv removed after run.

## Step 5 — Summary

| Category       | Questions | Pass | Notes |
| -------------- | :-------: | :--: | ----- |
| Setup & Build  | 3 | 3 | — |
| Test & Run     | 3 | 3 | backend tests executed: 26 passed |
| Conventions    | 3 | 3 | — |
| Development    | 3 | 3 | — |
| Deep Dive      | 3 | 3 | resolved at L2 as designed |
| **Total**      | **15** | **15** | — |

## Step 6 — Fixes / Retest

No failing questions; no fixes required. Evidence executed during this run:

- `pytest tests -v` (throwaway venv `/tmp/v_voice_todo`, Python 3.14.4) → `26 passed, 1 warning`.
- Warning: `httpx` deprecation in `fastapi.testclient` — informational, does not affect test results.
- Relative link check (`docs/ai/` tree) → `35 checked, 0 broken`.
