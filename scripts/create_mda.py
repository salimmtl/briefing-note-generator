"""Build the "Briefing Notes Hub" model-driven app (idempotent).

Creates or updates, inside the solution from .env:
  - main forms for every table (the Briefing Request form is the full "detail screen")
  - public views, quick find layouts and associated (subgrid) views
  - system charts and the "Briefing Overview" dashboard
  - the app module (brn_BriefingNotesHub) with its site map (Briefings and Configuration areas)
  - app access for the Briefing roles (and System Administrator)
  - the brn_AppBaseUrl environment variable value (…/main.aspx?appid=<id>)

Fixed GUIDs (uuid5) make every component re-runnable. Usage: python scripts/create_mda.py
"""

import os
import sys
import time
import uuid
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_def as S  # noqa: E402
from dv_api import BASE, SOLUTION, add_to_solution, call, log, ok, q, solution_inventory  # noqa: E402

P = S.PREFIX
v = S.v
NS = uuid.UUID("3c9e2b71-5d4a-4f8e-9b06-1a2b3c4d5e01")
APP_NAME = "Briefing Notes Hub"
APP_UNIQUE = f"{P}_BriefingNotesHub"
APP_DESC = ("Track briefing note requests from intake to delivery: AI drafts, clarifications, review, "
            "source documents and the activity timeline.")
APP_ROLES = ["Briefing Requester", "Briefing Reviewer", "Briefing Admin", "System Administrator"]
DEFAULT_APP_ICON = "953b9fac-1e5e-e611-80d6-00155ded156f"  # the platform's default model-driven app icon
ENV_URL = os.environ["DATAVERSE_URL"].rstrip("/")

CLASSID = {
    "string": "{4273EDBD-AC1D-40d3-9FB2-095C621B552D}", "autonumber": "{4273EDBD-AC1D-40d3-9FB2-095C621B552D}",
    # File columns use the text classid in platform forms (e.g. packagehistory.packagefile); UCI renders the file control.
    "file": "{4273EDBD-AC1D-40d3-9FB2-095C621B552D}",
    "email": "{ADA2203E-B4CD-49be-9DDF-234642B43B52}", "url": "{71716B6C-711E-476c-8AB8-5D11542BFB47}",
    "memo": "{E0DECE4B-6FC8-4a8f-A065-082708572369}", "int": "{C6D124CA-7EDA-4a60-AEA9-7FB8D318B68F}",
    "money": "{533B9E00-756B-4312-95A0-DC888637AC78}", "bool": "{67FAC785-CD58-4f9f-ABB3-4B7DDC6ED5ED}",
    "date": "{5B773807-9FB2-42db-97C3-7A91EFF8ADFF}", "datetime": "{5B773807-9FB2-42db-97C3-7A91EFF8ADFF}",
    "choice": "{3EF39988-22BB-4f0b-BBBE-64B5A3748AEE}", "multichoice": "{4AA28AB7-9C13-4F57-A73D-AD894D048B5F}",
    "lookup": "{270BD3DB-D9AF-4782-9025-509E298DEC0A}", "subgrid": "{E7A81278-8635-4d9e-8D4D-59480B391C5B}",
}


def gid(name):
    return str(uuid.uuid5(NS, name))


def brace(x):
    return "{" + x.upper() + "}"


def g():
    return brace(str(uuid.uuid4()))


def label_xml(text):
    return f'<labels><label description="{escape(text)}" languagecode="1033" /></labels>'


def f(name):
    return f"{P}_{name}"


TABLES = {t["schema"].lower(): t for t in S.TABLES}
TYPES = {}
for logical, t in TABLES.items():
    TYPES[logical] = {f"{P}_{t['primary'][0].lower()}": ("string", t["primary"][1]),
                      "createdon": ("datetime", "Created On"), "modifiedon": ("datetime", "Modified On")}
    if t.get("ownership", "UserOwned") != "OrganizationOwned":
        TYPES[logical]["ownerid"] = ("lookup", "Owner")
    for suffix, display, kind, _ in t["columns"]:
        TYPES[logical][f"{P}_{suffix.lower()}"] = (kind, display)
for r in S.RELATIONSHIPS:
    TYPES[r["referencing"]][r["lookup_schema"].lower()] = ("lookup", r["lookup_display"])

R, SD, ACT, PRO, TPL = f("request"), f("sourcedocument"), f("activity"), f("profile"), f("template")


def rel(referenced, referencing, lookup):
    return next(r["schema"] for r in S.RELATIONSHIPS if r["referenced"] == f"{P}_{referenced}"
                and r["referencing"] == f"{P}_{referencing}" and r["lookup_schema"] == f"{P}_{lookup}")


# ---------------------------------------------------------------- generic upsert helpers
def write(method, path, body, attempts=4, **kw):
    """call() plus retries for 'Connection State is closed' (0x8004023b, HTTP 405), which dv_api treats as final."""
    for i in range(attempts):
        status, payload, headers = call(method, path, body, **kw)
        if status < 300 or "0x8004023b" not in str(payload) or i == attempts - 1:
            return status, payload, headers
        log(f"[RETRY] {method} {path.split('?')[0]}: connection state closed")
        time.sleep(10)


