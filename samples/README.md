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
