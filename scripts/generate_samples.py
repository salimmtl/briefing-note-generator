"""Generate the fictional demo kit of source documents for the Briefing Note Generator.

All organizations, people, figures and events in these documents are fictional and
exist only to demonstrate the accelerator. Re-run at any time to regenerate:

    python scripts/generate_samples.py

Requires: reportlab, python-docx (pip install reportlab python-docx)
Output:   samples/<scenario>/... (existing generated files are overwritten)
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

rl_config.invariant = 1  # deterministic PDF output (no timestamps / random IDs)

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
DISCLAIMER = "FICTIONAL DOCUMENT - FOR DEMONSTRATION PURPOSES ONLY"
FIXED_DATE = _dt.datetime(2026, 11, 10, 9, 0, 0)

GOV_COLOR = colors.HexColor("#1F3A5F")
CORP_COLOR = colors.HexColor("#0B5A4A")


# --------------------------------------------------------------------------- #
# Generic renderers. A document is a list of blocks:
#   ("title", str) ("subtitle", str) ("meta", [(label, value)]) ("h1", str)
#   ("h2", str) ("p", str) ("note", str) ("bullets", [str])
#   ("table", {"header": [...], "rows": [[...]], "widths": [inches...]})
#   ("pagebreak",)
# --------------------------------------------------------------------------- #

def render_pdf(path: Path, blocks: list, header: str, accent=GOV_COLOR) -> None:
    styles = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle("t", parent=styles["Title"], fontSize=18, leading=22,
                                textColor=accent, alignment=TA_LEFT, spaceAfter=4),
        "subtitle": ParagraphStyle("st", parent=styles["Normal"], fontSize=11.5, leading=15,
                                   textColor=colors.HexColor("#444444"), spaceAfter=10),
        "h1": ParagraphStyle("h1", parent=styles["Heading2"], fontSize=13, leading=16,
                             textColor=accent, spaceBefore=10, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=styles["Heading3"], fontSize=11, leading=14,
                             textColor=colors.HexColor("#333333"), spaceBefore=6, spaceAfter=3),
        "p": ParagraphStyle("p", parent=styles["BodyText"], fontSize=10, leading=13.5, spaceAfter=6),
        "note": ParagraphStyle("n", parent=styles["BodyText"], fontSize=9, leading=12,
                               textColor=colors.HexColor("#555555"), fontName="Helvetica-Oblique",
                               spaceAfter=6),
        "cell": ParagraphStyle("c", parent=styles["BodyText"], fontSize=8.5, leading=10.5),
        "cellh": ParagraphStyle("ch", parent=styles["BodyText"], fontSize=8.5, leading=10.5,
                                fontName="Helvetica-Bold", textColor=colors.white),
        "meta": ParagraphStyle("m", parent=styles["BodyText"], fontSize=9, leading=11.5),
    }
    story = []
    for block in blocks:
        kind = block[0]
        if kind in ("title", "subtitle", "h1", "h2", "p", "note"):
            story.append(Paragraph(escape(block[1]), s[kind]))
        elif kind == "meta":
            data = [[Paragraph(f"<b>{escape(k)}</b>", s["meta"]), Paragraph(escape(v), s["meta"])]
                    for k, v in block[1]]
            t = Table(data, colWidths=[1.6 * inch, 5.0 * inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F4F7")),
                ("LINEBELOW", (0, -1), (-1, -1), 1, accent),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story += [t, Spacer(1, 10)]
        elif kind == "bullets":
            story.append(ListFlowable(
                [ListItem(Paragraph(escape(b), s["p"]), leftIndent=12) for b in block[1]],
                bulletType="bullet", start="\u2022", leftIndent=12))
        elif kind == "table":
            spec = block[1]
            data = [[Paragraph(escape(h), s["cellh"]) for h in spec["header"]]]
            data += [[Paragraph(escape(str(c)), s["cell"]) for c in row] for row in spec["rows"]]
            widths = [w * inch for w in spec["widths"]] if spec.get("widths") else None
            t = Table(data, colWidths=widths, repeatRows=1)
            style = [
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#A0A7B4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
            for i in range(2, len(data), 2):
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F5F7FA")))
            t.setStyle(TableStyle(style))
            story += [t, Spacer(1, 8)]
        elif kind == "pagebreak":
            story.append(PageBreak())
        else:
            raise ValueError(kind)

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.75 * inch, LETTER[1] - 0.5 * inch, header)
        canvas.setStrokeColor(accent)
        canvas.line(0.75 * inch, LETTER[1] - 0.55 * inch, LETTER[0] - 0.75 * inch, LETTER[1] - 0.55 * inch)
        canvas.drawString(0.75 * inch, 0.5 * inch, DISCLAIMER)
        canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    title = next((b[1] for b in blocks if b[0] == "title"), path.stem)
    doc = SimpleDocTemplate(str(path), pagesize=LETTER, leftMargin=0.75 * inch,
                            rightMargin=0.75 * inch, topMargin=0.8 * inch, bottomMargin=0.8 * inch,
                            title=title, author="Fictional demo content", subject=DISCLAIMER)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)


def render_docx(path: Path, blocks: list, header: str, accent=RGBColor(0x1F, 0x3A, 0x5F)) -> None:
    d = Document()
    normal = d.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    sec = d.sections[0]
    hp = sec.header.paragraphs[0]
    hp.text = header
    hp.runs[0].font.size = Pt(8)
    fp = sec.footer.paragraphs[0]
    fp.text = DISCLAIMER
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.runs[0].font.size = Pt(8)

    for block in blocks:
        kind = block[0]
        if kind == "title":
            p = d.add_heading(block[1], level=0)
            for r in p.runs:
                r.font.color.rgb = accent
                r.font.size = Pt(20)
        elif kind == "subtitle":
            p = d.add_paragraph()
            r = p.add_run(block[1])
            r.font.size = Pt(12)
            r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)
        elif kind == "h1":
            d.add_heading(block[1], level=1)
        elif kind == "h2":
            d.add_heading(block[1], level=2)
        elif kind == "p":
            d.add_paragraph(block[1])
        elif kind == "note":
            p = d.add_paragraph()
            r = p.add_run(block[1])
            r.italic = True
            r.font.size = Pt(9)
        elif kind == "bullets":
            for b in block[1]:
                d.add_paragraph(b, style="List Bullet")
        elif kind == "meta":
            t = d.add_table(rows=0, cols=2)
            t.style = "Light Shading Accent 1"
            for k, v in block[1]:
                cells = t.add_row().cells
                cells[0].text = k
                cells[0].paragraphs[0].runs[0].bold = True
                cells[1].text = v
            d.add_paragraph()
        elif kind == "table":
            spec = block[1]
            t = d.add_table(rows=1, cols=len(spec["header"]))
            t.style = "Light Grid Accent 1"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, h in enumerate(spec["header"]):
                t.rows[0].cells[i].text = h
            for row in spec["rows"]:
                cells = t.add_row().cells
                for i, c in enumerate(row):
                    cells[i].text = str(c)
            for row in t.rows:
                for c in row.cells:
                    for p in c.paragraphs:
                        for r in p.runs:
                            r.font.size = Pt(9)
            d.add_paragraph()
        elif kind == "pagebreak":
            d.add_page_break()
        else:
            raise ValueError(kind)

    cp = d.core_properties
    cp.title = next((b[1] for b in blocks if b[0] == "title"), path.stem)
    cp.author = "Fictional demo content"
    cp.comments = DISCLAIMER
    cp.created = FIXED_DATE
    cp.modified = FIXED_DATE
    cp.last_modified_by = "generate_samples.py"
    cp.revision = 1
    d.save(str(path))


def write_text(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


MDG = "Ministry of Digital Government"
MDG_HDR = f"{MDG}  |  UNCLASSIFIED - FICTIONAL DEMO"
CONTOSO_HDR = "Contoso Group  |  CONFIDENTIAL (FICTIONAL) - Corporate Development"


# =========================================================================== #
# Scenario 1 - Government cloud modernization (Briefing Note for Decision)
# =========================================================================== #

def scenario_01(out: Path) -> None:
    report = [
        ("title", "Legacy Application Portfolio - Cloud Migration Options Assessment"),
        ("subtitle", "Program Assessment Report, Enterprise Modernization Program (EMP)"),
        ("meta", [
            ("Organization", f"{MDG} - Office of the Chief Information Officer"),
            ("Prepared by", "Priya Ramanathan, Director, Enterprise Architecture & Modernization"),
            ("Reviewed by", "Thomas Achterberg, Director General, Infrastructure Services"),
            ("Date", "September 18, 2026"),
            ("Version", "1.2 (final for governance review)"),
        ]),
        ("h1", "1. Purpose"),
        ("p", "This report assesses options for the future of the Ministry's portfolio of 140 legacy "
              "business applications currently hosted in the Harbourview Data Centre. The Harbourview "
              "lease expires on March 31, 2028 and will not be renewed by the landlord, Adatum Properties. "
              "The report recommends a preferred option for consideration by the Deputy Minister and "
              "the Ministry's Investment Governance Committee."),
        ("h1", "2. Background"),
        ("p", "The portfolio supports 31 programs, including the Digital Benefits Access Program, "
              "business licensing, and the provincial land registry interface. The median application age "
              "is 14 years; 46 applications run on operating systems that reach end of vendor support by "
              "December 2027. In fiscal year 2025-26 the Ministry recorded 212 hours of unplanned outage "
              "across the portfolio, of which 61% was attributed to aging infrastructure."),
        ("table", {
            "header": ["Portfolio segment", "# Apps", "Examples", "Hosting cost 2025-26 ($M)"],
            "rows": [
                ["Mission critical", "22", "Benefits eligibility engine, Land registry gateway", "11.4"],
                ["Business important", "61", "Licensing portal, Grants management", "17.9"],
                ["Administrative", "44", "HR scheduling, Asset tracking", "6.3"],
                ["Candidates for retirement", "13", "Legacy reporting tools, duplicate case trackers", "1.8"],
                ["Total", "140", "", "37.4"],
            ],
            "widths": [1.7, 0.7, 2.9, 1.5],
        }),
        ("h1", "3. Options considered"),
        ("h2", "Option A - Status quo (renew on-premises hosting)"),
        ("p", "Relocate hardware to a new co-location facility and extend support contracts. Lowest "
              "change effort, but does not reduce technical debt and requires a hardware refresh of "
              "approximately $58M in 2028-29."),
        ("h2", "Option B - Lift-and-shift (rehost all applications to cloud)"),
        ("p", "Rehost all in-scope applications to the Government of the Province's approved cloud "
              "tenancy within 24 months. Fastest exit from Harbourview; limited modernization; run costs "
              "remain high because applications are not optimized for cloud."),
        ("h2", "Option C - Phased modernization (recommended)"),
        ("p", "Retire 13 applications, rehost 58, re-platform 47, and rebuild or replace 22 mission-critical "
              "applications over 48 months in three waves. Wave 1 (rehost) clears Harbourview before the "
              "lease expiry; Waves 2 and 3 deliver modernization and run-cost savings."),
        ("h1", "4. Five-year cost comparison (2026-27 to 2030-31)"),
        ("table", {
            "header": ["Cost element ($M, nominal)", "A - Status quo", "B - Lift-and-shift", "C - Phased modernization"],
            "rows": [
                ["One-time migration / build", "22.0", "96.5", "148.7"],
                ["Hosting and run costs (5 yrs)", "305.1", "214.3", "171.6"],
                ["Hardware refresh", "58.0", "0.0", "0.0"],
                ["Staff retraining and change mgmt", "2.5", "9.8", "16.4"],
                ["Contingency", "25.0", "17.8", "24.5"],
                ["Total 5-year cost", "412.6", "338.4", "361.2"],
                ["Annual run cost at steady state", "61.0", "42.9", "29.8"],
            ],
            "widths": [2.3, 1.4, 1.5, 1.6],
        }),
        ("note", "Source: EMP financial model v4.1, August 2026. Figures exclude HST and assume a USD/CAD "
                 "exchange rate of 1.34 for cloud consumption."),
        ("p", "Although Option B has the lowest five-year cost, Option C becomes the lowest-cost option from "
              "year 7 onward because of its steady-state run cost of $29.8M per year versus $42.9M for "
              "Option B. Over a 10-year horizon, Option C is projected to cost $510.2M versus $552.9M for "
              "Option B and $717.6M for Option A."),
        ("pagebreak",),
        ("h1", "5. Timelines"),
        ("table", {
            "header": ["Milestone", "Option B", "Option C"],
            "rows": [
                ["Funding approval required by", "February 2027", "February 2027"],
                ["Harbourview exit complete", "March 2028", "March 2028 (Wave 1)"],
                ["Wave 2 - re-platform 47 apps", "n/a", "April 2028 - March 2029"],
                ["Wave 3 - rebuild/replace 22 critical apps", "n/a", "April 2029 - March 2030"],
                ["Program close", "December 2028", "March 2030 (48 months)"],
            ],
            "widths": [2.8, 1.8, 2.2],
        }),
        ("h1", "6. Key risks"),
        ("table", {
            "header": ["Risk", "Likelihood", "Impact", "Mitigation"],
            "rows": [
                ["Harbourview exit not completed before lease expiry", "Medium", "High",
                 "Prioritize rehost of 58 apps in Wave 1; negotiate 6-month holdover option with Adatum Properties"],
                ["Shortage of cloud-skilled staff (85 FTE require retraining)", "High", "Medium",
                 "Retraining program with Litware Learning; 12 term hires; union consultation"],
                ["Benefits eligibility engine rebuild delays", "Medium", "High",
                 "Separate gated project with independent QA; parallel run of 3 months"],
                ["Cloud consumption costs exceed forecast", "Medium", "Medium",
                 "FinOps function; reserved capacity commitments; quarterly cost reviews"],
                ["Data residency and privacy requirements", "Low", "High",
                 "Canadian regions only; Privacy Impact Assessments for 22 critical apps"],
            ],
            "widths": [2.0, 0.8, 0.7, 3.3],
        }),
        ("h1", "7. Stakeholder considerations"),
        ("bullets", [
            "The Professional Technology Employees Association (PTEA) has requested formal consultation on "
            "the retraining plan and any changes to work location.",
            "Program areas (notably Benefits and Land Registry) support Option C but have asked that no "
            "major cutovers occur during peak periods (January-April).",
            "The Office of the Information and Privacy Commissioner expects to be consulted on the PIAs.",
            "Fabrikam Cloud Services and Contoso Cloud are both pre-qualified vendors under the provincial "
            "cloud framework agreement; no procurement decision is required at this stage.",
        ]),
        ("h1", "8. Recommendation"),
        ("p", "The Office of the CIO recommends Option C - Phased modernization, at an estimated five-year "
              "cost of $361.2M, of which $173.8M is incremental to the Ministry's existing reference levels "
              "and would be sought through a Treasury Board submission. A decision by the Deputy Minister is "
              "required in time to submit to the Treasury Board Secretariat for the winter 2027 cycle."),
    ]
    render_pdf(out / "Program-Assessment-Report_Cloud-Migration-Options.pdf", report, MDG_HDR)

    memo = [
        ("title", "Treasury Board Submission - Summary Memo"),
        ("subtitle", "Enterprise Modernization Program: Phased Cloud Modernization of Legacy Applications"),
        ("meta", [
            ("To", "Hélène Castonguay, Deputy Minister, Ministry of Digital Government"),
            ("From", "Marc-Antoine Delorme, Chief Financial Officer and ADM, Corporate Services"),
            ("Cc", "Grace Oyelaran, Chief Information Officer"),
            ("Date", "October 27, 2026"),
            ("Security", "Unclassified (fictional demo)"),
        ]),
        ("h1", "Purpose"),
        ("p", "To summarize the proposed Treasury Board submission seeking incremental funding for the "
              "Enterprise Modernization Program (EMP), based on Option C (Phased modernization) from the "
              "Program Assessment Report of September 18, 2026, and to note changes to the cost estimate "
              "since that report."),
        ("h1", "Funding request"),
        ("table", {
            "header": ["Fiscal year", "Total cost ($M)", "Existing reference level ($M)", "Incremental request ($M)"],
            "rows": [
                ["2026-27", "18.2", "14.0", "4.2"],
                ["2027-28", "96.4", "38.1", "58.3"],
                ["2028-29", "102.7", "40.2", "62.5"],
                ["2029-30", "88.5", "41.0", "47.5"],
                ["2030-31", "69.1", "54.1", "15.0"],
                ["Total", "374.9", "187.4", "187.5"],
            ],
            "widths": [1.3, 1.6, 2.0, 1.8],
        }),
        ("h1", "Changes since the Program Assessment Report"),
        ("bullets", [
            "Total five-year cost for Option C revised from $361.2M to $374.9M (+$13.7M, +3.8%), reflecting "
            "a revised USD/CAD exchange rate assumption of 1.39 (was 1.34) and a 6% increase in database "
            "licensing announced by the vendor in October 2026.",
            "Incremental funding requested is therefore $187.5M rather than the $173.8M cited in the report.",
            "Scope reduced from 140 to 138 applications: two administrative applications were retired in "
            "October 2026 ahead of schedule.",
            "Following consultation with program areas, Wave 3 will avoid the January-April peak period. "
            "Program close is now forecast for Q4 of 2030-31 (approximately 54 months), not March 2030.",
        ]),
        ("h1", "Key dates"),
        ("table", {
            "header": ["Milestone", "Date"],
            "rows": [
                ["Deputy Minister decision on preferred option", "November 20, 2026"],
                ["Minister's approval of submission", "November 27, 2026"],
                ["Submission due to Treasury Board Secretariat", "December 4, 2026"],
                ["Treasury Board meeting (target)", "January 21, 2027"],
                ["Harbourview Data Centre lease expiry", "March 31, 2028"],
            ],
            "widths": [4.0, 2.5],
        }),
        ("h1", "Considerations"),
        ("bullets", [
            "Treasury Board Secretariat analysts have signalled that submissions above $150M will require an "
            "independent third-party cost review; Woodgrove Advisory has been engaged at a cost of $0.35M.",
            "The Ministry's internal reallocation capacity is limited to $9M per year without affecting "
            "program delivery.",
            "If the submission misses the winter cycle, the next opportunity is June 2027, which would make "
            "the March 2028 Harbourview exit very difficult to achieve and would likely require a costly "
            "lease holdover (estimated $1.2M per month).",
        ]),
        ("h1", "Recommendation"),
        ("p", "That the Deputy Minister approve Option C as the preferred option and authorize finalization "
              "of the Treasury Board submission for an incremental $187.5M over five years."),
    ]
    render_docx(out / "TB-Submission-Summary-Memo_EMP.docx", memo, MDG_HDR)

    write_text(out / "Email_CIO-Office_DM-Decision-Deadline.txt", """
