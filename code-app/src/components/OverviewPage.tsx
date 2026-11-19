import { useCallback, useEffect, useMemo, useState } from 'react'
import { loadAllRequests, type Reference } from '../dataverse'
import { CLOSED_STATUSES, RequestStatus, STATUS_LABELS, STATUS_TONES, type BriefingRequest } from '../domain'
import { errorMessage } from '../format'
import { Loading, Message, PageHeader } from './Shared'

interface Bar {
  key: string
  label: string
  value: number
  tone?: string
}

function Bars({ bars, empty }: { bars: Bar[]; empty: string }) {
  const max = Math.max(1, ...bars.map((b) => b.value))
  if (bars.every((b) => b.value === 0)) return <div className="empty">{empty}</div>
  return (
    <div className="chartBars">
      {bars.map((bar) => (
        <div className="chartRow" key={bar.key}>
          <span className="truncate" title={bar.label}>
            {bar.label}
          </span>
          <span className="barTrack">
            <span className={`barFill ${bar.tone ? `fill-${bar.tone}` : ''}`} style={{ width: `${(bar.value / max) * 100}%` }} />
          </span>
          <b>{bar.value}</b>
        </div>
      ))}
    </div>
  )
}

export function OverviewPage({
  reference,
  refreshToken,
  open,
}: {
  reference: Reference
  refreshToken: number
  open: (id: string) => void
}) {
  const [requests, setRequests] = useState<BriefingRequest[] | null>(null)
  const [loadedAt, setLoadedAt] = useState<Date>(() => new Date())
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setRequests(await loadAllRequests(reference))
      setLoadedAt(new Date())
      setError(null)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [reference])

  useEffect(() => {
    void load()
  }, [load, refreshToken])

  const stats = useMemo(() => {
    const list = requests ?? []
    const now = loadedAt
    const openCount = list.filter((r) => !CLOSED_STATUSES.includes(r.status)).length
    const needsInput = list.filter((r) => r.status === RequestStatus.NeedsInfo).length
    const inReview = list.filter((r) => r.status === RequestStatus.InReview).length
    const deliveredThisMonth = list.filter((r) => {
      if (!r.deliveredOn) return false
      const d = new Date(r.deliveredOn)
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
    }).length
    const durations = list
      .filter((r) => r.submittedOn && r.draftedOn)
      .map((r) => (new Date(r.draftedOn as string).getTime() - new Date(r.submittedOn as string).getTime()) / 3_600_000)
      .filter((h) => Number.isFinite(h) && h >= 0)
    const avgHours = durations.length ? durations.reduce((a, b) => a + b, 0) / durations.length : null
    const attention = list.filter((r) => r.status === RequestStatus.NeedsAttention)

    const statusBars: Bar[] = Object.entries(STATUS_LABELS).map(([value, text]) => ({
      key: value,
      label: text,
      value: list.filter((r) => r.status === Number(value)).length,
      tone: STATUS_TONES[Number(value)],
    }))
    const templateCounts = new Map<string, number>()
    for (const r of list) {
      const name = r.templateName || 'No template'
      templateCounts.set(name, (templateCounts.get(name) ?? 0) + 1)
    }
    const templateBars: Bar[] = [...templateCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([name, value]) => ({ key: name, label: name, value }))
    return { openCount, needsInput, inReview, deliveredThisMonth, avgHours, durations: durations.length, statusBars, templateBars, attention }
  }, [requests, loadedAt])

  return (
    <div className="stack">
      <PageHeader eyebrow="Insights" title="Overview" subtitle="All briefing requests you have access to." />
      {error ? <Message kind="error">{error}</Message> : null}
      {requests === null && !error ? <Loading text="Loading the overview…" /> : null}
      {requests !== null ? (
        <>
          <div className="kpis">
            <div className="kpi">
              <strong>{stats.openCount}</strong>
              <span>Open requests</span>
            </div>
            <div className="kpi kpi--warning">
              <strong>{stats.needsInput}</strong>
              <span>Needs input</span>
            </div>
            <div className="kpi kpi--progress">
              <strong>{stats.inReview}</strong>
              <span>In review</span>
            </div>
            <div className="kpi kpi--success">
              <strong>{stats.deliveredThisMonth}</strong>
              <span>Delivered this month</span>
            </div>
            <div className="kpi">
              <strong>{stats.avgHours === null ? '—' : stats.avgHours < 10 ? stats.avgHours.toFixed(1) : Math.round(stats.avgHours)}</strong>
              <span>
                Avg hours to first draft{stats.durations ? ` (${stats.durations} note${stats.durations === 1 ? '' : 's'})` : ''}
              </span>
            </div>
          </div>
          {stats.attention.length ? (
            <Message kind="error">
              <b>{stats.attention.length} request(s) need attention:</b>{' '}
              {stats.attention.map((r, i) => (
                <span key={r.id}>
                  {i ? ', ' : ''}
                  <button type="button" className="linkBtn" onClick={() => open(r.id)}>
                    {r.number || r.subject}
                  </button>
                </span>
              ))}
            </Message>
          ) : null}
          <div className="grid2">
            <section className="panel">
              <h3>Requests by status</h3>
              <Bars bars={stats.statusBars} empty="No requests yet." />
            </section>
            <section className="panel">
              <h3>Requests by template</h3>
              <Bars bars={stats.templateBars} empty="No requests yet." />
            </section>
          </div>
        </>
      ) : null}
    </div>
  )
}
