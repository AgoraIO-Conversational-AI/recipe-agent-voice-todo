"""Pure builder — no agora_agent import."""
from typing import Dict, List


def build_mcp_servers(endpoint: str, name: str = "rpg") -> List[Dict[str, str]]:
    # NOTE: Agora's mcp_servers uses "streamable_http" (underscore). The FastMCP
    # server in mcp/ uses "streamable-http" (hyphen). Different SDK conventions —
    # do not "unify" them.
    return [{"name": name, "endpoint": endpoint, "transport": "streamable_http"}]