From:    Julien Okafor <julien.okafor@digitalgov.example>
         Chief of Staff, Office of the Chief Information Officer
To:      DM Office Correspondence <dmo.correspondence@digitalgov.example>
Cc:      Grace Oyelaran (CIO); Priya Ramanathan; Marc-Antoine Delorme
Date:    Monday, November 9, 2026 4:12 PM
Subject: ACTION REQUIRED - DM decision on Enterprise Modernization Program by Nov 20

[FICTIONAL DEMO EMAIL - all names and addresses are fictional]

Good afternoon,

On behalf of Grace, I'm writing to request that a decision note on the Enterprise
Modernization Program (EMP) be placed in the Deputy Minister's weekend reading.

We need the DM's decision on the preferred option no later than Friday, November 20,
2026. Without it, we can't get the Minister's sign-off on Nov 27 and we will miss the
TBS deadline of December 4 for the winter cycle.

Quick recap for the note:
 - 140 legacy apps currently in Harbourview; lease ends March 31, 2028 (no renewal).
 - CIO recommends Option C, phased modernization, approx. $361M over five years.
 - Option B (lift-and-shift) is cheaper over 5 years but more expensive after year 7.
 - PTEA (the union) wants formal consultation on retraining for ~85 staff before
   anything is announced. Their president, Lorna Feist, has asked for a meeting with
   the DM in early December.
 - Benefits and Land Registry ADMs are on side but want no cutovers Jan-April.