def upsert(entity_set, key, record_id, body, what):
    status, _, _ = call("GET", f"{entity_set}({record_id})?$select={key}", solution=False)
    if status == 200:
        ok(*write("PATCH", f"{entity_set}({record_id})", body)[:2], f"update {what}")
    else:
        ok(*write("POST", entity_set, {**body, key: record_id})[:2], f"create {what}")
    return record_id


def meta(table):
    status, payload, _ = call("GET", f"EntityDefinitions(LogicalName='{table}')?$select=ObjectTypeCode,MetadataId",
                              solution=False)
    ok(status, payload, f"metadata {table}")
    return payload["ObjectTypeCode"], payload["MetadataId"]


# ---------------------------------------------------------------- forms
def field_cell(table, attr, disabled=False, rowspan=None):
    kind, display = TYPES[table][attr]
    rs = f' rowspan="{rowspan}"' if rowspan else ""
    return (f'<cell id="{g()}" showlabel="true"{rs}>{label_xml(display)}'
            f'<control id="{attr}" classid="{CLASSID[kind]}" datafieldname="{attr}" disabled="{str(disabled).lower()}" /></cell>')


def section(title, table, fields, columns=2, show_label=True, readonly=(), tall=None):
    """tall: {attr: rowspan} for large text areas (single-column sections only)."""
    tall = tall or {}
    rows = []
    for i in range(0, len(fields), columns):
        chunk = fields[i:i + columns]
        cells = "".join(field_cell(table, x, x in readonly, tall.get(x)) for x in chunk)
        cells += "".join(f'<cell id="{g()}" showlabel="false">{label_xml("")}</cell>' for _ in range(columns - len(chunk)))
        rows.append(f"<row>{cells}</row>")
        span = max((tall.get(x, 1) for x in chunk), default=1)
        rows.extend("<row />" for _ in range(span - 1))
    return (f'<section name="{escape(title)}" id="{g()}" showlabel="{str(show_label).lower()}" showbar="false" '
            f'columns="{"1" * columns}">{label_xml(title)}<rows>{"".join(rows)}</rows></section>')


def raw_section(title, inner_cell, show_label=True):
    return (f'<section name="{escape(title)}" id="{g()}" showlabel="{str(show_label).lower()}" showbar="false" columns="1">'
            f'{label_xml(title)}<rows><row>{inner_cell}</row></rows></section>')


def tab(title, sections, expanded=True):
    return (f'<tab name="{escape(title)}" id="{g()}" expanded="{str(expanded).lower()}" showlabel="true">{label_xml(title)}'
            f'<columns><column width="100%"><sections>{"".join(sections)}</sections></column></columns></tab>')


def subgrid_cell(target, view_id, relationship, rows=8, title=""):
    control = f"{target}_{uuid.uuid4().hex[:6]}"
    return (f'<cell id="{g()}" showlabel="{str(bool(title)).lower()}" rowspan="{rows}" colspan="1" auto="false">'
            f'{label_xml(title)}<control id="{control}" classid="{CLASSID["subgrid"]}" indicationOfSubgrid="true"><parameters>'
            f'<ViewId>{brace(view_id)}</ViewId><IsUserView>false</IsUserView>'
            f'<RelationshipName>{relationship}</RelationshipName><TargetEntityType>{target}</TargetEntityType>'
            f'<AutoExpand>Fixed</AutoExpand><EnableQuickFind>false</EnableQuickFind><EnableViewPicker>false</EnableViewPicker>'
            f'<EnableJumpBar>false</EnableJumpBar><ChartGridMode>Grid</ChartGridMode><VisualizationId />'
            f'<IsUserChart>false</IsUserChart><EnableChartPicker>false</EnableChartPicker><RecordsPerPage>10</RecordsPerPage>'
            f'</parameters></control></cell>')


def subgrid_tab(title, target, view_id, relationship, rows=10):
    return tab(title, [raw_section(title, subgrid_cell(target, view_id, relationship, rows), show_label=False)])


def header(table, fields):
    cells = "".join(
        f'<cell id="{g()}" showlabel="true">{label_xml(TYPES[table][x][1])}'
        f'<control id="header_{x}" classid="{CLASSID[TYPES[table][x][0]]}" datafieldname="{x}" disabled="false" /></cell>'
        for x in fields)
    return (f'<header id="{g()}" celllabelposition="Top" columns="{"1" * len(fields)}" labelwidth="115" '
            f'celllabelalignment="Left"><rows><row>{cells}</row></rows></header>')


def form_xml(tabs, hdr=""):
    return (f'<form><tabs>{"".join(tabs)}</tabs>{hdr}<footer id="{g()}" celllabelposition="Top" columns="111" '
            f'labelwidth="115" celllabelalignment="Left"><rows /></footer></form>')


def main_form_id(table):
    status, payload, _ = call("GET", f"systemforms?$select=formid&$filter=objecttypecode%20eq%20'{table}'%20and%20type%20eq%202",
                              solution=False)
    ok(status, payload, f"find main form {table}")
    return payload["value"][0]["formid"]


