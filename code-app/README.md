# Briefing Studio (code app)

Briefing Studio is the requester and reviewer front end of the **Briefing Note Generator** accelerator. It's a
Power Apps code app (React 19, TypeScript, Vite) that reads and writes the `BriefingNoteGenerator` Dataverse tables.
The Copilot Studio workflow and the Briefing Note Writer agent do the drafting.

| Page | What it does |
|---|---|
| **My briefings** | Your requests (`brn_requesteremail` = your UPN), with search, a status filter and a "Needs your input" group |
| **New request** | Profile, template cards, subject, recipient, purpose, options and source documents. Text is extracted in the browser (PDF with `pdfjs-dist`, Word with `mammoth`, `.txt`/`.md` as text). On submit: request (Draft), then the sources (S1…Sn, text + original file in `brn_file`), then status **Submitted** and a timeline entry |
| **Request detail** | Header, status tracker, "Your input is needed" answers, the draft (bullets and [S1] citation chips), sources, verification, PDF/SharePoint links and the activity timeline. Refreshes every 15 s while the workflow is working. When the status is **In Review**, the assigned reviewer can edit the draft, request a revision or approve. Requests can be cancelled while no workflow is running |
| **Review queue** | All requests in review (or all open, or all), sortable by due date, priority or last update |
| **Overview** | KPIs and simple bar charts by status and by template |

## Rebuild and deploy

Prerequisites: Node.js 22+, PAC CLI signed in to the target environment (`pac org who`), and the
`BriefingNoteGenerator` solution already imported (tables and security roles).

```powershell
cd code-app
npm install
copy power.config.example.json power.config.json   # first time only, then:
pac code init --displayName "Briefing Studio" --environment <environment-url> --buildPath dist   # new environment only
npm run build; npm run lint
pac code push --solutionName BriefingNoteGenerator
```

`pac code push --solutionName` can report success without adding the app to the solution (no `canvasapps` row).
Check the solution. If the app is missing, run `python scripts/make_code_app_solution_aware.py <appId>` from the
repo root (it uses `.env` and the PAC CLI token cache).

To regenerate the data layer, run `pac code add-data-source -a dataverse -t <table>` for `brn_request`,
`brn_sourcedocument`, `brn_activity`, `brn_profile` and `brn_template`. All five generate without hand-written services.

**Local preview without Power Apps:** `npm run dev:mock` serves the UI on http://localhost:5199 with sample data
(`src/mock/dataverse.mock.ts`). It's only used in that mode and isn't in the build.

## Notes and limitations

- **Users need a security role:** *Briefing Requester* (own requests) or *Briefing Reviewer* (all requests). The
  review queue and overview show only the requests the user's role can read.
- **"My briefings" matches on the UPN.** `getContext()` only exposes the UPN, object ID and full name, so requests
  created elsewhere must store the requester's UPN in `brn_requesteremail`.
- **Scanned PDFs** have no text layer. The app warns, and the Writer can't read them, because there's no OCR.
- **Large text:** extracted text is capped at 1,000,000 characters per document, and files at 32 MB.
- **pdf.js worker:** bundled inline and started from a Blob URL. If the host blocks Blob workers, pdf.js falls back
  to the main thread, which is slower for large PDFs. This keeps the bundle large (about 2.4 MB, plus a 1.2 MB worker chunk).
- **File upload is best effort:** if the original file can't be attached, the extracted text is kept, and the
  request is submitted with a warning.
- **Only the assigned reviewer can review.** The review actions (edit draft, request revision, approve) appear
  only when the signed-in UPN matches `brn_revieweremail` (case-insensitive). The app re-checks this on the latest
  record before saving. Other users, including the requester, see "Waiting for review by …". The review queue lists
  every request in review that the user's role can read, but opening one follows the same rule. This check runs in
  the app; Dataverse security roles still allow any Briefing Reviewer to write the record by other means.
- **Cancel only when no workflow is running:** a request can be cancelled from Draft, Needs Info, In Review or
  Needs Attention.
- Don't publish `power.config.json` (it holds environment and app IDs). Use `power.config.example.json`.