Grace would also like the note to flag that the DM may wish to brief the Minister
before the Nov 27 sign-off, since the Minister has publicly committed to "no service
disruptions for benefit recipients" during the transition.

Happy to provide anything else you need. The CFO's office has the latest numbers.

Thanks,
Julien

Julien Okafor | Chief of Staff, Office of the CIO
Ministry of Digital Government (fictional)
""")


# =========================================================================== #
# Scenario 2 - Wildfire season / municipal stakeholder meeting (Meeting Brief)
# =========================================================================== #

def scenario_02(out: Path) -> None:
    outlook = [
        ("title", "2027 Regional Wildfire Season Outlook"),
        ("subtitle", "Connectivity and Emergency Communications Readiness Annex"),
        ("meta", [
            ("Prepared by", "Interagency Wildfire Coordination Office (IWCO), with the Ministry of Digital "
                            "Government - Connectivity Branch"),
            ("Lead analyst", "Dr. Kwame Boateng, Senior Fire Behaviour Analyst"),
            ("Date", "November 2, 2026"),
            ("Distribution", "Ministers' offices, Deputy Ministers' Emergency Management Committee"),
        ]),
        ("h1", "1. Summary"),
        ("p", "Following the 2026 season - the second most severe on record, with 1,284 wildfires and "
              "612,400 hectares burned - the IWCO forecasts an above-normal fire danger for 2027 in three of "
              "five regions, driven by persistent drought codes and a projected warm, dry spring. The "
              "2026 season exposed significant gaps in emergency communications: 19 communities experienced "
              "a loss of cellular service lasting more than 12 hours during evacuation orders, and public "
              "alerts failed to reach an estimated 7,300 residents."),
        ("h1", "2. Regional outlook"),
        ("table", {
            "header": ["Region", "2027 fire danger forecast", "10-yr avg fires", "2026 fires",
                       "2026 hectares burned", "Communities at high risk", "Households below 50/10 Mbps"],
            "rows": [
                ["North Ridge", "Extreme", "214", "402", "248,100", "14", "6,900"],
                ["Pine Valley", "High", "176", "311", "176,500", "11", "5,200"],
                ["Eastern Highlands", "High", "132", "247", "121,800", "9", "3,700"],
                ["Lakeshore", "Moderate", "98", "196", "52,300", "5", "1,800"],
                ["Southern Plains", "Low-Moderate", "71", "128", "13,700", "2", "1,000"],
                ["Total", "", "691", "1,284", "612,400", "41", "18,600"],
            ],
            "widths": [1.15, 1.05, 0.8, 0.7, 1.0, 1.05, 1.15],
        }),
        ("note", "Fire danger forecast issued for the period May 1 - September 30, 2027. Connectivity data "
                 "from the Connectivity Branch broadband map, June 2026."),
        ("h1", "3. Emergency communications findings from 2026"),
        ("bullets", [
            "41 cellular towers in North Ridge and Pine Valley lost power during the 2026 season; 29 had "
            "less than 4 hours of battery backup.",
            "Municipal and provincial responders in 3 regions use incompatible land mobile radio systems; "
            "interoperability was achieved only through manual patching at the regional EOC.",
            "The provincial public alerting system reached 92% of targeted devices in urban areas but only "
            "68% in North Ridge.",
            "Satellite backup terminals (provided by Tailspin Satellite on a pilot basis) restored command "
            "communications in 6 communities within 2 hours.",
        ]),
        ("h1", "4. Readiness priorities for 2027"),
        ("table", {
            "header": ["Priority", "Estimated cost ($M)", "Lead", "Ready by"],
            "rows": [
                ["Backup power (72-hr) for 41 critical cell towers", "6.2", "Connectivity Branch / carriers", "May 2027"],
                ["Radio interoperability gateways (3 regions)", "4.8", "Emergency Management Agency", "June 2027"],
                ["Satellite backup kits for 41 high-risk communities", "2.1", "IWCO", "April 2027"],
                ["Rural broadband acceleration (18,600 households)", "71.0 (over 3 years)", "Connectivity Branch", "2029"],
            ],
            "widths": [2.9, 1.3, 1.8, 0.9],
        }),
        ("p", "Current approved funding for 2027 readiness is $5.5M, leaving a gap of approximately $7.6M "
              "for the three short-term priorities. Rural broadband acceleration is partially funded "
              "($38M committed) through the Rural Connectivity Fund."),
    ]
    render_pdf(out / "Wildfire-Season-Outlook-2027_Connectivity-Annex.pdf", outlook, MDG_HDR)

    letter = [
        ("title", "Association of Northern and Rural Municipalities"),
        ("subtitle", "Request for a meeting with the Minister of Digital Government"),
        ("meta", [
            ("Date", "October 22, 2026"),
            ("To", "The Honourable Amara Lindqvist, Minister of Digital Government"),
            ("From", "Mayor Denise Arcand, President, ANRM (Mayor of the Town of Cedar Falls)"),
            ("Re", "Emergency communications and rural connectivity before the 2027 wildfire season"),
        ]),
        ("p", "Dear Minister Lindqvist,"),
        ("p", "On behalf of the 63 member municipalities of the Association of Northern and Rural "
              "Municipalities (ANRM), I am writing to request a meeting with you in late November to "
              "discuss urgent measures to protect our residents ahead of the 2027 wildfire season."),
        ("p", "The 2026 season tested our communities as never before. In Cedar Falls alone, 2,100 "
              "residents were evacuated while cellular service was down for 31 hours. Our volunteer fire "
              "departments relied on personal phones and runners to coordinate. Across our membership, "
              "we estimate that more than 8,000 residents did not receive emergency alerts - a figure "
              "higher than provincial estimates - and we believe this is a matter of public safety."),
        ("h2", "Our requests"),
        ("bullets", [
            "Emergency communications fund: $24 million over three years for municipal emergency "
            "communications, including backup power for cell towers, radio interoperability with "
            "provincial responders, and satellite kits for every high-risk community.",
            "Rural connectivity: accelerate broadband to the 18,600 underserved households in our "
            "regions, with completion by 2028 rather than 2029, prioritizing communities on evacuation routes.",
            "A seat at the table: a standing ANRM representative on the provincial Emergency "
            "Communications Working Group.",
            "Cellular coverage on highways: a commitment to close coverage gaps on Highways 11 and 64, "
            "which are primary evacuation routes (approx. 340 km without reliable coverage).",
        ]),
        ("p", "We recognize the Ministry's investments through the Rural Connectivity Fund and wish to "
              "work in partnership. However, our members have passed resolutions calling on the province "
              "to act before spring, and several mayors will be raising this issue publicly at our "
              "Winter Policy Forum on January 14, 2027."),
        ("p", "Our delegation would include myself; Reeve Paul Whitehorse (Pine Valley County); "
              "Councillor Mei-Lin Zhao (Lakeshore District), ANRM Emergency Preparedness Committee Chair; "
              "and Sandra Kowalczyk, ANRM Executive Director."),
        ("p", "Please contact Sandra Kowalczyk at s.kowalczyk@anrm.example or 555-0142 to arrange a "
              "date. We look forward to meeting with you."),
        ("p", "Sincerely,"),
        ("p", "Mayor Denise Arcand, President, Association of Northern and Rural Municipalities"),
    ]
    render_docx(out / "Letter_ANRM-Meeting-Request.docx", letter, "ANRM  |  FICTIONAL DEMO CORRESPONDENCE")

    write_text(out / "Meeting-Logistics-Notes.txt", """
