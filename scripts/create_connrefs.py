"""Create the solution's connection references with neutral logical names (idempotent).

Binds each reference to the maker's Connected connection (from ensure_connections.py) and adds it to the
solution. Neutral names keep environment-specific connection names out of the shipped package.

Usage: python scripts/create_connrefs.py
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dv_api import call, get, log, ok, q  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# logical name -> (connector, display name)
CONNREFS = {
    "brn_agents.cr.shared_commondataserviceforapps.dvmcp": ("shared_commondataserviceforapps", "Briefing Agents - Dataverse MCP"),
    "brn_agents.cr.shared_office365users.profile": ("shared_office365users", "Briefing Agents - Office 365 Users"),
    "brn_flows.cr.shared_commondataserviceforapps": ("shared_commondataserviceforapps", "Briefing Workflows - Dataverse"),
    "brn_flows.cr.shared_sharepointonline": ("shared_sharepointonline", "Briefing Workflows - SharePoint"),
    "brn_flows.cr.shared_teams": ("shared_teams", "Briefing Workflows - Microsoft Teams"),
    "brn_flows.cr.shared_office365": ("shared_office365", "Briefing Workflows - Outlook"),
    "brn_flows.cr.shared_agentnode": ("shared_agentnode", "Briefing Workflows - Agent"),
    "brn_flows.cr.shared_onedriveforbusiness": ("shared_onedriveforbusiness", "Briefing Workflows - OneDrive (PDF rendering)"),
}


def main():
    out = subprocess.check_output([sys.executable, os.path.join(HERE, "ensure_connections.py"),
                                   *sorted({c for c, _ in CONNREFS.values()})], text=True)
    connections = json.loads(out)
    for logical, (connector, display) in CONNREFS.items():
        body = {"connectionreferencelogicalname": logical, "connectionreferencedisplayname": display,
                "connectorid": f"/providers/Microsoft.PowerApps/apis/{connector}",
                "connectionid": connections[connector],
                "description": f"{display}. Rebind to your own connection after import."}
        rows = get("connectionreferences?$select=connectionreferenceid,connectionid&$filter="
                   + q(f"connectionreferencelogicalname eq '{logical}'"))["value"]
        if rows:
            if rows[0].get("connectionid") != connections[connector]:
                ok(*call("PATCH", f"connectionreferences({rows[0]['connectionreferenceid']})",
                         {"connectionid": connections[connector]})[:2], f"rebind {logical}")
            else:
                log(f"[SKIP] {logical}")
            continue
        ok(*call("POST", "connectionreferences", body)[:2], f"connection reference {logical}")


if __name__ == "__main__":
    main()

