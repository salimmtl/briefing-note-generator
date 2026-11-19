# Briefing Note Generator: concept validation and build plan

*Reusable Copilot Studio asset (Microsoft Copilot / GitHub Copilot harness, Dataverse, workflows, app). Draft for discussion, Nov 2026.*

---

## 1. Does the idea make sense? Yes, with conditions

### Why it's a strong shareable asset
| Signal | Evidence |
|---|---|
| **Universal, repeatable pain** | Public servants write briefing notes (BNs) for DMs and ministers constantly. Private-sector equivalents include executive briefs, account/meeting briefs and board pre-reads. The format is structured, template-driven and high-volume, which suits GenAI well. |
| **Academic validation** | ENAP / Université du Québec (*Science and Public Policy*, 2026) evaluated LLMs on policy briefing notes. GenAI is **strong on clarity, tone and structure** and **weaker on evidence integration, contextual completeness and decision justification** ([article](https://academic.oup.com/spp/advance-article/doi/10.1093/scipol/scag026/8662016); [response letter](https://academic.oup.com/spp/advance-article-abstract/doi/10.1093/scipol/scag075/8824130)). Design implications: ground every claim in the sources, keep a human reviewer, and never auto-write the "Recommendation" section. |
| **Peer governments doing it** | Governments widely use GenAI for summarization and drafting (e.g. UK i.AI *Redbox* for briefings/document summaries; [Apolitical overview](https://apolitical.co/en/pages/generative-ai-applications-in-depth)). |
| **Platform timing** | Copilot Studio (Sep–Oct 2026): the **GitHub Copilot harness** (now *Microsoft Copilot harness*) is GA. It handles reasoning-heavy, multi-step work, **natively creates and edits Word and PDF**, and supports **skills**, **hooks** (preview), **workflows and MCP as tools**, **file analysis** (preview), and **apps in Copilot Studio** (preview). It also adds Evaluations for AI nodes and automations ([harness overview](https://learn.microsoft.com/en-us/microsoft-copilot-studio/harnesses-overview), [Aug blog](https://www.microsoft.com/en-us/copilot/blog/copilot-studio/new-and-improved-github-copilot-harness-agent-skills-and-richer-context/), [Sep blog](https://www.microsoft.com/en-us/copilot/blog/copilot-studio/new-and-improved-build-apps-extend-agents-and-transform-business-processes-in-microsoft-copilot-studio/)). This asset shows **app + workflow + agent** in one solution, which matches Microsoft's current messaging. |

### Conditions for success (the asset's differentiators)
1. **Grounded and cited:** every statement traces to a source document, page or section, visible to the reviewer.
2. **Human-in-the-loop:** nothing reaches the leader without approval.
3. **Configurable, not hard-coded:** templates, style guide, glossary, classification markings and language live in Dataverse, so each customer configures them without rebuilding.
4. **Classification-aware:** check data classification first (e.g. Protected A/B in the GC). Apply Purview labels and markings to the output.
5. **Measurable:** built-in evals (Copilot Studio custom graders) plus capture of time saved and reviewer edits.

### Use-case variants (same engine, different templates)
- **Gov:** BN for Information, BN for Decision, Meeting/Event Brief (scenario note), Issue/Media Note (house card / QP card), Correspondence summary.
- **Commercial:** Executive 1-pager, Customer meeting brief, Board pre-read, Incident/Risk brief, Deal review.
- **Stretch:** "Re-brief" (update an existing note with new docs), bilingual EN/FR output, a briefing book that bundles several notes into one.

---

## 2. Target user journey

```
Requester (field)            System                                   Reviewer / Leader
─────────────────            ──────                                   ────────────────
1. Teams / M365 Copilot  ──► Request record + docs stored (Dataverse/SP)
   agent OR Request App      Status: Submitted
   - upload 1..n docs
   - recipient (leader)   ──► 2. Generation (harness worker)
   - purpose, template,         extract per doc → synthesize per template
     language, due date,        → verify grounding → draft .docx
     classification             Status: Draft ready
                          ◄── 3. Requester notified (Teams card / email)
                              4. Review in app: see draft + citations,     ──► Approver (optional
                                 edit / regenerate section / approve             manager / exec office)
                              5. On approval: final Word + PDF → SharePoint
                                 Email + Teams message prebuilt → requester
                                 + ultimate recipient                       ──► Leader receives note
```

---

## 3. Solution architecture

| # | Component | Technology | Responsibility |
|---|---|---|---|
| 1 | **Intake Agent** ("Briefing Assistant") | Copilot Studio agent, published to Teams / M365 Copilot | Conversational intake: understands "I need a decision note for the DM on X", collects fields via an Adaptive Card, accepts uploads, creates the Request, confirms the ID. Answers "status of BN-0123?". Thin and fast. |
| 2 | **Request & Review App** | Model-driven app (most portable) *or* App in Copilot Studio / Code App (richer UX) | Form-based submission, queue, side-by-side draft vs. sources, section-level regenerate, approve/return, admin config for templates and style. |
| 3 | **Dataverse data model** | Dataverse tables | System of record, audit, security roles, configuration. |
| 4 | **Briefing Writer** (generation worker) | Copilot Studio **GitHub/Microsoft Copilot harness** agent or workflow, started by a Dataverse trigger | Reads docs, applies the template **skill** + style guide, produces structured sections with citations, **natively generates the .docx**, writes results back. |
| 5 | **Skills library** | Copilot Studio Skills (one per template + shared skills) | `bn-information`, `bn-decision`, `meeting-brief`, `issue-note`, `exec-one-pager`, plus `cite-sources`, `plain-language`, `classification-marking`, `fr-ca-style`. Reusable across agents and customers. |
| 6 | **Hooks** (preview) | Harness hooks | Deterministic guardrails: session start loads template, style and glossary. A pre-tool hook blocks sending to the leader without approval. A post-run hook logs telemetry and validates citations. On error, the hook sets status to Failed and notifies. |
| 7 | **Delivery workflows** | Copilot Studio workflows / agent flows (Power Automate) | Approval (Approvals connector), PDF conversion, SharePoint filing with metadata and sensitivity label, Outlook email (prebuilt draft or send), Teams Adaptive Card to requester and recipient. |
| 8 | **Storage** | SharePoint document library (per customer env var) | `/Requests/BN-0123/sources`, `/drafts`, `/final` (.docx + .pdf). |
| 9 | **Governance & ops** | Managed Environments, DLP, Entra Agent ID, App Insights telemetry, Purview | Security, monitoring, auditability. |
| 10 | **Evaluation pack** | Copilot Studio Evaluations (custom graders) | Graders: grounding, template completeness, length, tone, "no invented recommendation". Includes a sample doc set. |

### Key design decision: how deterministic should generation be?
| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A. Harness agent end-to-end** (skills + hooks + native Word/PDF) | Least plumbing, native file creation, adapts to messy inputs, showcases the newest capabilities | Less predictable; Copilot Credit cost varies per run | **Primary path for the asset**, constrained with hooks and skills |
| **B. Deterministic workflow + prompt tools** (extract → synthesize → verify, map-reduce per doc) | Repeatable, auditable, predictable cost | More flows; Word template connector can't handle rich text | Fallback / "regulated mode" behind an env-var toggle |

Hybrid: a **workflow** owns the lifecycle (trigger, status, approval, delivery) and calls the **harness Briefing Writer as a tool** for the reasoning-heavy drafting step. You get deterministic control where it matters and agentic reasoning where it helps.

---

## 4. Dataverse data model (draft)

| Table | Key columns |
|---|---|
| **Briefing Request** | Request # (autonumber BN-####), Title, Requester (user), Ultimate Recipient (name/role/email), Purpose/Context, Template (lookup), Language (EN/FR/Both), Classification (lookup), Due date, Status (Submitted → Generating → Draft ready → In review → Approved → Delivered / Returned / Failed), Draft sections (JSON), Draft & Final file links, Reviewer, Approval outcome, Intake transcript, Template version, Skill/prompt version, Credits used, Time-to-draft |
| **Source Document** | Request (lookup), File (file column) or SharePoint URL, Type, Page count, Extracted summary/JSON, OCR required flag |
| **Note Template** | Name, Type, Language, Version, Active, Section schema (JSON: name, purpose, max words, required), Generation instructions / skill name, Word template file, Sample output |
| **Style Guide** | Org/department, tone, reading level, plain-language rules, banned phrases, formatting, acronym glossary |
| **Classification Marking** | Label, header/footer text, Purview label ID, allowed-for-AI flag |
| **Distribution List** (optional) | Recipient role → default approver(s), CC list, delivery channel preference |
| **Feedback** | Request, rating, reviewer edits %, comments (supports continuous improvement and evals) |

Security roles: **Requester** (own records), **Reviewer/Approver** (business unit), **Briefing Admin** (config tables).

---

## 5. Packaging as a "boxed" asset

- **One managed solution** (`BriefingNoteGenerator`) containing tables, app, agent(s), skills, workflows, connection references, **environment variables** (SP site/library, sender mailbox, default language, approver group, regulated-mode toggle, verify-step toggle) and security roles.
- **Seed data package** (Configuration Migration / `pac data`): 5 default templates (EN + FR), a default style guide, classification markings, and a sample document set.
- **Source control:** author agent YAML and solution in Git with GitHub Copilot and the Copilot Studio CLI (`pac`). CI with Power Platform Build Tools / GitHub Actions produces the managed solution zip and release notes.
- **Deployment guide:** prerequisites (licensing, DLP connector grouping, Managed Environment), import, connection setup, publish the agent to Teams/M365, a first-run checklist and a smoke test.
- **Demo kit:** a 5-minute scripted demo, sample docs (e.g. a public policy report and a stakeholder letter), before/after timing, and an architecture slide.
- **Per-tenant manual steps** (document them): channel publishing and Teams admin approval, event triggers re-auth, knowledge sources, sensitivity label IDs.

---

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Hallucinated or unsupported claims | Citation-required skill, verify step / post-run hook, reviewer sees sources, eval graders |
| Invented recommendations on Decision notes | Template rule: Recommendation = `[Requester to complete]` unless the sources contain one |
| Large / many / scanned docs | Store docs outside chat; map-reduce per doc; OCR for scans; size limits surfaced in the UI |
| Classified content | Classification gate at intake (block "not allowed for AI" labels); Purview labels on output; confirm data residency and model region |
| Long-running generation in chat | Always async: the chat returns BN-#### and a notification follows |
| Cost unpredictability | Log credits per request; budget per template; regulated-mode (deterministic) option |
| DLP / connector mismatches across tenants | Documented DLP prerequisites + pre-flight check flow |
| Preview features (hooks, apps, file analysis) | Feature flags via env vars; fallback paths on GA components |

---

## 7. Phased build plan

| Phase | Scope | Exit criteria |
|---|---|---|
| **0. Design (1 wk)** | Confirm templates with 1–2 pilot customers (gov + commercial); collect 3–5 real anonymized BNs per type; define section schemas; choose app UX (model-driven vs. Copilot Studio app); confirm licensing | Signed-off template schemas + sample corpus |
| **1. Foundation (1 wk)** | Dev environment + solution; Dataverse tables, security roles, env vars, connection refs; SharePoint library; seed data | Tables + seed data importable via `pac` |
| **2. Generation core (2 wks)** | Briefing Writer on the harness; 5 template skills + shared skills (citations, style, classification, FR); hooks; Word/PDF output; status write-back | A Request record produces a cited .docx draft for all 5 templates |
| **3. Intake (1 wk)** | Intake agent (Teams/M365): orchestration, Adaptive Card form, upload handling, request creation, status lookup, async notification | End-to-end from chat to draft notification |
| **4. Review & delivery (1–2 wks)** | Review app (draft vs. sources, regenerate section, approve/return); approval workflow; PDF + SharePoint filing + labels; prebuilt email + Teams card to requester and recipient | Approved note delivered to both parties |
| **5. Quality (1 wk)** | Eval sets + custom graders; telemetry dashboard (time-to-draft, edits %, credits); RAI / error handling; Teams hardening | Eval pass thresholds met; dashboard live |
| **6. Package & share (1 wk)** | Managed solution via CI, seed data, deployment guide, demo kit, test import into a clean tenant | Clean-tenant install under 1 hour |

**MVP cut (≈3–4 wks):** 2 templates (BN for Information and BN for Decision, EN only), intake agent, model-driven review app, harness generation with citations, Word/PDF to SharePoint, and an email/Teams notification with a simple approval step.

---

## 8. Open questions to settle before building
1. Primary UI: Teams agent only, or agent + app from day one? Which app type?
2. Default delivery: **send** to the leader after approval, or **prepare a draft email** for the requester to send?
3. Approval chain: single reviewer or multi-stage (manager → exec office)?
4. Bilingual: generate natively in FR, or EN then translate and review?
5. Which classification levels must be supported at launch?
6. Target pilot customers and their licensing (Copilot Credits vs. M365 Copilot users)?