def save_form(table, name, tabs, hdr_fields=()):
    hdr = header(table, list(hdr_fields)) if hdr_fields else ""
    form_id = main_form_id(table)
    ok(*write("PATCH", f"systemforms({form_id})", {"name": name, "formxml": form_xml(tabs, hdr)})[:2],
       f"main form {name}")
    return form_id


def request_form(views):
    tabs = [
        tab("Request", [
            section("Briefing request", R, [f("name"), f("requestnumber"), f("status"), f("profileid"),
                                            f("templateid"), f("intakechannel")], readonly=(f("requestnumber"),)),
            section("People", R, [f("requestername"), f("requesteremail"), f("recipientname"), f("recipienttitle"),
                                  f("recipientemail"), f("revieweremail")]),
            section("Purpose", R, [f("purpose"), f("additionalcontext")], columns=1,
                    tall={f("purpose"): 4, f("additionalcontext"): 6}),
            section("Handling", R, [f("language"), f("classification"), f("priority"), f("duedate"),
                                    f("deliverymode")]),
        ]),
        tab("Clarifications", [
            section("Clarifications", R, [f("clarificationrounds")], show_label=False),
            section("Questions and answers", R, [f("clarificationquestions"), f("clarificationanswers")], columns=1,
                    tall={f("clarificationquestions"): 6, f("clarificationanswers"): 8}),
        ]),
        tab("Draft", [
            section("Draft", R, [f("notetitle"), f("confidence"), f("wordcount"), f("draftversion")]),
            section("Key message", R, [f("keymessage")], columns=1, show_label=False, tall={f("keymessage"): 3}),
            section("Draft sections (JSON)", R, [f("draftsections")], columns=1, readonly=(f("draftsections"),),
                    tall={f("draftsections"): 16}),
            section("Sources and verification", R, [f("sourcesused"), f("verificationnotes")], columns=1,
                    tall={f("sourcesused"): 4, f("verificationnotes"): 6}),
            section("Review", R, [f("reviewercomments")], columns=1, tall={f("reviewercomments"): 6}),
        ]),
        tab("Delivery", [
            section("Documents", R, [f("draftpdfurl"), f("finalpdfurl"), f("sharepointfolderurl")], columns=1),
            section("Tracking", R, [f("submittedon"), f("draftedon"), f("approvedon"), f("approvedby"),
                                    f("deliveredon"), "ownerid"]),
            section("Last error", R, [f("lasterror")], columns=1, tall={f("lasterror"): 4}),
        ]),
        subgrid_tab("Source documents", SD, views["assoc:sourcedocument"], rel("request", "sourcedocument", "RequestId")),
        subgrid_tab("Timeline", ACT, views["assoc:activity"], rel("request", "activity", "RequestId"), 14),
    ]
    return save_form(R, "Briefing Request", tabs, [f("status"), f("priority"), f("duedate"), "ownerid"])


def source_document_form():
    tabs = [
        tab("Document", [
            section("Source document", SD, [f("sourcelabel"), f("name"), f("requestid"), f("documenttype"),
                                            f("file"), f("extractionstatus"), f("pagecount"), f("charactercount")]),
            section("Summary", SD, [f("summary")], columns=1, tall={f("summary"): 5}),
        ]),
        tab("Extracted text", [section("Extracted text", SD, [f("extractedtext")], columns=1, show_label=False,
                                       readonly=(f("extractedtext"),), tall={f("extractedtext"): 20})]),
    ]
    return save_form(SD, "Source Document", tabs, [f("sourcelabel"), f("documenttype"), f("extractionstatus")])


def profile_form(views):
    tabs = [
        tab("General", [
            section("Organization", PRO, [f("name"), f("code"), f("sector"), f("defaultlanguage"),
                                          f("defaultrevieweremail"), f("leadertitles"), f("isactive")]),
            section("Description", PRO, [f("description")], columns=1, show_label=False, tall={f("description"): 3}),
        ]),
        tab("Writing guidance", [
            section("Writing guidance", PRO, [f("styleguide"), f("glossary"), f("classificationguidance")], columns=1,
                    show_label=False, tall={f("styleguide"): 10, f("glossary"): 10, f("classificationguidance"): 5}),
        ]),
        tab("Documents and filing", [
            section("SharePoint", PRO, [f("sharepointsiteurl"), f("sharepointlibrary"), f("sharepointrootfolder")],
                    columns=1),
            section("PDF branding", PRO, [f("accentcolor"), f("footertext")]),
        ]),
        subgrid_tab("Briefing requests", R, views["assoc:request"], rel("profile", "request", "ProfileId")),
    ]
    return save_form(PRO, "Briefing Profile", tabs, [f("code"), f("sector"), f("isactive")])


