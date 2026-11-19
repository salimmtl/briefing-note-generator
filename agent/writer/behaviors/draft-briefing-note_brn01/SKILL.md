---
name: draft-briefing-note
description: Drafts a cited briefing note from a briefing request's source documents, profile and template, or writes clarification questions to the request when essential information is missing.
---
<!-- bic:source=blank -->
# Draft a briefing note

The workflow message gives you the **request id**, the request number, the **mode** (`first draft`, `clarification answers received` or `revision requested`) and today's date.

## 1. Load the context
1. Request: `SELECT brn_requestid, brn_requestnumber, brn_name, brn_status, brn_requestername, brn_requesteremail, brn_recipientname, brn_recipienttitle, brn_purpose, brn_additionalcontext, brn_language, brn_classification, brn_priority, brn_duedate, brn_clarificationquestions, brn_clarificationanswers, brn_clarificationrounds, brn_reviewercomments, brn_notetitle, brn_keymessage, brn_draftsections, brn_draftversion, _brn_profileid_value, _brn_templateid_value FROM brn_request WHERE brn_requestid = '<request id>'`.
2. Profile (style guide, glossary, classification guidance): `SELECT brn_name, brn_sector, brn_styleguide, brn_glossary, brn_classificationguidance, brn_leadertitles FROM brn_profile WHERE brn_profileid = '<profile id>'`. If the request has no profile, use plain-language, neutral, factual defaults.
3. Template (sections and rules): `SELECT brn_name, brn_notetype, brn_whentouse, brn_sections, brn_writingrules, brn_maxwords FROM brn_template WHERE brn_templateid = '<template id>'`. `brn_sections` lists one section per line as `Heading | guidance | max words`. If the request has no template, use "Briefing Note for Information": Purpose, Summary, Background, Current Situation, Considerations, Next Steps.
4. Source documents: `SELECT brn_sourcedocumentid, brn_name, brn_sourcelabel, brn_documenttype, brn_charactercount, brn_extractionstatus FROM brn_sourcedocument WHERE _brn_requestid_value = '<request id>' ORDER BY brn_sourcelabel`. Then read the text of **each** document, one at a time: `SELECT brn_extractedtext FROM brn_sourcedocument WHERE brn_sourcedocumentid = '<source document id>'`. Read all of it. Source labels (S1, S2…) are the citation keys.

## 2. Decide whether you can write a good note
Ask the requester **only when the note would be wrong or useless without the answer**, for example:
- there is no usable source text and the purpose and context aren't enough to write from;
- a **decision note** where neither the sources nor the request give the options or the decision sought;
- a **meeting brief** with no date, participants or objective anywhere;
- the sources contradict each other on a point that changes the bottom line, and the request doesn't say which is right;
- the purpose is unclear and two very different notes could be written.

Don't ask about anything you can reasonably assume, and never about style or length. When you assume, record it in the verification notes.

If you must ask, and `brn_clarificationrounds` is less than 2:
- Write 1 to 3 short, specific questions, each answerable in one or two sentences, numbered "1.", "2.", "3.". Explain in a few words why each one matters.
- `update_record` on `brn_request`: `brn_clarificationquestions` = the numbered questions; `brn_clarificationrounds` = current value + 1.
- Don't write a draft. Finish with outcome `needs_info`.

If `brn_clarificationrounds` is 2 or more, never ask again: write the best note you can and list every gap in the verification notes.

## 3. Write the note
- Mode `clarification answers received`: use `brn_clarificationanswers` (the latest round matters most) together with the sources.
- Mode `revision requested`: start from the current draft (`brn_draftsections`) and apply every point in `brn_reviewercomments`. Keep what the reviewer didn't ask to change.
- Follow the template sections **in order with the exact headings** (translated if the note is in French). Respect each section's guidance and word limit, and the template's maximum length.
- Follow the profile's style guide; expand acronyms with the glossary on first use.
- Bullets start on a new line with "- ". Paragraphs are separated by a blank line. No Markdown headings, bold, tables or HTML inside section bodies.
- **Note title**: specific and informative, for example "Cloud migration of legacy applications: funding decision".
- **Key message**: the bottom line in 1 to 3 sentences.

## 4. Save the draft
1. For each source document, `update_record` on `brn_sourcedocument`: `brn_summary` = 1 or 2 sentences on what this source contributes to the note (or "Not used" and why).
2. One `update_record` on `brn_request` with:
   - `brn_notetitle`, `brn_keymessage`
   - `brn_draftsections`: a **JSON array** (as a string) of objects with exactly two keys: `heading` and `body`, for example `[{"heading": "Purpose", "body": "To inform you of… [S1]"}]`. Escape quotes and line breaks so the JSON is valid.
   - `brn_sourcesused`: one line per source: `[S1] <file name>: <what it supports>`.
   - `brn_verificationnotes`: one line per item, starting with "- ": assumptions, discrepancies between sources, statements to double-check, "[To be confirmed]" items, and any concern that the content looks more sensitive than the chosen classification. Write "- No issues found." if there are none.
   - `brn_confidence`: 743800000 = Low, 743800001 = Medium, 743800002 = High. High = all sections well supported; Medium = some gaps or assumptions; Low = thin or conflicting sources.
   - `brn_wordcount` (whole note), `brn_draftversion` = current value + 1 (0 if empty).

## Final JSON
```json
{"outcome": "draft", "requestNumber": "BN-00001", "noteTitle": "...", "keyMessage": "...", "questions": "", "confidence": "Medium", "wordCount": 0, "draftVersion": 1, "summary": "<one or two sentences for the notification>"}
```
For `needs_info`, set `"outcome": "needs_info"`, put the questions separated by " | " in `questions`, and leave the draft fields empty (wordCount 0, draftVersion = the current value).

## Dataverse contract (columns you may update)
### `brn_request` (Briefing Request)

| Column | Type | Notes |
|---|---|---|
| `brn_name` | text (max 300) | Subject. Required |
| `brn_clarificationquestions` | multiline text | Clarification Questions (max 4000 chars) |
| `brn_clarificationrounds` | whole number | Clarification Rounds |
| `brn_notetitle` | text | Note Title (max 300 chars) |
| `brn_keymessage` | multiline text | Key Message (max 2000 chars). Bottom line up front: 1-3 sentences. |
| `brn_draftsections` | multiline text | Draft Sections (JSON) (max 100000 chars). [{"heading": "...", "body": "..."}] |
| `brn_sourcesused` | multiline text | Sources Used (max 10000 chars) |
| `brn_verificationnotes` | multiline text | Verification Notes (max 10000 chars). Assumptions, gaps and statements to check. |
| `brn_confidence` | choice | Draft Confidence. Values: 743800000 = Low, 743800001 = Medium, 743800002 = High |
| `brn_wordcount` | whole number | Word Count |
| `brn_draftversion` | whole number | Draft Version |

### `brn_sourcedocument` (Source Document)

| Column | Type | Notes |
|---|---|---|
| `brn_name` | text (max 300) | File Name. Required |
| `brn_summary` | multiline text | Summary (max 4000 chars). Written by the Writer: what this source contributes. |
