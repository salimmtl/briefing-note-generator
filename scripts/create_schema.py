"""Deploy the Dataverse schema from schema_def.py into the solution (idempotent).

Creates global choices, tables, columns, 1:N relationships and environment variables inside
SOLUTION_NAME, then publishes. Existing items are skipped, so it's safe to re-run after editing
schema_def.py. It never deletes or changes existing columns.

Usage: python scripts/create_schema.py [--schema path/to/schema_def.py]
"""

import argparse
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dv_api import call, exists, get, label, log, ok, publish_xml, q  # noqa: E402


def load_schema(path):
    spec = importlib.util.spec_from_file_location("schema_def", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def required(flag):
    return {"Value": "ApplicationRequired" if flag else "None", "CanBeChanged": True,
            "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings"}


def option_list(options, first_value):
    result = []
    for i, opt in enumerate(options):
        value, text = opt if isinstance(opt, tuple) else (first_value + i, opt)
        result.append({"Value": value, "Label": label(text)})
    return result


def create_choices(S):
    first = S.OPTION_VALUE_PREFIX * 10000
    for name, (display, options) in S.CHOICES.items():
        if exists(f"GlobalOptionSetDefinitions(Name='{name}')"):
            log(f"[SKIP] choice {name}")
            continue
        ok(*call("POST", "GlobalOptionSetDefinitions", {
            "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
            "Name": name, "DisplayName": label(display), "OptionSetType": "Picklist", "IsGlobal": True,
            "Options": option_list(options, first)})[:2], f"choice {name}")


_optionset_ids = {}


def optionset_id(name):
    # GlobalOptionSet@odata.bind needs the MetadataId GUID; binding by Name='…' fails with HTTP 500.
    if name not in _optionset_ids:
        _optionset_ids[name] = get(f"GlobalOptionSetDefinitions(Name='{name}')?$select=MetadataId")["MetadataId"]
    return _optionset_ids[name]


def attribute_body(prefix, col):
    suffix, display, kind, extra = col
    schema = f"{prefix}_{suffix}"
    body = {"SchemaName": schema, "DisplayName": label(display), "RequiredLevel": required(extra.get("required", False))}
    if extra.get("description"):
        body["Description"] = label(extra["description"])
    if kind in ("string", "email", "url", "phone", "autonumber"):
        fmt = {"email": "Email", "url": "Url", "phone": "Phone"}.get(kind, "Text")
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                     "MaxLength": extra.get("max", {"email": 320, "url": 2000}.get(kind, 100)),
                     "FormatName": {"Value": fmt}})
        if kind == "autonumber":
            body["AutoNumberFormat"] = extra["format"]
    elif kind == "memo":
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
                     "MaxLength": extra.get("max", 4000), "Format": "TextArea"})
    elif kind == "int":
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
                     "MinValue": extra.get("min", -2147483648), "MaxValue": extra.get("max", 2147483647), "Format": "None"})
    elif kind == "decimal":
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
                     "Precision": extra.get("precision", 2), "MinValue": extra.get("min", -100000000000),
                     "MaxValue": extra.get("max", 100000000000)})
    elif kind == "money":
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.MoneyAttributeMetadata",
                     "Precision": extra.get("precision", 2), "PrecisionSource": 2,
                     "MinValue": extra.get("min", 0), "MaxValue": extra.get("max", 1000000000)})
    elif kind == "bool":
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
                     "DefaultValue": extra.get("default", False),
                     "OptionSet": {"TrueOption": {"Value": 1, "Label": label("Yes")},
                                   "FalseOption": {"Value": 0, "Label": label("No")}}})
    elif kind in ("date", "datetime"):
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
                     "Format": "DateOnly" if kind == "date" else "DateAndTime",
                     "DateTimeBehavior": {"Value": "DateOnly" if kind == "date" else "UserLocal"}})
    elif kind in ("choice", "multichoice"):
        odt = "PicklistAttributeMetadata" if kind == "choice" else "MultiSelectPicklistAttributeMetadata"
        body.update({"@odata.type": f"Microsoft.Dynamics.CRM.{odt}",
                     "GlobalOptionSet@odata.bind": f"/GlobalOptionSetDefinitions({optionset_id(extra['set'])})"})
        if "default" in extra:
            body["DefaultFormValue"] = extra["default"]
    elif kind == "file":
        body.update({"@odata.type": "Microsoft.Dynamics.CRM.FileAttributeMetadata", "MaxSizeInKB": extra.get("max_kb", 32768)})
    else:
        raise SystemExit(f"[FAIL] unknown column kind '{kind}' for {schema}")
    return schema.lower(), body


