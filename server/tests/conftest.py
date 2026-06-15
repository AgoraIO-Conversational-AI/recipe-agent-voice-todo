"""Shared fixtures for the server test suite (standalone: no cloud, no creds)."""
import importlib
import os
import sys

import pytest

_SERVER_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SERVER_SRC not in sys.path:
    sys.path.insert(0, _SERVER_SRC)

FAKE_ENV = {
    "AGORA_APP_ID": "0123456789abcdef0123456789abcdef",
    "AGORA_APP_CERTIFICATE": "fedcba9876543210fedcba9876543210",
    "MCP_ENDPOINT": "https://example.ngrok-free.dev/mcp",
    "OPENAI_MODEL": "gpt-4o-mini",
}


@pytest.fixture
def fake_env(monkeypatch, tmp_path):
    import dotenv
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    for key, value in FAKE_ENV.items():
        monkeypatch.setenv(key, value)
    # Point the board at a throwaway DB so tests never touch server/board.db.
    monkeypatch.setenv("BOARD_DB_PATH", str(tmp_path / "board.db"))
    return dict(FAKE_ENV)


class FakeAgent:
    def __init__(self):
        self.started = []
        self.stopped = []

    async def start(self, channel_name, agent_uid, user_uid, output_audio_codec=None):
        self.started.append((channel_name, agent_uid, user_uid, output_audio_codec))
        return {"agent_id": f"fake-agent-{agent_uid}", "channel_name": channel_name,
                "status": "started"}

    async def stop(self, agent_id):
        self.stopped.append(agent_id)


@pytest.fixture
def server_module(fake_env):
    for name in ("server", "agent", "board", "mcp_server"):
        sys.modules.pop(name, None)
    import server
    importlib.reload(server)
    return server


@pytest.fixture
def client(server_module):
    from fastapi.testclient import TestClient
    fake = FakeAgent()
    server_module.agent = fake
    test_client = TestClient(server_module.app)
    test_client.fake_agent = fake
    return test_client
