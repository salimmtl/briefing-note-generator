"""Submit a sample briefing request from samples/<scenario>/ exactly as Briefing Studio does (demo data + smoke test).

Creates the request (Draft), one Source Document per file (extracted text + the original file in the file column),
then sets the status to Submitted, which starts the "BN 1 - Draft Briefing Note" workflow.

Usage:
  python scripts/submit_sample.py 01 --requester you@contoso.com [--reviewer someone@contoso.com] [--recipient-email x@y]
  python scripts/submit_sample.py --list
Requires: pip install pypdf python-docx
"""

import argparse
import datetime
import glob
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_def as S  # noqa: E402
from dv_api import BASE, call, get, log, ok, q, token  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = S.PREFIX
v = S.v

SCENARIOS = {
    "01": {"folder": "01-gov-cloud-modernization-decision", "profile": "MDG", "template": "DEC",
           "subject": "Cloud migration of the legacy application portfolio: option decision",
           "recipient": ("Hélène Castonguay", "Deputy Minister"), "priority": "Priority",
           "purpose": "Seek the Deputy Minister's decision on the preferred option for migrating the Ministry's legacy "
                      "application portfolio to cloud, so the Treasury Board submission can be finalized for the "
                      "December 4, 2026 deadline.",
           "classification": "Protected A"},
    "02": {"folder": "02-gov-wildfire-stakeholder-meeting", "profile": "MDG", "template": "MTG",
           "subject": "Meeting with the Association of Northern and Rural Municipalities",
           "recipient": ("Hon. Amara Lindqvist", "Minister of Digital Government"), "priority": "Routine",
           "purpose": "Prepare the Minister for her November 26 meeting with the Association of Northern and Rural "
                      "Municipalities on emergency communications and rural connectivity ahead of the 2027 wildfire season.",
           "classification": "Unclassified"},
    "03": {"folder": "03-gov-data-breach-issue", "profile": "MDG", "template": "ISSUE",
           "subject": "Litware vendor data breach: Digital Benefits Access Program",
           "recipient": ("Hélène Castonguay", "Deputy Minister"), "priority": "Urgent",
           "purpose": "Brief the Deputy Minister on the Litware vendor data breach affecting Digital Benefits Access "
                      "Program applicants: current status, media and OIPC exposure, and decisions needed in the next 72 hours.",
           "classification": "Protected B"},
    "04": {"folder": "04-contoso-acquisition-exec-summary", "profile": "CTSO", "template": "EXEC",
           "subject": "Project Lighthouse: proposed acquisition of Fabrikam Analytics",
           "recipient": ("Daniel Achebe", "Chief Executive Officer"), "priority": "Priority",
           "purpose": "Summarize the case for acquiring Fabrikam Analytics so the CEO can decide whether to take the "
                      "letter-of-intent recommendation to the December 3 Board meeting, highlighting price, risks and "
                      "open questions.",
           "classification": "Confidential"},
}
DOC_TYPES = {".pdf": "Report", ".docx": "Memo or briefing", ".txt": "Email or correspondence", ".md": "Meeting notes"}


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages), len(reader.pages)
    if ext == ".docx":
        import docx
        d = docx.Document(path)
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts), None
    with open(path, encoding="utf-8") as f:
        return f.read(), None


