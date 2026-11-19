"""Show recent runs of the AMF workflows and the failing actions (for debugging).

Usage: python scripts/flow_runs.py <workflow id> [--actions]
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_token, load_env  # noqa: E402

load_env()
ENV = os.environ["ENVIRONMENT_ID"]
BASE = f"https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/{ENV}/flows"


def get(url):
    tok = get_token("https://service.flow.microsoft.com/.default")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read()[:800]}")


def main():
    flow = sys.argv[1]
    runs = get(f"{BASE}/{flow}/runs?api-version=2016-11-01&$top=5")["value"]
    for run in runs:
        p = run["properties"]
        print(run["name"], p["status"], p.get("startTime"), p.get("endTime"), p.get("error", {}).get("message", "")[:300])
    if runs and "--actions" in sys.argv:
        run = runs[0]["name"]
        acts = get(f"{BASE}/{flow}/runs/{run}/actions?api-version=2016-11-01")["value"]
        if "--dump" in sys.argv:
            target = sys.argv[sys.argv.index("--dump") + 1]
            for a in acts:
                if a["name"] == target and a["properties"].get("outputsLink"):
                    with urllib.request.urlopen(a["properties"]["outputsLink"]["uri"], timeout=60) as r:
                        body = json.loads(r.read()).get("body")
                    if isinstance(body, dict) and isinstance(body.get("files"), list):
                        body["files"] = [{"name": x.get("name"), "contentType": x.get("contentType"),
                                          "bytes": len(x.get("contentBytes") or "")} for x in body["files"]]
                    print(json.dumps(body, indent=1, ensure_ascii=False)[:12000])
            return
        for a in acts:
            p = a["properties"]
            line = f"  {a['name']}: {p['status']}"
            if p["status"] in ("Failed", "TimedOut"):
                err = p.get("error") or {}
                line += f"  {err.get('code', '')} {err.get('message', '')[:500]}"
                if p.get("outputsLink"):
                    try:
                        with urllib.request.urlopen(p["outputsLink"]["uri"], timeout=60) as r:
                            line += "\n    OUT: " + r.read().decode("utf-8", "replace")[-900:]
                    except Exception as e:  # noqa: BLE001
                        line += f"\n    (outputs unavailable: {e})"
            print(line)


if __name__ == "__main__":
    main()

