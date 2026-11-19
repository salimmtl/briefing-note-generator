"""Generate and deploy the two Copilot Studio workflows of the Briefing Note Generator (idempotent).

  BN 1 - Draft Briefing Note    trigger: request status -> Submitted | Info Provided | Revision Requested
      claim (Drafting) -> run the Briefing Note Writer (GHCP agent node) ->
        needs_info: status Needs Info, notify the requester (Teams + email) with the questions   <- human in the loop
        draft:      render the DRAFT PDF (HTML -> OneDrive convert -> SharePoint), status In Review,
                    notify the reviewer and the requester                                         <- human in the loop
  BN 2 - Deliver Briefing Note  trigger: request status -> Approved
      render the FINAL PDF with the classification marking -> SharePoint -> email (PDF attached) and Teams to the
      requester and, per the delivery mode, the ultimate recipient -> status Delivered

Both are solution-aware cloud flows of the Copilot Studio workflow type (modernflowtype 1). A Catch scope sets
"Needs Attention" with the error, so no request stays "Drafting". Notifications never fail a run.

Usage: python scripts/build_workflows.py [--only draft deliver] [--no-activate]
Writes readable definitions to flows/*.json.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_def as S  # noqa: E402
from dv_api import call, created_id, get, ok, q  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = S.PREFIX
v = S.v
AGENT_OP = "InvokeAgent_V2"
WRITER = f"{P}_BriefingNoteWriter"  # the agent node addresses published agents by schema name
CONNS = {
    "shared_commondataserviceforapps": f"{P}_flows.cr.shared_commondataserviceforapps",
    "shared_sharepointonline": f"{P}_flows.cr.shared_sharepointonline",
    "shared_teams": f"{P}_flows.cr.shared_teams",
    "shared_office365": f"{P}_flows.cr.shared_office365",
    "shared_agentnode": f"{P}_flows.cr.shared_agentnode",
    "shared_onedriveforbusiness": f"{P}_flows.cr.shared_onedriveforbusiness",
}
HUB_URL = f"{P}_AppBaseUrl ({P}_AppBaseUrl)"
STUDIO_URL = f"{P}_StudioUrl ({P}_StudioUrl)"
NL = "decodeUriComponent('%0A')"
ST = {label: value for value, label in S.REQUEST_STATUS}
REQ = "Get_Request"
PRO = "Get_Profile"
T = "triggerOutputs()?['body/{}']"
REQ_ID = T.format(f"{P}_requestid")
FV = "@OData.Community.Display.V1.FormattedValue"
ANY = ["Succeeded", "Failed", "Skipped", "TimedOut"]
TEMPLATE_NAME = f"body('{REQ}')?['_{P}_templateid_value{FV}']"


# ---------------------------------------------------------------- generic builders
def op(connector, operation, params, timeout=None):
    a = {"type": "OpenApiConnection",
         "inputs": {"host": {"apiId": f"/providers/Microsoft.PowerApps/apis/{connector}",
                             "connectionName": connector, "operationId": operation},
                    "parameters": params},
         "runAfter": {}}
    if timeout:
        a["limit"] = {"timeout": timeout}
    return a


def dv(operation, params):
    return op("shared_commondataserviceforapps", operation, params)


def create(entity_set, item):
    return dv("CreateRecord", {"entityName": entity_set, **{f"item/{k}": val for k, val in item.items()}})


def update(entity_set, record_id, item):
    return dv("UpdateRecord", {"entityName": entity_set, "recordId": record_id,
                               **{f"item/{k}": val for k, val in item.items()}})


def get_row(entity_set, record_id):
    return dv("GetItem", {"entityName": entity_set, "recordId": record_id})


def list_rows(entity_set, flt, order=None, top=None):
    params = {"entityName": entity_set, "$filter": flt}
    if order:
        params["$orderby"] = order
    if top:
        params["$top"] = top
    return dv("ListRecords", params)


def compose(value):
    return {"type": "Compose", "inputs": value, "runAfter": {}}


def select(source, mapping):
    return {"type": "Select", "inputs": {"from": source, "select": mapping}, "runAfter": {}}


def chain(actions):
    """Sequential runAfter for an ordered dict of actions (unless one is already set)."""
    prev = None
    for name, a in actions.items():
        if not a.get("runAfter") and prev:
            a["runAfter"] = {prev: ["Succeeded"]}
        prev = name
    return actions


def scope(actions, run_after=None):
    return {"type": "Scope", "actions": chain(actions), "runAfter": run_after or {}}


def tolerant(actions, after):
    """A notification scope that can fail without failing the run: each notification runs whatever happened to the
    previous one, and the action after the scope runs after any outcome."""
    prev = None
    for name, a in actions.items():
        if not a.get("runAfter") and prev:
            a["runAfter"] = {prev: ANY}
        prev = name
    return {"type": "Scope", "actions": actions, "runAfter": {after: ["Succeeded"]}}


def bind(entity_set, expr):
    return f"/{entity_set}(@{{{expr}}})"


def r(col):
    """Expression for a column of the freshly read request."""
    return f"body('{REQ}')?['{P}_{col}']"


def pr(col):
    return f"body('{PRO}')?['{P}_{col}']"


def esc(expr):
    return f"replace(replace(replace(coalesce({expr}, ''), '&', '&amp;'), '<', '&lt;'), '>', '&gt;')"


def para(expr):
    """Plain text -> HTML: escape, keep line breaks, render '- ' lines as bullets."""
    return (f"@{{substring(replace(replace(replace(concat({NL}, {esc(expr)}), {NL}, '<br>'), '<br>- ', "
            f"'<br>&bull;&nbsp;'), '<br><br>&bull;', '<br>&bull;'), 4)}}")


def trunc(expr, size):
    return f"@{{substring(coalesce({expr}, ''), 0, min({size}, length(coalesce({expr}, ''))))}}"


def safe(expr):
    out = expr
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '#', '%', '&']:
        out = f"replace({out}, '{ch}', '-')"
    return out


def agent_node(prompt, props):
    return op("shared_agentnode", AGENT_OP, {
        "body/agentId": WRITER, "body/prompt": prompt,
        "body/outputSchema": {"type": "object", "properties": props, "required": list(props)}}, timeout="PT40M")


def email(to_expr, subject, html, cc_expr=None, attachment=None):
    params = {"emailMessage/To": to_expr, "emailMessage/Subject": subject, "emailMessage/Body": html,
              "emailMessage/Importance": "Normal"}
    if cc_expr:
        params["emailMessage/Cc"] = cc_expr
    if attachment:
        name_expr, content_action = attachment
        params["emailMessage/Attachments"] = [{"Name": f"@{{{name_expr}}}", "ContentBytes": f"@body('{content_action}')"}]
    return op("shared_office365", "SendEmailV2", params)


def teams_chat(to_expr, html):
    """Post to a user in a 1:1 chat with the Flow bot."""
    return op("shared_teams", "PostMessageToConversation", {
        "poster": "Flow bot", "location": "Chat with Flow bot", "body/recipient": to_expr, "body/messageBody": html})


def activity(name, actor, atype, details="", completed=True):
    item = {f"{P}_name": name, f"{P}_RequestId@odata.bind": bind(f"{P}_requests", REQ_ID),
            f"{P}_actor": v("actor", actor), f"{P}_activitytype": v("activitytype", atype),
            f"{P}_startedon": "@variables('startTime')", f"{P}_workflowrun": "@{workflow()?['run']?['name']}",
            f"{P}_details": details}
    if completed:
        item[f"{P}_completedon"] = "@utcNow()"
        item[f"{P}_durationseconds"] = "@div(sub(ticks(utcNow()), ticks(variables('startTime'))), 10000000)"
    return create(f"{P}_activities", item)


def record_link():
    return f"@{{parameters('{HUB_URL}')}}&pagetype=entityrecord&etn={P}_request&id=@{{{REQ_ID}}}"


def links_html(extra=()):
    studio = (f"@{{if(empty(parameters('{STUDIO_URL}')), '', concat('<a href=\"', parameters('{STUDIO_URL}'), "
              f"'\">Open in Briefing Studio</a> &nbsp;|&nbsp; '))}}")
    parts = [f"<a href=\"{u}\">{t}</a>" for t, u in extra]
    return "<p>" + studio + " &nbsp;|&nbsp; ".join(parts + [f"<a href=\"{record_link()}\">Open in Briefing Notes Hub</a>"]) + "</p>"


SIGNATURE = "<p style=\"color:#737373;font-size:9pt\">Sent by the Briefing Note Generator. The note is an AI-assisted draft reviewed by staff.</p>"


# ---------------------------------------------------------------- the briefing note document (HTML -> PDF)
def doc_css():
    accent = f"@{{coalesce({pr('accentcolor')}, '#0F6CBD')}}"
    return ("body{font-family:'Segoe UI',Arial,sans-serif;color:#242424;font-size:10.5pt;line-height:1.45;margin:26px}"
            ".class{text-align:center;font-weight:700;letter-spacing:2px;font-size:9pt;color:#A4262C;margin:0 0 6px}"
            f".rule{{border-top:5px solid {accent};margin:6px 0 12px}}"
            ".kicker{color:#616161;font-size:9pt;text-transform:uppercase;letter-spacing:1px;margin:0}"
            f"h1{{color:{accent};font-size:19pt;margin:4px 0 8px}}"
            f"h2{{color:{accent};font-size:12.5pt;margin:18px 0 5px;border-bottom:1px solid #d1d1d1;padding-bottom:3px}}"
            "table.meta{border-collapse:collapse;width:100%;margin:4px 0 10px}"
            "table.meta td{padding:3px 8px 3px 0;font-size:9.5pt;vertical-align:top}table.meta td.k{color:#616161;width:110px}"
            f".key{{border:1px solid #d1d1d1;border-left:5px solid {accent};background:#f7f9fc;padding:8px 12px;margin:10px 0}}"
            ".draft{background:#FFF4CE;border:1px solid #F1C40F;padding:6px 10px;font-size:9pt;margin:0 0 10px}"
            "table.src{border-collapse:collapse;width:100%}table.src th,table.src td{border:1px solid #d1d1d1;"
            "padding:4px 6px;font-size:8.5pt;text-align:left;vertical-align:top}table.src th{background:#f0f6fc}"
            ".foot{margin-top:26px;border-top:1px solid #d1d1d1;padding-top:6px;color:#707070;font-size:8.5pt}")


def document_html(draft):
    classification = f"@{{toUpper(coalesce({r('classification' + FV)}, 'Unclassified'))}}"
    banner = (f"<div class=\"draft\"><b>DRAFT v@{{{r('draftversion')}}}: for review, not for distribution.</b> "
              f"Confidence: @{{coalesce({r('confidence' + FV)}, 'n/a')}}. Check the verification notes before approving.</div>"
              if draft else "")
    date_line = ("@{formatDateTime(utcNow(), 'yyyy-MM-dd')}" if draft
                 else f"@{{formatDateTime(coalesce({r('approvedon')}, utcNow()), 'yyyy-MM-dd')}}")
    meta = ("<table class=\"meta\">"
            f"<tr><td class=\"k\">For</td><td>@{{coalesce({r('recipientname')}, '')}}@{{if(empty(coalesce({r('recipienttitle')}, '')), '', concat(', ', {r('recipienttitle')}))}}</td></tr>"
            f"<tr><td class=\"k\">Prepared by</td><td>@{{coalesce({r('requestername')}, {r('requesteremail')})}}</td></tr>"
            f"<tr><td class=\"k\">Date</td><td>{date_line}</td></tr>"
            f"<tr><td class=\"k\">Reference</td><td>@{{{r('requestnumber')}}} &middot; @{{coalesce({TEMPLATE_NAME}, 'Briefing note')}}</td></tr>"
            "</table>")
    sections = "@{join(body('Select_Sections'), '')}"
    sources = ("<h2>Sources</h2><table class=\"src\"><tr><th>Ref.</th><th>Document</th><th>Type</th><th>Contribution</th></tr>"
               "@{join(body('Select_Sources'), '')}</table>")
    verification = (f"<h2>Verification notes (reviewer only)</h2><p>{para(r('verificationnotes'))}</p>" if draft else "")
    return ("<html><head><meta charset=\"utf-8\"><style>" + doc_css() + "</style></head><body>"
            f"<p class=\"class\">{classification}</p><div class=\"rule\"></div>{banner}"
            f"<p class=\"kicker\">@{{{pr('name')}}} &middot; @{{coalesce({TEMPLATE_NAME}, 'Briefing note')}}</p>"
            f"<h1>@{{{esc(r('notetitle'))}}}</h1>{meta}"
            f"<div class=\"key\"><b>Key message.</b> {para(r('keymessage'))}</div>"
            f"{sections}{sources}{verification}"
            f"<div class=\"foot\">@{{coalesce({pr('footertext')}, '')}} &middot; @{{{r('requestnumber')}}} &middot; "
            f"{classification}</div><p class=\"class\" style=\"margin-top:8px\">{classification}</p></body></html>")


def render_actions(pfx, draft, sp_sub, name_expr):
    """Sections + sources -> HTML -> temp file in OneDrive -> PDF -> SharePoint."""
    folder = (f"concat({pr('sharepointrootfolder')}, '/', {safe(r('requestnumber'))}, '/{sp_sub}')")
    section_html = ("<h2>@{replace(replace(coalesce(item()?['heading'], ''), '&', '&amp;'), '<', '&lt;')}</h2><p>"
                    + para("item()?['body']") + "</p>")
    source_row = ("<tr><td>@{item()?['" + P + "_sourcelabel']}</td><td>@{item()?['" + P + "_name']}</td>"
                  "<td>@{item()?['" + P + "_documenttype" + FV + "']}</td><td>@{coalesce(item()?['" + P + "_summary'], '')}</td></tr>")
    return {
        "Select_Sections": select(f"@json(coalesce({r('draftsections')}, '[]'))", section_html),
        "List_Sources": list_rows(f"{P}_sourcedocuments", f"_{P}_requestid_value eq @{{{REQ_ID}}}", f"{P}_sourcelabel asc"),
        "Select_Sources": select("@outputs('List_Sources')?['body/value']", source_row),
        f"{pfx}_Html": compose(document_html(draft)),
        f"{pfx}_Temp_Html": op("shared_onedriveforbusiness", "CreateFile", {
            "folderPath": "/Briefing Notes Rendering", "name": "@{guid()}.html", "body": f"@outputs('{pfx}_Html')"}),
        f"{pfx}_Pdf": op("shared_onedriveforbusiness", "ConvertFile", {
            "id": f"@body('{pfx}_Temp_Html')?['Id']", "type": "PDF"}),
        f"{pfx}_Save_Pdf": op("shared_sharepointonline", "CreateFile", {
            "dataset": f"@{pr('sharepointsiteurl')}",
            "folderPath": f"@concat('/', {pr('sharepointlibrary')}, '/', {folder})",
            "name": f"@{{{name_expr}}}", "body": f"@body('{pfx}_Pdf')"}),
        f"{pfx}_Delete_Temp": op("shared_onedriveforbusiness", "DeleteFile", {"id": f"@body('{pfx}_Temp_Html')?['Id']"}),
        f"{pfx}_Url": compose(f"@replace(concat({pr('sharepointsiteurl')}, '/', {pr('sharepointlibrary')}, '/', {folder}, '/', {name_expr}), ' ', '%20')"),
        f"{pfx}_Folder_Url": compose(f"@replace(concat({pr('sharepointsiteurl')}, '/', {pr('sharepointlibrary')}, '/', "
                                     f"{pr('sharepointrootfolder')}, '/', {safe(r('requestnumber'))}), ' ', '%20')"),
    }


# ---------------------------------------------------------------- shared skeleton
def definition(status_values, actions):
    flt = " or ".join(f"{P}_status eq {s}" for s in status_values)
    trig = {"type": "OpenApiConnectionWebhook",
            "inputs": {"host": {"apiId": "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps",
                                "connectionName": "shared_commondataserviceforapps",
                                "operationId": "SubscribeWebhookTrigger"},
                       "parameters": {"subscriptionRequest/message": 3, "subscriptionRequest/entityname": f"{P}_request",
                                      "subscriptionRequest/scope": 4,
                                      "subscriptionRequest/filteringattributes": f"{P}_status",
                                      "subscriptionRequest/filterexpression": f"({flt})"}}}
    return {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "$connections": {"defaultValue": {}, "type": "Object"},
            "$authentication": {"defaultValue": {}, "type": "SecureObject"},
            HUB_URL: {"defaultValue": "", "type": "String",
                      "metadata": {"schemaName": f"{P}_AppBaseUrl", "description": "Model-driven app URL for links."}},
            STUDIO_URL: {"defaultValue": "", "type": "String",
                         "metadata": {"schemaName": f"{P}_StudioUrl", "description": "Code app URL for links."}},
        },
        "triggers": {"When_status_changes": trig},
        "actions": actions,
        "outputs": {},
    }


def load_context():
    """Profile: the request's, or the first active one."""
    return {
        "List_Active_Profiles": list_rows(f"{P}_profiles", f"{P}_isactive eq true", "createdon asc", 1),
        "Profile_Id": compose(f"@coalesce({T.format('_' + P + '_profileid_value')}, "
                              f"first(outputs('List_Active_Profiles')?['body/value'])?['{P}_profileid'])"),
        PRO: get_row(f"{P}_profiles", "@outputs('Profile_Id')"),
    }


