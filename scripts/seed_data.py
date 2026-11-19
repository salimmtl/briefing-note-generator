"""Seed the configuration: two Briefing Profiles (public and private sector) and five Note Templates (idempotent upserts).

Usage: python scripts/seed_data.py [--site-url https://<tenant>.sharepoint.com/sites/<site>] [--reviewer someone@contoso.com]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_def as S  # noqa: E402
from dv_api import call, get, log, ok, q  # noqa: E402

P = S.PREFIX
v = S.v

PUBLIC_STYLE = """- Write for a busy minister or deputy minister: lead with the bottom line, then the facts that support it.
- Plain language (Canada.ca style): short sentences (average under 20 words), active voice, everyday words. Avoid jargon; spell out every acronym on first use.
- Neutral, non-partisan, factual tone. Never speculate about political motives. Attribute positions to their source ("Stakeholders say…").
- Use headings exactly as the template lists them. Use short paragraphs and "- " bullets for lists of 3 or more items.
- Numbers: use numerals for 10 and over, include units and dates (e.g. "$4.2 million in 2025-26", "as of March 31, 2026").
- Canadian spelling (colour, centre, program). In French, follow the Office québécois de la langue française typography (spaces before : ; ? !).
- Every factual statement must be traceable to a source document: cite it as [S1], [S2]…
- Never write a recommendation the sources or the requester don't support; flag gaps instead."""

PUBLIC_GLOSSARY = """ADM = Assistant Deputy Minister
DM = Deputy Minister
MO = Minister's Office
PCO = Privy Council Office
TB = Treasury Board
TBS = Treasury Board of Canada Secretariat
MC = Memorandum to Cabinet
QP = Question Period
FTE = full-time equivalent
O&M = operating and maintenance
GBA Plus = Gender-based Analysis Plus
ATIP = Access to Information and Privacy
FPT = federal-provincial-territorial"""

PUBLIC_CLASSIFICATION = """- Mark the note with the classification chosen by the requester (Unclassified, Protected A, Protected B).
- Personal information about identifiable individuals: at least Protected A. Cabinet confidences and advice to ministers: Protected B (Secret is out of scope for this tool).
- If a source looks more sensitive than the chosen classification, say so in the verification notes."""

PRIVATE_STYLE = """- Write for a C-level executive with five minutes: bottom line first, then the three things that matter, then the ask.
- Crisp business English: short sentences, active voice, no filler, no marketing language.
- Quantify impact (revenue, cost, margin, risk, customers, timeline) wherever the sources allow, with the period and currency.
- Use the template headings. Prefer "- " bullets over long paragraphs; bold nothing.
- Be candid about risks and unknowns; never overstate certainty.
- Cite every fact from the sources as [S1], [S2]…
- Don't invent recommendations, owners or numbers; flag what's missing."""

PRIVATE_GLOSSARY = """ARR = annual recurring revenue
EBITDA = earnings before interest, taxes, depreciation and amortization
SLT = senior leadership team
QBR = quarterly business review
OKR = objectives and key results
TCO = total cost of ownership
RFP = request for proposal
SLA = service level agreement
YoY = year over year"""

PRIVATE_CLASSIFICATION = """- Internal: default for business information. Confidential: financials not yet public, M&A, personnel matters, customer contracts.
- If a source looks more sensitive than the chosen classification, say so in the verification notes."""

