# Briefing Note Generator: plan

> **v0.1** (2026-11-10): first plan. Built from the concept plan (`docs/concept.md`) and the user's instruction:
> "build it in the Apps Center environment … stand-alone solution … push to GitHub as an asset … Copilot Studio
> GHCP harness, workflows rather than Power Automate flows … lean toward Option A but bring the human in for
> clarifications … one code app and one model-driven app". The user is away during the build, so the gates are
> self-approved and every decision is logged here.

## Environment and tooling

| Item | Value |
|---|---|
| Environment | the author's development environment (Dataverse, Canada region) |
| Account | the environment admin (the active PAC profile; not switched) |
| Publisher | `BriefingNoteGenerator`, prefix `brn`, choice value prefix `74380` |
| Solution | `BriefingNoteGenerator` (Briefing Note Generator) |
| Method | `pp-demo-builder` kit (`.github/skills`): schema as code, idempotent scripts, export + unpack |

## Who it's for

Field staff (analysts, policy officers, account managers) who prepare **briefing notes** for a leader (a minister,
deputy minister, executive, board). It is demonstrated to sellers who take it to **public-sector and private-sector**
customers, so the same engine serves both, through *Briefing Profiles* (style, glossary, classification, SharePoint
target) and *Note Templates* (sections and writing rules).

## Architecture (Option A: an agent does the reasoning, a human is brought in when needed)

```
 Requester ──► Briefing Studio (code app)  ─┐            ┌─► Briefing Assistant (GHCP agent, Teams / M365 Copilot)
               upload docs, pick template,   │            │   chat intake: upload files, answer the questions,
               recipient, language…          ▼            ▼   check status, answer clarifications
                                   Briefing Request (BN-#####) + Source Documents (Dataverse)
                                              │  status = Submitted | Info Provided | Revision Requested
                                              ▼
 BN 1 - Draft Briefing Note (Copilot Studio workflow)
   claim (Drafting) ─► Briefing Note Writer (GHCP agent, agent node) reads request, sources, template, profile
        │                 └─ writes title, key message, sections (JSON, cited [S1]), sources, verification notes
        ├─ outcome = needs_info ─► status Needs Info, questions saved ─► Teams + email to requester  ◄── HUMAN
        └─ outcome = draft     ─► render DRAFT PDF (HTML → OneDrive convert → SharePoint /Drafts)
                                  status In Review ─► Teams + email to reviewer and requester        ◄── HUMAN
 Reviewer (Studio / Hub) edits sections, then Approve, or Request revision (comments → back to the Writer)
                                              │  status = Approved
                                              ▼
 BN 2 - Deliver Briefing Note (Copilot Studio workflow)
   render FINAL PDF with classification marking ─► SharePoint /Final ─► email (PDF attached) to requester
   + ultimate recipient (per delivery mode) ─► Teams message ─► status Delivered ─► activity log
```

**Why this split.** The GHCP Writer reasons over messy, multi-document input and decides whether it has enough to
write (Option A). Workflows own what must happen every time: status, rendering, filing, sending, logging, failure
handling. Lessons from earlier builds that shaped it:
- GHCP agents can't be called from Power Automate cloud flows; **Copilot Studio workflows** with the **agent node**
  (`shared_agentnode` / `InvokeAgent_V2`, agent addressed by schema name) can.
- Files created by GHCP agents don't come back to workflows, so the Writer writes **structured content to Dataverse**
  and the workflow renders the PDF deterministically (same look every time, no extra credits).
- The Writer runs unattended: it never chats. Human input comes through **status + questions on the record**,
  answered in either app or through the intake agent.

## Data model (prefix `brn`)

| Table | Purpose |
|---|---|
| `brn_profile` Briefing Profile | Organization configuration: sector, style guide, glossary, classification guidance, default reviewer, SharePoint site/library/folder, accent colour, footer |
| `brn_template` Note Template | Note type, when to use, section list with guidance, writing rules, length |
| `brn_request` Briefing Request | BN-#####: requester, recipient, purpose, template, language, classification, due date, status, clarification Q&A, reviewer comments, draft (title, key message, sections JSON, sources, verification notes), PDF links, timestamps |
| `brn_sourcedocument` Source Document | File (file column), extracted text, label (S1…), type, page count, per-document summary |
| `brn_activity` Briefing Activity | Timeline: submitted, drafting, clarification requested/provided, draft ready, revision, approved, delivered, failed (with duration and workflow run) |

Source of truth: `scripts/schema_def.py`.

## Components

| Component | Built with |
|---|---|
| Publisher, solution, schema, roles, env vars | `create_schema.py`, `create_roles.py` (Web API) |
| Seed profiles (public + private sector) and 5 templates | `seed_data.py` |
| SharePoint library and connections | `provision_m365.py`, `ensure_connections.py`, `create_connrefs.py` |
| Briefing Note Writer + Briefing Assistant (GHCP) | `build_agents.py` → `pac copilot init / push / publish` |
| BN 1 Draft, BN 2 Deliver (Copilot Studio workflows) | `build_workflows.py` (Web API, `modernflowtype` 1) |
| Model-driven app *Briefing Notes Hub* | `create_mda.py` |
| Code app *Briefing Studio* | React + Vite + `pac code` |
| Demo documents | `samples/` (generated by `scripts/generate_samples.py`) |

## Security roles

- **Briefing Requester**: create/read/write own requests and source documents; read profiles, templates, activity.
- **Briefing Reviewer**: read/write all requests and documents; read config.
- **Briefing Admin**: full on all tables.

## Risks and limitations (accepted for the demo)

- Copilot Credits: every Writer run and every intake conversation consumes credits (GHCP). Cap them.
- Source text is extracted in the code app (PDF, Word, text) or by the intake agent from chat attachments. Scanned
  PDFs without a text layer aren't supported (no OCR).
- The Writer runs as the workflow's connection owner; the Dataverse MCP tool is restricted to `brn_` tables by
  instructions and an allowed-tool list, while the connection owner's role is the real boundary.
- Agent-created Word files aren't used (see above); the deliverable is a PDF, plus the editable sections in the apps.

## Changelog

- v0.1: initial plan.
- v0.2 (2026-11-10, after live runs): workflows and agents verified end to end (draft, clarification round, revision, delivery). Fixes: the template name comes from the request's formatted lookup value; bullets separated by blank lines are collapsed in the PDF; the auto-number seed retries until the column metadata is ready; `pac copilot pull` crashed (FormatException) so agents are re-synced with `push_agents.ps1 -Fresh`; `pac copilot init` container solutions and the extra `brn` publisher were deleted; environment variable values are kept out of the solution so the packages carry no tenant URLs. The SharePoint target is a folder on an existing site (set per profile) because Graph provisioning needed an interactive sign-in.