def upload_file(doc_id, path):
    with open(path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(f"{BASE}{P}_sourcedocuments({doc_id})/{P}_file", data=data, method="PATCH", headers={
        "Authorization": f"Bearer {token()}", "Content-Type": "application/octet-stream",
        "x-ms-file-name": os.path.basename(path)})
    with urllib.request.urlopen(req) as resp:
        return resp.status


def lookup_id(entity_set, code):
    rows = get(f"{entity_set}?$select={entity_set[:-1]}id&$filter=" + q(f"{P}_code eq '{code}'"))["value"]
    return rows[0][f"{entity_set[:-1]}id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", nargs="?")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--requester", default=os.environ.get("BRN_REQUESTER_EMAIL", ""))
    parser.add_argument("--requester-name", default="Demo Requester")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--recipient-email", default="")
    parser.add_argument("--no-submit", action="store_true")
    args = parser.parse_args()
    if args.list or not args.scenario:
        for k, s in SCENARIOS.items():
            print(f"{k}  {s['folder']}  ({s['template']}, {s['profile']})")
        return
    if not args.requester:
        raise SystemExit("--requester is required (the requester's work email)")
    s = SCENARIOS[args.scenario]
    files = sorted(f for f in glob.glob(os.path.join(ROOT, "samples", s["folder"], "*")) if os.path.isfile(f))

    body = {
        f"{P}_name": s["subject"], f"{P}_status": v("requeststatus", "Draft"),
        f"{P}_requestername": args.requester_name, f"{P}_requesteremail": args.requester,
        f"{P}_recipientname": s["recipient"][0], f"{P}_recipienttitle": s["recipient"][1],
        f"{P}_purpose": s["purpose"], f"{P}_language": v("language", "English"),
        f"{P}_classification": v("classification", s["classification"]), f"{P}_priority": v("priority", s["priority"]),
        f"{P}_duedate": (datetime.date.today() + datetime.timedelta(days=5)).isoformat(),
        f"{P}_deliverymode": v("deliverymode", "Send to requester and recipient" if args.recipient_email else "Send to requester only"),
        f"{P}_intakechannel": v("intakechannel", "Briefing Studio"),
        f"{P}_ProfileId@odata.bind": f"/{P}_profiles({lookup_id(P + '_profiles', s['profile'])})",
        f"{P}_TemplateId@odata.bind": f"/{P}_templates({lookup_id(P + '_templates', s['template'])})",
    }
    if args.reviewer:
        body[f"{P}_revieweremail"] = args.reviewer
    if args.recipient_email:
        body[f"{P}_recipientemail"] = args.recipient_email
    status, payload, headers = call("POST", f"{P}_requests", body, solution=False,
                                    extra_headers={"Prefer": "return=representation"})
    req = ok(status, payload, "create request")
    rid = req[f"{P}_requestid"]

    for i, path in enumerate(files, start=1):
        text, pages = extract(path)
        doc = {f"{P}_name": os.path.basename(path), f"{P}_sourcelabel": f"S{i}",
               f"{P}_documenttype": v("documenttype", DOC_TYPES.get(os.path.splitext(path)[1].lower(), "Other")),
               f"{P}_extractedtext": text[:1000000], f"{P}_charactercount": len(text),
               f"{P}_extractionstatus": v("extractionstatus", "Extracted" if text.strip() else "Failed"),
               f"{P}_RequestId@odata.bind": f"/{P}_requests({rid})"}
        if pages:
            doc[f"{P}_pagecount"] = pages
        status, payload, _ = call("POST", f"{P}_sourcedocuments", doc, solution=False,
                                  extra_headers={"Prefer": "return=representation"})
        d = ok(status, payload, f"source S{i} {os.path.basename(path)} ({len(text)} chars)")
        upload_file(d[f"{P}_sourcedocumentid"], path)
        log(f"[OK]   uploaded {os.path.basename(path)}")

    if not args.no_submit:
        ok(*call("PATCH", f"{P}_requests({rid})", {f"{P}_status": v("requeststatus", "Submitted"),
                                                    f"{P}_submittedon": datetime.datetime.utcnow().isoformat() + "Z"},
                 solution=False)[:2], "submit")
        ok(*call("POST", f"{P}_activities", {
            f"{P}_name": f"{req[P + '_requestnumber']} submitted (sample {args.scenario})",
            f"{P}_actor": v("actor", "Requester"), f"{P}_activitytype": v("activitytype", "Submitted"),
            f"{P}_details": f"{len(files)} documents", f"{P}_startedon": datetime.datetime.utcnow().isoformat() + "Z",
            f"{P}_RequestId@odata.bind": f"/{P}_requests({rid})"}, solution=False)[:2], "activity")
    print(json.dumps({"requestId": rid, "requestNumber": req[f"{P}_requestnumber"]}))


if __name__ == "__main__":
    main()
