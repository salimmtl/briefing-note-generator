import { useCallback, useEffect, useRef, useState } from 'react'
import { SubmitError, submitNewRequest, type Reference } from '../dataverse'
import {
  ACCEPTED_EXTENSIONS,
  ACCEPTED_FILE_TYPES,
  CLASSIFICATION_LABELS,
  Classification,
  DELIVERY_MODE_LABELS,
  DOCUMENT_TYPE_LABELS,
  DeliveryMode,
  DocumentType,
  LANGUAGE_LABELS,
  Language,
  MAX_EXTRACTED_CHARS,
  MAX_FILE_BYTES,
  NOTE_TYPE_LABELS,
  PRIORITY_LABELS,
  Priority,
  label,
  localDateOnly,
  options,
  type CurrentUser,
  type NewRequestInput,
  type PendingSource,
} from '../domain'
import { extractText } from '../extract'
import { errorMessage, formatNumber } from '../format'
import { IconTrash, IconUpload } from '../icons'
import { Message, PageHeader } from './Shared'

function guessType(fileName: string): number {
  const name = fileName.toLowerCase()
  if (/minutes|meeting|notes/.test(name)) return DocumentType.MeetingNotes
  if (/memo|brief/.test(name)) return DocumentType.Memo
  if (/email|letter|correspondence/.test(name)) return DocumentType.Email
  if (/deck|presentation|slides/.test(name)) return DocumentType.Presentation
  if (/report|study|review|audit|evaluation/.test(name)) return DocumentType.Report
  return DocumentType.Other
}

function initialInput(reference: Reference): NewRequestInput {
  const profile = reference.profiles[0]
  return {
    profileId: profile?.id ?? null,
    templateId: null,
    subject: '',
    recipientName: '',
    recipientTitle: '',
    recipientEmail: '',
    reviewerEmail: profile?.defaultReviewerEmail ?? '',
    purpose: '',
    additionalContext: '',
    language: profile?.defaultLanguage ?? Language.English,
    classification: Classification.Unclassified,
    priority: Priority.Routine,
    dueDate: localDateOnly(7),
    deliveryMode: DeliveryMode.RequesterAndRecipient,
  }
}

