import { useCallback, useEffect, useState } from 'react'
import {
  approveRequest,
  cancelRequest,
  loadRequestBundle,
  requestRevision,
  saveDraftEdits,
  sendClarificationAnswers,
  submitDraft,
  type Reference,
  type RequestBundle,
} from '../dataverse'
import {
  ACTIVE_STATUSES,
  ACTIVITY_TYPE_LABELS,
  ACTOR_LABELS,
  ActivityType,
  CANCELLABLE_STATUSES,
  CLASSIFICATION_LABELS,
  CLOSED_STATUSES,
  CONFIDENCE_LABELS,
  DELIVERY_MODE_LABELS,
  DOCUMENT_TYPE_LABELS,
  EXTRACTION_STATUS_LABELS,
  ExtractionStatus,
  LANGUAGE_LABELS,
  RequestStatus,
  STATUS_LABELS,
  isAssignedReviewer,
  label,
  type Activity,
  type BriefingRequest,
  type CurrentUser,
} from '../domain'
import { errorMessage, formatDateTime, formatNumber } from '../format'
import { IconAlert, IconBack, IconLink, IconRefresh } from '../icons'
import { DraftEditor, type DraftEdits } from './DraftEditor'
import { DraftText, DueDate, Loading, Message, PriorityPill, StatusPill } from './Shared'

type StepState = 'done' | 'active' | 'todo' | 'failed'

function trackerSteps(request: BriefingRequest, activities: Activity[]): { label: string; state: StepState; at?: string | null }[] {
  const s = request.status
  const neededInfo =
    s === RequestStatus.NeedsInfo ||
    s === RequestStatus.InfoProvided ||
    request.clarificationRounds > 0 ||
    request.clarificationQuestions.trim() !== '' ||
    activities.some((a) => a.activityType === ActivityType.ClarificationRequested)
  const steps: { key: string; label: string; at?: string | null }[] = [
    { key: 'submitted', label: 'Submitted', at: request.submittedOn },
    { key: 'drafting', label: 'Drafting' },
    ...(neededInfo ? [{ key: 'needsinfo', label: 'Needs Info' }] : []),
    { key: 'review', label: 'In Review', at: request.draftedOn },
    { key: 'approved', label: 'Approved', at: request.approvedOn },
    { key: 'delivered', label: 'Delivered', at: request.deliveredOn },
  ]
  const indexOf = (key: string) => steps.findIndex((step) => step.key === key)
  let current: number
  switch (s) {
    case RequestStatus.Draft:
      current = -1
      break
    case RequestStatus.Submitted:
      current = indexOf('submitted') + 1
      break
    case RequestStatus.Drafting:
      current = indexOf('drafting')
      break
    case RequestStatus.NeedsInfo:
    case RequestStatus.InfoProvided:
      current = indexOf('needsinfo')
      break
    case RequestStatus.RevisionRequested:
    case RequestStatus.InReview:
      current = indexOf('review')
      break
    case RequestStatus.Approved:
      current = indexOf('approved') + 1
      break
    case RequestStatus.Delivered:
      current = steps.length
      break
    default: {
      // Cancelled or Needs Attention: highlight the step after the last one that was reached.
      const reached = request.approvedOn
        ? indexOf('approved')
        : request.draftedOn
          ? indexOf('review')
          : request.submittedOn
            ? indexOf('submitted')
            : -1
      return steps.map((step, i) => ({
        label: step.label,
        at: step.at,
        state: i <= reached ? 'done' : i === reached + 1 ? 'failed' : 'todo',
      }))
    }
  }
  return steps.map((step, i) => ({
    label: step.label,
    at: step.at,
    state: i < current ? 'done' : i === current ? 'active' : 'todo',
  }))
}