TEMPLATES = [
    {
        "code": "INFO", "name": "Briefing Note for Information", "type": "Briefing Note for Information", "order": 10,
        "max": 900,
        "when": "The leader needs to be informed about a file, a development or an upcoming event. No decision is asked.",
        "sections": """Purpose | One or two sentences: what this note informs the recipient about and why now. | 60
Summary | The bottom line in 3-5 bullets the recipient can repeat. | 120
Background | Only the context needed to understand the current situation, with dates. | 200
Current Situation | What is happening now: facts, figures, positions of key stakeholders, each cited. | 250
Considerations | Implications, risks, sensitivities (financial, legal, reputational, intergovernmental or customer). | 180
Next Steps | What happens next, who does it, and when. | 90""",
        "rules": """- No recommendation section: this note informs.
- The Summary must stand on its own: a reader who stops there knows the essentials.
- Keep to about two pages.""",
    },
    {
        "code": "DEC", "name": "Briefing Note for Decision", "type": "Briefing Note for Decision", "order": 20,
        "max": 1300,
        "when": "The leader must make a decision or approve something (funding, a position, an approach, a signature).",
        "sections": """Purpose | State the decision sought in one sentence ("To seek your approval of…"). | 60
Summary | The issue, the options in one line each, and the recommendation if one is supported. | 150
Background | Context and history needed to decide, with dates. | 200
Issue | What needs to be decided, by when, and what happens if no decision is made. | 150
Options | 2-3 options. For each: description, advantages, disadvantages, cost and risk, all cited. | 400
Recommendation | The recommended option and why. Only if supported by the sources or stated by the requester; otherwise write exactly: "[Recommendation to be confirmed by the program area.]" | 120
Next Steps | What happens once the decision is made, who does it, and when. | 90""",
        "rules": """- Present options fairly, including the status quo when relevant.
- Never invent a recommendation, costs or timelines. If options aren't in the sources, ask the requester (clarification) before drafting.
- End the Purpose with the deadline for the decision if one is known.""",
    },
    {
        "code": "MTG", "name": "Meeting or Event Brief", "type": "Meeting or Event Brief", "order": 30,
        "max": 1200,
        "when": "The leader is attending a meeting, call, visit or event and needs to be prepared.",
        "sections": """Event Overview | What, when, where, format, duration, who requested it. | 90
Objectives | What the leader wants to achieve (2-4 bullets). | 90
Participants | Who attends, their role and their interest or position, each cited. | 200
Key Messages | 3-5 messages the leader can say, in speakable first-person sentences. | 180
Issues Likely to Be Raised | Each likely question or ask, with a suggested response. | 300
Background | Short context on the relationship or file, with dates. | 200
Logistics and Follow-Up | Logistics known from the sources and follow-ups to plan. | 90""",
        "rules": """- Key Messages are written to be spoken aloud.
- If the date, time or participants aren't in the sources or the request, ask for them (clarification).""",
    },
    {
        "code": "ISSUE", "name": "Issue Note", "type": "Issue Note", "order": 40,
        "max": 700,
        "when": "A sensitive or emerging issue (media, stakeholder, incident, Question Period or shareholder question) where the leader needs lines to use.",
        "sections": """Issue | One or two sentences describing the issue and why it's sensitive now. | 60
Key Messages | 3-5 short lines the leader can use publicly, consistent with the sources. | 150
If Pressed | 2-4 responsive lines for likely follow-up questions. | 150
Background | Factual context and timeline, each cited. | 200
Facts and Figures | Key numbers with dates and sources, as bullets. | 120""",
        "rules": """- Lines must be factual, defensible and non-speculative; never assign blame.
- Only public or releasable information in Key Messages and If Pressed; sensitive context stays in Background.
- Keep to one page if possible.""",
    },
    {
        "code": "EXEC", "name": "Executive Summary (one page)", "type": "Executive Summary", "order": 50,
        "max": 450,
        "when": "A one-page synthesis of one or more long documents for a senior executive or board member.",
        "sections": """Bottom Line | The single most important conclusion, in 1-2 sentences. | 50
What You Need to Know | 3-5 bullets with the essential facts, each cited. | 150
Implications | What it means for the organization (financial, operational, customer, risk). | 100
Risks and Unknowns | The main risks and what we don't know yet. | 80
Recommended Actions | Actions supported by the sources, with owners if known; otherwise "[To be confirmed]". | 70""",
        "rules": """- Strictly one page: be ruthless.
- Every bullet starts with the point, not the context.""",
    },
]