def stop_unless(status_label, stage):
    """Stop the run quietly when the request left the expected status meanwhile (e.g. it was cancelled)."""
    return {"type": "If", "runAfter": {},
            "expression": {"not": {"equals": [f"@{r('status')}", ST[status_label]]}},
            "actions": chain({
                "Log_Stopped": activity(f"{stage} stopped: the request is no longer {status_label}", "Workflow", "Note",
                                        f"Status found: @{{{r('status' + FV)}}}. Nothing was written or sent."),
                "Stop": {"type": "Terminate", "inputs": {"runStatus": "Succeeded"}, "runAfter": {}},
            }),
            "else": {"actions": {}}}


def catch(stage):
    first = "first(body('Failed_Actions'))"
    err_text = (f"concat({first}?['name'], ': ', string(coalesce({first}?['outputs']?['body']?['error'], "
                f"{first}?['error'], {first}?['outputs']?['body'], 'unknown error')))")
    err = f"@{{substring({err_text}, 0, min(3900, length({err_text})))}}"
    return {"type": "Scope", "runAfter": {"Try": ["Failed", "TimedOut"]}, "actions": chain({
        "Failed_Actions": {"type": "Query", "inputs": {
            "from": "@result('Try')", "where": "@equals(item()?['status'], 'Failed')"}, "runAfter": {}},
        "Mark_Needs_Attention": update(f"{P}_requests", f"@{REQ_ID}", {
            f"{P}_status": ST["Needs Attention"], f"{P}_lasterror": err}),
        "Log_Failure": activity(f"{stage} failed", "Workflow", "Failed", err),
    })}