MEETING LOGISTICS NOTES  [FICTIONAL DEMO]
Minister's Office - Scheduling
Prepared by: Owen Fairweather, Scheduling Assistant to the Minister
Last updated: November 6, 2026

Meeting:     Minister Lindqvist with the Association of Northern and Rural
             Municipalities (ANRM)
Date:        Thursday, November 26, 2026
Time:        TBC - two holds in the Minister's calendar; ANRM to confirm which
             works. (Do not circulate a time until confirmed.)
Duration:    45 minutes
Location:    Minister's boardroom, 5th floor, 200 Legislature Way
             (virtual link available for one ANRM attendee if needed)

ANRM attendees (per E.D. Sandra Kowalczyk, confirmed by phone Nov 5):
  - Mayor Denise Arcand, President (Cedar Falls)
  - Reeve Paul Whitehorse (Pine Valley County)
  - Councillor Mei-Lin Zhao (Lakeshore District)  -- may join virtually
  - Sandra Kowalczyk, Executive Director
  - NEW: Mayor Robert Tanaka (Town of Granite Bay) asked to be added; not in
    the original letter. Kowalczyk says he will raise Highway 64 coverage.

Ministry attendees:
  - Hon. Amara Lindqvist, Minister
  - Farah Haddad, Director of Policy, Minister's Office
  - Victor Lemaire, ADM, Connectivity & Digital Infrastructure
  - Dr. Kwame Boateng (IWCO) - for the wildfire outlook portion, 10 min max

