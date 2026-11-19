"""Schema definition: the single source of truth for a demo's Dataverse model.

Copy to your repo as scripts/schema_def.py, edit, then run:
    python scripts/create_schema.py      # choices, tables, columns, relationships, env vars (idempotent)
    python scripts/create_roles.py       # security roles

Generate everything else from this file (app constants, skill resources, docs) so nothing drifts.
"""

PREFIX = "contoso"              # publisher customization prefix (permanent)
OPTION_VALUE_PREFIX = 10000     # publisher option value prefix (5 digits); option values start at 100000000
V = OPTION_VALUE_PREFIX * 10000  # first choice value


def opts(*labels):
    """Choice options with values V, V+1, …, in the order given. Never reorder existing labels."""
    return [(V + i, text) for i, text in enumerate(labels)]


# Global choices: name -> (display name, options)
CHOICES = {
    f"{PREFIX}_requeststatus": ("Request Status", opts("Draft", "Submitted", "In review", "Approved", "Rejected")),
    f"{PREFIX}_priority": ("Priority", opts("Low", "Medium", "High")),
}

# Column kinds: string, email, url, phone, memo, int, decimal, money, bool, date, datetime,
#               choice, multichoice, autonumber, file
# extra: required, max, min, description, set (choice name), default (choice value), format (autonumber),
#        seed (autonumber start), precision (decimal/money), max_kb (file)
TABLES = [
    {
        "schema": f"{PREFIX}_Request",
        "display": "Request",
        "plural": "Requests",
        "description": "A request submitted by an employee.",
        "ownership": "UserOwned",          # or "OrganizationOwned"
        "primary": ("Name", "Title", 200),
        "columns": [
            ("RequestNumber", "Request ID", "autonumber", {"format": "REQ-{SEQNUM:5}", "seed": 1}),
            ("SubmitterEmail", "Submitter Email", "email", {"required": True}),
            ("Description", "Description", "memo", {"max": 4000}),
            ("Status", "Status", "choice", {"set": f"{PREFIX}_requeststatus", "default": V + 1}),
            ("Priority", "Priority", "choice", {"set": f"{PREFIX}_priority"}),
            ("DueDate", "Due Date", "date", {}),
            ("Attachment", "Attachment", "file", {"max_kb": 32768}),
        ],
    },
    {
        "schema": f"{PREFIX}_RequestItem",
        "display": "Request Item",
        "plural": "Request Items",
        "description": "A line item of a request.",
        "ownership": "UserOwned",
        "primary": ("Name", "Item", 200),
        "columns": [
            ("Quantity", "Quantity", "int", {"min": 0, "max": 100000}),
            ("Amount", "Amount", "money", {"precision": 2}),
        ],
    },
]

# 1:N relationships (lookup on the referencing table)
RELATIONSHIPS = [
    {
        "schema": f"{PREFIX}_Request_RequestItem",
        "referenced": f"{PREFIX}_request",
        "referencing": f"{PREFIX}_requestitem",
        "lookup_schema": f"{PREFIX}_RequestId",     # never name a plain column *Id: it collides with lookups
        "lookup_display": "Request",
        "required": True,
        "cascade_delete": True,
    },
]

# Environment variables: (schema name, display name, description, default value). Type = text.
ENV_VARS = [
    (f"{PREFIX}_SupportUrl", "Support URL", "Link shown in the apps for help.", "https://learn.microsoft.com"),
]

# Security roles: role -> {table logical name or "*" (all TABLES) -> {privilege: depth}}
# Privileges: Create, Read, Write, Delete, Append, AppendTo, Assign, Share
# Depth: Basic (user), Local (business unit), Deep (parent: child BUs), Global (organization)
ROLES = {
    "Contoso Requester": {"*": {"Create": "Basic", "Read": "Basic", "Append": "Basic", "AppendTo": "Basic"}},
    "Contoso Approver": {"*": {"Create": "Global", "Read": "Global", "Write": "Global", "Append": "Global", "AppendTo": "Global"}},
    "Contoso Admin": {"*": {p: "Global" for p in ("Create", "Read", "Write", "Delete", "Append", "AppendTo", "Assign", "Share")}},
}