def template_form(views):
    tabs = [
        tab("General", [
            section("Template", TPL, [f("name"), f("code"), f("notetype"), f("maxwords"), f("sortorder"),
                                      f("isactive")]),
            section("When to use", TPL, [f("whentouse")], columns=1, show_label=False, tall={f("whentouse"): 4}),
        ]),
        tab("Structure and rules", [
            section("Structure and rules", TPL, [f("sections"), f("writingrules")], columns=1, show_label=False,
                    tall={f("sections"): 10, f("writingrules"): 10}),
        ]),
        subgrid_tab("Briefing requests", R, views["assoc:request"], rel("template", "request", "TemplateId")),
    ]
    return save_form(TPL, "Note Template", tabs, [f("notetype"), f("maxwords"), f("isactive")])


def activity_form():
    tabs = [
        tab("Activity", [
            section("Activity", ACT, [f("name"), f("requestid"), f("actor"), f("activitytype"), f("startedon"),
                                      f("completedon"), f("durationseconds"), f("workflowrun")]),
            section("Details", ACT, [f("details")], columns=1, show_label=False, tall={f("details"): 10}),
        ]),
    ]
    return save_form(ACT, "Briefing Activity", tabs, [f("actor"), f("activitytype"), f("startedon")])


# ---------------------------------------------------------------- views
VIEW_COLS = {
    R: [(f("requestnumber"), 100), (f("name"), 260), (f("status"), 140), (f("templateid"), 190),
        (f("recipientname"), 160), (f("duedate"), 100), (f("priority"), 90), (f("requestername"), 150),
        ("modifiedon", 130)],
    SD: [(f("sourcelabel"), 70), (f("name"), 260), (f("documenttype"), 160), (f("extractionstatus"), 120),
         (f("pagecount"), 70), (f("charactercount"), 90), (f("requestid"), 200), ("createdon", 130)],
    ACT: [(f("name"), 300), (f("actor"), 160), (f("activitytype"), 160), (f("startedon"), 140),
          (f("durationseconds"), 90), (f("requestid"), 200), ("createdon", 140)],
    PRO: [(f("name"), 240), (f("code"), 80), (f("sector"), 120), (f("defaultlanguage"), 110),
          (f("defaultrevieweremail"), 200), (f("isactive"), 70)],
    TPL: [(f("name"), 260), (f("code"), 80), (f("notetype"), 220), (f("maxwords"), 90), (f("sortorder"), 80),
          (f("isactive"), 70)],
}
QUICKFIND = {R: [f("requestnumber"), f("name")], SD: [f("name"), f("sourcelabel")], ACT: [f("name")],
             PRO: [f("name"), f("code")], TPL: [f("name"), f("code")]}
ORDER = {R: [("modifiedon", True)], SD: [(f("sourcelabel"), False)], ACT: [("createdon", True)],
         PRO: [(f("name"), False)], TPL: [(f("sortorder"), False), (f("name"), False)]}
ASSOC_DROP = {f("requestid"), f("profileid"), f("templateid")}


def fetch(table, cols, conditions="", order=None, active=True):
    order = order or ORDER.get(table, [("createdon", True)])
    attrs = "".join(f'<attribute name="{c}" />' for c, _ in cols) + f'<attribute name="{table}id" />'
    orders = "".join(f'<order attribute="{a}" descending="{str(d).lower()}" />' for a, d in order)
    state = '<condition attribute="statecode" operator="eq" value="0" />' if active else ""
    flt = f'<filter type="and">{state}{conditions}</filter>' if (state or conditions) else ""
    return (f'<fetch version="1.0" output-format="xml-platform" mapping="logical" distinct="false">'
            f'<entity name="{table}">{attrs}{orders}{flt}</entity></fetch>')


def quickfind_fetch(table, cols):
    finds = "".join(f'<condition attribute="{c}" operator="like" value="{{0}}" />' for c in QUICKFIND[table])
    attrs = "".join(f'<attribute name="{c}" />' for c, _ in cols) + f'<attribute name="{table}id" />'
    orders = "".join(f'<order attribute="{a}" descending="{str(d).lower()}" />' for a, d in ORDER[table])
    return (f'<fetch version="1.0" output-format="xml-platform" mapping="logical" distinct="false">'
            f'<entity name="{table}">{attrs}{orders}<filter type="and">'
            f'<condition attribute="statecode" operator="eq" value="0" /></filter>'
            f'<filter type="or" isquickfindfields="1">{finds}</filter></entity></fetch>')


def layout(table, code, cols):
    cells = "".join(f'<cell name="{c}" width="{w}" />' for c, w in cols)
    return (f'<grid name="resultset" object="{code}" jump="{P}_name" select="1" icon="1" preview="1">'
            f'<row name="result" id="{table}id">{cells}</row></grid>')


def status_in(attr, choice, *labels, operator="in"):
    vals = "".join(f"<value>{v(choice, lbl)}</value>" for lbl in labels)
    return f'<condition attribute="{attr}" operator="{operator}">{vals}</condition>'


def existing_views(table, querytype, default_only=False):
    flt = f"returnedtypecode%20eq%20'{table}'%20and%20querytype%20eq%20{querytype}"
    if default_only:
        flt += "%20and%20isdefault%20eq%20true"
    status, payload, _ = call("GET", f"savedqueries?$select=savedqueryid,name&$filter={flt}", solution=False)
    ok(status, payload, f"find views {table}/{querytype}")
    return payload["value"]


