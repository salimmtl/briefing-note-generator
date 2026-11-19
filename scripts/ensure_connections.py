"""Ensure a Connected connection exists for each connector the solution uses (idempotent).

For Microsoft 365 first-party connectors (SharePoint, Teams, Outlook, Agent, Office 365 Users) the
connection is authenticated silently with the signed-in user's token. Other connectors print a consent
link to open in a browser.

Usage: python scripts/ensure_connections.py [connector ...]
Prints a JSON map {connector: connectionName} on stdout (used by create_connrefs.py).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_token, load_env  # noqa: E402

load_env()
ENV_ID = os.environ.get("ENVIRONMENT_ID", "")
BASE = "https://api.powerapps.com/providers/Microsoft.PowerApps"
DEFAULT_CONNECTORS = [
    "shared_commondataserviceforapps",
    "shared_sharepointonline",
    "shared_teams",
    "shared_office365",
    "shared_office365users",
    "shared_agentnode",
    "shared_rss",
    "shared_onedriveforbusiness",
]


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def req(method, url, body=None, token=None, retries=4):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {token or get_token('https://service.powerapps.com/.default')}",
               "Content-Type": "application/json", "Accept": "application/json"}
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=headers), timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            if e.code >= 500 and attempt < retries - 1:
                time.sleep(5)
                continue
            raise SystemExit(f"[FAIL] {method} {url.split('?')[0]}: HTTP {e.code}\n{text}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            raise SystemExit(f"[FAIL] {method} {url.split('?')[0]}: {e}")


def qs():
    return f"?api-version=2016-11-01&$filter=environment%20eq%20%27{ENV_ID}%27"


def connected(conn):
    return any(s.get("status") == "Connected" for s in conn["properties"].get("statuses", []))


def ensure(connector):
    existing = req("GET", f"{BASE}/apis/{connector}/connections{qs()}")["value"]
    for c in existing:
        if connected(c):
            log(f"[SKIP] {connector}: {c['name']} (Connected)")
            return c["name"]
    if existing:
        name = existing[0]["name"]
        log(f"[FIX]  {connector}: {name} is not connected; authenticating")
    else:
        name = f"{connector.replace('shared_', 'shared-')[:20]}-{uuid.uuid4()}"
        req("PUT", f"{BASE}/apis/{connector}/connections/{name}{qs()}", {
            "properties": {"environment": {"id": f"/providers/Microsoft.PowerApps/environments/{ENV_ID}", "name": ENV_ID},
                           "connectionParameters": {}}})
        log(f"[OK]   {connector}: created {name}")
    conn = req("GET", f"{BASE}/apis/{connector}/connections/{name}{qs()}")
    if connected(conn):
        return name
    consent = req("POST", f"{BASE}/apis/{connector}/connections/{name}/getConsentLink{qs()}",
                  {"redirectUrl": "https://make.powerautomate.com"})
    if consent.get("firstPartyLoginUri"):
        hub = get_token("https://apihub.azure.com/.default")
        req("POST", consent["firstPartyLoginUri"], {"accessToken": hub}, token=hub)
    for _ in range(10):
        conn = req("GET", f"{BASE}/apis/{connector}/connections/{name}{qs()}")
        if connected(conn):
            log(f"[OK]   {connector}: {name} Connected")
            return name
        time.sleep(3)
    if consent.get("consentLink"):
        log(f"[ACTION] Open this link to authorise {connector}, then re-run:\n  {consent['consentLink']}")
    else:
        log(f"[WARN] {connector}: {name} not connected: {conn['properties'].get('statuses')}")
    return name


def main():
    if not ENV_ID:
        raise SystemExit("[FAIL] set ENVIRONMENT_ID in .env")
    result = {c: ensure(c) for c in (sys.argv[1:] or DEFAULT_CONNECTORS)}
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