def create_table(S, t):
    logical = t["schema"].lower()
    p_suffix, p_display, p_max = t["primary"]
    if exists(f"EntityDefinitions(LogicalName='{logical}')"):
        log(f"[SKIP] table {logical}")
    else:
        ok(*call("POST", "EntityDefinitions", {
            "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
            "SchemaName": t["schema"], "DisplayName": label(t["display"]),
            "DisplayCollectionName": label(t["plural"]), "Description": label(t.get("description", "")),
            "OwnershipType": t.get("ownership", "UserOwned"),
            "HasActivities": t.get("activities", False), "HasNotes": t.get("notes", True), "IsActivity": False,
            "Attributes": [{
                "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                "SchemaName": f"{S.PREFIX}_{p_suffix}", "IsPrimaryName": True, "MaxLength": p_max,
                "FormatName": {"Value": "Text"}, "DisplayName": label(p_display), "RequiredLevel": required(True)}],
        })[:2], f"table {logical}")

    for col in t["columns"]:
        a_logical, body = attribute_body(S.PREFIX, col)
        if exists(f"EntityDefinitions(LogicalName='{logical}')/Attributes(LogicalName='{a_logical}')"):
            log(f"[SKIP]   column {a_logical}")
            continue
        ok(*call("POST", f"EntityDefinitions(LogicalName='{logical}')/Attributes", body)[:2], f"  column {a_logical}")
        seed = col[3].get("seed")
        if col[2] == "autonumber" and seed is not None:
            # New auto-number columns start at 1000 unless seeded. The metadata can take a few seconds to propagate.
            import time
            for attempt in range(6):
                status, payload, _ = call("POST", "SetAutoNumberSeed", {
                    "EntityName": logical, "AttributeName": a_logical, "Value": seed}, solution=False)
                if status < 300:
                    log(f"[OK]     seed {a_logical} = {seed}")
                    break
                time.sleep(10)
            else:
                log(f"[WARN]   seed {a_logical} not set: {payload}")


def create_relationships(S):
    for r in getattr(S, "RELATIONSHIPS", []):
        if exists(f"RelationshipDefinitions(SchemaName='{r['schema']}')"):
            log(f"[SKIP] relationship {r['schema']}")
            continue
        delete = "Cascade" if r.get("cascade_delete") else "RemoveLink"
        ok(*call("POST", "RelationshipDefinitions", {
            "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
            "SchemaName": r["schema"], "ReferencedEntity": r["referenced"], "ReferencingEntity": r["referencing"],
            "CascadeConfiguration": {"Assign": "Cascade" if r.get("cascade_delete") else "NoCascade",
                                     "Delete": delete, "Merge": "NoCascade", "Reparent": "NoCascade",
                                     "Share": "NoCascade", "Unshare": "NoCascade", "RollupView": "NoCascade"},
            "AssociatedMenuConfiguration": {"Behavior": "UseCollectionName", "Group": "Details", "Order": 10000},
            "Lookup": {"@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
                       "SchemaName": r["lookup_schema"], "DisplayName": label(r["lookup_display"]),
                       "RequiredLevel": required(r.get("required", False))},
        })[:2], f"relationship {r['schema']}")


def create_env_vars(S):
    for schema, display, desc, default in getattr(S, "ENV_VARS", []):
        flt = q("schemaname eq '%s'" % schema)
        rows = get(f"environmentvariabledefinitions?$select=schemaname&$filter={flt}")["value"]
        if rows:
            log(f"[SKIP] env var {schema}")
            continue
        body = {"schemaname": schema, "displayname": display, "description": desc, "type": 100000000}
        if default:
            body["defaultvalue"] = default
        ok(*call("POST", "environmentvariabledefinitions", body)[:2], f"env var {schema}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_def.py"))
    S = load_schema(parser.parse_args().schema)
    create_choices(S)
    for t in S.TABLES:
        create_table(S, t)
    create_relationships(S)
    create_env_vars(S)
    publish_xml(entities=[t["schema"].lower() for t in S.TABLES], optionsets=list(S.CHOICES))
    log("Done. Verify: every table, choice and env var should appear in the solution.")


if __name__ == "__main__":
    main()