export function NewRequestPage({
  user,
  reference,
  onSubmitted,
  cancel,
}: {
  user: CurrentUser
  reference: Reference
  onSubmitted: (requestId: string, warnings: string[]) => void
  cancel: () => void
}) {
  const [input, setInput] = useState<NewRequestInput>(() => initialInput(reference))
  const [sources, setSources] = useState<PendingSource[]>([])
  const [fileError, setFileError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [createdId, setCreatedId] = useState<string | null>(null)
  const [touched, setTouched] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const reviewerEdited = useRef(false)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const set = <K extends keyof NewRequestInput>(key: K, value: NewRequestInput[K]) =>
    setInput((previous) => ({ ...previous, [key]: value }))

  const selectProfile = (profileId: string) => {
    const profile = reference.profiles.find((p) => p.id === profileId)
    setInput((previous) => ({
      ...previous,
      profileId: profileId || null,
      reviewerEmail: reviewerEdited.current ? previous.reviewerEmail : (profile?.defaultReviewerEmail ?? ''),
      language: profile?.defaultLanguage ?? previous.language,
    }))
  }

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const rejected: string[] = []
    const added: PendingSource[] = []
    for (const file of Array.from(incoming)) {
      const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
      if (!(ACCEPTED_EXTENSIONS as readonly string[]).includes(extension)) {
        rejected.push(`${file.name}: only PDF, Word (.docx), .txt and .md files are supported`)
        continue
      }
      if (file.size > MAX_FILE_BYTES) {
        rejected.push(`${file.name}: larger than 32 MB`)
        continue
      }
      added.push({
        key: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
        file,
        documentType: guessType(file.name),
        state: 'extracting',
        text: '',
        pageCount: null,
        characterCount: 0,
        warning: null,
        error: null,
      })
    }
    setFileError(rejected.length ? rejected.join('; ') : null)
    if (!added.length) return
    setSources((previous) => [...previous, ...added])
    for (const source of added) {
      void extractText(source.file).then((result) => {
        if (!mounted.current) return
        setSources((previous) =>
          previous.map((s) =>
            s.key === source.key
              ? {
                  ...s,
                  state: result.state,
                  text: result.text,
                  pageCount: result.pageCount,
                  characterCount: result.text.length,
                  warning:
                    result.warning ??
                    (result.text.length > MAX_EXTRACTED_CHARS
                      ? `Long document: only the first ${MAX_EXTRACTED_CHARS.toLocaleString()} characters will be saved.`
                      : null),
                  error: result.error,
                }
              : s,
          ),
        )
      })
    }
  }, [])

  const extracting = sources.some((s) => s.state === 'extracting')
  const missing: string[] = []
  if (!input.subject.trim()) missing.push('subject')
  if (!input.purpose.trim()) missing.push('purpose')
  if (reference.templates.length > 0 && !input.templateId) missing.push('template')
  const emailInvalid = [input.recipientEmail, input.reviewerEmail].some((e) => e.trim() && !/^\S+@\S+\.\S+$/.test(e.trim()))

  async function submit() {
    setTouched(true)
    setError(null)
    if (createdId || missing.length || emailInvalid || extracting) return
    setSubmitting(true)
    try {
      const result = await submitNewRequest(input, sources, user, (message) => setProgress(message))
      onSubmitted(result.requestId, result.warnings)
    } catch (err) {
      // Once the request exists, never create a second one: offer to open it instead.
      if (err instanceof SubmitError) setCreatedId(err.requestId)
      setError(errorMessage(err))
      setSubmitting(false)
      setProgress(null)
    }
  }

  const totalChars = sources.reduce((sum, s) => sum + Math.min(s.characterCount, MAX_EXTRACTED_CHARS), 0)

  return (
    <div className="stack">
      <PageHeader
        eyebrow="New request"
        title="Request a briefing note"
        subtitle="Describe what the leader needs, add your source documents, and the Briefing Note Writer prepares a draft for review."
      />

      <section className="panel formSection">
        <h3>
          <span className="stepNo">1</span> Organization and note type
        </h3>
        <div className="grid2">
          <div className="field">
            <label htmlFor="profile">Briefing profile</label>
            <select id="profile" value={input.profileId ?? ''} onChange={(e) => selectProfile(e.target.value)} disabled={submitting}>
              {reference.profiles.length === 0 ? <option value="">No active profiles</option> : null}
              {reference.profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.code ? ` (${p.code})` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="fieldLabel">
          Template <span className="req">*</span>
        </p>
        {reference.templates.length === 0 ? (
          <Message kind="warning">No active note templates are configured. The Writer will use its default format.</Message>
        ) : (
          <div className="templateGrid" role="radiogroup" aria-label="Note template">
            {reference.templates.map((t) => (
              <button
                key={t.id}
                type="button"
                role="radio"
                aria-checked={input.templateId === t.id}
                className={input.templateId === t.id ? 'templateCard selected' : 'templateCard'}
                onClick={() => set('templateId', t.id)}
                disabled={submitting}
              >
                {label(NOTE_TYPE_LABELS, t.noteType) && label(NOTE_TYPE_LABELS, t.noteType) !== t.name ? (
                  <span className="templateCard__type">{label(NOTE_TYPE_LABELS, t.noteType)}</span>
                ) : null}
                <strong>{t.name}</strong>
                <span className="templateCard__when">{t.whenToUse || 'No guidance provided.'}</span>
                {t.maxWords ? <span className="muted small">Up to {t.maxWords.toLocaleString()} words</span> : null}
              </button>
            ))}
          </div>
        )}
        {touched && missing.includes('template') ? <p className="fieldError">Choose a template.</p> : null}
      </section>

      <section className="panel formSection">
        <h3>
          <span className="stepNo">2</span> What is the note about?
        </h3>
        <div className="field">
          <label htmlFor="subject">
            Subject <span className="req">*</span>
          </label>
          <input
            id="subject"
            maxLength={300}
            value={input.subject}
            onChange={(e) => set('subject', e.target.value)}
            placeholder="e.g. Funding options for the regional transit expansion"
            disabled={submitting}
          />
          {touched && missing.includes('subject') ? <p className="fieldError">Enter a subject.</p> : null}
        </div>
        <div className="field">
          <label htmlFor="purpose">
            Purpose <span className="req">*</span>
          </label>
          <textarea
            id="purpose"
            maxLength={4000}
            value={input.purpose}
            onChange={(e) => set('purpose', e.target.value)}
            placeholder="Why does the leader need this note, and what should it help them decide or do?"
            disabled={submitting}
          />
          {touched && missing.includes('purpose') ? <p className="fieldError">Describe the purpose.</p> : null}
        </div>
        <div className="field">
          <label htmlFor="context">Additional context</label>
          <textarea
            id="context"
            maxLength={10000}
            value={input.additionalContext}
            onChange={(e) => set('additionalContext', e.target.value)}
            placeholder="Background, sensitivities, points to emphasize or avoid…"
            disabled={submitting}
          />
        </div>
        <div className="grid4">
          <div className="field">
            <label htmlFor="language">Language</label>
            <select id="language" value={input.language} onChange={(e) => set('language', Number(e.target.value))} disabled={submitting}>
              {options(LANGUAGE_LABELS).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="classification">Classification</label>
            <select
              id="classification"
              value={input.classification}
              onChange={(e) => set('classification', Number(e.target.value))}
              disabled={submitting}
            >
              {options(CLASSIFICATION_LABELS).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="priority">Priority</label>
            <select id="priority" value={input.priority} onChange={(e) => set('priority', Number(e.target.value))} disabled={submitting}>
              {options(PRIORITY_LABELS).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="due">Due date</label>
            <input
              id="due"
              type="date"
              min={localDateOnly(0)}
              value={input.dueDate}
              onChange={(e) => set('dueDate', e.target.value)}
              disabled={submitting}
            />
          </div>
        </div>
      </section>

      <section className="panel formSection">
        <h3>
          <span className="stepNo">3</span> Recipient and review
        </h3>
        <div className="grid3">
          <div className="field">
            <label htmlFor="rname">Recipient name</label>
            <input id="rname" maxLength={200} value={input.recipientName} onChange={(e) => set('recipientName', e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label htmlFor="rtitle">Recipient title</label>
            <input
              id="rtitle"
              maxLength={200}
              list="leader-titles"
              value={input.recipientTitle}
              onChange={(e) => set('recipientTitle', e.target.value)}
              disabled={submitting}
            />
            <datalist id="leader-titles">
              {(reference.profiles.find((p) => p.id === input.profileId)?.leaderTitles ?? '')
                .split(/[;\n]/)
                .map((t) => t.trim())
                .filter(Boolean)
                .map((t) => (
                  <option key={t} value={t} />
                ))}
            </datalist>
          </div>
          <div className="field">
            <label htmlFor="remail">Recipient email</label>
            <input id="remail" type="email" value={input.recipientEmail} onChange={(e) => set('recipientEmail', e.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label htmlFor="reviewer">Reviewer email</label>
            <input
              id="reviewer"
              type="email"
              value={input.reviewerEmail}
              onChange={(e) => {
                reviewerEdited.current = true
                set('reviewerEmail', e.target.value)
              }}
              disabled={submitting}
            />
          </div>
          <div className="field">
            <label htmlFor="delivery">Delivery</label>
            <select id="delivery" value={input.deliveryMode} onChange={(e) => set('deliveryMode', Number(e.target.value))} disabled={submitting}>
              {options(DELIVERY_MODE_LABELS).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        {touched && emailInvalid ? <p className="fieldError">Check the email addresses.</p> : null}
      </section>

      <section className="panel formSection">
        <h3>
          <span className="stepNo">4</span> Source documents
        </h3>
        <p className="muted">
          The Writer only uses what you provide. Text is extracted in your browser; scanned PDFs without a text layer can't be read.
        </p>
        <div
          className={dragOver ? 'drop drop--over' : 'drop'}
          onDragEnter={(e) => {
            e.preventDefault()
            if (!submitting) setDragOver(true)
          }}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={(e) => {
            e.preventDefault()
            setDragOver(false)
          }}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            if (!submitting) addFiles(e.dataTransfer.files)
          }}
        >
          <input
            ref={fileInput}
            type="file"
            className="hiddenFile"
            multiple
            accept={ACCEPTED_FILE_TYPES}
            disabled={submitting}
            onChange={(e) => {
              if (e.target.files) addFiles(e.target.files)
              e.target.value = ''
            }}
          />
          <button type="button" className="drop__button" disabled={submitting} onClick={() => fileInput.current?.click()}>
            <IconUpload size={22} />
            <span>
              <strong>Choose files or drop them here</strong>
              <small>PDF, Word (.docx), .txt or .md · up to 32 MB each</small>
            </span>
          </button>
        </div>
        {fileError ? <Message kind="error">{fileError}</Message> : null}
        {sources.length > 0 ? (
          <div className="tableWrap">
            <table className="sourceTable">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>File</th>
                  <th>Type</th>
                  <th>Extraction</th>
                  <th>Pages</th>
                  <th>Characters</th>
                  <th aria-label="Remove" />
                </tr>
              </thead>
              <tbody>
                {sources.map((s, index) => (
                  <tr key={s.key}>
                    <td>
                      <span className="cite">S{index + 1}</span>
                    </td>
                    <td className="truncateCell" title={s.file.name}>
                      {s.file.name}
                      {s.warning ? <div className="warnText small">{s.warning}</div> : null}
                      {s.error ? <div className="errorText small">{s.error}</div> : null}
                    </td>
                    <td>
                      <select
                        aria-label={`Document type for ${s.file.name}`}
                        value={s.documentType}
                        disabled={submitting}
                        onChange={(e) =>
                          setSources((previous) =>
                            previous.map((x) => (x.key === s.key ? { ...x, documentType: Number(e.target.value) } : x)),
                          )
                        }
                      >
                        {options(DOCUMENT_TYPE_LABELS).map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      {s.state === 'extracting' ? (
                        <span className="pill tone-info">
                          <span className="miniSpin" /> Extracting
                        </span>
                      ) : s.state === 'extracted' ? (
                        <span className={s.warning ? 'pill tone-warning' : 'pill tone-success'}>{s.warning ? 'Check' : 'Extracted'}</span>
                      ) : s.state === 'unsupported' ? (
                        <span className="pill tone-neutral">Not supported</span>
                      ) : (
                        <span className="pill tone-danger">Failed</span>
                      )}
                    </td>
                    <td>{formatNumber(s.pageCount)}</td>
                    <td>{s.state === 'extracting' ? '…' : formatNumber(s.characterCount)}</td>
                    <td>
                      <button
                        type="button"
                        className="iconBtn"
                        disabled={submitting}
                        onClick={() => setSources((previous) => previous.filter((x) => x.key !== s.key))}
                        aria-label={`Remove ${s.file.name}`}
                        title="Remove"
                      >
                        <IconTrash size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty small">No documents yet. You can submit without sources, but the note will be less specific.</div>
        )}
        {sources.length > 0 ? (
          <p className="muted small">
            {sources.length} document{sources.length === 1 ? '' : 's'} · {totalChars.toLocaleString()} characters of text
          </p>
        ) : null}
      </section>

      <section className="panel submitBar">
        <div className="submitBar__text">
          {progress ? (
            <span className="inline">
              <span className="miniSpin" /> {progress}
            </span>
          ) : extracting ? (
            <span className="muted">Waiting for text extraction to finish…</span>
          ) : touched && missing.length ? (
            <span className="errorText">Complete the required fields: {missing.join(', ')}.</span>
          ) : (
            <span className="muted">
              Requested by <b>{user.fullName}</b> ({user.upn})
            </span>
          )}
        </div>
        <div className="inline">
          <button className="btn" type="button" onClick={cancel} disabled={submitting}>
            {createdId ? 'Close' : 'Cancel'}
          </button>
          {createdId ? (
            <button className="btn primary" type="button" onClick={() => onSubmitted(createdId, error ? [error] : [])}>
              Open the saved request
            </button>
          ) : (
            <button className="btn primary" type="button" onClick={() => void submit()} disabled={submitting || extracting}>
              {submitting ? 'Submitting…' : 'Submit request'}
            </button>
          )}
        </div>
      </section>
      {error ? <Message kind="error">{error}</Message> : null}
    </div>
  )
}
