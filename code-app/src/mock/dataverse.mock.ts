// Local preview only: `npm run dev:mock` swaps ../dataverse for this file (see vite.config.ts). Not used in builds.
import type { Reference, RequestBundle, SubmitProgress } from '../dataverse'
import {
  ActivityType,
  Actor,
  RequestStatus,
  localDateOnly,
  type Activity,
  type BriefingRequest,
  type CurrentUser,
  type DraftSection,
  type NewRequestInput,
  type PendingSource,
  type SourceDocument,
  type SubmitResult,
} from '../domain'

const V = 743800000
const delay = (ms = 250) => new Promise((resolve) => window.setTimeout(resolve, ms))
const hoursAgo = (h: number) => new Date(Date.now() - h * 3_600_000).toISOString()

const user: CurrentUser = { upn: 'avery.chen@contoso.gov', fullName: 'Avery Chen' }

const reference: Reference = {
  profiles: [
    {
      id: 'p1',
      name: 'Ministry of Digital Services',
      code: 'MDS',
      defaultLanguage: V,
      defaultReviewerEmail: 'jordan.lee@contoso.gov',
      leaderTitles: 'Minister; Deputy Minister; ADM',
    },
  ],
  templates: [
    { id: 't1', name: 'Briefing Note for Information', code: 'INFO', noteType: V, whenToUse: 'Inform a senior leader about an issue, event or development. No decision required.', sections: '', maxWords: 800, sortOrder: 10 },
    { id: 't2', name: 'Briefing Note for Decision', code: 'DEC', noteType: V + 1, whenToUse: 'A leader must choose between options. Presents analysis, options and a recommendation.', sections: '', maxWords: 1200, sortOrder: 20 },
    { id: 't3', name: 'Meeting or Event Brief', code: 'MTG', noteType: V + 2, whenToUse: 'Prepare a leader for a meeting, speech or site visit: objectives, key messages, participants.', sections: '', maxWords: 1000, sortOrder: 30 },
    { id: 't4', name: 'Issue Note', code: 'ISSUE', noteType: V + 3, whenToUse: 'A short note on an emerging or sensitive issue, with suggested responsive lines.', sections: '', maxWords: 500, sortOrder: 40 },
  ],
}

const sections: DraftSection[] = [
  {
    heading: 'Purpose',
    body: 'To inform the Deputy Minister of the results of the cloud migration readiness assessment and the proposed next steps [S1].',
  },
  {
    heading: 'Background',
    body:
      'The department operates 412 applications, of which 61% run on infrastructure that reaches end of support by 2028 [S1].\n' +
      '- The 2025 audit identified three critical systems without tested recovery plans [S2].\n' +
      '- Hosting costs rose 14% year over year, mainly from data centre leases [S1, S3].',
  },
  {
    heading: 'Current status',
    body: 'Wave 1 (38 low-risk applications) is complete and on budget [S3]. Wave 2 starts in January and includes the grants management system, which handles Protected B data [S2].',
  },
  {
    heading: 'Next steps',
    body: '- Approve the Wave 2 security assessment plan by December 15.\n- Confirm funding for the recovery testing program [S3].',
  },
]

const base = (over: Partial<BriefingRequest>): BriefingRequest => ({
  id: crypto.randomUUID(),
  number: 'BN-00000',
  subject: '',
  status: RequestStatus.Draft,
  requesterName: user.fullName,
  requesterEmail: user.upn,
  recipientName: 'Morgan Patel',
  recipientTitle: 'Deputy Minister',
  recipientEmail: '',
  reviewerEmail: 'jordan.lee@contoso.gov',
  purpose: 'Prepare the Deputy Minister for the quarterly briefing with central agencies.',
  additionalContext: '',
  language: V,
  classification: V,
  priority: V,
  dueDate: localDateOnly(5),
  deliveryMode: V,
  clarificationQuestions: '',
  clarificationAnswers: '',
  clarificationRounds: 0,
  reviewerComments: '',
  noteTitle: '',
  keyMessage: '',
  draftSections: [],
  draftSectionsError: null,
  sourcesUsed: '',
  verificationNotes: '',
  confidence: null,
  wordCount: null,
  draftVersion: null,
  draftPdfUrl: '',
  finalPdfUrl: '',
  sharePointFolderUrl: '',
  submittedOn: null,
  draftedOn: null,
  approvedBy: '',
  approvedOn: null,
  deliveredOn: null,
  lastError: '',
  profileId: 'p1',
  profileName: 'Ministry of Digital Services',
  templateId: 't1',
  templateName: 'Briefing Note for Information',
  createdOn: hoursAgo(30),
  modifiedOn: hoursAgo(1),
  ...over,
})