ST = f("status")
OPEN = status_in(ST, "requeststatus", "Delivered", "Cancelled", operator="not-in")
CUSTOM_VIEWS = [
    # (name, table, condition, order, active only)
    ("My Briefing Requests", R, '<condition attribute="ownerid" operator="eq-userid" />', None, True),
    ("Briefing Requests Needing Info", R, status_in(ST, "requeststatus", "Needs Info"), None, True),
    ("Briefing Requests In Review", R, status_in(ST, "requeststatus", "In Review"), [(f("duedate"), False)], True),
    ("Approved and Delivered Briefing Requests", R, status_in(ST, "requeststatus", "Approved", "Delivered"), None, True),
    ("Briefing Requests Needing Attention", R, status_in(ST, "requeststatus", "Needs Attention"), None, True),
    ("Overdue Briefing Requests", R,
     f'<condition attribute="{f("duedate")}" operator="olderthan-x-days" value="1" />{OPEN}',
     [(f("duedate"), False)], True),
    ("All Briefing Requests", R, "", None, False),
    ("Activities by Request", ACT, "", [(f("requestid"), False), ("createdon", True)], True),
]


def build_views(codes):
    views = {}
    for table, cols in VIEW_COLS.items():
        code, short = codes[table], table[len(P) + 1:]
        default = existing_views(table, 0, default_only=True)[0]
        ok(*write("PATCH", f"savedqueries({default['savedqueryid']})",
                 {"fetchxml": fetch(table, cols), "layoutxml": layout(table, code, cols)})[:2],
           f"default view {default['name']}")
        views[f"default:{short}"] = default["savedqueryid"]
        for qv in existing_views(table, 4):
            # The Web API may reject fetchxml updates on quick find views (0x80040216): fall back to the layout only.
            status, err, _ = call("PATCH", f"savedqueries({qv['savedqueryid']})",
                                {"fetchxml": quickfind_fetch(table, cols[:6]), "layoutxml": layout(table, code, cols[:6])},
                                retries=0)
            if status >= 300:
                log(f"[INFO] quick find fetchxml rejected for {table}: {str(err)[:160]}")
                status, _, _ = write("PATCH", f"savedqueries({qv['savedqueryid']})",
                                     {"layoutxml": layout(table, code, cols[:6])}, retries=0)
                log(f"[{'OK' if status < 300 else 'WARN'}]   quick find layout only {table}")
            else:
                log(f"[OK]   quick find {table} ({', '.join(QUICKFIND[table])})")
        assoc = existing_views(table, 2)
        if assoc:
            a_cols = [c for c in cols if c[0] not in ASSOC_DROP][:8]
            ok(*write("PATCH", f"savedqueries({assoc[0]['savedqueryid']})",
                     {"fetchxml": fetch(table, a_cols), "layoutxml": layout(table, code, a_cols)})[:2],
               f"associated view {table}")
            views[f"assoc:{short}"] = assoc[0]["savedqueryid"]
    for name, table, cond, order, active in CUSTOM_VIEWS:
        vid = gid(f"view:{name}")
        upsert("savedqueries", "savedqueryid", vid, {
            "name": name, "returnedtypecode": table, "querytype": 0, "isdefault": False, "isquickfindquery": False,
            "fetchxml": fetch(table, VIEW_COLS[table], cond, order, active),
            "layoutxml": layout(table, codes[table], VIEW_COLS[table]),
        }, f"view {name}")
        views[name] = vid
    return views


# ---------------------------------------------------------------- charts
PALETTE = "0,120,212; 127,186,0; 255,185,0; 242,80,34; 0,164,239; 135,100,184; 115,115,115; 16,124,16"


def chart_data(table, group_attr, measure=("count", None), date_grouping=None):
    agg, attr = measure
    dg = f' dategrouping="{date_grouping}"' if date_grouping else ""
    return (f'<datadefinition><fetchcollection><fetch mapping="logical" aggregate="true"><entity name="{table}">'
            f'<attribute groupby="true" alias="groupby_column" name="{group_attr}"{dg} />'
            f'<attribute alias="aggregate_column" name="{attr or table + "id"}" aggregate="{agg}" />'
            f'</entity></fetch></fetchcollection><categorycollection><category alias="groupby_column">'
            f'<measurecollection><measure alias="aggregate_column" /></measurecollection></category>'
            f'</categorycollection></datadefinition>')


