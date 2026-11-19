"""Schema definition: the single source of truth for the Briefing Note Generator Dataverse model.

Run:
    python scripts/create_schema.py      # choices, tables, columns, relationships, env vars (idempotent)
    python scripts/create_roles.py       # security roles

The agents' Dataverse contracts, the workflows' choice values and the code app's domain constants are generated
from this file.
"""

PREFIX = "brn"
OPTION_VALUE_PREFIX = 74380
V = OPTION_VALUE_PREFIX * 10000  # 743800000


def opts(*labels):
    """Choice options with values V, V+1, ... in the order given. Never reorder existing labels."""
    return [(V + i, text) for i, text in enumerate(labels)]


REQUEST_STATUS = opts(
    "Draft",               # 743800000  being prepared by the requester (not yet submitted)
    "Submitted",           # 743800001  -> BN 1 workflow
    "Drafting",            # 743800002  the Writer agent is working
    "Needs Info",          # 743800003  the Writer asked the requester questions
    "Info Provided",       # 743800004  -> BN 1 workflow (re-draft with the answers)
    "In Review",           # 743800005  draft ready for the reviewer
    "Revision Requested",  # 743800006  -> BN 1 workflow (re-draft with reviewer comments)
    "Approved",            # 743800007  -> BN 2 workflow
    "Delivered",           # 743800008
    "Cancelled",           # 743800009
    "Needs Attention",     # 743800010  a workflow failed
)

CHOICES = {
    f"{PREFIX}_requeststatus": ("Briefing Request Status", REQUEST_STATUS),
    f"{PREFIX}_notetype": ("Note Type", opts(
        "Briefing Note for Information", "Briefing Note for Decision", "Meeting or Event Brief",
        "Issue Note", "Executive Summary")),
    f"{PREFIX}_language": ("Briefing Language", opts("English", "French")),
    f"{PREFIX}_classification": ("Classification", opts(
        "Unclassified", "Protected A", "Protected B", "Internal", "Confidential")),
    f"{PREFIX}_priority": ("Briefing Priority", opts("Routine", "Priority", "Urgent")),
    f"{PREFIX}_deliverymode": ("Delivery Mode", opts(
        "Send to requester and recipient", "Send to requester only")),
    f"{PREFIX}_sector": ("Sector", opts("Public sector", "Private sector")),
    f"{PREFIX}_intakechannel": ("Intake Channel", opts("Briefing Studio", "Briefing Assistant", "Briefing Notes Hub")),
    f"{PREFIX}_confidence": ("Draft Confidence", opts("Low", "Medium", "High")),
    f"{PREFIX}_documenttype": ("Source Document Type", opts(
        "Report", "Memo or briefing", "Email or correspondence", "Presentation", "Data or spreadsheet",
        "Web page or article", "Meeting notes", "Other")),
    f"{PREFIX}_extractionstatus": ("Extraction Status", opts("Pending", "Extracted", "Failed", "Not supported")),
    f"{PREFIX}_actor": ("Activity Actor", opts(
        "Requester", "Briefing Assistant", "Briefing Note Writer", "Workflow", "Reviewer")),
    f"{PREFIX}_activitytype": ("Activity Type", opts(
        "Submitted", "Drafting started", "Clarification requested", "Clarification provided", "Draft ready",
        "Revision requested", "Approved", "Delivered", "Failed", "Cancelled", "Note")),
}


def v(choice, label):
    """Value of a choice label, e.g. v('requeststatus', 'Submitted')."""
    for value, text in CHOICES[f"{PREFIX}_{choice}"][1]:
        if text == label:
            return value
    raise KeyError(f"{choice}: {label}")


def memo(max_len=4000, **extra):
    return {"max": max_len, **extra}