export function RequestDetailPage({
  requestId,
  refreshToken,
  user,
  reference,
  back,
  backLabel,
  initialWarnings,
}: {
  requestId: string
  refreshToken: number
  user: CurrentUser
  reference: Reference
  back: () => void
  backLabel: string
  initialWarnings: string[]
}) {
  const [bundle, setBundle] = useState<RequestBundle | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [lastLoaded, setLastLoaded] = useState<Date | null>(null)
  const [warnings, setWarnings] = useState<string[]>(initialWarnings)
  const [notice, setNotice] = useState<string | null>(null)

  const [answers, setAnswers] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const [editing, setEditing] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [revisionOpen, setRevisionOpen] = useState(false)
  const [revisionComments, setRevisionComments] = useState('')
  const [approveConfirm, setApproveConfirm] = useState(false)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [cancelReason, setCancelReason] = useState('')

  const load = useCallback(async () => {
    try {
      const next = await loadRequestBundle(requestId, reference)
      setBundle(next)
      setLoadError(null)
      setLastLoaded(new Date())
    } catch (err) {
      setLoadError(errorMessage(err))
    }
  }, [requestId, reference])

  useEffect(() => {
    void load()
  }, [load, refreshToken])

  const status = bundle?.request.status
  const polling = status !== undefined && ACTIVE_STATUSES.includes(status) && !editing
  useEffect(() => {
    if (!polling) return undefined
    const timer = window.setInterval(() => void load(), 15000)
    return () => window.clearInterval(timer)
  }, [polling, load])

  async function run(name: string, action: () => Promise<string | null>, success: string, after?: () => void) {
    setBusy(name)
    setActionError(null)
    setNotice(null)
    try {
      const warning = await action()
      after?.()
      setNotice(success)
      if (warning) setWarnings((previous) => [...previous, warning])
    } catch (err) {
      setActionError(errorMessage(err))
    } finally {
      // Always show the real server state, also after a failure (the change may have partly saved).
      await load()
      setBusy(null)
    }
  }

  if (!bundle) {
    return (
      <div className="stack">
        <button type="button" className="btn backBtn" onClick={back}>
          <IconBack size={16} /> {backLabel}
        </button>
        {loadError ? <Message kind="error">{loadError}</Message> : <Loading text="Loading the briefing request…" />}
      </div>
    )
  }

  const { request, sources, activities } = bundle
  const closed = CLOSED_STATUSES.includes(request.status)
  const inReview = request.status === RequestStatus.InReview
  const isReviewer = isAssignedReviewer(request.reviewerEmail, user.upn)
  const canCancel = CANCELLABLE_STATUSES.includes(request.status)
  const hasDraft = Boolean(request.noteTitle || request.keyMessage || request.draftSections.length)
  const steps = trackerSteps(request, activities)

  async function saveEdits(edits: DraftEdits) {
    setBusy('save')
    setEditError(null)
    try {
      const warning = await saveDraftEdits(request.id, edits.noteTitle, edits.keyMessage, edits.sections, user)
      setEditing(false)
      setNotice('Draft saved.')
      if (warning) setWarnings((previous) => [...previous, warning])
      await load()
    } catch (err) {
      setEditError(errorMessage(err))
      void load()
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="stack">
      <div className="toolbar">
        <button type="button" className="btn backBtn" onClick={back}>
          <IconBack size={16} /> {backLabel}
        </button>
        <span className="muted small inline">
          {polling ? <span className="pulse" aria-hidden="true" /> : null}
          {polling ? 'Auto-refreshing every 15 s · ' : ''}
          {lastLoaded ? `Updated ${lastLoaded.toLocaleTimeString()}` : ''}
          <button type="button" className="iconBtn" onClick={() => void load()} title="Refresh" aria-label="Refresh">
            <IconRefresh size={16} />
          </button>
        </span>
      </div>

      <section className="panel detailHeader">
        <div className="detailHeader__top">
          <div className="detailHeader__title">
            <p className="eyebrow">{request.number || 'Briefing request'}</p>
            <h2>{request.subject || '(no subject)'}</h2>
          </div>
          <div className="inline">
            <StatusPill status={request.status} />
            <PriorityPill priority={request.priority} />
          </div>
        </div>
        <dl className="meta">
          <div>
            <dt>Recipient</dt>
            <dd>
              {request.recipientName || '—'}
              {request.recipientTitle ? <span className="muted"> · {request.recipientTitle}</span> : null}
            </dd>
          </div>
          <div>
            <dt>Template</dt>
            <dd>{request.templateName || '—'}</dd>
          </div>
          <div>
            <dt>Language</dt>
            <dd>{label(LANGUAGE_LABELS, request.language, '—')}</dd>
          </div>
          <div>
            <dt>Classification</dt>
            <dd>{label(CLASSIFICATION_LABELS, request.classification, '—')}</dd>
          </div>
          <div>
            <dt>Due</dt>
            <dd>
              <DueDate value={request.dueDate} closed={closed} />
            </dd>
          </div>
          <div>
            <dt>Requester</dt>
            <dd className="truncate" title={request.requesterEmail}>
              {request.requesterName || request.requesterEmail || '—'}
            </dd>
          </div>
          <div>
            <dt>Reviewer</dt>
            <dd className="truncate">{request.reviewerEmail || '—'}</dd>
          </div>
          <div>
            <dt>Delivery</dt>
            <dd>{label(DELIVERY_MODE_LABELS, request.deliveryMode, '—')}</dd>
          </div>
        </dl>
        <ol className="tracker" aria-label="Progress">
          {steps.map((step) => (
            <li key={step.label} className={`tracker__step ${step.state}`}>
              <span className="tracker__dot" aria-hidden="true" />
              <b>{step.label}</b>
              <small>
                {step.state === 'active'
                  ? label(STATUS_LABELS, request.status) === step.label
                    ? 'Current step'
                    : label(STATUS_LABELS, request.status)
                  : step.state === 'failed'
                    ? label(STATUS_LABELS, request.status, 'Stopped')
                    : step.at
                      ? formatDateTime(step.at)
                      : step.state === 'done'
                        ? 'Done'
                        : ''}
              </small>
            </li>
          ))}
        </ol>
        {canCancel ? (
          <div className="detailHeader__actions">
            {request.status === RequestStatus.Draft ? (
              <button
                type="button"
                className="btn primary"
                disabled={busy !== null}
                onClick={() => void run('submit', () => submitDraft(request.id, user, sources.length), 'Request submitted.')}
              >
                {busy === 'submit' ? 'Submitting…' : 'Submit request'}
              </button>
            ) : null}
            <button type="button" className="btn outline dangerText" disabled={busy !== null} onClick={() => setCancelOpen((v) => !v)}>
              Cancel request
            </button>
          </div>
        ) : null}
        {cancelOpen && canCancel ? (
          <div className="confirmBox">
            <div className="field">
              <label htmlFor="cancel-reason">Reason for cancelling (optional)</label>
              <input id="cancel-reason" value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} disabled={busy !== null} />
            </div>
            <div className="inline">
              <button type="button" className="btn" onClick={() => setCancelOpen(false)} disabled={busy !== null}>
                Keep request
              </button>
              <button
                type="button"
                className="btn dangerFill"
                disabled={busy !== null}
                onClick={() =>
                  void run('cancel', () => cancelRequest(request, user, cancelReason), 'Request cancelled.', () => {
                    setCancelOpen(false)
                    setCancelReason('')
                  })
                }
              >
                {busy === 'cancel' ? 'Cancelling…' : 'Confirm cancel'}
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {warnings.length ? (
        <Message kind="warning">
          <b>Please note</b>
          <ul>
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
          <button type="button" className="linkBtn" onClick={() => setWarnings([])}>
            Dismiss
          </button>
        </Message>
      ) : null}
      {loadError ? <Message kind="error">Refresh failed: {loadError}</Message> : null}
      {notice ? <Message kind="success">{notice}</Message> : null}
      {actionError ? <Message kind="error">{actionError}</Message> : null}
      {request.status === RequestStatus.NeedsAttention ? (
        <Message kind="error">
          <b>The workflow needs attention.</b> {request.lastError || 'A step failed. An administrator has been notified.'}
        </Message>
      ) : null}

      {request.status === RequestStatus.NeedsInfo ? (
        <section className="panel inputNeeded" aria-labelledby="input-heading">
          <h3 id="input-heading">
            <IconAlert size={18} /> Your input is needed
          </h3>
          <p className="muted">The Briefing Note Writer needs more information before it can finish the draft.</p>
          <div className="questions">
            <DraftText text={request.clarificationQuestions || 'No questions were recorded.'} />
          </div>
          <div className="field">
            <label htmlFor="answers">Your answers</label>
            <textarea
              id="answers"
              rows={6}
              value={answers}
              onChange={(e) => setAnswers(e.target.value)}
              placeholder="Answer each question. Say so if something is unknown."
              disabled={busy !== null}
            />
          </div>
          <div className="inline end">
            <button
              type="button"
              className="btn primary"
              disabled={busy !== null || !answers.trim()}
              onClick={() =>
                void run('answers', () => sendClarificationAnswers(request.id, answers, user), 'Answers sent. The Writer is updating the draft.', () =>
                  setAnswers(''),
                )
              }
            >
              {busy === 'answers' ? 'Sending…' : 'Send answers'}
            </button>
          </div>
        </section>
      ) : null}

      {[RequestStatus.Submitted, RequestStatus.Drafting, RequestStatus.InfoProvided, RequestStatus.RevisionRequested].includes(
        request.status as never,
      ) ? (
        <Message kind="info">
          <span className="inline">
            <span className="miniSpin" /> The Briefing Note Writer is working on this request. This page refreshes automatically.
          </span>
        </Message>
      ) : null}

      {inReview && !isReviewer ? (
        <Message kind="info">
          {request.reviewerEmail.trim()
            ? `Waiting for review by ${request.reviewerEmail.trim()}.`
            : 'Waiting for review. No reviewer is assigned to this request.'}
        </Message>
      ) : null}

      {inReview && isReviewer ? (
        <section className="panel reviewPanel" aria-labelledby="review-heading">
          <div className="toolbar">
            <div>
              <h3 id="review-heading">Review</h3>
              <p className="muted small">Edit the draft if needed, then approve it or send it back with comments.</p>
            </div>
            <div className="inline">
              <button
                type="button"
                className="btn outline"
                disabled={busy !== null || editing || request.draftSectionsError !== null}
                title={request.draftSectionsError ? 'The stored sections could not be read, so editing would overwrite them.' : undefined}
                onClick={() => setEditing(true)}
              >
                Edit draft
              </button>
              <button
                type="button"
                className="btn outline"
                disabled={busy !== null || editing}
                onClick={() => {
                  setRevisionOpen((v) => !v)
                  setApproveConfirm(false)
                }}
              >
                Request revision
              </button>
              <button
                type="button"
                className="btn primary"
                disabled={busy !== null || editing}
                onClick={() => {
                  setApproveConfirm((v) => !v)
                  setRevisionOpen(false)
                }}
              >
                Approve
              </button>
            </div>
          </div>
          {revisionOpen ? (
            <div className="confirmBox">
              <div className="field">
                <label htmlFor="revision">
                  Comments for the Writer <span className="req">*</span>
                </label>
                <textarea
                  id="revision"
                  value={revisionComments}
                  onChange={(e) => setRevisionComments(e.target.value)}
                  placeholder="What should change? Be specific: sections, tone, facts to check…"
                  maxLength={10000}
                  disabled={busy !== null}
                />
              </div>
              <div className="inline end">
                <button type="button" className="btn" onClick={() => setRevisionOpen(false)} disabled={busy !== null}>
                  Close
                </button>
                <button
                  type="button"
                  className="btn primary"
                  disabled={busy !== null || !revisionComments.trim()}
                  onClick={() =>
                    void run('revision', () => requestRevision(request.id, revisionComments, user), 'Revision requested.', () => {
                      setRevisionOpen(false)
                      setRevisionComments('')
                    })
                  }
                >
                  {busy === 'revision' ? 'Sending…' : 'Send for revision'}
                </button>
              </div>
            </div>
          ) : null}
          {approveConfirm ? (
            <div className="confirmBox">
              <p>
                Approve this draft as <b>{user.upn}</b>? The final PDF is then produced and delivered
                {request.deliveryMode !== null ? ` (${label(DELIVERY_MODE_LABELS, request.deliveryMode).toLowerCase()})` : ''}.
              </p>
              <div className="inline end">
                <button type="button" className="btn" onClick={() => setApproveConfirm(false)} disabled={busy !== null}>
                  Not yet
                </button>
                <button
                  type="button"
                  className="btn primary"
                  disabled={busy !== null}
                  onClick={() =>
                    void run('approve', () => approveRequest(request.id, user), 'Approved. The final note is being delivered.', () =>
                      setApproveConfirm(false),
                    )
                  }
                >
                  {busy === 'approve' ? 'Approving…' : 'Confirm approval'}
                </button>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="detailGrid">
        <div className="stack">
          <section className="panel draftPanel" aria-labelledby="draft-heading">
            <div className="toolbar">
              <h3 id="draft-heading">Draft</h3>
              <span className="muted small">
                {request.draftVersion ? `Version ${request.draftVersion} · ` : ''}
                {request.wordCount ? `${request.wordCount.toLocaleString()} words` : ''}
                {request.draftedOn ? ` · drafted ${formatDateTime(request.draftedOn)}` : ''}
              </span>
            </div>
            {editing ? (
              <DraftEditor
                initial={{ noteTitle: request.noteTitle, keyMessage: request.keyMessage, sections: request.draftSections }}
                saving={busy === 'save'}
                error={editError}
                onSave={(edits) => void saveEdits(edits)}
                onCancel={() => {
                  setEditing(false)
                  setEditError(null)
                }}
              />
            ) : hasDraft ? (
              <article className="note">
                {request.noteTitle ? <h1 className="note__title">{request.noteTitle}</h1> : null}
                {request.keyMessage ? (
                  <div className="keyMessage">
                    <span className="keyMessage__label">Key message</span>
                    <DraftText text={request.keyMessage} />
                  </div>
                ) : null}
                {request.draftSectionsError ? <Message kind="error">{request.draftSectionsError}</Message> : null}
                {request.draftSections.map((section, index) => (
                  <section key={index} className="note__section">
                    {section.heading ? <h2>{section.heading}</h2> : null}
                    <DraftText text={section.body} />
                  </section>
                ))}
              </article>
            ) : (
              <div className="empty">No draft yet. It appears here when the Briefing Note Writer finishes.</div>
            )}
          </section>

          {request.reviewerComments ? (
            <section className="panel">
              <h3>Reviewer comments</h3>
              <p className="richText">{request.reviewerComments}</p>
            </section>
          ) : null}

          {request.clarificationAnswers ? (
            <section className="panel">
              <h3>Clarifications</h3>
              {request.clarificationQuestions && request.status !== RequestStatus.NeedsInfo ? (
                <>
                  <p className="fieldLabel">Last questions</p>
                  <p className="richText muted">{request.clarificationQuestions}</p>
                </>
              ) : null}
              <p className="fieldLabel">Answers</p>
              <p className="richText">{request.clarificationAnswers}</p>
            </section>
          ) : null}

          <section className="panel">
            <h3>Request</h3>
            <p className="fieldLabel">Purpose</p>
            <p className="richText">{request.purpose || '—'}</p>
            {request.additionalContext ? (
              <>
                <p className="fieldLabel">Additional context</p>
                <p className="richText">{request.additionalContext}</p>
              </>
            ) : null}
          </section>
        </div>

        <div className="stack">
          <section className="panel">
            <h3>Documents</h3>
            <div className="linkList">
              <DocLink url={request.draftPdfUrl} text="Draft PDF" />
              <DocLink url={request.finalPdfUrl} text="Final PDF" />
              <DocLink url={request.sharePointFolderUrl} text="SharePoint folder" />
            </div>
            {request.approvedBy ? (
              <p className="muted small">
                Approved by {request.approvedBy} on {formatDateTime(request.approvedOn)}
              </p>
            ) : null}
            {request.deliveredOn ? <p className="muted small">Delivered {formatDateTime(request.deliveredOn)}</p> : null}
          </section>

          <section className="panel">
            <div className="toolbar">
              <h3>Verification</h3>
              {request.confidence !== null ? (
                <span className={`pill confidence-${label(CONFIDENCE_LABELS, request.confidence).toLowerCase()}`}>
                  {label(CONFIDENCE_LABELS, request.confidence)} confidence
                </span>
              ) : null}
            </div>
            {request.verificationNotes ? (
              <DraftText text={request.verificationNotes} />
            ) : (
              <p className="muted">No verification notes yet.</p>
            )}
            {request.sourcesUsed ? (
              <>
                <p className="fieldLabel">Sources used</p>
                <DraftText text={request.sourcesUsed} />
              </>
            ) : null}
          </section>

          <section className="panel">
            <h3>
              Sources <span className="count">{sources.length}</span>
            </h3>
            {sources.length === 0 ? (
              <p className="muted">No source documents.</p>
            ) : (
              <ul className="sourceList">
                {sources.map((s) => (
                  <li key={s.id}>
                    <div className="sourceList__head">
                      <span className="cite">{s.label || '?'}</span>
                      <span className="truncate" title={s.name}>
                        {s.name}
                      </span>
                    </div>
                    <div className="muted small">
                      {label(DOCUMENT_TYPE_LABELS, s.documentType, 'Document')} · {formatNumber(s.characterCount)} chars
                      {s.pageCount ? ` · ${s.pageCount} pages` : ''}
                      {s.extractionStatus !== null && s.extractionStatus !== ExtractionStatus.Extracted ? (
                        <span className="warnText"> · {label(EXTRACTION_STATUS_LABELS, s.extractionStatus)}</span>
                      ) : null}
                      {!s.hasFile ? ' · text only' : ''}
                    </div>
                    {s.summary ? <p className="small">{s.summary}</p> : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel">
            <h3>Activity</h3>
            {activities.length === 0 ? (
              <p className="muted">No activity yet.</p>
            ) : (
              <ol className="timeline">
                {activities.map((a) => (
                  <li key={a.id} className={`timelineItem ${a.activityType === ActivityType.Failed ? 'failed' : ''}`}>
                    <div className="timelineItem__head">
                      <b>{a.name || label(ACTIVITY_TYPE_LABELS, a.activityType, 'Activity')}</b>
                    </div>
                    <div className="muted small">
                      {label(ACTOR_LABELS, a.actor, 'System')} · {label(ACTIVITY_TYPE_LABELS, a.activityType, '')} ·{' '}
                      {formatDateTime(a.startedOn ?? a.createdOn)}
                      {a.durationSeconds ? ` · ${formatDuration(a.durationSeconds)}` : ''}
                    </div>
                    {a.details ? <p className="small richText clamp">{a.details}</p> : null}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

function DocLink({ url, text }: { url: string; text: string }) {
  if (!url) {
    return (
      <span className="docLink disabled">
        <IconLink size={16} /> {text} <small>not available yet</small>
      </span>
    )
  }
  return (
    <a className="docLink" href={url} target="_blank" rel="noreferrer">
      <IconLink size={16} /> {text}
    </a>
  )
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.round(seconds / 60)
  return minutes < 60 ? `${minutes} min` : `${(minutes / 60).toFixed(1)} h`
}