const requests: BriefingRequest[] = [
  base({
    id: 'r1',
    number: 'BN-00012',
    subject: 'Cloud migration readiness: results and next steps',
    status: RequestStatus.InReview,
    reviewerEmail: user.upn,
    clarificationRounds: 1,
    clarificationQuestions: '1. Should the note cover the Wave 2 budget?',
    clarificationAnswers: 'Round 1 (Nov 9, 2026, 10:12 AM):\nYes, include the budget at a high level.',
    noteTitle: 'Cloud Migration Readiness Assessment – Results and Next Steps',
    keyMessage:
      'Wave 1 of the cloud migration is complete on budget; Wave 2 needs a security assessment plan approved by December 15 to stay on schedule [S3].',
    draftSections: sections,
    sourcesUsed: 'S1 Readiness assessment report\nS2 2025 internal audit\nS3 Wave 1 close-out memo',
    verificationNotes: '- Confirm the 61% figure with the CIO office [S1].\n- The audit date is assumed to be fiscal 2025.',
    confidence: V + 2,
    wordCount: 312,
    draftVersion: 2,
    draftPdfUrl: 'https://contoso.sharepoint.com/draft.pdf',
    sharePointFolderUrl: 'https://contoso.sharepoint.com/folder',
    submittedOn: hoursAgo(28),
    draftedOn: hoursAgo(26),
    priority: V + 1,
    dueDate: localDateOnly(1),
  }),
  base({
    id: 'r2',
    number: 'BN-00014',
    subject: 'Ministerial visit to the Northern Service Centre',
    status: RequestStatus.NeedsInfo,
    templateId: 't3',
    templateName: 'Meeting or Event Brief',
    recipientName: 'Hon. Sam Rivera',
    recipientTitle: 'Minister',
    clarificationQuestions: '1. Who from the service centre will attend?\n2. Should the brief include the 2026 wait-time data?',
    submittedOn: hoursAgo(5),
    priority: V + 2,
    dueDate: localDateOnly(2),
  }),
  base({
    id: 'r3',
    number: 'BN-00015',
    subject: 'Options for the accessibility standard rollout',
    status: RequestStatus.Drafting,
    templateId: 't2',
    templateName: 'Briefing Note for Decision',
    submittedOn: hoursAgo(1),
    dueDate: localDateOnly(9),
  }),
  base({
    id: 'r4',
    number: 'BN-00009',
    subject: 'Data centre lease renewal',
    status: RequestStatus.Delivered,
    submittedOn: hoursAgo(200),
    draftedOn: hoursAgo(196),
    deliveredOn: hoursAgo(150),
    dueDate: localDateOnly(-5),
    templateId: 't4',
    templateName: 'Issue Note',
  }),
  base({
    id: 'r5',
    number: 'BN-00011',
    subject: 'Response to the privacy commissioner’s annual report',
    status: RequestStatus.Approved,
    submittedOn: hoursAgo(60),
    draftedOn: hoursAgo(57),
    approvedOn: hoursAgo(2),
    approvedBy: 'jordan.lee@contoso.gov',
    dueDate: localDateOnly(0),
  }),
]

