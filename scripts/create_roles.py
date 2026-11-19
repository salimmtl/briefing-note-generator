"""Create or update the security roles defined in schema_def.ROLES (idempotent).

Roles are created in the root business unit and inside SOLUTION_NAME. Privileges are (re)applied
with AddPrivilegesRole, so re-running is safe after changing depths. Assign roles together with
the built-in Basic User role.

Usage: python scripts/create_roles.py [--schema path/to/schema_def.py]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from create_schema import load_schema  # noqa: E402
from dv_api import call, created_id, get, log, ok, q  # noqa: E402

ACTIONS = ("Create", "Read", "Write", "Delete", "Append", "AppendTo", "Assign", "Share")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_def.py"))
    S = load_schema(parser.parse_args().schema)
    all_tables = [t["schema"] for t in S.TABLES]

    root_bu = get("businessunits?$select=businessunitid&$filter=_parentbusinessunitid_value eq null")["value"][0]["businessunitid"]

    # Privilege names use the table's SCHEMA name casing (prvCreatecontoso_Request) -> match case-insensitively.
    schema_names = {}
    for role_def in S.ROLES.values():
        for table in role_def:
            for name in (all_tables if table == "*" else [table]):
                schema_names[name.lower()] = name
    names = [f"prv{a}{t}" for t in schema_names for a in ACTIONS]
    privileges = {}
    for i in range(0, len(names), 40):
        flt = " or ".join(f"name eq '{n}'" for n in names[i:i + 40])
        for p in get(f"privileges?$select=name,privilegeid&$filter={q(flt)}")["value"]:
            privileges[p["name"].lower()] = p["privilegeid"]

    for role_name, role_def in S.ROLES.items():
        flt = q(f"name eq '{role_name}' and _businessunitid_value eq {root_bu}")
        existing = get(f"roles?$select=roleid&$filter={flt}")["value"]
        if existing:
            role_id = existing[0]["roleid"]
            log(f"[SKIP] role {role_name} exists")
        else:
            status, payload, headers = call("POST", "roles", {"name": role_name,
                                                              "businessunitid@odata.bind": f"/businessunits({root_bu})"})
            ok(status, payload, f"role {role_name}")
            role_id = created_id(headers)

        grants = []
        for table, rights in role_def.items():
            for t in (all_tables if table == "*" else [table]):
                for action, depth in rights.items():
                    key = f"prv{action}{t}".lower()
                    if key not in privileges:
                        raise SystemExit(f"[FAIL] privilege {key} not found (table created? action valid?)")
                    grants.append({"PrivilegeId": privileges[key], "Depth": depth, "BusinessUnitId": root_bu})
        ok(*call("POST", f"roles({role_id})/Microsoft.Dynamics.CRM.AddPrivilegesRole", {"Privileges": grants})[:2],
           f"  {len(grants)} privileges for {role_name}")


if __name__ == "__main__":
    main()