def chart_presentation(kind):
    axis = ('<AxisY LabelAutoFitMinFontSize="8" TitleForeColor="59, 59, 59" TitleFont="{0}, 10.5px" LineColor="165, 172, 181" IntervalAutoMode="VariableCount">'
            '<MajorGrid LineColor="239, 242, 246" /><MajorTickMark LineColor="165, 172, 181" /><LabelStyle Font="{0}, 10.5px" ForeColor="59, 59, 59" /></AxisY>'
            '<AxisX LabelAutoFitMinFontSize="8" TitleForeColor="59, 59, 59" TitleFont="{0}, 10.5px" LineColor="165, 172, 181" IntervalAutoMode="VariableCount">'
            '<MajorTickMark LineColor="165, 172, 181" /><MajorGrid LineColor="Transparent" /><LabelStyle Font="{0}, 10.5px" ForeColor="59, 59, 59" /></AxisX>')
    if kind == "Pie":
        series = ('<Series ChartType="Doughnut" IsValueShownAsLabel="True" Font="{0}, 9.5px" LabelForeColor="59, 59, 59" '
                  'CustomProperties="PieLabelStyle=Inside, PieDrawingStyle=Default, DoughnutRadius=60"><SmartLabelStyle Enabled="True" /></Series>')
        legend = ('<Legends><Legend Alignment="Center" LegendStyle="Table" Docking="right" IsEquallySpacedItems="True" '
                  'Font="{0}, 11px" ShadowColor="0, 0, 0, 0" ForeColor="59, 59, 59" /></Legends>')
        area = '<ChartArea BorderColor="White" BorderDashStyle="Solid" />'
    else:
        series = (f'<Series ChartType="{kind}" IsValueShownAsLabel="True" Font="{{0}}, 9.5px" LabelForeColor="59, 59, 59" '
                  f'Color="0, 120, 212" BorderWidth="3" CustomProperties="PointWidth=0.75, MaxPixelPointWidth=40">'
                  f'<SmartLabelStyle Enabled="True" /></Series>')
        legend = ""
        area = f'<ChartArea BorderColor="White" BorderDashStyle="Solid">{axis}</ChartArea>'
    return (f'<Chart Palette="None" PaletteCustomColors="{PALETTE}"><Series>{series}</Series><ChartAreas>{area}</ChartAreas>'
            f'<Titles><Title Alignment="TopLeft" DockingOffset="-3" Font="{{0}}, 13px" ForeColor="59, 59, 59"></Title></Titles>'
            f'{legend}</Chart>')


CHARTS = [
    # name, table, group by, kind, measure, date grouping
    ("Briefing Requests by Status", R, f("status"), "Column", ("count", None), None),
    ("Briefing Requests by Note Template", R, f("templateid"), "Bar", ("count", None), None),
    ("Briefing Requests by Priority", R, f("priority"), "Pie", ("count", None), None),
    ("Briefing Requests Created per Week", R, "createdon", "Line", ("count", None), "week"),
    ("Briefing Activities by Type", ACT, f("activitytype"), "Bar", ("count", None), None),
]


def build_charts():
    ids = {}
    for name, table, attr, kind, measure, dg in CHARTS:
        cid = gid(f"chart:{name}")
        upsert("savedqueryvisualizations", "savedqueryvisualizationid", cid, {
            "name": name, "primaryentitytypecode": table, "isdefault": False,
            "datadescription": chart_data(table, attr, measure, dg), "presentationdescription": chart_presentation(kind),
        }, f"chart {name}")
        ids[name] = cid
    return ids


# ---------------------------------------------------------------- dashboard
def dash_cell(title, target, view_id, chart_id=None, colspan=1, rowspan=12):
    mode = "Chart" if chart_id else "Grid"
    vis = f"<VisualizationId>{brace(chart_id)}</VisualizationId>" if chart_id else "<VisualizationId />"
    return (f'<cell id="{g()}" showlabel="true" rowspan="{rowspan}" colspan="{colspan}" auto="false">{label_xml(title)}'
            f'<control id="{target}_{uuid.uuid4().hex[:8]}" classid="{CLASSID["subgrid"]}"><parameters>'
            f'<ViewId>{brace(view_id)}</ViewId><IsUserView>false</IsUserView><RelationshipName />'
            f'<TargetEntityType>{target}</TargetEntityType><AutoExpand>Fixed</AutoExpand><EnableQuickFind>false</EnableQuickFind>'
            f'<EnableViewPicker>false</EnableViewPicker><EnableJumpBar>false</EnableJumpBar><ChartGridMode>{mode}</ChartGridMode>'
            f'{vis}<IsUserChart>false</IsUserChart><EnableChartPicker>false</EnableChartPicker><RecordsPerPage>10</RecordsPerPage>'
            f'</parameters></control></cell>')


def dashboard(key, name, desc, rows):
    blank = "<row />" * 11
    body = "".join("<row>" + "".join(r) + "</row>" + blank for r in rows)
    xml = (f'<form><tabs><tab name="{escape(name)}" id="{g()}" verticallayout="true" showlabel="false">{label_xml(name)}'
           f'<columns><column width="100%"><sections><section name="{escape(name)}" showlabel="false" showbar="false" '
           f'columns="111" id="{g()}">{label_xml(name)}<rows>{body}</rows></section></sections></column>'
           f'</columns></tab></tabs></form>')
    did = gid(f"dashboard:{key}")
    upsert("systemforms", "formid", did, {"name": name, "description": desc, "type": 0, "formxml": xml}, f"dashboard {name}")
    return did


