import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import mcp_config as cfg  # noqa: E402

def test_build_mcp_servers():
    s = cfg.build_mcp_servers("https://x.ngrok-free.dev/mcp")
    assert s == [{"name": "rpg", "endpoint": "https://x.ngrok-free.dev/mcp", "transport": "streamable_http"}]

def test_build_mcp_servers_custom_name():
    s = cfg.build_mcp_servers("https://x/mcp", name="weather")
    assert s[0]["name"] == "weather"
    assert s[0]["transport"] == "streamable_http"
