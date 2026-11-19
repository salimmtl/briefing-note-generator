# Briefing Board (Canvas): plan

> v0.1 (2026-11-13). Self-approved during an autonomous build: the user asked for "an app to visualise the list of
> briefings as a Canvas app, on the same Dataverse backend, just a different way to visualise the same data".

## Canvas App Plan

### Screens
| Action | Screen | File | Purpose | Key Controls |
|--------|--------|------|---------|--------------|
| Create | Board | Screen1.pa.yaml | Kanban view of every briefing request by stage | Header (title, Needs Attention badge, Refresh), nav tabs, 5 lane columns (horizontal gallery of lanes, nested vertical gallery of cards: BN number, subject, recipient, template, due date with overdue colour, priority badge) |
| Create | List | ListScreen.pa.yaml | Searchable, filterable list | Search box, status dropdown, template dropdown, "Overdue only" toggle, result count, gallery rows (number, subject, status pill, template, recipient, due, priority, requester) |
| Create | Detail | DetailScreen.pa.yaml | Read-only view of one request | Back, header (number, subject, status pill, meta grid), key message card, draft sections (parsed from the sections JSON), verification notes and confidence, open questions (Needs Info), sources gallery (S1…, file, type, characters, summary), activity timeline, Draft PDF / Final PDF / SharePoint folder links |
| Create | Overview | OverviewScreen.pa.yaml | KPIs and distribution | KPI tiles (open, needs info, in review, delivered this month, overdue, needs attention), bars by status, bars by template, recent activity |

Target: tablet / desktop landscape (1366×768), AutoLayout, responsive down to 1024 px.

### Data Strategy
- **Dataverse backend (existing solution `BriefingNoteGenerator`)**: `Briefing Requests` (`brn_request`), `Source
  Documents` (`brn_sourcedocument`), `Briefing Activities` (`brn_activity`). Read-only.
- **Single data layer**: a behavior user-defined function `LoadBriefings()` in `App.Formulas` fills three collections with
  plain fields, so screens never touch Dataverse directly:
  - `colRequests`: Id (GUID), Number, Subject, Status (text label), Lane (text), Template, Profile, Requester,
    Recipient, RecipientTitle, DueDate (date), Priority, Classification, Language, KeyMessage, NoteTitle, SectionsJson,
    Verification, Confidence, Questions, DraftPdf, FinalPdf, Folder, Reviewer, LastError, WordCount, Version,
    SubmittedOn, DraftedOn, DeliveredOn, CreatedOn (date-times).
  - `colSources`: RequestId, Label, FileName, DocType, Characters, Summary.
  - `colActivities`: RequestId, Title, Actor, ActivityType, Details, CreatedOn.
- **Build-time mock**: the scratch authoring session has no data sources yet, so `LoadBriefings()` first ships with 6
  compact mock requests (one per lane, plus a Needs Attention one), their sources and activities, in exactly these
  shapes. The Dataverse version of `LoadBriefings()` (`docs/canvas-board-dataverse-loader.md`) replaces it once the tables
  are added in Studio. Screens don't change.
- Lanes: *In progress* = Draft, Submitted, Drafting, Info Provided, Revision Requested; *Needs info*; *In review*;
  *Approved*; *Delivered*. Cancelled is hidden from the board (visible in the list). Needs Attention shows in *In
  progress* with a red flag.
- State: `varSelected` (record from `colRequests`), filter variables on the list screen. No writes.

### Functional Scope
| Capability | User path | Source transition | Visible success |
|---|---|---|---|
| See all briefings by stage | Board (start screen) | Read `colRequests`, grouped by Lane | Each lane shows its count and cards |
| Refresh | Header → Refresh | `LoadBriefings()` reloads the three collections | "Updated hh:mm" label changes; counts reflect the reload |
| Search and filter | List → search / status / template / overdue | Filter `colRequests` | Result count and rows match the filters; clear resets |
| Open a request | Card or row → select | `Set(varSelected, ThisItem)`, navigate to Detail | Detail header shows the same BN number and subject |
| Read the draft | Detail | Parse `varSelected.SectionsJson` | Each section heading and body visible; empty state when no draft |
| Sources and timeline | Detail | Filter `colSources` / `colActivities` by `varSelected.Id` | Rows for that request only, timeline newest first |
| Open PDFs / folder | Detail → links | `Launch(url)` | Disabled with "not available yet" when empty |
| Overview | Nav → Overview | Aggregate `colRequests` | KPI values and bars |

### Aesthetic Direction
Calm, government-appropriate, matching Briefing Studio: white surfaces on a light grey canvas, one accent.
- Canvas `RGBA(245,246,248,1)`, surface `RGBA(255,255,255,1)`, border `RGBA(225,228,232,1)`
- Text `RGBA(36,36,36,1)`, secondary `RGBA(97,97,97,1)`
- Accent `RGBA(15,108,189,1)` (hover `RGBA(17,94,163,1)`), accent tint `RGBA(235,243,252,1)`
- Status: amber `RGBA(188,75,9,1)` on `RGBA(255,244,206,1)` (Needs info), purple `RGBA(92,46,145,1)` on
  `RGBA(239,233,246,1)` (In review), green `RGBA(16,124,16,1)` on `RGBA(223,246,221,1)` (Approved/Delivered), red
  `RGBA(196,49,75,1)` on `RGBA(253,231,233,1)` (Needs attention / overdue), grey `RGBA(97,97,97,1)` on
  `RGBA(240,240,240,1)` (Draft/Cancelled)
- Font: Segoe UI; titles 20–24, body 13–14.