def init_vars():
    return {"Init_Start_Time": {"type": "InitializeVariable", "inputs": {"variables": [
        {"name": "startTime", "type": "string", "value": "@utcNow()"}]}, "runAfter": {}}}


# ---------------------------------------------------------------- BN 1: draft
def wf_draft():
    AG = "Run_Briefing_Note_Writer"
    so = f"body('{AG}')?['structuredOutput']"
    status = T.format(f"{P}_status")
    mode = (f"@{{if(equals({status}, {ST['Info Provided']}), 'clarification answers received', "
            f"if(equals({status}, {ST['Revision Requested']}), 'revision requested', 'first draft'))}}")
    prompt = ("Draft the briefing note for this request.\n"
              f"- Request id: @{{{REQ_ID}}}\n"
              f"- Request number: @{{{T.format(P + '_requestnumber')}}}\n"
              f"- Mode: {mode}\n"
              "- Today (UTC): @{formatDateTime(utcNow(), 'yyyy-MM-dd')}\n"
              "Follow your draft-briefing-note skill. Either save the draft to the request or save clarification "
              "questions, then end with the JSON result. The workflow renders the PDF from what you save.")
    reviewer = f"coalesce({r('revieweremail')}, {pr('defaultrevieweremail')}, {r('requesteremail')})"
    pdf_name = f"concat({safe(r('requestnumber'))}, ' - DRAFT v', string({r('draftversion')}), '.pdf')"
    title = f"@{{{r('requestnumber')}}}"

    # -- branch: the Writer needs information from the requester
    needs_info = chain({
        "Set_Needs_Info": update(f"{P}_requests", f"@{REQ_ID}", {
            f"{P}_status": ST["Needs Info"], f"{P}_lasterror": ""}),
        "Notify_Requester_Questions": tolerant({
            "Email_Questions": email(
                f"@{r('requesteremail')}",
                f"[{title}] A question before your briefing note can be drafted",
                f"<p>Hello @{{coalesce({r('requestername')}, '')}},</p>"
                f"<p>The Briefing Note Writer needs a little more information to draft <b>@{{{esc(r('name'))}}}</b> "
                f"for @{{coalesce({r('recipientname')}, 'your leader')}}.</p>"
                f"<div style=\"border-left:4px solid #0F6CBD;padding:6px 12px;background:#f7f9fc\">{para(r('clarificationquestions'))}</div>"
                "<p>Answer in Briefing Studio (<i>Your input is needed</i>), or ask the <b>Briefing Assistant</b> in Teams: "
                f"<i>\"Answer the questions for @{{{r('requestnumber')}}}\"</i>. Drafting resumes as soon as you answer.</p>"
                + links_html() + SIGNATURE),
            "Teams_Questions": teams_chat(
                f"@{r('requesteremail')}",
                f"<p><b>❓ @{{{r('requestnumber')}}}: the writer has a question</b></p><p>{para(r('clarificationquestions'))}</p>"
                "<p>Reply in Briefing Studio or ask the Briefing Assistant.</p>" + links_html()),
        }, "Set_Needs_Info"),
        "Log_Questions": {**activity("Clarification requested from the requester", "Briefing Note Writer",
                                     "Clarification requested", trunc(r('clarificationquestions'), 3900)),
                          "runAfter": {"Notify_Requester_Questions": ANY}},
    })

    # -- branch: a draft is ready for review
    draft_ready = chain({
        **render_actions("Draft", True, "Drafts", pdf_name),
        "Set_In_Review": update(f"{P}_requests", f"@{REQ_ID}", {
            f"{P}_status": ST["In Review"], f"{P}_draftpdfurl": "@outputs('Draft_Url')",
            f"{P}_sharepointfolderurl": "@outputs('Draft_Folder_Url')", f"{P}_draftedon": "@utcNow()",
            f"{P}_revieweremail": f"@{reviewer}", f"{P}_lasterror": ""}),
        "Notify_Review": tolerant({
            "Email_Reviewer": email(
                f"@{reviewer}",
                f"[{title}] Draft ready for review: @{{{r('notetitle')}}}",
                f"<p>A draft briefing note is ready for your review.</p>"
                f"<p><b>@{{{esc(r('notetitle'))}}}</b><br>For: @{{coalesce({r('recipientname')}, '')}} "
                f"@{{coalesce({r('recipienttitle')}, '')}}<br>Requested by: @{{coalesce({r('requestername')}, {r('requesteremail')})}}<br>"
                f"Classification: @{{{r('classification' + FV)}}} &middot; Confidence: @{{coalesce({r('confidence' + FV)}, 'n/a')}} "
                f"&middot; Draft v@{{{r('draftversion')}}}</p>"
                f"<h3>Key message</h3><p>{para(r('keymessage'))}</p>"
                f"<h3>Verification notes</h3><p>{para(r('verificationnotes'))}</p>"
                "<p>Edit the sections, then <b>Approve</b> or <b>Request revision</b> in Briefing Studio (or ask the "
                "Briefing Assistant in Teams). The draft PDF is attached.</p>"
                + links_html([("Draft PDF", "@{outputs('Draft_Url')}")]) + SIGNATURE,
                cc_expr=f"@{r('requesteremail')}", attachment=(pdf_name, "Draft_Pdf")),
            "Teams_Reviewer": teams_chat(
                f"@{reviewer}",
                f"<p><b>📝 @{{{r('requestnumber')}}}: draft ready for your review</b></p><p><b>@{{{esc(r('notetitle'))}}}</b></p>"
                f"<p>{para(r('keymessage'))}</p>" + links_html([("Draft PDF", "@{outputs('Draft_Url')}")])),
            "Teams_Requester": {**teams_chat(
                f"@{r('requesteremail')}",
                f"<p><b>✅ @{{{r('requestnumber')}}}: your draft is ready</b> and was sent to @{{{reviewer}}} for review.</p>"
                f"<p><b>@{{{esc(r('notetitle'))}}}</b></p>" + links_html([("Draft PDF", "@{outputs('Draft_Url')}")])),
                "runAfter": {"Teams_Reviewer": ANY}},
        }, "Set_In_Review"),
        "Log_Draft_Ready": {**activity(f"Draft v@{{{r('draftversion')}}} ready for review", "Briefing Note Writer",
                                       "Draft ready", trunc(f"{so}?['summary']", 3900)),
                            "runAfter": {"Notify_Review": ANY}},
    })

    try_actions = {
        "Claim": update(f"{P}_requests", f"@{REQ_ID}", {f"{P}_status": ST["Drafting"], f"{P}_lasterror": ""}),
        "Log_Started": activity(f"Drafting started ({mode})", "Briefing Note Writer", "Drafting started", completed=False),
        AG: agent_node(prompt, {
            "outcome": {"type": "string", "description": "draft or needs_info"},
            "requestNumber": {"type": "string", "description": "BN-xxxxx"},
            "noteTitle": {"type": "string", "description": "Note title (empty for needs_info)"},
            "keyMessage": {"type": "string", "description": "Bottom line (empty for needs_info)"},
            "questions": {"type": "string", "description": "Questions separated by ' | ' (needs_info only)"},
            "confidence": {"type": "string", "description": "Low, Medium or High"},
            "wordCount": {"type": "integer", "description": "Words in the note"},
            "draftVersion": {"type": "integer", "description": "Draft version saved"},
            "summary": {"type": "string", "description": "One or two sentences for the notification"}}),
        REQ: get_row(f"{P}_requests", f"@{REQ_ID}"),
        "Still_Drafting": stop_unless("Drafting", "Drafting"),
        **load_context(),
        "Needs_Info_Or_Draft": {
            "type": "If", "runAfter": {},
            "expression": {"or": [
                {"equals": [f"@toLower(coalesce({so}?['outcome'], ''))", "needs_info"]},
                {"and": [{"equals": [f"@empty(coalesce({r('draftsections')}, ''))", True]},
                         {"equals": [f"@empty(coalesce({r('clarificationquestions')}, ''))", False]}]}]},
            "actions": needs_info,
            "else": {"actions": draft_ready},
        },
    }
    actions = chain({**init_vars(), "Try": scope(try_actions)})
    actions["Catch"] = catch("Drafting")
    return definition([ST["Submitted"], ST["Info Provided"], ST["Revision Requested"]], actions)