Notes from pre-call with ANRM staff:
  - ANRM will bring a one-page "ask" summary; main priority is the $24M
    emergency communications fund. Broadband acceleration is second.
  - They mentioned a local news crew may be outside after the meeting.
  - ANRM wants a commitment they can announce at their Winter Policy Forum
    (Jan 14, 2027).
  - Kowalczyk was told by someone at the Emergency Management Agency that $5.5M
    is already approved for 2027 readiness - they view this as "not enough".

Open items:
  [ ] Confirm meeting time with ANRM
  [ ] Policy to provide briefing note + key messages by Nov 20
  [ ] Confirm whether the Minister of Emergency Management's office should attend
  [ ] Photo op? Comms to advise
""")


# =========================================================================== #
# Scenario 3 - Vendor data breach (Issue Note)
# =========================================================================== #

def scenario_03(out: Path) -> None:
    incident = [
        ("title", "Privacy Incident Report - PIR-2026-0417"),
        ("subtitle", "Third-party vendor breach affecting Digital Benefits Access Program applicants"),
        ("meta", [
            ("Organization", f"{MDG} - Information and Privacy Office"),
            ("Prepared by", "Naomi Castellanos, Chief Privacy Officer"),
            ("Contributors", "Office of the CISO; Benefits Delivery Branch; Legal Services"),
            ("Date", "November 6, 2026 (Update 2)"),
            ("Status", "Contained - notification in progress"),
        ]),
        ("h1", "1. Summary"),
        ("p", "On October 24, 2026, Litware Document Services Inc. ('Litware'), the vendor contracted to "
              "scan and index paper applications for the Digital Benefits Access Program (DBAP), detected "
              "unauthorized access to one of its file-transfer servers. Litware notified the Ministry on "
              "October 29, 2026 - five days after detection, contrary to the 24-hour notification "
              "requirement in Schedule F of its contract. Forensic analysis confirms that personal "
              "information of 12,400 benefit applicants was exfiltrated."),
        ("h1", "2. Personal information involved"),
        ("table", {
            "header": ["Data element", "# Individuals", "Sensitivity"],
            "rows": [
                ["Name, mailing address, date of birth", "12,400", "Medium"],
                ["Social Insurance Number", "12,400", "High"],
                ["Household income and benefit amounts", "8,950", "High"],
                ["Banking information (direct deposit)", "3,150", "High"],
                ["Medical documentation (disability supplement)", "410", "Very high"],
            ],
            "widths": [3.2, 1.4, 1.6],
        }),
        ("h1", "3. Timeline"),
        ("table", {
            "header": ["Date (2026)", "Event"],
            "rows": [
                ["Oct 21", "Earliest evidence of unauthorized access (compromised vendor service account)"],
                ["Oct 24", "Litware security team detects anomalous outbound transfer (2.3 GB)"],
                ["Oct 29", "Litware notifies Ministry Benefits Delivery Branch by email"],
                ["Oct 29", "Ministry suspends all file transfers to Litware; incident team convened"],
                ["Oct 31", "Independent forensic firm (Adatum Cyber) engaged by the Ministry"],
                ["Nov 2", "Data set confirmed; affected population determined at 12,400"],
                ["Nov 3", "Office of the Information and Privacy Commissioner (OIPC) formally notified"],
                ["Nov 4", "Police service notified; file opened"],
                ["Nov 5", "Notification letters begin mailing; dedicated call centre opens"],
                ["Nov 6", "This report (Update 2)"],
            ],
            "widths": [1.1, 5.6],
        }),
        ("h1", "4. Containment and remediation"),
        ("bullets", [
            "Compromised service account disabled; all Litware credentials rotated on October 29.",
            "File transfers to Litware remain suspended; paper applications (approx. 1,900 per week) are "
            "being processed in-house with overtime, creating a backlog of 3,400 applications.",
            "No evidence that Ministry systems were accessed. No evidence to date of the data being "
            "published or offered for sale (dark-web monitoring by Adatum Cyber ongoing).",
            "Litware has engaged its own forensic firm and has committed to a full remediation plan by "
            "November 20.",
        ]),
        ("h1", "5. Notification status (as of Nov 6)"),
        ("table", {
            "header": ["Activity", "Status"],
            "rows": [
                ["Letters mailed to affected individuals", "9,870 of 12,400 (80%)"],
                ["Pending - address verification required", "2,530"],
                ["Call centre calls received (Nov 5-6)", "1,146; average wait 14 minutes"],
                ["Credit monitoring offered", "2 years, at no cost (Woodgrove Credit Services)"],
                ["Bank notification for 3,150 direct-deposit accounts", "Coordinated with financial institutions; complete"],
            ],
            "widths": [3.4, 3.3],
        }),
        ("h1", "6. Costs and contractual matters"),
        ("p", "Estimated direct costs to date are $1.1M (forensics $0.28M, mail-out $0.09M, call centre "
              "$0.21M, credit monitoring $0.52M). Legal Services advises that the Ministry may recover "
              "costs from Litware under the indemnity clause. The Litware contract ($4.6M, expiring "
              "March 2027) is under review; the Benefits Delivery Branch notes that no alternative vendor "
              "could be onboarded before spring."),
        ("h1", "7. Outstanding issues"),
        ("bullets", [
            "Whether to terminate, suspend, or continue the Litware contract.",
            "Whether to proactively publish a public notice before all letters are delivered.",
            "OIPC has indicated it may open a formal investigation; decision expected by November 30.",
            "A class-action law firm has posted a notice seeking affected individuals.",
        ]),
    ]
    render_pdf(out / "Privacy-Incident-Report_PIR-2026-0417.pdf", incident, MDG_HDR)

    media = [
        ("title", "Media Monitoring Summary"),
        ("subtitle", "Issue: Benefit applicant data breach (Litware Document Services)"),
        ("meta", [
            ("Prepared by", "Communications Branch - Media Relations, Ministry of Digital Government"),
            ("Analyst", "Bianca Ferreira, Senior Media Relations Advisor"),
            ("Period covered", "November 5, 2026 06:00 to November 9, 2026 12:00"),
            ("Date", "November 9, 2026"),
        ]),
        ("h1", "Coverage overview"),
        ("table", {
            "header": ["Indicator", "Value"],
            "rows": [
                ["Total stories", "14 (6 print/online, 5 radio, 3 TV)"],
                ["Tone", "Negative 9, Neutral 5, Positive 0"],
                ["Social media mentions", "3,870 (peak Nov 6: 1,640)"],
                ["Top hashtag", "#BenefitsBreach"],
                ["Opposition statements", "2 (Digital Government critic; Official Opposition leader)"],
            ],
            "widths": [2.4, 4.3],
        }),
        ("h1", "Key storylines"),
        ("bullets", [
            "Delay in notification: most coverage focuses on the five-day gap between the vendor's "
            "detection (Oct 24) and the Ministry being told (Oct 29), and asks why the public learned only "
            "on November 5.",
            "Scope: the Northern Ledger reported that 'more than 15,000' people may be affected, citing an "
            "unnamed source inside the vendor. The Ministry's figure is 12,400.",
            "Vulnerable populations: CityWave Radio highlighted that disability supplement applicants' "
            "medical information was involved.",
            "Vendor accountability: two outlets noted that Litware received a contract extension in "
            "March 2026 without competition.",
            "Call centre: social media complaints about wait times; one viral post (2,100 shares) claims "
            "a 2-hour wait.",
        ]),
        ("h1", "Opposition statements"),
        ("p", "Digital Government critic Gordon MacAllister (fictional) said: 'Twelve thousand families "
              "trusted this government with their most sensitive information. The Minister must explain "
              "why it took nearly two weeks to tell them.' The Official Opposition has called for the "
              "Litware contract to be cancelled immediately and for an independent review."),
        ("h1", "Outstanding journalist questions"),
        ("table", {
            "header": ["Outlet / Journalist", "Question", "Deadline"],
            "rows": [
                ["Northern Ledger - Aisha Rahman", "Is the true number above 15,000? Will the Ministry "
                 "release the forensic report?", "Nov 10, 3 PM"],
                ["Capital Times - Derek Lindgren", "Will the Litware contract be cancelled? How much has "
                 "Litware been paid since 2022?", "Nov 10, 5 PM"],
                ["CityWave Radio - Joanne Pelletier", "What is being done for disability supplement "
                 "applicants whose medical records were exposed?", "Nov 11, 9 AM"],
                ["Provincial Broadcast News - Sam Okoro", "Request for on-camera interview with the "
                 "Minister", "Nov 12"],
            ],
            "widths": [1.9, 3.6, 1.2],
        }),
        ("h1", "Recommended approach (Communications Branch)"),
        ("bullets", [
            "Minister to issue a statement confirming the 12,400 figure and explaining the verification "
            "process; avoid speculation on the contract until the review is complete.",
            "Publish an online FAQ and call-centre hours; add 20 agents to reduce wait times.",
            "Decline on-camera interview until all letters are delivered (target November 13), or accept "
            "with tight messages - decision required from the Minister's Office.",
        ]),
    ]
    render_docx(out / "Media-Monitoring-Summary_Benefits-Breach.docx", media, MDG_HDR)

    write_text(out / "Email_Privacy-Office-Update.txt", """
