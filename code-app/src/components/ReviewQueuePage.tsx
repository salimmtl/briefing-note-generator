import { useCallback, useEffect, useMemo, useState } from 'react'
import { loadAllRequests, type Reference } from '../dataverse'
import { CLOSED_STATUSES, Priority, RequestStatus, type BriefingRequest } from '../domain'
import { errorMessage } from '../format'
import { RequestTable } from './RequestTable'
import { Loading, Message, PageHeader } from './Shared'

type Scope = 'review' | 'open' | 'all'
type Sort = 'due' | 'priority' | 'updated'

const PRIORITY_RANK: Record<number, number> = { [Priority.Urgent]: 0, [Priority.Priority]: 1, [Priority.Routine]: 2 }

function byDue(a: BriefingRequest, b: BriefingRequest): number {
  if (!a.dueDate && !b.dueDate) return 0
  if (!a.dueDate) return 1
  if (!b.dueDate) return -1
  return a.dueDate.localeCompare(b.dueDate)
}

export function ReviewQueuePage({
  reference,
  refreshToken,
  open,
}: {
  reference: Reference
  refreshToken: number
  open: (id: string) => void
}) {
  const [requests, setRequests] = useState<BriefingRequest[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [scope, setScope] = useState<Scope>('review')
  const [sort, setSort] = useState<Sort>('due')
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    try {
      setRequests(await loadAllRequests(reference))
      setError(null)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [reference])

  useEffect(() => {
    void load()
  }, [load, refreshToken])

  useEffect(() => {
    const timer = window.setInterval(() => void load(), 30000)
    return () => window.clearInterval(timer)
  }, [load])

  const inReviewCount = (requests ?? []).filter((r) => r.status === RequestStatus.InReview).length

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase()
    const list = (requests ?? []).filter((r) => {
      if (scope === 'review' && r.status !== RequestStatus.InReview) return false
      if (scope === 'open' && CLOSED_STATUSES.includes(r.status)) return false
      if (!term) return true
      return [r.number, r.subject, r.requesterName, r.requesterEmail, r.recipientName, r.templateName]
        .join(' ')
        .toLowerCase()
        .includes(term)
    })
    return [...list].sort((a, b) => {
      if (sort === 'due') return byDue(a, b) || (PRIORITY_RANK[a.priority ?? -1] ?? 3) - (PRIORITY_RANK[b.priority ?? -1] ?? 3)
      if (sort === 'priority') return (PRIORITY_RANK[a.priority ?? -1] ?? 3) - (PRIORITY_RANK[b.priority ?? -1] ?? 3) || byDue(a, b)
      return (b.modifiedOn ?? '').localeCompare(a.modifiedOn ?? '')
    })
  }, [requests, scope, sort, search])

  return (
    <div className="stack">
      <PageHeader
        eyebrow="Reviewers"
        title="Review queue"
        subtitle={`${inReviewCount} draft${inReviewCount === 1 ? '' : 's'} waiting for review. Open one to edit, approve or request a revision.`}
      />
      {error ? <Message kind="error">{error}</Message> : null}
      {requests === null && !error ? <Loading text="Loading the review queue…" /> : null}
      {requests !== null ? (
        <section className="panel">
          <div className="filters">
            <div className="segmented" role="group" aria-label="Scope">
              {(
                [
                  ['review', `In Review (${inReviewCount})`],
                  ['open', 'All open'],
                  ['all', 'All'],
                ] as [Scope, string][]
              ).map(([value, text]) => (
                <button key={value} type="button" className={scope === value ? 'active' : ''} aria-pressed={scope === value} onClick={() => setScope(value)}>
                  {text}
                </button>
              ))}
            </div>
            <input
              type="search"
              className="search"
              placeholder="Search subject, ID, requester…"
              aria-label="Search the queue"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <label className="inline small muted">
              Sort by
              <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort by">
                <option value="due">Due date</option>
                <option value="priority">Priority</option>
                <option value="updated">Last updated</option>
              </select>
            </label>
            <span className="muted small resultCount">
              {rows.length} request{rows.length === 1 ? '' : 's'}
            </span>
          </div>
          <RequestTable
            requests={rows}
            open={open}
            showRequester
            emptyText={scope === 'review' ? 'Nothing is waiting for review.' : 'No requests match.'}
          />
        </section>
      ) : null}
    </div>
  )
}