TABLES = [
    {
        "schema": f"{PREFIX}_Profile",
        "display": "Briefing Profile",
        "plural": "Briefing Profiles",
        "description": "An organization's briefing configuration: style guide, glossary, classification guidance, "
                       "default reviewer and SharePoint filing target.",
        "ownership": "OrganizationOwned",
        "primary": ("Name", "Organization", 200),
        "columns": [
            ("Code", "Code", "string", {"max": 20, "description": "Short code used in folder names, e.g. MDS."}),
            ("Sector", "Sector", "choice", {"set": f"{PREFIX}_sector", "default": V}),
            ("Description", "Description", "memo", memo(2000)),
            ("StyleGuide", "Style Guide", "memo", memo(20000, description="Tone, plain-language and formatting rules the Writer follows.")),
            ("Glossary", "Glossary", "memo", memo(20000, description="Acronyms and preferred terms, one per line: TERM = meaning.")),
            ("ClassificationGuidance", "Classification Guidance", "memo", memo(4000)),
            ("DefaultLanguage", "Default Language", "choice", {"set": f"{PREFIX}_language", "default": V}),
            ("DefaultReviewerEmail", "Default Reviewer Email", "email", {}),
            ("LeaderTitles", "Typical Recipients", "string", {"max": 1000, "description": "e.g. Minister; Deputy Minister; ADM."}),
            ("SharePointSiteUrl", "SharePoint Site URL", "url", {}),
            ("SharePointLibrary", "SharePoint Library", "string", {"max": 200}),
            ("SharePointRootFolder", "SharePoint Root Folder", "string", {"max": 200}),
            ("AccentColor", "Accent Colour", "string", {"max": 7, "description": "Hex colour used in PDFs, e.g. #0F6CBD."}),
            ("FooterText", "Document Footer", "string", {"max": 500}),
            ("IsActive", "Active", "bool", {"default": True}),
        ],
    },
    {
        "schema": f"{PREFIX}_Template",
        "display": "Note Template",
        "plural": "Note Templates",
        "description": "A briefing note format: when to use it, its sections and the writing rules.",
        "ownership": "OrganizationOwned",
        "primary": ("Name", "Template", 200),
        "columns": [
            ("Code", "Code", "string", {"max": 20}),
            ("NoteType", "Note Type", "choice", {"set": f"{PREFIX}_notetype", "default": V}),
            ("WhenToUse", "When to Use", "memo", memo(2000)),
            ("Sections", "Sections", "memo", memo(10000, description="One section per line: Heading | guidance | max words.")),
            ("WritingRules", "Writing Rules", "memo", memo(10000)),
            ("MaxWords", "Maximum Words", "int", {"min": 100, "max": 5000}),
            ("SortOrder", "Sort Order", "int", {"min": 0, "max": 1000}),
            ("IsActive", "Active", "bool", {"default": True}),
        ],
    },
    {
        "schema": f"{PREFIX}_Request",
        "display": "Briefing Request",
        "plural": "Briefing Requests",
        "description": "A request for a briefing note: who it's for, the source documents, the AI draft, "
                       "clarifications, review and delivery.",
        "primary": ("Name", "Subject", 300),
        "columns": [
            ("RequestNumber", "Request ID", "autonumber", {"format": "BN-{SEQNUM:5}", "max": 20, "seed": 1}),
            ("Status", "Status", "choice", {"set": f"{PREFIX}_requeststatus", "default": V}),
            # Who
            ("RequesterName", "Requester Name", "string", {"max": 200}),
            ("RequesterEmail", "Requester Email", "email", {"required": True}),
            ("RecipientName", "Recipient Name", "string", {"max": 200}),
            ("RecipientTitle", "Recipient Title", "string", {"max": 200}),
            ("RecipientEmail", "Recipient Email", "email", {}),
            ("ReviewerEmail", "Reviewer Email", "email", {}),
            # What
            ("Purpose", "Purpose", "memo", memo(4000, description="Why the leader needs this note and what it should help them do.")),
            ("AdditionalContext", "Additional Context", "memo", memo(10000)),
            ("Language", "Language", "choice", {"set": f"{PREFIX}_language", "default": V}),
            ("Classification", "Classification", "choice", {"set": f"{PREFIX}_classification", "default": V}),
            ("Priority", "Priority", "choice", {"set": f"{PREFIX}_priority", "default": V}),
            ("DueDate", "Due Date", "date", {}),
            ("DeliveryMode", "Delivery Mode", "choice", {"set": f"{PREFIX}_deliverymode", "default": V}),
            ("IntakeChannel", "Intake Channel", "choice", {"set": f"{PREFIX}_intakechannel", "default": V}),
            # Human in the loop
            ("ClarificationQuestions", "Clarification Questions", "memo", memo(4000)),
            ("ClarificationAnswers", "Clarification Answers", "memo", memo(10000)),
            ("ClarificationRounds", "Clarification Rounds", "int", {"min": 0, "max": 20}),
            ("ReviewerComments", "Reviewer Comments", "memo", memo(10000)),
            # Draft (written by the Briefing Note Writer)
            ("NoteTitle", "Note Title", "string", {"max": 300}),
            ("KeyMessage", "Key Message", "memo", memo(2000, description="Bottom line up front: 1-3 sentences.")),
            ("DraftSections", "Draft Sections (JSON)", "memo", memo(100000, description='[{"heading": "...", "body": "..."}]')),
            ("SourcesUsed", "Sources Used", "memo", memo(10000)),
            ("VerificationNotes", "Verification Notes", "memo", memo(10000, description="Assumptions, gaps and statements to check.")),
            ("Confidence", "Draft Confidence", "choice", {"set": f"{PREFIX}_confidence"}),
            ("WordCount", "Word Count", "int", {"min": 0, "max": 100000}),
            ("DraftVersion", "Draft Version", "int", {"min": 0, "max": 1000}),
            # Outputs and tracking
            ("DraftPdfUrl", "Draft PDF", "url", {}),
            ("FinalPdfUrl", "Final PDF", "url", {}),
            ("SharePointFolderUrl", "SharePoint Folder", "url", {}),
            ("SubmittedOn", "Submitted On", "datetime", {}),
            ("DraftedOn", "Drafted On", "datetime", {}),
            ("ApprovedBy", "Approved By", "email", {}),
            ("ApprovedOn", "Approved On", "datetime", {}),
            ("DeliveredOn", "Delivered On", "datetime", {}),
            ("LastError", "Last Error", "memo", memo(4000)),
            ("ConversationId", "Conversation ID", "string", {"max": 200}),
        ],
    },
    {
        "schema": f"{PREFIX}_SourceDocument",
        "display": "Source Document",
        "plural": "Source Documents",
        "description": "A document submitted with a briefing request, with its extracted text.",
        "primary": ("Name", "File Name", 300),
        "columns": [
            ("SourceLabel", "Source Label", "string", {"max": 10, "description": "S1, S2… used for citations."}),
            ("DocumentType", "Document Type", "choice", {"set": f"{PREFIX}_documenttype", "default": V}),
            ("File", "File", "file", {"max_kb": 32768}),
            ("ExtractedText", "Extracted Text", "memo", memo(1048576)),
            ("ExtractionStatus", "Extraction Status", "choice", {"set": f"{PREFIX}_extractionstatus", "default": V}),
            ("PageCount", "Pages", "int", {"min": 0, "max": 100000}),
            ("CharacterCount", "Characters", "int", {"min": 0, "max": 2000000000}),
            ("Summary", "Summary", "memo", memo(4000, description="Written by the Writer: what this source contributes.")),
        ],
    },
    {
        "schema": f"{PREFIX}_Activity",
        "display": "Briefing Activity",
        "plural": "Briefing Activities",
        "description": "Timeline of a briefing request: agent and workflow steps, human actions and failures.",
        "ownership": "OrganizationOwned",
        "primary": ("Name", "Activity", 300),
        "columns": [
            ("Actor", "Actor", "choice", {"set": f"{PREFIX}_actor"}),
            ("ActivityType", "Activity Type", "choice", {"set": f"{PREFIX}_activitytype"}),
            ("Details", "Details", "memo", memo(8000)),
            ("StartedOn", "Started On", "datetime", {}),
            ("CompletedOn", "Completed On", "datetime", {}),
            ("DurationSeconds", "Duration (s)", "int", {"min": 0, "max": 2000000000}),
            ("WorkflowRun", "Workflow Run", "string", {"max": 200}),
        ],
    },
]