From:    Naomi Castellanos <naomi.castellanos@digitalgov.example>
         Chief Privacy Officer
To:      ADM Benefits Delivery; Director of Communications; DM Office Issues Manager
Date:    Monday, November 9, 2026 5:47 PM
Subject: PIR-2026-0417 - update on affected count and OIPC

[FICTIONAL DEMO EMAIL]

All,

Quick update ahead of tomorrow's media deadlines:

1. Count: Adatum Cyber completed de-duplication today. The confirmed number of unique
   affected individuals is 12,412 (up 12 from 12,400). The 12 additional people are
   disability supplement applicants whose files were stored in a separate folder.
   That brings the medical-documentation group to 422. We see NO basis for the
   "15,000+" figure in the Northern Ledger - the vendor's total file count includes
   duplicates and test records.

2. Letters: 10,640 mailed as of end of day. 1,772 still need address verification.

3. OIPC: The Commissioner's office called this afternoon. They will open a formal
   investigation and expect to announce it publicly on or around November 16. They
   asked for our draft notification letter and the Litware contract by Nov 13.

4. Litware: their CEO, Martin Osei, has asked for a call with the ADM. He wants to
   discuss "continuity of service" - I suspect they are worried about termination.

Can someone confirm whether the DM wants an issue note tonight or tomorrow AM?

