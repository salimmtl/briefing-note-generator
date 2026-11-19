---
name: review-briefing
description: Lets the reviewer of a briefing request read the draft and approve it or request a revision with comments.
---
<!-- bic:source=blank -->
# Review a draft

1. Find the request in In Review (743800005) where `brn_revieweremail` is the user's email. If the user isn't the reviewer, explain that only the reviewer can approve, and offer to show the status instead.
2. Show the note title, key message, confidence, the verification notes and the draft PDF link (`brn_draftpdfurl`). Show the sections from `brn_draftsections` (JSON array of heading/body) if the user asks.
3. Ask: approve, or request a revision?
   - **Revision**: collect the comments (what to change). `update_record`: `brn_reviewercomments` = the comments, `brn_status` = 743800006. Activity: actor 743800004, type 743800005.
   - **Approve**: confirm first ("The final PDF will be filed and sent per the delivery mode."). `update_record`: `brn_approvedby` = user email, `brn_approvedon` = now (UTC), `brn_status` = 743800007. Activity: actor 743800004, type 743800006.
   Small wording edits are best done in Briefing Studio, where sections can be edited before approving.
4. Confirm what happens next.
