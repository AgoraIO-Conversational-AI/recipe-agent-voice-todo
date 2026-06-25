# Deep Dive — Board State Sync

> **When to Read This:** You are modifying the live kanban panel, changing the board polling interval, understanding the reset flow, or debugging why the web UI does not reflect the latest board state. For the high-level picture, start at [02_architecture](../02_architecture.md).

The web client does not receive board mutations over RTM. Instead it polls `GET /api/board` on a regular interval. This keeps the kanban panel decoupled from the voice session — the panel updates independently of transcript events.

## How polling works (`web/src/lib/board.ts`)

`useBoardPolling(active: boolean, intervalMs = 1000)` is a React hook that:

1. Returns `EMPTY_BOARD` (`{ todo: [], in_progress: [], done: [] }`) when `active` is false.
2. When `active` becomes true, calls `getBoard()` immediately (first tick), then sets a `setInterval` at `intervalMs` (default 1000ms).
3. On each tick, calls `getBoard()` and calls `setBoard` only when not cancelled (guards against race conditions on unmount).
4. Swallows transient fetch errors and keeps the last good board state — a brief network blip does not clear the panel.
5. Clears the interval and sets `cancelled = true` on unmount or when `active` becomes false.

`active` is `true` while `showConversation` is true in `LandingPage.tsx` — i.e. from the moment the conversation starts until the user ends it.

## `TodoBoard` component (`web/src/components/TodoBoard.tsx`)

```tsx
export function TodoBoard({ active }: { active: boolean }) {
  const board = useBoardPolling(active)
  // Renders 3 columns (To Do / In Progress / Done) from board snapshot
  // "Reset board" button calls resetBoard() from api.ts
}
```

The three columns are rendered in a CSS grid (`grid-cols-1 sm:grid-cols-3`). Each task card is a `<div>` keyed on `task.id`. The column count badge (`col.label · board[col.key].length`) updates on every poll.

## Reset flow

When the user clicks "Reset board":
1. `setResetting(true)` disables the button.
2. `resetBoard()` POSTs to `/api/board/reset`; the backend calls `board.reset(conn)` which deletes all tasks and re-inserts the 5 seed tasks, then returns the new snapshot.
3. On success or error, `setResetting(false)` re-enables the button. On error, no state is cleared — the next poll will reflect the true state.

## SQLite state model

Board state is global — there is no per-session or per-user key in the SQLite schema. This is intentional for the single-user demo model: Agora's ConvoAI Engine starts one session at a time per channel, and the board is shared across all board reads.

The `meta` table records `key='seeded'` to track first-time initialization. Seeding happens exactly once:
- First `get_db()` call inserts the 5 seed tasks (`Buy milk`, `Walk dog`, `Call mom`, `Email Bob`, `Pay rent`) and writes `meta.seeded=1`.
- Subsequent `get_db()` calls find `meta.seeded=1` and skip seeding — so deleting all tasks results in an empty board (a valid state), not a re-seeded board.
- `POST /board/reset` uses `board.reset(conn)` which deletes tasks and re-inserts seeds, updating `meta.seeded` with `INSERT OR REPLACE`.

## Board API endpoints

`GET /board` and `POST /board/reset` are served by the FastAPI router (not through the MCP mount). They read/write from the same `board.db` file that the MCP tools use. There is no cache layer — every poll reads directly from SQLite.

## Why polling instead of RTM push

RTM transcript events arrive per turn, not per board mutation. Wiring board updates through RTM would require the MCP tools to emit RTM messages, coupling the board store to the RTM channel. Polling `GET /board` is simpler: the board updates automatically after any tool call, and the web client sees the change within one polling interval (default 1s).

## Related L1

- [02_architecture](../02_architecture.md) · [03_code_map](../03_code_map.md) · [06_interfaces](../06_interfaces.md)