Naomi
""")


# =========================================================================== #
# Scenario 4 - Contoso acquisition of Fabrikam Analytics (Executive Summary)
# =========================================================================== #

def scenario_04(out: Path) -> None:
    dd = [
        ("title", "Project Lighthouse - Due Diligence Summary"),
        ("subtitle", "Proposed acquisition of Fabrikam Analytics Inc. by Contoso Group"),
        ("meta", [
            ("Prepared by", "Contoso Group Corporate Development - Rafael Mendes, VP Corporate Development"),
            ("Advisors", "Woodgrove Bank Capital Markets (financial); Adatum LLP (legal); "
                         "Wide World Consulting (technology)"),
            ("Date", "November 4, 2026"),
            ("Data as of", "October 31, 2026 (unaudited management accounts)"),
        ]),
        ("h1", "1. Target overview"),
        ("p", "Fabrikam Analytics Inc. is a privately held, venture-backed SaaS company headquartered in "
              "Toronto, providing supply-chain demand forecasting and inventory analytics to mid-market "
              "and enterprise retailers and distributors. Founded in 2017, it has 212 employees (61% in "
              "R&D) and 184 customers in North America and the UK. The founder-CEO is Lucia Ferraro; "
              "the CTO and co-founder is Anand Krishnaswamy."),
        ("h1", "2. Key financial and operating metrics"),
        ("table", {
            "header": ["Metric", "FY2024", "FY2025", "LTM Oct 2026"],
            "rows": [
                ["Annual recurring revenue (ARR, US$M)", "27.1", "36.0", "48.2"],
                ["ARR growth (YoY)", "41%", "33%", "34%"],
                ["Gross margin", "71%", "74%", "76%"],
                ["Net revenue retention (NRR)", "121%", "119%", "117%"],
                ["Gross revenue retention (GRR)", "91%", "90%", "89%"],
                ["Annual logo churn", "6.1%", "7.0%", "7.8%"],
                ["Adjusted EBITDA (US$M)", "-6.4", "-4.1", "-1.9"],
                ["Adjusted EBITDA margin", "-26%", "-12%", "-4%"],
                ["Cash burn (US$M / yr)", "9.8", "7.2", "4.5"],
            ],
            "widths": [2.9, 1.2, 1.2, 1.4],
        }),
        ("note", "Woodgrove's quality-of-earnings review identified $0.6M of ARR from contracts with "
                 "termination-for-convenience clauses that may not qualify as recurring. Adjusted ARR "
                 "would be $47.6M."),
        ("h1", "3. Valuation and proposed terms"),
        ("bullets", [
            "Indicative enterprise value: US$410M (8.5x LTM ARR), all-cash at closing.",
            "Comparable transactions: 7.2x - 10.4x ARR (median 8.8x) for vertical analytics SaaS, 2024-2026.",
            "Seller expectation (per Fabrikam's banker): US$450M+; a competing indication from a private "
            "equity sponsor is rumoured.",
            "Proposed retention pool of US$18M for 40 key employees over 3 years.",
        ]),
        ("h1", "4. Strategic rationale"),
        ("bullets", [
            "Adds predictive analytics to Contoso's Retail Operations Cloud, closing a gap cited in 38% of "
            "lost deals in FY2026.",
            "Cross-sell potential into Contoso's 1,150 retail customers; Fabrikam has penetrated fewer than 5%.",
            "Revenue synergies estimated at US$9M run-rate by FY2029; cost synergies US$5M (hosting, G&A).",
        ]),
        ("pagebreak",),
        ("h1", "5. Integration risks"),
        ("table", {
            "header": ["Risk", "Rating", "Commentary"],
            "rows": [
                ["Key-person dependency", "High",
                 "CTO Anand Krishnaswamy holds core IP knowledge; no signed retention agreement yet."],
                ["Customer concentration", "Medium-High",
                 "Top 10 customers = 31% of ARR; Northwind Traders alone = 9% (US$4.3M), renewal due "
                 "June 2027."],
                ["Technology platform", "Medium",
                 "Fabrikam runs on a different cloud platform and data stack; re-platforming estimated "
                 "at US$7-9M over 18 months."],
                ["Data residency / privacy", "Medium",
                 "UK customers (14% of ARR) require UK data residency; current setup partially compliant."],
                ["Culture and talent", "Medium",
                 "Engineering attrition 19% LTM; Glassdoor-style internal survey shows concern about "
                 "'big company' processes."],
                ["Open-source licensing", "Low",
                 "Two components under copyleft licences; remediation straightforward."],
            ],
            "widths": [1.6, 1.0, 4.1],
        }),
        ("h1", "6. Recommendation of Corporate Development"),
        ("p", "Proceed to a non-binding letter of intent at an enterprise value of up to US$410M with a "
              "60-day exclusivity period, conditional on (i) signed retention agreements for the CTO and "
              "12 senior engineers, (ii) confirmatory diligence on Northwind Traders' renewal intent, and "
              "(iii) a UK data residency remediation plan. Walk-away price: US$440M."),
    ]
    render_pdf(out / "Due-Diligence-Summary_Fabrikam-Analytics.pdf", dd, CONTOSO_HDR, accent=CORP_COLOR)

    board = [
        ("title", "Board of Directors - Pre-Read (Excerpt)"),
        ("subtitle", "Agenda item 4: Project Lighthouse - Authority to submit a letter of intent"),
        ("meta", [
            ("Meeting", "Contoso Group Board of Directors, December 3, 2026"),
            ("Sponsor", "Elena Vasquez, Chief Strategy Officer"),
            ("Prepared by", "Office of the Corporate Secretary with Corporate Development"),
            ("Date", "November 12, 2026 (circulated draft v0.9)"),
        ]),
        ("h1", "Decision requested"),
        ("p", "The Board is asked to authorize management to submit a non-binding letter of intent to "
              "acquire 100% of Fabrikam Analytics Inc. for a total consideration of up to US$425M, "
              "comprising US$390M cash at closing and an earn-out of up to US$35M tied to FY2028 ARR "
              "targets, and to enter a 60-day exclusivity period."),
        ("h1", "Key figures for the Board"),
        ("table", {
            "header": ["Item", "Value"],
            "rows": [
                ["ARR (as of September 30, 2026)", "US$47.6M"],
                ["ARR growth", "34% YoY"],
                ["Net revenue retention", "117%"],
                ["Implied multiple (closing cash / ARR)", "8.2x"],
                ["Total synergies (run-rate FY2029)", "US$14M (US$9M revenue, US$5M cost)"],
                ["Integration cost (one-time)", "US$22M incl. re-platforming and retention"],
                ["EPS impact", "Dilutive by ~US$0.04 in FY2027; accretive from FY2029"],
                ["Funding", "Cash on hand (US$310M) plus US$120M from revolving credit facility"],
            ],
            "widths": [3.0, 3.7],
        }),
        ("h1", "Management view"),
        ("bullets", [
            "The earn-out structure bridges the valuation gap with the seller (expectation US$450M+) "
            "while protecting Contoso if growth slows.",
            "The CFO, Kenji Watanabe, notes that drawing on the revolver will move net leverage from 0.4x "
            "to 1.1x EBITDA, within the Board-approved ceiling of 2.0x.",
            "The Chief People Officer recommends that retention agreements be a condition of signing, not "
            "closing.",
        ]),
        ("h1", "Questions raised at the November 10 Audit & Risk Committee"),
        ("bullets", [
            "Director Abena Mensah asked how Northwind Traders' renewal risk is reflected in the price.",
            "Director Hugh Pemberton asked for a downside case assuming NRR falls to 105%.",
            "The Committee requested clarity on whether Fabrikam's UK operations trigger any regulatory "
            "approvals (management believes none are required; Adatum LLP to confirm).",
        ]),
        ("note", "Draft - figures to be reconciled with the Due Diligence Summary of November 4, 2026 "
                 "before final circulation."),
    ]
    render_docx(out / "Board-PreRead-Excerpt_Project-Lighthouse.docx", board, CONTOSO_HDR,
                accent=RGBColor(0x0B, 0x5A, 0x4A))

    write_text(out / "Customer-Interview-Notes_Fabrikam.md", """
# Project Lighthouse - Customer Reference Interviews (Fabrikam Analytics)

*FICTIONAL DEMO CONTENT. Interviews conducted October 26 - November 6, 2026 by
Wide World Consulting on behalf of Contoso Group Corporate Development.
Interviewer lead: Hannah Brightwater. 8 customers interviewed (of 10 requested).*

| # | Customer | Segment | ARR to Fabrikam (US$) | Customer since | Sentiment |
|---|----------|---------|-----------------------|----------------|-----------|
| 1 | Northwind Traders | Enterprise distributor | 4.3M | 2019 | Mixed / at risk |
| 2 | Tailspin Toys | Specialty retail | 1.6M | 2021 | Very positive |
| 3 | Wide World Importers | Enterprise distributor | 2.2M | 2020 | Positive |
| 4 | Fourth Coffee | Food & beverage retail | 0.7M | 2022 | Positive |
| 5 | Litware Home | Home goods retail | 0.9M | 2023 | Neutral |
| 6 | Woodgrove Grocers | Grocery | 1.1M | 2021 | Positive |
| 7 | Adventure Works Outdoor | Sporting goods | 0.5M | 2024 | Very positive |
| 8 | Alpine Ski House | Seasonal retail | 0.3M | 2024 | Negative |

## Themes

- **Forecast accuracy is the differentiator.** 6 of 8 customers cite 15-25% improvement in
  forecast accuracy vs. prior tools. Tailspin Toys: "Fabrikam paid for itself in one holiday season."
- **Support quality is slipping.** 5 of 8 noted slower support response in 2026; two
  mentioned their dedicated customer success manager left.
- **Integration with Contoso seen as positive by most** - 5 customers already use Contoso
  Retail Operations Cloud and want "one login, one data model".
- **Pricing concerns.** 3 customers worry Contoso will raise prices at renewal.

## Notable interviews

### Northwind Traders (9% of Fabrikam ARR)
- VP Supply Chain, Oliver Brandt: "We love the models, but the platform hasn't kept up
  with our volumes. We are piloting a competitor in two distribution centres."
- Renewal in June 2027. Brandt said an acquisition by Contoso "could go either way -
  if it means real investment, we stay; if it means a migration project, we'd rather switch now."
- Said they were told by Fabrikam sales that a new scaling architecture would ship in
  Q1 2027 - the CTO's roadmap shared in diligence shows Q3 2027.

### Tailspin Toys
- Planning to expand from 140 to 260 stores on Fabrikam in 2027 (+US$0.9M ARR potential).
- Strongly values access to the CTO, Anand Krishnaswamy: "If Anand leaves, I'd want to talk."

