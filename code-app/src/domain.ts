// Choice values mirror scripts/schema_def.py (value = 743800000 + index). Never reorder.
const V = 743800000

function choice<const T extends readonly string[]>(labels: T): Record<number, string> {
  return Object.fromEntries(labels.map((label, index) => [V + index, label]))
}

export const RequestStatus = {
  Draft: V,
  Submitted: V + 1,
  Drafting: V + 2,
  NeedsInfo: V + 3,
  InfoProvided: V + 4,
  InReview: V + 5,
  RevisionRequested: V + 6,
  Approved: V + 7,
  Delivered: V + 8,
  Cancelled: V + 9,
  NeedsAttention: V + 10,
} as const
export type RequestStatusValue = (typeof RequestStatus)[keyof typeof RequestStatus]

export const STATUS_LABELS: Record<number, string> = choice([
  'Draft',
  'Submitted',
  'Drafting',
  'Needs Info',
  'Info Provided',
  'In Review',
  'Revision Requested',
  'Approved',
  'Delivered',
  'Cancelled',
  'Needs Attention',
] as const)

export type Tone = 'neutral' | 'info' | 'progress' | 'warning' | 'success' | 'danger'

export const STATUS_TONES: Record<number, Tone> = {
  [RequestStatus.Draft]: 'neutral',
  [RequestStatus.Submitted]: 'info',
  [RequestStatus.Drafting]: 'progress',
  [RequestStatus.NeedsInfo]: 'warning',
  [RequestStatus.InfoProvided]: 'info',
  [RequestStatus.InReview]: 'progress',
  [RequestStatus.RevisionRequested]: 'warning',
  [RequestStatus.Approved]: 'success',
  [RequestStatus.Delivered]: 'success',
  [RequestStatus.Cancelled]: 'neutral',
  [RequestStatus.NeedsAttention]: 'danger',
}

/** Statuses where the backend is working, so the detail page polls for changes. */
export const ACTIVE_STATUSES: number[] = [
  RequestStatus.Submitted,
  RequestStatus.Drafting,
  RequestStatus.InfoProvided,
  RequestStatus.RevisionRequested,
  RequestStatus.Approved,
]

export const CLOSED_STATUSES: number[] = [RequestStatus.Delivered, RequestStatus.Cancelled]

/** A request can be cancelled only while no workflow is running on it. */
export const CANCELLABLE_STATUSES: number[] = [
  RequestStatus.Draft,
  RequestStatus.NeedsInfo,
  RequestStatus.InReview,
  RequestStatus.NeedsAttention,
]

/** Only the assigned reviewer (brn_revieweremail) may edit, approve or send back a draft. */
export function isAssignedReviewer(reviewerEmail: string | null | undefined, upn: string): boolean {
  const reviewer = (reviewerEmail ?? '').trim().toLowerCase()
  return reviewer !== '' && reviewer === upn.trim().toLowerCase()
}

export const NOTE_TYPE_LABELS = choice([
  'Briefing Note for Information',
  'Briefing Note for Decision',
  'Meeting or Event Brief',
  'Issue Note',
  'Executive Summary',
] as const)

export const LANGUAGE_LABELS = choice(['English', 'French'] as const)
export const CLASSIFICATION_LABELS = choice([
  'Unclassified',
  'Protected A',
  'Protected B',
  'Internal',
  'Confidential',
] as const)
export const PRIORITY_LABELS = choice(['Routine', 'Priority', 'Urgent'] as const)
export const Priority = { Routine: V, Priority: V + 1, Urgent: V + 2 } as const
export const DELIVERY_MODE_LABELS = choice(['Send to requester and recipient', 'Send to requester only'] as const)
export const IntakeChannel = { BriefingStudio: V, BriefingAssistant: V + 1, BriefingNotesHub: V + 2 } as const
export const CONFIDENCE_LABELS = choice(['Low', 'Medium', 'High'] as const)

export const DOCUMENT_TYPE_LABELS = choice([
  'Report',
  'Memo or briefing',
  'Email or correspondence',
  'Presentation',
  'Data or spreadsheet',
  'Web page or article',
  'Meeting notes',
  'Other',
] as const)
export const DocumentType = {
  Report: V,
  Memo: V + 1,
  Email: V + 2,
  Presentation: V + 3,
  Data: V + 4,
  WebPage: V + 5,
  MeetingNotes: V + 6,
  Other: V + 7,
} as const

export const Language = { English: V, French: V + 1 } as const
export const Classification = { Unclassified: V } as const
export const DeliveryMode = { RequesterAndRecipient: V, RequesterOnly: V + 1 } as const

export const ExtractionStatus = { Pending: V, Extracted: V + 1, Failed: V + 2, NotSupported: V + 3 } as const
export const EXTRACTION_STATUS_LABELS = choice(['Pending', 'Extracted', 'Failed', 'Not supported'] as const)

export const Actor = {
  Requester: V,
  BriefingAssistant: V + 1,
  BriefingNoteWriter: V + 2,
  Workflow: V + 3,
  Reviewer: V + 4,
} as const
export const ACTOR_LABELS = choice([
  'Requester',
  'Briefing Assistant',
  'Briefing Note Writer',
  'Workflow',
  'Reviewer',
] as const)

