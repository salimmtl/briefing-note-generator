---
name: check-my-briefings
description: Lists the user's briefing requests (as requester or reviewer) and shows the status, questions, draft summary and document links of one request.
---
<!-- bic:source=blank -->
# Check my briefings

1. List: `SELECT TOP 20 brn_requestid, brn_requestnumber, brn_name, brn_status, brn_duedate, brn_recipientname, modifiedon FROM brn_request WHERE brn_requesteremail = '<user email>' OR brn_revieweremail = '<user email>' ORDER BY modifiedon DESC`.
2. Show a compact list: number, subject, status label, due date. Highlight **Needs Info** (the writer has a question: offer to answer it now) and, for reviewers, **In Review**.
3. For one request ("status of BN-00012"), read `brn_status`, `brn_clarificationquestions`, `brn_notetitle`, `brn_keymessage`, `brn_confidence`, `brn_verificationnotes`, `brn_draftpdfurl`, `brn_finalpdfurl`, `brn_lasterror` and show what matters for that status, with the PDF links.
4. Recent activity: `SELECT TOP 5 brn_name, brn_activitytype, createdon FROM brn_activity WHERE _brn_requestid_value = '<request id>' ORDER BY createdon DESC`.

Status values: 743800000 = Draft, 743800001 = Submitted, 743800002 = Drafting, 743800003 = Needs Info, 743800004 = Info Provided, 743800005 = In Review, 743800006 = Revision Requested, 743800007 = Approved, 743800008 = Delivered, 743800009 = Cancelled, 743800010 = Needs Attention.
