"""Thin Dataverse Web API helper shared by the pp-demo-builder scripts.

- Reads DATAVERSE_URL, TENANT_ID and SOLUTION_NAME from the environment or a .env file (see auth.py).
- Adds the MSCRM.SolutionUniqueName header by default, so created components land in the solution.
- Retries transient metadata errors (0x80040216 right after a customization, HTTP 5xx, lock contention).
- Prompts and diagnostics go to stderr; stdout stays clean for callers that parse it.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth import get_token, load_env  # noqa: E402

load_env()
BASE = os.environ["DATAVERSE_URL"].rstrip("/") + "/api/data/v9.2/"
SOLUTION = os.environ.get("SOLUTION_NAME", "")
_token = None
_TRANSIENT = ("0x80040216", "0x80060891", "another customization", "another operation is running")


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def token():
    global _token
    if _token is None:
        _token = get_token()
    return _token


def call(method, path, body=None, solution=True, retries=4, extra_headers=None):
    """Return (status, payload, headers). payload is parsed JSON, the raw error text, or None."""
    headers = {
        "Authorization": f"Bearer {token()}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    }
    if solution and SOLUTION:
        headers["MSCRM.SolutionUniqueName"] = SOLUTION
    headers.update(extra_headers or {})
    url = BASE + path.replace(" ", "%20")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None), resp.headers
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8", "replace")
        if e.code == 401 and retries:
            global _token
            _token = None  # access token expired in a long-running script: refresh and retry
            return call(method, path, body, solution, retries - 1, extra_headers)
        if retries and method != "GET" and (e.code >= 500 or any(t in payload for t in _TRANSIENT)):
            time.sleep(10)
            return call(method, path, body, solution, retries - 1, extra_headers)
        return e.code, payload, e.headers
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        # Transient network failures (Wi-Fi/VPN blips): wait and retry.
        if retries:
            log(f"[RETRY] {method} {path.split('?')[0]}: {e}")
            time.sleep(15)
            return call(method, path, body, solution, retries - 1, extra_headers)
        raise


def ok(status, payload, what):
    if status >= 300:
        raise SystemExit(f"[FAIL] {what}: HTTP {status}\n{payload}")
    log(f"[OK]   {what}")
    return payload


def get(path):
    status, payload, _ = call("GET", path, solution=False)
    return ok(status, payload, f"GET {path.split('?')[0]}")


def exists(path):
    return call("GET", path, solution=False)[0] == 200


def created_id(headers):
    return headers["OData-EntityId"].split("(")[-1].rstrip(")")


def q(text):
    return urllib.parse.quote(text)


def label(text):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel", "Label": text, "LanguageCode": 1033}],
    }


_component_types = {}


def component_type(primary_entity):
    """Solution component type code for a table-backed component (bot, botcomponent, skill, connectionreference…).
    These codes differ between environments, so resolve them; never hard-code them."""
    if primary_entity not in _component_types:
        flt = q("primaryentityname eq '%s'" % primary_entity)
        rows = get(f"solutioncomponentdefinitions?$select=solutioncomponenttype&$filter={flt}")["value"]
        if not rows:
            raise SystemExit(f"[FAIL] no solution component definition for '{primary_entity}'")
        _component_types[primary_entity] = rows[0]["solutioncomponenttype"]
    return _component_types[primary_entity]


def add_to_solution(object_id, ctype, what=""):
    """ctype: an int (1 table, 9 choice, 20 role, 26 view, 59 chart, 60 form, 62 site map, 80 app, 300 canvas/code app,
    380 env var definition) or a primary entity name resolved with component_type()."""
    if isinstance(ctype, str):
        ctype = component_type(ctype)
    status, payload, _ = call("POST", "AddSolutionComponent", {
        "ComponentId": object_id, "ComponentType": ctype, "SolutionUniqueName": SOLUTION,
        "AddRequiredComponents": False, "DoNotIncludeSubcomponents": False}, solution=False)
    ok(status, payload, f"add to solution {what or object_id} (type {ctype})")


def publish_xml(entities=(), optionsets=(), dashboards=(), appmodules=()):
    parts = []
    if entities:
        parts.append("<entities>" + "".join(f"<entity>{e}</entity>" for e in entities) + "</entities>")
    if optionsets:
        parts.append("<optionsets>" + "".join(f"<optionset>{o}</optionset>" for o in optionsets) + "</optionsets>")
    if dashboards:
        parts.append("<dashboards>" + "".join(f"<dashboard>{{{d}}}</dashboard>" for d in dashboards) + "</dashboards>")
    if appmodules:
        parts.append("<appmodules>" + "".join(f"<appmodule>{a}</appmodule>" for a in appmodules) + "</appmodules>")
    xml = "<importexportxml>" + "".join(parts) + "</importexportxml>"
    ok(*call("POST", "PublishXml", {"ParameterXml": xml}, solution=False)[:2], "publish")


def solution_inventory(solution=None):
    """Count solution components by type, to verify that everything landed in the solution."""
    name = solution or SOLUTION
    flt = q("uniquename eq '%s'" % name)
    sol = get(f"solutions?$select=solutionid&$filter={flt}")["value"]
    if not sol:
        raise SystemExit(f"[FAIL] solution {name} not found")
    rows = get(f"solutioncomponents?$select=componenttype&$filter=_solutionid_value eq {sol[0]['solutionid']}")["value"]
    counts = {}
    for r in rows:
        counts[r["componenttype"]] = counts.get(r["componenttype"], 0) + 1
    return counts