# ---------------------------------------------------------------- BN 2: deliver
def wf_deliver():
    title_expr = f"coalesce({r('notetitle')}, {r('name')})"
    final_name = f"concat({safe(r('requestnumber'))}, ' - ', substring({safe(title_expr)}, 0, min(80, length({title_expr}))), '.pdf')"
    send_to_recipient = (f"and(equals({r('deliverymode')}, {v('deliverymode', 'Send to requester and recipient')}), "
                         f"not(empty(coalesce({r('recipientemail')}, ''))))")
    to_expr = f"if({send_to_recipient}, concat({r('requesteremail')}, ';', {r('recipientemail')}), {r('requesteremail')})"
    to = f"@{{{to_expr}}}"
    subject = (f"@{{{r('classification' + FV)}}} | Briefing note: @{{coalesce({r('notetitle')}, {r('name')})}} "
               f"(@{{{r('requestnumber')}}})")
    cover = (f"<p>@{{if({send_to_recipient}, concat('Dear ', coalesce({r('recipientname')}, ''), ','), concat('Hello ', coalesce({r('requestername')}, ''), ','))}}</p>"
             f"<p>Please find attached the briefing note <b>@{{{esc(r('notetitle'))}}}</b>, prepared by @{{coalesce({r('requestername')}, {r('requesteremail')})}}"
             f" and approved by @{{coalesce({r('approvedby')}, {r('revieweremail')}, 'the reviewer')}}.</p>"
             f"<div style=\"border-left:4px solid #0F6CBD;padding:6px 12px;background:#f7f9fc\"><b>Key message.</b> {para(r('keymessage'))}</div>"
             f"<p>Classification: <b>@{{{r('classification' + FV)}}}</b>. Handle and store accordingly.</p>"
             "<p><a href=\"@{outputs('Final_Url')}\">Open the note in SharePoint</a></p>" + SIGNATURE)
    try_actions = {
        REQ: get_row(f"{P}_requests", f"@{REQ_ID}"),
        "Still_Approved": stop_unless("Approved", "Delivery"),
        **load_context(),
        **render_actions("Final", False, "Final", final_name),
        "Set_Delivered": update(f"{P}_requests", f"@{REQ_ID}", {
            f"{P}_status": ST["Delivered"], f"{P}_finalpdfurl": "@outputs('Final_Url')",
            f"{P}_sharepointfolderurl": "@outputs('Final_Folder_Url')", f"{P}_deliveredon": "@utcNow()",
            f"{P}_approvedon": f"@coalesce({r('approvedon')}, utcNow())", f"{P}_lasterror": ""}),
        "Notify_Delivery": tolerant({
            "Email_Final": email(to, subject, cover, attachment=(final_name, "Final_Pdf")),
            "Teams_Requester": {**teams_chat(
                f"@{r('requesteremail')}",
                f"<p><b>📨 @{{{r('requestnumber')}}} delivered</b>: <b>@{{{esc(r('notetitle'))}}}</b> was approved and "
                f"sent @{{if({send_to_recipient}, concat('to you and ', coalesce({r('recipientname')}, {r('recipientemail')})), 'to you')}}.</p>"
                "<p><a href=\"@{outputs('Final_Url')}\">Final PDF</a></p>"), "runAfter": {"Email_Final": ANY}},
            "If_Send_To_Recipient": {
                "type": "If", "runAfter": {"Teams_Requester": ANY},
                "expression": {"equals": [f"@{send_to_recipient}", True]},
                "actions": {"Teams_Recipient": teams_chat(
                    f"@{r('recipientemail')}",
                    f"<p><b>📨 Briefing note for you</b>: <b>@{{{esc(r('notetitle'))}}}</b> (@{{{r('requestnumber')}}}, "
                    f"@{{{r('classification' + FV)}}})</p><p>{para(r('keymessage'))}</p>"
                    "<p><a href=\"@{outputs('Final_Url')}\">Open the note</a> · also sent by email.</p>")},
                "else": {"actions": {}}},
        }, "Set_Delivered"),
        "Log_Delivered": {**activity(f"Delivered: @{{{r('requestnumber')}}}", "Workflow", "Delivered",
                                     f"Final PDF filed and sent to @{{replace({to_expr}, ';', ', ')}}."),
                          "runAfter": {"Notify_Delivery": ANY}},
    }
    actions = chain({**init_vars(), "Try": scope(try_actions)})
    actions["Catch"] = catch("Delivery")
    return definition([ST["Approved"]], actions)


