import { parseDateOnly } from './domain'

const dateFormat = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDateOnly(value: string | null | undefined, fallback = '—'): string {
  const date = parseDateOnly(value)
  return date ? dateFormat.format(date) : fallback
}

export function formatDateTime(value: string | null | undefined, fallback = '—'): string {
  if (!value) return fallback
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? fallback : dateTimeFormat.format(date)
}

/** Days from today to a DateOnly value (negative = overdue). */
export function daysUntil(value: string | null | undefined): number | null {
  const date = parseDateOnly(value)
  if (!date) return null
  const today = new Date()
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((date.getTime() - start.getTime()) / 86_400_000)
}

export function formatNumber(value: number | null | undefined, fallback = '—'): string {
  return value === null || value === undefined ? fallback : value.toLocaleString()
}

export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}