def build_dashboard(views, charts):
    all_req, all_act = views["default:request"], views["default:activity"]
    return dashboard("overview", "Briefing Overview",
                     "Briefing requests by status, note template and priority; intake trend; work waiting on people.", [
                         [dash_cell("Requests by Status", R, all_req, charts["Briefing Requests by Status"]),
                          dash_cell("Requests by Note Template", R, all_req, charts["Briefing Requests by Note Template"]),
                          dash_cell("Requests by Priority", R, all_req, charts["Briefing Requests by Priority"])],
                         [dash_cell("Requests Created per Week", R, views["All Briefing Requests"],
                                    charts["Briefing Requests Created per Week"]),
                          dash_cell("Activities by Type", ACT, all_act, charts["Briefing Activities by Type"]),
                          dash_cell("Overdue", R, views["Overdue Briefing Requests"])],
                         [dash_cell("In Review", R, views["Briefing Requests In Review"], colspan=3)],
                         [dash_cell("Needs Info", R, views["Briefing Requests Needing Info"], colspan=3)],
                         [dash_cell("Needs Attention", R, views["Briefing Requests Needing Attention"], colspan=3)],
                     ])


# ---------------------------------------------------------------- app + site map
def sitemap_xml(dash_id):
    def sub(sid, title, attrs):
        return f'<SubArea Id="{sid}" {attrs}><Titles><Title LCID="1033" Title="{escape(title)}" /></Titles></SubArea>'

    def group(gid_, title, subs):
        return (f'<Group Id="{gid_}" IsProfile="false"><Titles><Title LCID="1033" Title="{escape(title)}" /></Titles>'
                f'{"".join(subs)}</Group>')

    def area(aid, title, groups):
        return f'<Area Id="{aid}" ShowGroups="true"><Titles><Title LCID="1033" Title="{escape(title)}" /></Titles>{"".join(groups)}</Area>'

    def ent(sid, title, table):
        return sub(sid, title, f'Entity="{table}"')

    dash = sub(f"{P}_sa_dashboard", "Dashboard",
               f'DefaultDashboard="{brace(dash_id)}" Url="/workplace/home_dashboards.aspx" '
               'Client="All,Outlook,OutlookLaptopClient,OutlookWorkstationClient,Web" AvailableOffline="true"')
    return (
        '<SiteMap IntroducedVersion="7.0.0.0">'
        + area(f"{P}_area_briefings", "Briefings", [
            group(f"{P}_grp_briefings", "Briefings", [
                dash,
                ent(f"{P}_sa_requests", "Briefing Requests", R),
                ent(f"{P}_sa_sourcedocs", "Source Documents", SD),
                ent(f"{P}_sa_activity", "Activity", ACT),
            ]),
        ])
        + area(f"{P}_area_config", "Configuration", [
            group(f"{P}_grp_config", "Configuration", [
                ent(f"{P}_sa_profiles", "Briefing Profiles", PRO),
                ent(f"{P}_sa_templates", "Note Templates", TPL),
            ]),
        ])
        + "</SiteMap>"
    )


def find_app():
    flt = f"$select=appmoduleid,uniquename,name&$filter=uniquename%20eq%20'{APP_UNIQUE}'"
    for path in (f"appmodules?{flt}", f"appmodules/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple()?{flt}"):
        status, payload, _ = call("GET", path, solution=False)
        if status == 200 and payload["value"]:
            return payload["value"][0]
    return None


def find_sitemap():
    flt = f"$select=sitemapid&$filter=sitemapnameunique%20eq%20'{APP_UNIQUE}'"
    for path in (f"sitemaps?{flt}", f"sitemaps/Microsoft.Dynamics.CRM.RetrieveUnpublishedMultiple()?{flt}"):
        status, payload, _ = call("GET", path, solution=False)
        if status == 200 and payload["value"]:
            return payload["value"][0]["sitemapid"]
    return None


def build_app(dash_id, views, entity_ids, form_ids, chart_ids):
    app = find_app()
    if app:
        app_id = app["appmoduleid"]
        ok(*write("PATCH", f"appmodules({app_id})", {"name": APP_NAME, "description": APP_DESC})[:2], "update app module")
    else:
        app_id = gid("appmodule:hub")
        ok(*write("POST", "appmodules", {
            "appmoduleid": app_id, "name": APP_NAME, "uniquename": APP_UNIQUE, "description": APP_DESC,
            "webresourceid": DEFAULT_APP_ICON, "clienttype": 4, "formfactor": 1, "navigationtype": 0,
        })[:2], "create app module")

    sm_id = find_sitemap()
    if sm_id:
        ok(*write("PATCH", f"sitemaps({sm_id})", {"sitemapname": APP_NAME, "sitemapxml": sitemap_xml(dash_id)})[:2],
           "update site map")
    else:
        sm_id = gid("sitemap:hub")
        ok(*write("POST", "sitemaps", {"sitemapid": sm_id, "sitemapname": APP_NAME, "sitemapnameunique": APP_UNIQUE,
                                      "isappaware": True, "sitemapxml": sitemap_xml(dash_id)})[:2], "create site map")

    comps = [{"@odata.type": "Microsoft.Dynamics.CRM.sitemap", "sitemapid": sm_id},
             {"@odata.type": "Microsoft.Dynamics.CRM.systemform", "formid": dash_id}]
    comps += [{"@odata.type": "Microsoft.Dynamics.CRM.entity", "entityid": e} for e in entity_ids]
    comps += [{"@odata.type": "Microsoft.Dynamics.CRM.systemform", "formid": x} for x in form_ids]
    comps += [{"@odata.type": "Microsoft.Dynamics.CRM.savedquery", "savedqueryid": x} for x in views.values()]
    comps += [{"@odata.type": "Microsoft.Dynamics.CRM.savedqueryvisualization", "savedqueryvisualizationid": c}
              for c in chart_ids]
    ok(*write("POST", "AddAppComponents", {"AppId": app_id, "Components": comps}, solution=False)[:2], "app components")
    status, payload, _ = call("GET", f"ValidateApp(AppModuleId={app_id})", solution=False)
    ok(status, payload, "validate app")
    for issue in payload.get("AppValidationResponse", {}).get("ValidationIssueList", []):
        if issue.get("Message"):
            log(f"       {issue.get('ErrorType')}: {issue.get('Message')}")
    return app_id, sm_id


