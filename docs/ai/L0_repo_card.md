# recipe-agent-voice-todo — Repo Card

> Next.js web client + Python FastAPI backend for a voice-driven kanban board. A managed-keyless OpenAI assistant manages 3-column tasks through 4 MCP tools mounted in-process; the web client polls GET /board and cards move columns in real time.

## Identity

| Field          | Value                                                                                          |
| -------------- | ---------------------------------------------------------------------------------------------- |
| Repo           | `AgoraIO-Conversational-AI/recipe-agent-voice-todo`                                            |
| Type           | `distributed-system` (single repo, two co-located processes + in-process MCP server)          |
| Language       | Python 3.10+ (FastAPI + uvicorn) backend + Next.js / React / TypeScript web                   |
| Deploy Target  | `web/` as Next.js app, `server/` as a single publicly reachable FastAPI service (also serves `/mcp`) |
| Owner          | Agora Conversational AI DevEx                                                                  |
| Last Reviewed  | 2026-06-25                                                                                     |
| Recipe Role    | `base`                                                                                         |
| Recipe Version | `1.0.0`                                                                                        |
| Recipe Status  | `experimental`                                                                                 |

## L1 — Summaries

The Audience column helps agents prioritise: **Use** = consuming the recipe's behavior, **Maintain** = modifying internals.

| File                                     | Purpose                                                                                  | Audience       |
| ---------------------------------------- | ---------------------------------------------------------------------------------------- | -------------- |
| [01_setup](L1/01_setup.md)               | bun + venv + pip setup, env vars (incl. required `MCP_ENDPOINT`), ngrok, commands       | Use & Maintain |
| [02_architecture](L1/02_architecture.md) | Single-process topology, MCP mount, board polling, pipeline flow                        | Maintain       |
| [03_code_map](L1/03_code_map.md)         | `web/` and `server/` trees with key file responsibilities                               | Maintain       |
| [04_conventions](L1/04_conventions.md)   | Python async + FastAPI patterns, board store isolation, MCP tool shape, response envelope | Maintain       |
| [05_workflows](L1/05_workflows.md)       | Add a route, add a tool, change the LLM, swap the board store, verify, deploy           | Use            |
| [06_interfaces](L1/06_interfaces.md)     | FastAPI route contracts, rewrites, env vars, MCP tool signatures, `mcp_servers` config  | Use & Maintain |
| [07_gotchas](L1/07_gotchas.md)           | `MCP_ENDPOINT` must be public, router-before-mount order, tunnel caveats, PORT, proxies | Maintain       |
| [08_security](L1/08_security.md)         | Token007, App Certificate server-only, co-public MCP/token port, CORS, unauthenticated MCP | Maintain    |

## Recipe Profile

This repo declares `Recipe Role: base`. See [RECIPE.md](RECIPE.md) for extension points, invariants, and stable contracts before changing reusable surfaces.