### Alpine Ski House
- Considering non-renewal in March 2027 due to poor fit for highly seasonal demand.
  Small account, but they report two other ski retailers share the same view.

## Interviewer's assessment
Overall customer sentiment is positive (net promoter proxy: +31), with product strength
offset by support capacity and scalability concerns. **The Northwind Traders relationship
is the single largest commercial risk** and should be validated with a direct
executive-to-executive conversation before signing an LOI.
""")


SCENARIOS = {
    "01-gov-cloud-modernization-decision": scenario_01,
    "02-gov-wildfire-stakeholder-meeting": scenario_02,
    "03-gov-data-breach-issue": scenario_03,
    "04-contoso-acquisition-exec-summary": scenario_04,
}


README = """
# Briefing Note Generator - Demo Kit (fictional source documents)

> **Everything in this folder is fictional.** The Ministry of Digital Government, Contoso Group,
> Fabrikam Analytics, all people, figures and events are invented for demonstration purposes.
> Regenerate with `python scripts/generate_samples.py`.

Each scenario folder contains 2-4 source documents (PDF with text layer, DOCX, and a TXT/MD
email or notes). Upload **all** files in the folder, then fill in the request as shown below.
Figures deliberately differ between some documents so you can show the agent's verification
notes and [S#] citations.

---

## 1. `01-gov-cloud-modernization-decision/` - Government, decision

| Field | Value |
|---|---|
| Template | **Briefing Note for Decision** |
| Profile | Ministry of Digital Government |
| Recipient | Hélène Castonguay, Deputy Minister |
| Files | Program assessment report (PDF), TB submission summary memo (DOCX), CIO office email (TXT) |

**Purpose (paste):**
> Seek the Deputy Minister's decision on the preferred option for migrating the Ministry's legacy
> application portfolio to cloud, so the Treasury Board submission can be finalized for the
> December 4, 2026 deadline.

**A good draft should:**
- Present Options A/B/C with 5-year costs (A $412.6M, B $338.4M, C $361.2M -> revised $374.9M) and
  recommend Option C, citing each figure.
- State the decision deadline (Nov 20, 2026), Minister sign-off (Nov 27), TBS deadline (Dec 4),
  lease expiry (Mar 31, 2028).
- Cover risks (85 FTE retraining/PTEA union, no Jan-Apr cutovers, missing the winter cycle = ~$1.2M/month holdover).
- **Verification notes should flag:** cost $361.2M vs $374.9M; incremental $173.8M vs $187.5M;
  140 vs 138 apps; 48 vs ~54 months; the email still quotes the old ~$361M.

**Agent may ask:** which cost figure to treat as authoritative; whether to include the Minister's
"no service disruptions" commitment as a consideration.

---

## 2. `02-gov-wildfire-stakeholder-meeting/` - Government, meeting brief

| Field | Value |
|---|---|
| Template | **Meeting or Event Brief** |
| Profile | Ministry of Digital Government |
| Recipient | Hon. Amara Lindqvist, Minister of Digital Government |
| Files | Wildfire outlook + connectivity annex (PDF), ANRM letter (DOCX), scheduling notes (TXT) |

**Purpose (paste):**
> Prepare the Minister for her November 26 meeting with the Association of Northern and Rural
> Municipalities on emergency communications and rural connectivity ahead of the 2027 wildfire season.

**A good draft should:**
- Summarize who is attending (incl. the late addition Mayor Robert Tanaka), the four ANRM asks
  ($24M over 3 years, broadband by 2028, working-group seat, Highways 11/64 coverage).
- Use outlook data: 18,600 underserved households, 41 towers, $5.5M approved vs ~$7.6M gap,
  North Ridge "Extreme" forecast.
- Offer key messages / suggested responses and anticipate the Jan 14, 2027 Winter Policy Forum and media presence.
- **Verification notes:** ANRM says 8,000+ residents missed alerts vs provincial estimate of 7,300.

**Agent should ask / flag:** the **meeting time is not confirmed** in any document (TBC);
whether the Minister of Emergency Management's office attends.

---

## 3. `03-gov-data-breach-issue/` - Government, issue note

| Field | Value |
|---|---|
| Template | **Issue Note** |
| Profile | Ministry of Digital Government |
| Recipient | Hélène Castonguay, Deputy Minister |
| Files | Privacy incident report (PDF), media monitoring summary (DOCX), CPO update email (TXT) |

**Purpose (paste):**
> Brief the Deputy Minister on the Litware vendor data breach affecting Digital Benefits Access
> Program applicants: current status, media and OIPC exposure, and decisions needed in the next 72 hours.

**A good draft should:**
- Give the timeline (detected Oct 24, Ministry told Oct 29 - breach of 24-hour clause; public Nov 5).
- State scope and sensitivity (SIN for all, 3,150 banking, medical docs), containment, notification
  progress, $1.1M cost, credit monitoring.
- List decisions: Litware contract, on-camera interview, public notice; note OIPC investigation (~Nov 16).
- **Verification notes:** 12,400 vs 12,412 affected; 410 vs 422 medical; letters 9,870 vs 10,640;
  media's "15,000+" is unsupported.

**Agent may ask:** which update is most current (use the Nov 9 email); whether journalist deadlines
(Nov 10-12) should be included.

---

## 4. `04-contoso-acquisition-exec-summary/` - Private sector, executive summary

| Field | Value |
|---|---|
| Template | **Executive Summary** (or Briefing Note for Decision) |
| Profile | Contoso Group |
| Recipient | Daniel Achebe, Chief Executive Officer, Contoso Group (ahead of Dec 3 Board) |
| Files | Due diligence summary (PDF), Board pre-read excerpt (DOCX), customer interview notes (MD) |

**Purpose (paste):**
> Summarize the case for acquiring Fabrikam Analytics so the CEO can decide whether to take the
> letter-of-intent recommendation to the December 3 Board meeting, highlighting price, risks and
> open questions.

**A good draft should:**
- Cover ARR ~$48M, 34% growth, NRR 117%, churn 7.8%, adj. EBITDA -$1.9M, synergies $14M, funding/leverage.
- Highlight risks: CTO key-person, Northwind Traders (9% ARR, piloting a competitor, June 2027 renewal),
  re-platforming $7-9M, UK data residency, support quality.
- **Verification notes:** EV $410M (DD) vs $425M incl. earn-out (Board); ARR $48.2M vs $47.6M
  (different dates / QoE adjustment); walk-away $440M; roadmap Q1 vs Q3 2027.

**Agent may ask:** whether to frame as a recommendation or neutral summary; which valuation to
present as the management position.

---

### Demo tips
- Start with Scenario 1 for public-sector audiences, Scenario 4 for private sector.
- After drafting, open the verification/citations section and click through [S1]/[S2] to show
  traceability to the uploaded documents.
- Try Scenario 2 to show the agent asking for missing information rather than inventing it.
"""


def main() -> None:
    SAMPLES.mkdir(exist_ok=True)
    for name, fn in SCENARIOS.items():
        folder = SAMPLES / name
        folder.mkdir(exist_ok=True)
        fn(folder)
    write_text(SAMPLES / "README.md", README)
    for f in sorted(SAMPLES.rglob("*")):
        if f.is_file():
            print(f"{f.relative_to(SAMPLES)}  ({f.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
