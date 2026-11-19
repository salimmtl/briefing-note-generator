"""Add the non-schema components (agents, agent components, connection references, tool links, workflows, app)
to the solution (idempotent: AddSolutionComponent ignores components already present).

Usage: python scripts/add_to_solution.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dv_api import add_to_solution, component_type, get, log, q, solution_inventory  # noqa: E402

AGENTS = ["brn_BriefingNoteWriter", "brn_BriefingAssistant"]


def main():
    for schema in AGENTS:
        bots = get(f"bots?$select=botid,name&$filter={q(f'schemaname eq {chr(39)}{schema}{chr(39)}')}")["value"]
        if not bots:
            log(f"[WARN] agent {schema} not found")
            continue
        bot_id = bots[0]["botid"]
        add_to_solution(bot_id, "bot", schema)
        comps = get(f"botcomponents?$select=botcomponentid,schemaname&$filter=_parentbotid_value eq {bot_id}")["value"]
        for c in comps:
            add_to_solution(c["botcomponentid"], "botcomponent", c["schemaname"])
            links = get("botcomponent_connectionreferenceset?$select=botcomponent_connectionreferenceid"
                        f"&$filter=botcomponentid eq {c['botcomponentid']}")["value"]
            for link in links:
                add_to_solution(link["botcomponent_connectionreferenceid"], "botcomponent_connectionreference",
                                f"tool link of {c['schemaname']}")

    crs = get("connectionreferences?$select=connectionreferenceid,connectionreferencelogicalname&$filter="
              + q("startswith(connectionreferencelogicalname,'brn_')"))["value"]
    for cr in crs:
        add_to_solution(cr["connectionreferenceid"], "connectionreference", cr["connectionreferencelogicalname"])

    flows = get("workflows?$select=workflowid,name&$filter=" + q("category eq 5 and startswith(name,'BN ')"))["value"]
    for f in flows:
        add_to_solution(f["workflowid"], 29, f["name"])

    log(f"Inventory: {solution_inventory()}")


if __name__ == "__main__":
    main()

