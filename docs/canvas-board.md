# Briefing Board (canvas app)

A read-only canvas app over the Briefing Note Generator's Dataverse tables, a third way to view the same briefings:

| Screen | What it shows |
|---|---|
| **Board** (start) | Kanban by stage: In progress · Needs info · In review · Approved · Delivered, with count badges, priority and status pills, overdue dates in red and Needs Attention cards with a red border. Cancelled requests are counted but kept off the board |
| **List** | Search (number, subject, requester, recipient), status and template filters, "Overdue only", result count and Clear filters |
| **Detail** | Number, subject, status, a 12-field metadata grid, key message, the draft rendered from the sections JSON, verification notes and confidence, open questions, last error, sources (S1…), the activity timeline (newest first), and Draft PDF / Final PDF / SharePoint folder links |
| **Overview** | Six KPI tiles (open, needs info, in review, delivered this month, overdue, needs attention), bars by status and by template, and recent activity |

Every screen reads three collections (`colRequests`, `colSources`, `colActivities`) filled by one behavior function,
`LoadBriefings()`, in `App.Formulas`. The **Refresh** button in each header calls it again. The app never writes.

## Status

- The source in this folder compiles clean with the Canvas Authoring service. `LoadBriefings()` currently loads
  **8 mock requests** (one or more per lane, plus Needs Attention and Cancelled), 14 sources and 17 activities, so
  every screen can be demonstrated immediately.
- **To use real data:** replace the body of `LoadBriefings()` with the Dataverse version in
  [`docs/canvas-board-dataverse-loader.md`](canvas-board-dataverse-loader.md). Screens don't change.

## Put it in the environment (one-time, about 5 minutes)

1. In make.powerapps.com, open **Solutions → Briefing Note Generator → New → App → Canvas app**, name it
   **Briefing Board**, format **Tablet**, then **Create**. Don't change the display size afterwards.
2. In Studio: **Data → Add data → Dataverse**, then add **Briefing Requests**, **Source Documents** and **Briefing
   Activities**.
3. **Save**, then turn on **Settings → Updates → Coauthoring**. Keep the tab open.
4. Ask the agent (Canvas Authoring tools) to `connect` with the app ID, sync into a **scratch** folder, then push this
   folder's `.pa.yaml` files with the Dataverse loader, and compile. Or paste each screen through **Tree view → Paste
   YAML**.
5. **Save** and **Publish**, then share the app with the Briefing roles.

Source: `canvas-board/` (only `.pa.yaml` files, so `sync_canvas` works).