def rel(referenced, referencing, lookup, display, required=False, cascade=False, schema=None):
    return {
        "schema": schema or f"{PREFIX}_{referenced}_{referencing}_{lookup}",
        "referenced": f"{PREFIX}_{referenced.lower()}",
        "referencing": f"{PREFIX}_{referencing.lower()}",
        "lookup_schema": f"{PREFIX}_{lookup}",
        "lookup_display": display,
        "required": required,
        "cascade_delete": cascade,
    }


RELATIONSHIPS = [
    rel("Profile", "Request", "ProfileId", "Briefing Profile"),
    rel("Template", "Request", "TemplateId", "Note Template"),
    rel("Request", "SourceDocument", "RequestId", "Briefing Request", required=True, cascade=True),
    rel("Request", "Activity", "RequestId", "Briefing Request", cascade=True),
]

ENV_VARS = [
    (f"{PREFIX}_AppBaseUrl", "Briefing Notes Hub URL",
     "Model-driven app URL used in notification links (…/main.aspx?appid=<id>).", ""),
    (f"{PREFIX}_StudioUrl", "Briefing Studio URL", "Code app URL used in notification links (play link).", ""),
]

_ALL = ("Create", "Read", "Write", "Delete", "Append", "AppendTo", "Assign", "Share")
_CONFIG = [f"{PREFIX}_profile", f"{PREFIX}_template"]
_ACTIVITY = f"{PREFIX}_activity"
_WORK = [f"{PREFIX}_request", f"{PREFIX}_sourcedocument"]

ROLES = {
    "Briefing Requester": {
        **{t: {"Read": "Global", "AppendTo": "Global"} for t in _CONFIG},
        _ACTIVITY: {"Create": "Global", "Read": "Global", "Append": "Global"},
        **{t: {"Create": "Basic", "Read": "Basic", "Write": "Basic", "Append": "Basic", "AppendTo": "Basic"}
           for t in _WORK},
    },
    "Briefing Reviewer": {
        **{t: {"Read": "Global", "AppendTo": "Global"} for t in _CONFIG},
        _ACTIVITY: {"Create": "Global", "Read": "Global", "Append": "Global"},
        **{t: {"Create": "Global", "Read": "Global", "Write": "Global", "Append": "Global", "AppendTo": "Global"}
           for t in _WORK},
    },
    # Organization-owned tables have no Assign/Share privileges.
    "Briefing Admin": {
        **{t: {p: "Global" for p in _ALL if p not in ("Assign", "Share")} for t in _CONFIG + [_ACTIVITY]},
        **{t: {p: "Global" for p in _ALL} for t in _WORK},
    },
}
