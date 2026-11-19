"""Call the environment's Dataverse MCP server directly (JSON-RPC over HTTP) to dry-run the agent's queries.

Usage: python scripts/mcp_call.py read_query "{\"querytext\": \"SELECT ...\"}"
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dv_api import token  # noqa: E402

URL = os.environ["DATAVERSE_URL"].rstrip("/") + "/api/mcp"
_session = None


def rpc(method, params=None, rid=1):
    global _session
    headers = {"Authorization": f"Bearer {token()}", "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if _session:
        headers["Mcp-Session-Id"] = _session
    body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
    if rid is not None:
        body["id"] = rid
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            _session = resp.headers.get("Mcp-Session-Id") or _session
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:1000]}
    for line in raw.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:])
    return json.loads(raw) if raw.strip() else None


def call_tool(name, arguments):
    rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "vendor-intake-dryrun", "version": "1.0"}})
    rpc("notifications/initialized", rid=None)
    return rpc("tools/call", {"name": name, "arguments": arguments}, rid=2)


if __name__ == "__main__":
    result = call_tool(sys.argv[1], json.loads(sys.argv[2]))
    print(json.dumps(result, indent=1)[:6000])
