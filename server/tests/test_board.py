import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import board  # noqa: E402


def fresh():
    path = os.path.join(tempfile.mkdtemp(), "board.db")
    return board.get_db(path), path


def test_seeds_five_tasks_on_fresh_db():
    conn, _ = fresh()
    snap = board.snapshot(conn)
    total = sum(len(snap[c]) for c in board.COLUMNS)
    assert total == 5
    titles = [t["title"] for c in board.COLUMNS for t in snap[c]]
    assert "Buy milk" in titles and "Pay rent" in titles


def test_snapshot_groups_by_column():
    conn, _ = fresh()
    snap = board.snapshot(conn)
    assert [t["title"] for t in snap["done"]] == ["Pay rent"]
    assert [t["title"] for t in snap["in_progress"]] == ["Email Bob"]


def test_parse_column_synonyms():
    assert board.parse_column("in progress") == "in_progress"
    assert board.parse_column("doing") == "in_progress"
    assert board.parse_column("finished") == "done"
    assert board.parse_column("backlog") == "todo"
    assert board.parse_column("i'm working on it") == "in_progress"
    assert board.parse_column("nonsense") is None


def test_parse_column_to_done_is_not_todo():
    # "to do" must not swallow "done" as a substring.
    assert board.parse_column("move to done") == "done"
    assert board.parse_column("to done") == "done"
    assert board.parse_column("move it to do") == "todo"


def test_parse_column_accepts_canonical_keys():
    assert board.parse_column("in_progress") == "in_progress"
    assert board.parse_column("todo") == "todo"
    assert board.parse_column("done") == "done"


def test_find_task_fuzzy():
    conn, _ = fresh()
    assert board.find_task(conn, "milk")[1] == "Buy milk"
    assert board.find_task(conn, "the dog walking one")[1] == "Walk dog"
    assert board.find_task(conn, "zzz") is None


def test_add_task_lands_in_todo_and_returns_snapshot():
    conn, _ = fresh()
    msg = board.add_task(conn, "Water the plants")
    assert "Water the plants" in msg and "To Do" in msg
    assert [t["title"] for t in board.snapshot(conn)["todo"]][-1] == "Water the plants"


def test_move_task_changes_column():
    conn, _ = fresh()
    msg = board.move_task(conn, "buy milk", "in progress")
    assert "Buy milk" in msg and "In Progress" in msg
    assert any(t["title"] == "Buy milk" for t in board.snapshot(conn)["in_progress"])


def test_move_unknown_column_reports_valid_columns():
    conn, _ = fresh()
    msg = board.move_task(conn, "buy milk", "sideways")
    assert "To Do" in msg and "In Progress" in msg and "Done" in msg
    assert any(t["title"] == "Buy milk" for t in board.snapshot(conn)["todo"])  # unmoved


def test_move_no_match_does_not_mutate():
    conn, _ = fresh()
    before = board.snapshot(conn)
    msg = board.move_task(conn, "zzz nonexistent", "done")
    assert "No task matching" in msg
    assert board.snapshot(conn) == before


def test_delete_task_removes_it():
    conn, _ = fresh()
    board.delete_task(conn, "call mom")
    titles = [t["title"] for c in board.COLUMNS for t in board.snapshot(conn)[c]]
    assert "Call mom" not in titles


def test_list_tasks_when_empty_after_deleting_all():
    conn, _ = fresh()
    for title in ["Buy milk", "Walk dog", "Call mom", "Email Bob", "Pay rent"]:
        board.delete_task(conn, title)
    assert "empty" in board.list_tasks(conn).lower()


def test_deleting_all_does_not_reseed_on_next_connection():
    conn, path = fresh()
    for title in ["Buy milk", "Walk dog", "Call mom", "Email Bob", "Pay rent"]:
        board.delete_task(conn, title)
    conn2 = board.get_db(path)  # reopen
    total = sum(len(board.snapshot(conn2)[c]) for c in board.COLUMNS)
    assert total == 0  # seeded ONCE, not on every empty connection


def test_reset_restores_seed():
    conn, _ = fresh()
    board.delete_task(conn, "buy milk")
    board.reset(conn)
    titles = [t["title"] for c in board.COLUMNS for t in board.snapshot(conn)[c]]
    assert "Buy milk" in titles and len(titles) == 5


def test_persistence_across_connections():
    conn, path = fresh()
    board.add_task(conn, "Remember me")
    conn.close()
    conn2 = board.get_db(path)
    titles = [t["title"] for c in board.COLUMNS for t in board.snapshot(conn2)[c]]
    assert "Remember me" in titles