WORKFLOWS = [
    ("BN 1 - Draft Briefing Note", "draft", wf_draft,
     "Starts when a briefing request is Submitted, Info Provided or Revision Requested: runs the Briefing Note Writer "
     "(GitHub Copilot harness). It either asks the requester for clarification (Needs Info) or renders the draft PDF to "
     "SharePoint and sends it to the reviewer (In Review)."),
    ("BN 2 - Deliver Briefing Note", "deliver", wf_deliver,
     "Starts when a briefing request is Approved: renders the final PDF with its classification marking, files it in "
     "SharePoint, emails it with a prebuilt cover message and posts in Teams to the requester and the ultimate recipient."),
]


def clientdata(defn):
    refs = {c: {"runtimeSource": "embedded", "connection": {"connectionReferenceLogicalName": ln}, "api": {"name": c}}
            for c, ln in CONNS.items()}
    return {"properties": {"connectionReferences": refs, "definition": defn, "templateName": ""},
            "schemaVersion": "1.0.0.0"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-activate", action="store_true")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    os.makedirs(os.path.join(ROOT, "flows"), exist_ok=True)
    for name, key, builder, desc in WORKFLOWS:
        if args.only and key not in args.only:
            continue
        data = clientdata(builder())
        with open(os.path.join(ROOT, "flows", f"{key}.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False)
        rows = get(f"workflows?$select=workflowid,statecode&$filter={q(f'name eq {chr(39)}{name}{chr(39)} and category eq 5')}")["value"]
        body = {"name": name, "description": desc, "clientdata": json.dumps(data, ensure_ascii=False)}
        if rows:
            wid = rows[0]["workflowid"]
            if rows[0]["statecode"] == 1:
                ok(*call("PATCH", f"workflows({wid})", {"statecode": 0, "statuscode": 1})[:2], f"deactivate {name}")
            ok(*call("PATCH", f"workflows({wid})", body)[:2], f"update {name}")
        else:
            body.update({"category": 5, "type": 1, "primaryentity": "none", "modernflowtype": 1})
            status, payload, headers = call("POST", "workflows", body)
            ok(status, payload, f"create {name}")
            wid = created_id(headers)
        if not args.no_activate:
            ok(*call("PATCH", f"workflows({wid})", {"statecode": 1, "statuscode": 2})[:2], f"activate {name}")
        print(f"{key}\t{wid}")


if __name__ == "__main__":
    main()