def assign_roles(app_id):
    status, payload, _ = call("GET", f"appmodules({app_id})/appmoduleroles_association?$select=roleid", solution=False)
    current = {r["roleid"] for r in payload["value"]} if status == 200 else set()
    for name in APP_ROLES:
        status, payload, _ = call("GET", f"roles?$select=roleid&$filter=name%20eq%20'{q(name)}'%20and%20"
                                  "_parentroleid_value%20eq%20null", solution=False)
        ok(status, payload, f"find role {name}")
        if not payload["value"]:
            log(f"[WARN] role {name} not found")
            continue
        role_id = payload["value"][0]["roleid"]
        if role_id in current:
            log(f"[OK]   app role {name} (already assigned)")
            continue
        status, payload, _ = call("POST", f"appmodules({app_id})/appmoduleroles_association/$ref",
                                  {"@odata.id": f"{BASE}roles({role_id})"}, solution=False)
        if status >= 300 and "duplicate" in str(payload).lower():
            status = 204
        ok(status, payload, f"app role {name}")


def set_app_url(app_id):
    url = f"{ENV_URL}/main.aspx?appid={app_id}"
    schema = f"{P}_AppBaseUrl"
    status, payload, _ = call("GET", f"environmentvariabledefinitions?$select=environmentvariabledefinitionid&"
                              f"$filter=schemaname%20eq%20'{schema}'", solution=False)
    ok(status, payload, f"find env var {schema}")
    if not payload["value"]:
        log(f"[WARN] environment variable {schema} not found: run create_schema.py")
        return url
    def_id = payload["value"][0]["environmentvariabledefinitionid"]
    status, payload, _ = call("GET", "environmentvariablevalues?$select=environmentvariablevalueid,value&$filter="
                              f"_environmentvariabledefinitionid_value%20eq%20{def_id}", solution=False)
    ok(status, payload, "find env var value")
    if payload["value"]:
        val_id = payload["value"][0]["environmentvariablevalueid"]
        ok(*write("PATCH", f"environmentvariablevalues({val_id})", {"value": url})[:2], f"update {schema} value")
    else:
        val_id = gid("envvalue:AppBaseUrl")
        ok(*write("POST", "environmentvariablevalues", {
            "environmentvariablevalueid": val_id, "schemaname": schema, "value": url,
            "EnvironmentVariableDefinitionId@odata.bind": f"/environmentvariabledefinitions({def_id})"})[:2],
           f"create {schema} value")
    add_to_solution(val_id, 381, f"{schema} value")
    return url


def main():
    codes, metas = {}, {}
    for table in TABLES:
        codes[table], metas[table] = meta(table)
    views = build_views(codes)
    forms = [request_form(views), source_document_form(), profile_form(views), template_form(views), activity_form()]
    charts = build_charts()
    dash_id = build_dashboard(views, charts)
    for vid in views.values():
        add_to_solution(vid, 26, "view")
    for cid in charts.values():
        add_to_solution(cid, 59, "chart")
    for fid in forms + [dash_id]:
        add_to_solution(fid, 60, "form")
    app_id, sm_id = build_app(dash_id, views, list(metas.values()), forms, list(charts.values()))
    add_to_solution(sm_id, 62, "site map")
    add_to_solution(app_id, 80, APP_NAME)
    assign_roles(app_id)
    xml = ("<importexportxml><entities>" + "".join(f"<entity>{t}</entity>" for t in TABLES) + "</entities>"
           f"<dashboards><dashboard>{brace(dash_id)}</dashboard></dashboards>"
           f"<sitemaps><sitemap>{brace(sm_id)}</sitemap></sitemaps>"
           f"<appmodules><appmodule>{app_id}</appmodule></appmodules></importexportxml>")
    ok(*write("POST", "PublishXml", {"ParameterXml": xml}, solution=False)[:2], "publish")
    url = set_app_url(app_id)
    log(f"[OK]   solution inventory {solution_inventory()}")
    log(f"[OK]   {APP_NAME}: {url}")
    print(app_id)


if __name__ == "__main__":
    main()
