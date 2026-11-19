# Briefing Note Writer: end-to-end test scenarios

The Writer runs unattended inside the **BN 1 - Draft Briefing Note** workflow, so it's tested end to end: submit a
request (Briefing Studio, the Briefing Assistant, or `python scripts/submit_sample.py <nn> --requester <email>`), then
check the outcome on the request and in the timeline.

| # | Scenario | Setup | Expected outcome |
|---|---|---|---|
| 1 | Executive summary from 3 documents | `submit_sample.py 04` (Contoso, Executive Summary) | **In Review** in about 6 minutes. Template headings in order; every bullet cited [S1]–[S3]; verification notes flag EV US$410M vs US$425M and ARR US$48.2M vs US$47.6M; draft PDF in SharePoint `…/CTSO/BN-xxxxx/Drafts` |
| 2 | Meeting brief with a gap | `submit_sample.py 02` (Meeting or Event Brief) | **In Review**; the meeting time is TBC in the logistics section and in the verification notes; the 8,000+ vs 7,300 residents discrepancy is flagged. (The Writer may instead ask for the time: both are acceptable.) |
| 3 | Clarification loop | Decision note, purpose "The DM needs to decide on the hybrid work policy.", **no documents** | **Needs Info** with 1–3 numbered questions (options, decision sought, deadline); Teams + email to the requester; no draft written |
| 4 | Answer the questions | Answer in Briefing Studio or the Briefing Assistant ("Answer the questions for BN-xxxxx") | Status **Info Provided** → **Drafting** → **In Review**; the draft uses the answers; anything still missing is "[To be confirmed]" |
| 5 | Third round | A request already at 2 clarification rounds | The Writer never asks again; it drafts and lists gaps in the verification notes |
| 6 | Revision | Reviewer comments + **Request revision** on an In Review draft | Draft version + 1; the comments are applied; other sections unchanged |
| 7 | Approval and delivery | **Approve** with delivery mode "Send to requester and recipient" and a recipient email | **Delivered**; final PDF (no draft banner, no verification notes, classification marking top and bottom) in `…/Final`; email with the PDF attached to requester + recipient; Teams messages to both |
| 8 | Decision note without options | `submit_sample.py 01` | Options A/B/C with 5-year costs, cited; recommendation only because the sources support it; the $361.2M vs $374.9M discrepancy is flagged |
| 9 | French | Any sample, language French | Headings translated, French typography, citations kept |
| 10 | Failure handling | Temporarily break the profile's SharePoint site URL | Status **Needs Attention** with the failing action in Last Error; a Failed activity in the timeline |

Check each run with `python scripts/flow_runs.py <workflow id> --actions`.