export const ActivityType = {
  Submitted: V,
  DraftingStarted: V + 1,
  ClarificationRequested: V + 2,
  ClarificationProvided: V + 3,
  DraftReady: V + 4,
  RevisionRequested: V + 5,
  Approved: V + 6,
  Delivered: V + 7,
  Failed: V + 8,
  Cancelled: V + 9,
  Note: V + 10,
} as const
export const ACTIVITY_TYPE_LABELS = choice([
  'Submitted',
  'Drafting started',
  'Clarification requested',
  'Clarification provided',
  'Draft ready',
  'Revision requested',
  'Approved',
  'Delivered',
  'Failed',
  'Cancelled',
  'Note',
] as const)

export const MAX_FILE_BYTES = 32 * 1024 * 1024
export const MAX_EXTRACTED_CHARS = 1_000_000
export const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'] as const
export const ACCEPTED_FILE_TYPES = ACCEPTED_EXTENSIONS.join(',')

export function label(map: Record<number, string>, value: number | null | undefined, fallback = ''): string {
  return value === null || value === undefined ? fallback : (map[value] ?? fallback)
}

export function options(map: Record<number, string>): { value: number; label: string }[] {
  return Object.entries(map).map(([value, text]) => ({ value: Number(value), label: text }))
}

export interface CurrentUser {
  upn: string
  fullName: string
}

export interface Profile {
  id: string
  name: string
  code: string
  defaultLanguage: number | null
  defaultReviewerEmail: string
  leaderTitles: string
}

export interface Template {
  id: string
  name: string
  code: string
  noteType: number | null
  whenToUse: string
  sections: string
  maxWords: number | null
  sortOrder: number
}

export interface DraftSection {
  heading: string
  body: string
}

export interface BriefingRequest {
  id: string
  number: string
  subject: string
  status: number
  requesterName: string
  requesterEmail: string
  recipientName: string
  recipientTitle: string
  recipientEmail: string
  reviewerEmail: string
  purpose: string
  additionalContext: string
  language: number | null
  classification: number | null
  priority: number | null
  dueDate: string | null
  deliveryMode: number | null
  clarificationQuestions: string
  clarificationAnswers: string
  clarificationRounds: number
  reviewerComments: string
  noteTitle: string
  keyMessage: string
  draftSections: DraftSection[]
  draftSectionsError: string | null
  sourcesUsed: string
  verificationNotes: string
  confidence: number | null
  wordCount: number | null
  draftVersion: number | null
  draftPdfUrl: string
  finalPdfUrl: string
  sharePointFolderUrl: string
  submittedOn: string | null
  draftedOn: string | null
  approvedBy: string
  approvedOn: string | null
  deliveredOn: string | null
  lastError: string
  profileId: string | null
  profileName: string
  templateId: string | null
  templateName: string
  createdOn: string | null
  modifiedOn: string | null
}

export interface SourceDocument {
  id: string
  name: string
  label: string
  documentType: number | null
  extractionStatus: number | null
  pageCount: number | null
  characterCount: number | null
  summary: string
  hasFile: boolean
}

export interface Activity {
  id: string
  name: string
  actor: number | null
  activityType: number | null
  details: string
  startedOn: string | null
  completedOn: string | null
  durationSeconds: number | null
  createdOn: string | null
}

export type ExtractionState = 'extracting' | 'extracted' | 'failed' | 'unsupported'

export interface PendingSource {
  key: string
  file: File
  documentType: number
  state: ExtractionState
  text: string
  pageCount: number | null
  characterCount: number
  warning: string | null
  error: string | null
}

export interface NewRequestInput {
  profileId: string | null
  templateId: string | null
  subject: string
  recipientName: string
  recipientTitle: string
  recipientEmail: string
  reviewerEmail: string
  purpose: string
  additionalContext: string
  language: number
  classification: number
  priority: number
  dueDate: string
  deliveryMode: number
}

export interface SubmitResult {
  requestId: string
  warnings: string[]
}

/** Parses the draftsections JSON; tolerant of an empty value. */
export function parseSections(json: string | null | undefined): { sections: DraftSection[]; error: string | null } {
  if (!json || !json.trim()) return { sections: [], error: null }
  try {
    const parsed: unknown = JSON.parse(json)
    if (!Array.isArray(parsed)) return { sections: [], error: 'Draft sections are not a JSON array.' }
    return {
      sections: parsed.map((item) => {
        const record = (item ?? {}) as Record<string, unknown>
        return {
          heading: typeof record.heading === 'string' ? record.heading : '',
          body: typeof record.body === 'string' ? record.body : '',
        }
      }),
      error: null,
    }
  } catch (err) {
    return { sections: [], error: `Draft sections could not be read: ${err instanceof Error ? err.message : String(err)}` }
  }
}

export function countWords(...parts: string[]): number {
  return parts
    .join(' ')
    .replace(/\[S\d+\]/g, ' ')
    .split(/\s+/)
    .filter((word) => /[\p{L}\p{N}]/u.test(word)).length
}

/** Today (or today + days) as a DateOnly string built from local date parts. */
export function localDateOnly(daysFromToday = 0): string {
  const date = new Date()
  date.setDate(date.getDate() + daysFromToday)
  return toDateOnly(date)
}

export function toDateOnly(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** Reads a DateOnly value ("2026-11-10" or "2026-11-10T00:00:00Z") as a local date without shifting the day. */
export function parseDateOnly(value: string | null | undefined): Date | null {
  if (!value) return null
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}
