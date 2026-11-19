import type { ReactNode } from 'react'
import { PRIORITY_LABELS, Priority, STATUS_LABELS, STATUS_TONES, label } from '../domain'
import { daysUntil, formatDateOnly } from '../format'

export function StatusPill({ status }: { status: number }) {
  return <span className={`pill tone-${STATUS_TONES[status] ?? 'neutral'}`}>{label(STATUS_LABELS, status, 'Unknown')}</span>
}

export function PriorityPill({ priority }: { priority: number | null }) {
  if (priority === null || priority === Priority.Routine) return <span className="muted small">Routine</span>
  return (
    <span className={`pill ${priority === Priority.Urgent ? 'tone-danger' : 'tone-warning'}`}>
      {label(PRIORITY_LABELS, priority)}
    </span>
  )
}

export function DueDate({ value, closed }: { value: string | null; closed?: boolean }) {
  const days = daysUntil(value)
  if (!value) return <span className="muted">—</span>
  const overdue = !closed && days !== null && days < 0
  const soon = !closed && days !== null && days >= 0 && days <= 2
  return (
    <span className={overdue ? 'due overdue' : soon ? 'due soon' : 'due'}>
      {formatDateOnly(value)}
      {overdue ? <small> · overdue</small> : soon ? <small> · {days === 0 ? 'today' : `${days}d`}</small> : null}
    </span>
  )
}

export function Message({ kind, children }: { kind: 'error' | 'warning' | 'success' | 'info'; children: ReactNode }) {
  return (
    <div className={`message message--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      {children}
    </div>
  )
}

export function Loading({ text }: { text: string }) {
  return (
    <div className="loading">
      <span className="spinner" />
      {text}
    </div>
  )
}

export function PageHeader({ eyebrow, title, subtitle, actions }: {
  eyebrow?: string
  title: string
  subtitle?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="pageHeader">
      <div className="pageHeader__text">
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2>{title}</h2>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="pageHeader__actions">{actions}</div> : null}
    </header>
  )
}

/** Renders plain draft text: "- " lines become bullets and [S1] markers become citation chips. */
export function DraftText({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  let paragraph: string[] = []
  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(<p key={`p${blocks.length}`}>{withCitations(paragraph.join(' '))}</p>)
      paragraph = []
    }
  }
  const flushBullets = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`u${blocks.length}`}>
          {bullets.map((item, index) => (
            <li key={index}>{withCitations(item)}</li>
          ))}
        </ul>,
      )
      bullets = []
    }
  }
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim()
    if (/^[-•*]\s+/.test(line)) {
      flushParagraph()
      bullets.push(line.replace(/^[-•*]\s+/, ''))
    } else if (!line) {
      flushParagraph()
      flushBullets()
    } else {
      flushBullets()
      flushParagraph()
      paragraph.push(line)
    }
  }
  flushParagraph()
  flushBullets()
  return <div className="draftText">{blocks}</div>
}

function withCitations(value: string): ReactNode[] {
  return value.split(/(\[S\d+(?:\s*,\s*S\d+)*\])/g).map((part, index) => {
    const match = /^\[(S\d+(?:\s*,\s*S\d+)*)\]$/.exec(part)
    if (!match) return part
    return match[1].split(/\s*,\s*/).map((cite) => (
      <span className="cite" key={`${index}-${cite}`} title={`Source ${cite}`}>
        {cite}
      </span>
    ))
  })
}