const sources: SourceDocument[] = [
  { id: 's1', name: 'Cloud readiness assessment 2026.pdf', label: 'S1', documentType: V, extractionStatus: V + 1, pageCount: 42, characterCount: 118230, summary: 'Inventory of applications, end-of-support dates and cost model.', hasFile: true },
  { id: 's2', name: 'Internal audit - IT continuity.docx', label: 'S2', documentType: V, extractionStatus: V + 1, pageCount: null, characterCount: 35110, summary: 'Findings on recovery plans for critical systems.', hasFile: true },
  { id: 's3', name: 'Wave 1 close-out memo.pdf', label: 'S3', documentType: V + 1, extractionStatus: V + 1, pageCount: 6, characterCount: 9870, summary: 'Wave 1 scope, budget and lessons learned.', hasFile: true },
]

const activities: Activity[] = [
  { id: 'a4', name: 'Draft ready (version 2)', actor: Actor.BriefingNoteWriter, activityType: ActivityType.DraftReady, details: '312 words, 4 sections, high confidence.', startedOn: hoursAgo(26), completedOn: hoursAgo(26), durationSeconds: 412, createdOn: hoursAgo(26) },
  { id: 'a3', name: 'Clarification provided by Avery Chen (round 1)', actor: Actor.Requester, activityType: ActivityType.ClarificationProvided, details: 'Yes, include the budget at a high level.', startedOn: hoursAgo(27), completedOn: hoursAgo(27), durationSeconds: 0, createdOn: hoursAgo(27) },
  { id: 'a2', name: 'Clarification requested', actor: Actor.BriefingNoteWriter, activityType: ActivityType.ClarificationRequested, details: '1 question', startedOn: hoursAgo(27.5), completedOn: hoursAgo(27.5), durationSeconds: 95, createdOn: hoursAgo(27.5) },
  { id: 'a1', name: 'Submitted by Avery Chen', actor: Actor.Requester, activityType: ActivityType.Submitted, details: 'Submitted from Briefing Studio with 3 source document(s).', startedOn: hoursAgo(28), completedOn: hoursAgo(28), durationSeconds: 0, createdOn: hoursAgo(28) },
]

export class SubmitError extends Error {
  readonly requestId: string

  constructor(message: string, requestId: string) {
    super(message)
    this.requestId = requestId
  }
}

export function escapeOData(value: string): string {
  return value.replace(/'/g, "''")
}

export async function getCurrentUser(): Promise<CurrentUser> {
  await delay()
  return user
}

export async function loadReference(): Promise<Reference> {
  await delay()
  return reference
}

export async function loadMyRequests(): Promise<BriefingRequest[]> {
  await delay()
  return requests.filter((r) => r.requesterEmail === user.upn)
}

export async function loadAllRequests(): Promise<BriefingRequest[]> {
  await delay()
  return [
    ...requests,
    base({
      id: 'r6',
      number: 'BN-00016',
      subject: 'Cybersecurity incident lessons learned',
      status: RequestStatus.InReview,
      requesterName: 'Riley Brooks',
      requesterEmail: 'riley@contoso.gov',
      submittedOn: hoursAgo(10),
      draftedOn: hoursAgo(7),
      dueDate: localDateOnly(3),
      templateId: 't4',
      templateName: 'Issue Note',
    }),
  ]
}

export async function loadRequestBundle(id: string): Promise<RequestBundle> {
  await delay()
  const request = requests.find((r) => r.id === id) ?? requests[0]
  const full = request.id === 'r1'
  return { request, sources: full ? sources : sources.slice(0, 1), activities: full ? activities : activities.slice(-1) }
}

export async function submitNewRequest(
  _input: NewRequestInput,
  _sources: PendingSource[],
  _user: CurrentUser,
  progress: SubmitProgress,
): Promise<SubmitResult> {
  progress('Creating the briefing request…')
  await delay(600)
  return { requestId: 'r3', warnings: [] }
}

export async function submitDraft(): Promise<void> {
  await delay()
}

export async function sendClarificationAnswers(): Promise<void> {
  await delay()
}

export async function saveDraftEdits(): Promise<void> {
  await delay()
}

export async function requestRevision(): Promise<void> {
  await delay()
}

export async function approveRequest(): Promise<void> {
  await delay()
}

export async function cancelRequest(): Promise<void> {
  await delay()
}
