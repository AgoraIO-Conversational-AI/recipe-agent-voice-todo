"""Pure todo-board store — SQLite-backed, no MCP/agora import (fully unit-testable).

State is global (single-user demo — the MCP server gets no session id from Agora).
Every mutating op returns a human-readable string that EMBEDS the post-mutation
board snapshot, so the LLM tool result is self-grounding in a single call.
"""
import os
import sqlite3
import time

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("BOARD_DB_PATH") or os.path.join(_base_dir, "board.db")

COLUMNS = ("todo", "in_progress", "done")
COLUMN_LABELS = {"todo": "To Do", "in_progress": "In Progress", "done": "Done"}

# Free-text phrase -> canonical column. Longest phrases win (see parse_column).
_COLUMN_SYNONYMS = {
    "to do": "todo", "todo": "todo", "backlog": "todo", "not started": "todo",
    "in progress": "in_progress", "in-progress": "in_progress", "doing": "in_progress",
    "working on": "in_progress", "started": "in_progress", "wip": "in_progress",
    "done": "done", "complete": "done", "completed": "done", "finished": "done",
}

SEED_TASKS = [
    ("Buy milk", "todo"),
    ("Walk dog", "todo"),
    ("Call mom", "todo"),
    ("Email Bob", "in_progress"),
    ("Pay rent", "done"),
]


def get_db(path: str = DB_PATH) -> "sqlite3.Connection":
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    conn.commit()
    _seed_once(conn)
    return conn


def _insert_seed(conn) -> None:
    now = time.time()
    for i, (title, status) in enumerate(SEED_TASKS):
        conn.execute(
            "INSERT INTO tasks (title, status, created_at) VALUES (?, ?, ?)",
            (title, status, now + i),
        )


def _seed_once(conn) -> None:
    # Seed exactly once (first init). If the user later deletes every task, an
    # empty board is a valid state — we must NOT re-seed on the next connection.
    seeded = conn.execute("SELECT value FROM meta WHERE key='seeded'").fetchone()
    if seeded is None:
        _insert_seed(conn)
        conn.execute("INSERT INTO meta (key, value) VALUES ('seeded', '1')")
        conn.commit()


def parse_column(text: str):
    """Map free text to a canonical column key, or None."""
    t = (text or "").strip().lower()
    if t in _COLUMN_SYNONYMS:
        return _COLUMN_SYNONYMS[t]
    for phrase in sorted(_COLUMN_SYNONYMS, key=len, reverse=True):
        if phrase in t:
            return _COLUMN_SYNONYMS[phrase]
    return None


def find_task(conn, title: str):
    """Fuzzy-match a stored task by spoken title. Returns (id, title, status) or None."""
    q = (title or "").strip().lower()
    if not q:
        return None
    rows = conn.execute(
        "SELECT id, title, status FROM tasks ORDER BY created_at DESC, id DESC"
    ).fetchall()
    for r in rows:                       # 1) exact, case-insensitive
        if r[1].lower() == q:
            return r
    for r in rows:                       # 2) substring either direction
        tl = r[1].lower()
        if q in tl or tl in q:
            return r
    qtokens = set(q.split())             # 3) token overlap
    best, best_score = None, 0
    for r in rows:
        score = len(qtokens & set(r[1].lower().split()))
        if score > best_score:
            best, best_score = r, score
    return best if best_score > 0 else None


def snapshot(conn) -> dict:
    rows = conn.execute(
        "SELECT id, title, status FROM tasks ORDER BY created_at ASC, id ASC"
    ).fetchall()
    board = {c: [] for c in COLUMNS}
    for tid, title, status in rows:
        if status in board:
            board[status].append({"id": tid, "title": title})
    return board


def _render(conn) -> str:
    snap = snapshot(conn)
    parts = []
    for c in COLUMNS:
        titles = ", ".join(t["title"] for t in snap[c]) or "(empty)"
        parts.append(f"{COLUMN_LABELS[c]} — {titles}")
    return "; ".join(parts)


def add_task(conn, title: str) -> str:
    title = (title or "").strip()
    if not title:
        return f"I didn't catch a task name. Board now: {_render(conn)}"
    row = conn.execute("SELECT MAX(created_at) FROM tasks").fetchone()
    existing_max = row[0] or 0.0
    created_at = max(time.time(), existing_max + 1)
    conn.execute(
        "INSERT INTO tasks (title, status, created_at) VALUES (?, 'todo', ?)",
        (title, created_at),
    )
    conn.commit()
    return f'Added "{title}" to To Do. Board now: {_render(conn)}'


def move_task(conn, title: str, column: str) -> str:
    col = parse_column(column)
    if col is None:
        return (f"'{column}' isn't a column. Valid columns: To Do, In Progress, Done. "
                f"Board now: {_render(conn)}")
    row = find_task(conn, title)
    if row is None:
        return f"No task matching '{title}'. Current tasks: {_render(conn)}"
    conn.execute("UPDATE tasks SET status=? WHERE id=?", (col, row[0]))
    conn.commit()
    return f'Moved "{row[1]}" to {COLUMN_LABELS[col]}. Board now: {_render(conn)}'


def delete_task(conn, title: str) -> str:
    row = find_task(conn, title)
    if row is None:
        return f"No task matching '{title}'. Current tasks: {_render(conn)}"
    conn.execute("DELETE FROM tasks WHERE id=?", (row[0],))
    conn.commit()
    return f'Deleted "{row[1]}". Board now: {_render(conn)}'


def list_tasks(conn) -> str:
    snap = snapshot(conn)
    if not any(snap.values()):
        return "Your board is empty. Say 'add buy milk' to create a task."
    return f"Here's your board: {_render(conn)}"


def reset(conn) -> str:
    conn.execute("DELETE FROM tasks")
    _insert_seed(conn)
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('seeded', '1')")
    conn.commit()
    return _render(conn)
