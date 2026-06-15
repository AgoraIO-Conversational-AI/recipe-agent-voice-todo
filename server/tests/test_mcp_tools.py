import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_run_wrapper_invokes_board_op_and_returns_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("BOARD_DB_PATH", str(tmp_path / "board.db"))
    import board
    import mcp_server
    reply = mcp_server._run(board.add_task, "Test task")
    assert "Test task" in reply
    assert "Board now" in reply


def test_run_wrapper_no_match_path(tmp_path, monkeypatch):
    monkeypatch.setenv("BOARD_DB_PATH", str(tmp_path / "board.db"))
    import board
    import mcp_server
    reply = mcp_server._run(board.move_task, "zzz nope", "done")
    assert "No task matching" in reply


def test_mcp_server_imports_no_agora():
    src = os.path.join(os.path.dirname(__file__), "..", "src", "mcp_server.py")
    tree = ast.parse(open(src, encoding="utf-8").read())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    assert not any((n or "").startswith("agora") for n in names), names
