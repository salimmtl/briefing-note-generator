import { useCallback, useEffect, useMemo, useState } from 'react'
import { loadMyRequests, type Reference } from '../dataverse'
import {
  ACTIVE_STATUSES,
  CLOSED_STATUSES,
  RequestStatus,
  STATUS_LABELS,
  options,
  type BriefingRequest,
  type CurrentUser,
} from '../domain'
import { errorMessage } from '../format'
import { IconAdd, IconAlert } from '../icons'
import { RequestTable } from './RequestTable'
import { DueDate, Loading, Message, PageHeader } from './Shared'

const OPEN = 'open'
const ALL = 'all'

export function MyBriefingsPage({
  user,
  reference,
  refreshToken,
  open,
  newRequest,
}: {
  user: CurrentUser
  reference: Reference
  refreshToken: number
  open: (id: string) => void
  newRequest: () => void
}) {
  const [requests, setRequests] = useState<BriefingRequest[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<string>(OPEN)

  const load = useCallback(async () => {
    try {
      setRequests(await loadMyRequests(user, reference))
      setError(null)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [user, reference])

  useEffect(() => {
    void load()
  }, [load, refreshToken])

  const anyActive = requests?.some((r) => ACTIVE_STATUSES.includes(r.status)) ?? false
  useEffect(() => {
    if (!anyActive) return undefined
    const timer = window.setInterval(() => void load(), 15000)
    return () => window.clearInterval(timer)
  }, [anyActive, load])

  const needsInput = useMemo(() => (requests ?? []).filter((r) => r.status === RequestStatus.NeedsInfo), [requests])

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (requests ?? []).filter((r) => {
      if (status === OPEN && CLOSED_STATUSES.includes(r.status)) return false
      if (status !== OPEN && status !== ALL && r.status !== Number(status)) return false
      if (!term) return true
      return [r.number, r.subject, r.recipientName, r.recipientTitle, r.templateName]
        .join(' ')
        .toLowerCase()
        .includes(term)
    })
  }, [requests, search, status])

  const filtersActive = search.trim() !== '' || status !== OPEN

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Briefing Studio"
        title="My briefings"
        subtitle={`Briefing notes you have requested as ${user.upn}.`}
        actions={
          <button className="btn primary" type="button" onClick={newRequest}>
            <IconAdd size={16} />
            New request
          </button>
        }
      />
      {error ? <Message kind="error">{error}</Message> : null}
      {requests === null && !error ? <Loading text="Loading your briefings…" /> : null}
      {needsInput.length > 0 ? (
        <section className="panel attention" aria-labelledby="needs-input-heading">
          <h3 id="needs-input-heading">
            <IconAlert size={18} /> Needs your input <span className="count">{needsInput.length}</span>
          </h3>
          <p className="muted">The Briefing Note Writer has questions before it can finish these drafts.</p>
          <div className="attentionList">
            {needsInput.map((r) => (
              <button key={r.id} type="button" className="attentionItem" onClick={() => open(r.id)}>
                <span className="mono">{r.number}</span>
                <span className="truncate">{r.subject}</span>
                <DueDate value={r.dueDate} />
                <span className="linkText">Answer questions →</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}
      {requests !== null ? (
        <section className="panel">
          <div className="filters">
            <input
              type="search"
              className="search"
              placeholder="Search subject, ID, recipient or template"
              aria-label="Search requests"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select aria-label="Status filter" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value={OPEN}>Open requests</option>
              <option value={ALL}>All statuses</option>
              {options(STATUS_LABELS).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <span className="muted small resultCount">
              {filtered.length} of {requests.length} request{requests.length === 1 ? '' : 's'}
            </span>
            {filtersActive ? (
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setSearch('')
                  setStatus(OPEN)
                }}
              >
                Clear filters
              </button>
            ) : null}
          </div>
          <RequestTable
            requests={filtered}
            open={open}
            emptyText={
              requests.length === 0
                ? 'You have no briefing requests yet. Select “New request” to ask for your first briefing note.'
                : 'No requests match these filters.'
            }
          />
        </section>
      ) : null}
    </div>
  )
}