def upsert(entity_set, key_col, key, body, what):
    flt = q(f"{key_col} eq '{key}'")
    rows = get(f"{entity_set}?$select={entity_set[:-1]}id&$filter={flt}")["value"]
    if rows:
        rid = rows[0][f"{entity_set[:-1]}id"]
        ok(*call("PATCH", f"{entity_set}({rid})", body, solution=False)[:2], f"update {what}")
        return rid
    status, payload, headers = call("POST", entity_set, body, solution=False)
    ok(status, payload, f"create {what}")
    return headers["OData-EntityId"].split("(")[-1].rstrip(")")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-url", default=os.environ.get("BRN_SHAREPOINT_SITE", ""))
    parser.add_argument("--library", default="Shared Documents")
    parser.add_argument("--reviewer", default=os.environ.get("BRN_REVIEWER_EMAIL", ""))
    args = parser.parse_args()

    profiles = [
        {
            f"{P}_name": "Ministry of Digital Government", f"{P}_code": "MDG", f"{P}_sector": v("sector", "Public sector"),
            f"{P}_description": "Sample public-sector profile: a provincial or federal ministry preparing notes for the "
                                "Minister, the Deputy Minister and Assistant Deputy Ministers.",
            f"{P}_styleguide": PUBLIC_STYLE, f"{P}_glossary": PUBLIC_GLOSSARY,
            f"{P}_classificationguidance": PUBLIC_CLASSIFICATION,
            f"{P}_defaultlanguage": v("language", "English"),
            f"{P}_leadertitles": "Minister; Deputy Minister; Associate Deputy Minister; Assistant Deputy Minister",
            f"{P}_sharepointrootfolder": "Briefing Notes/MDG", f"{P}_accentcolor": "#26374A",
            f"{P}_footertext": "Ministry of Digital Government · Prepared with AI assistance and reviewed by staff.",
            f"{P}_isactive": True,
        },
        {
            f"{P}_name": "Contoso Group", f"{P}_code": "CTSO", f"{P}_sector": v("sector", "Private sector"),
            f"{P}_description": "Sample private-sector profile: an enterprise preparing executive briefs for the CEO, "
                                "the senior leadership team and the board.",
            f"{P}_styleguide": PRIVATE_STYLE, f"{P}_glossary": PRIVATE_GLOSSARY,
            f"{P}_classificationguidance": PRIVATE_CLASSIFICATION,
            f"{P}_defaultlanguage": v("language", "English"),
            f"{P}_leadertitles": "CEO; CFO; COO; SVP; Board of Directors",
            f"{P}_sharepointrootfolder": "Briefing Notes/CTSO", f"{P}_accentcolor": "#0F6CBD",
            f"{P}_footertext": "Contoso Group · Internal · Prepared with AI assistance and reviewed by staff.",
            f"{P}_isactive": True,
        },
    ]
    for body in profiles:
        if args.site_url:
            body[f"{P}_sharepointsiteurl"] = args.site_url
            body[f"{P}_sharepointlibrary"] = args.library
        if args.reviewer:
            body[f"{P}_defaultrevieweremail"] = args.reviewer
        upsert(f"{P}_profiles", f"{P}_code", body[f"{P}_code"], body, f"profile {body[f'{P}_name']}")

    for t in TEMPLATES:
        upsert(f"{P}_templates", f"{P}_code", t["code"], {
            f"{P}_name": t["name"], f"{P}_code": t["code"], f"{P}_notetype": v("notetype", t["type"]),
            f"{P}_whentouse": t["when"], f"{P}_sections": t["sections"], f"{P}_writingrules": t["rules"],
            f"{P}_maxwords": t["max"], f"{P}_sortorder": t["order"], f"{P}_isactive": True}, f"template {t['code']}")
    log("Done.")


if __name__ == "__main__":
    main()
