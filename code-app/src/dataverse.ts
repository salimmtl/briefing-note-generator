import { getContext } from '@microsoft/power-apps/app'
import type { IOperationResult } from '@microsoft/power-apps/data'
import { Brn_activitiesService } from './generated/services/Brn_activitiesService'
import { Brn_profilesService } from './generated/services/Brn_profilesService'
import { Brn_requestsService } from './generated/services/Brn_requestsService'
import { Brn_sourcedocumentsService } from './generated/services/Brn_sourcedocumentsService'
import { Brn_templatesService } from './generated/services/Brn_templatesService'
import type { Brn_activities } from './generated/models/Brn_activitiesModel'
import type { Brn_profiles } from './generated/models/Brn_profilesModel'
import type { Brn_requests } from './generated/models/Brn_requestsModel'
import type { Brn_sourcedocuments } from './generated/models/Brn_sourcedocumentsModel'
import type { Brn_templates } from './generated/models/Brn_templatesModel'
import {
  ActivityType,
  Actor,
  CANCELLABLE_STATUSES,
  ExtractionStatus,
  IntakeChannel,
  MAX_EXTRACTED_CHARS,
  RequestStatus,
  STATUS_LABELS,
  countWords,
  isAssignedReviewer,
  parseSections,
  type Activity,
  type BriefingRequest,
  type CurrentUser,
  type DraftSection,
  type NewRequestInput,
  type PendingSource,
  type Profile,
  type SourceDocument,
  type SubmitResult,
  type Template,
} from './domain'

const REQUEST_SELECT = [
  'brn_requestid',
  'brn_name',
  'brn_requestnumber',
  'brn_status',
  'brn_requestername',
  'brn_requesteremail',
  'brn_recipientname',
  'brn_recipienttitle',
  'brn_recipientemail',
  'brn_revieweremail',
  'brn_purpose',
  'brn_additionalcontext',
  'brn_language',
  'brn_classification',
  'brn_priority',
  'brn_duedate',
  'brn_deliverymode',
  'brn_clarificationquestions',
  'brn_clarificationanswers',
  'brn_clarificationrounds',
  'brn_reviewercomments',
  'brn_notetitle',
  'brn_keymessage',
  'brn_draftsections',
  'brn_sourcesused',
  'brn_verificationnotes',
  'brn_confidence',
  'brn_wordcount',
  'brn_draftversion',
  'brn_draftpdfurl',
  'brn_finalpdfurl',
  'brn_sharepointfolderurl',
  'brn_submittedon',
  'brn_draftedon',
  'brn_approvedby',
  'brn_approvedon',
  'brn_deliveredon',
  'brn_lasterror',
  '_brn_profileid_value',
  '_brn_templateid_value',
  'createdon',
  'modifiedon',
]

/** Lighter column set for lists and the overview (no draft bodies or long text). */
const REQUEST_LIST_SELECT = [
  'brn_requestid',
  'brn_name',
  'brn_requestnumber',
  'brn_status',
  'brn_requestername',
  'brn_requesteremail',
  'brn_recipientname',
  'brn_recipienttitle',
  'brn_revieweremail',
  'brn_priority',
  'brn_duedate',
  'brn_language',
  'brn_classification',
  'brn_submittedon',
  'brn_draftedon',
  'brn_deliveredon',
  '_brn_profileid_value',
  '_brn_templateid_value',
  'createdon',
  'modifiedon',
]

const SOURCE_SELECT = [
  'brn_sourcedocumentid',
  'brn_name',
  'brn_sourcelabel',
  'brn_documenttype',
  'brn_extractionstatus',
  'brn_pagecount',
  'brn_charactercount',
  'brn_summary',
  'brn_file_name',
]

const ACTIVITY_SELECT = [
  'brn_activityid',
  'brn_name',
  'brn_actor',
  'brn_activitytype',
  'brn_details',
  'brn_startedon',
  'brn_completedon',
  'brn_durationseconds',
  'createdon',
]

function requireData<T>(result: IOperationResult<T>, action: string): T {
  if (!result.success) {
    throw new Error(`${action} failed: ${result.error?.message ?? 'Dataverse rejected the request.'}`)
  }
  if (result.data === undefined || result.data === null) {
    throw new Error(`${action} failed: Dataverse returned no data.`)
  }
  return result.data
}

function requireSuccess<T>(result: IOperationResult<T>, action: string): void {
  if (!result.success) {
    throw new Error(`${action} failed: ${result.error?.message ?? 'Dataverse rejected the request.'}`)
  }
}

export function escapeOData(value: string): string {
  return value.replace(/'/g, "''")
}

const text = (value: unknown): string => (typeof value === 'string' ? value : '')
const num = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null)
const str = (value: unknown): string | null => (typeof value === 'string' && value ? value : null)

export async function getCurrentUser(): Promise<CurrentUser> {
  const context = await getContext()
  const upn = context.user.userPrincipalName ?? ''
  if (!upn) throw new Error('Power Apps did not return the signed-in user principal name.')
  return { upn, fullName: context.user.fullName || upn }
}

function toProfile(row: Brn_profiles): Profile {
  return {
    id: row.brn_profileid,
    name: text(row.brn_name),
    code: text(row.brn_code),
    defaultLanguage: num(row.brn_defaultlanguage),
    defaultReviewerEmail: text(row.brn_defaultrevieweremail),
    leaderTitles: text(row.brn_leadertitles),
  }
}

function toTemplate(row: Brn_templates): Template {
  return {
    id: row.brn_templateid,
    name: text(row.brn_name),
    code: text(row.brn_code),
    noteType: num(row.brn_notetype),
    whenToUse: text(row.brn_whentouse),
    sections: text(row.brn_sections),
    maxWords: num(row.brn_maxwords),
    sortOrder: num(row.brn_sortorder) ?? 0,
  }
}

function toRequest(row: Brn_requests, profiles: Profile[], templates: Template[]): BriefingRequest {
  const profileId = str(row._brn_profileid_value)
  const templateId = str(row._brn_templateid_value)
  const parsed = parseSections(row.brn_draftsections)
  return {
    id: row.brn_requestid,
    number: text(row.brn_requestnumber),
    subject: text(row.brn_name),
    status: num(row.brn_status) ?? RequestStatus.Draft,
    requesterName: text(row.brn_requestername),
    requesterEmail: text(row.brn_requesteremail),
    recipientName: text(row.brn_recipientname),
    recipientTitle: text(row.brn_recipienttitle),
    recipientEmail: text(row.brn_recipientemail),
    reviewerEmail: text(row.brn_revieweremail),
    purpose: text(row.brn_purpose),
    additionalContext: text(row.brn_additionalcontext),
    language: num(row.brn_language),
    classification: num(row.brn_classification),
    priority: num(row.brn_priority),
    dueDate: str(row.brn_duedate),
    deliveryMode: num(row.brn_deliverymode),
    clarificationQuestions: text(row.brn_clarificationquestions),
    clarificationAnswers: text(row.brn_clarificationanswers),
    clarificationRounds: num(row.brn_clarificationrounds) ?? 0,
    reviewerComments: text(row.brn_reviewercomments),
    noteTitle: text(row.brn_notetitle),
    keyMessage: text(row.brn_keymessage),
    draftSections: parsed.sections,
    draftSectionsError: parsed.error,
    sourcesUsed: text(row.brn_sourcesused),
    verificationNotes: text(row.brn_verificationnotes),
    confidence: num(row.brn_confidence),
    wordCount: num(row.brn_wordcount),
    draftVersion: num(row.brn_draftversion),
    draftPdfUrl: text(row.brn_draftpdfurl),
    finalPdfUrl: text(row.brn_finalpdfurl),
    sharePointFolderUrl: text(row.brn_sharepointfolderurl),
    submittedOn: str(row.brn_submittedon),
    draftedOn: str(row.brn_draftedon),
    approvedBy: text(row.brn_approvedby),
    approvedOn: str(row.brn_approvedon),
    deliveredOn: str(row.brn_deliveredon),
    lastError: text(row.brn_lasterror),
    profileId,
    profileName: profiles.find((p) => p.id === profileId)?.name ?? text(row.brn_profileidname),
    templateId,
    templateName: templates.find((t) => t.id === templateId)?.name ?? text(row.brn_templateidname),
    createdOn: str(row.createdon),
    modifiedOn: str(row.modifiedon),
  }
}

function toSource(row: Brn_sourcedocuments): SourceDocument {
  return {
    id: row.brn_sourcedocumentid,
    name: text(row.brn_name),
    label: text(row.brn_sourcelabel),
    documentType: num(row.brn_documenttype),
    extractionStatus: num(row.brn_extractionstatus),
    pageCount: num(row.brn_pagecount),
    characterCount: num(row.brn_charactercount),
    summary: text(row.brn_summary),
    hasFile: Boolean(row.brn_file_name),
  }
}

function toActivity(row: Brn_activities): Activity {
  return {
    id: row.brn_activityid,
    name: text(row.brn_name),
    actor: num(row.brn_actor),
    activityType: num(row.brn_activitytype),
    details: text(row.brn_details),
    startedOn: str(row.brn_startedon),
    completedOn: str(row.brn_completedon),
    durationSeconds: num(row.brn_durationseconds),
    createdOn: str(row.createdon),
  }
}

export interface Reference {
  profiles: Profile[]
  templates: Template[]
}

/** Active profiles and templates (templates sorted by sort order). */
export async function loadReference(): Promise<Reference> {
  const [profiles, templates] = await Promise.all([
    Brn_profilesService.getAll({
      select: [
        'brn_profileid',
        'brn_name',
        'brn_code',
        'brn_defaultlanguage',
        'brn_defaultrevieweremail',
        'brn_leadertitles',
      ],
      filter: 'brn_isactive eq true',
      orderBy: ['brn_name asc'],
      top: 100,
    }),
    Brn_templatesService.getAll({
      select: [
        'brn_templateid',
        'brn_name',
        'brn_code',
        'brn_notetype',
        'brn_whentouse',
        'brn_sections',
        'brn_maxwords',
        'brn_sortorder',
      ],
      filter: 'brn_isactive eq true',
      orderBy: ['brn_sortorder asc', 'brn_name asc'],
      top: 100,
    }),
  ])
  return {
    profiles: requireData(profiles, 'Loading briefing profiles').map(toProfile),
    templates: requireData(templates, 'Loading note templates')
      .map(toTemplate)
      .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name)),
  }
}

export async function loadMyRequests(user: CurrentUser, ref: Reference): Promise<BriefingRequest[]> {
  const rows = requireData(
    await Brn_requestsService.getAll({
      select: REQUEST_LIST_SELECT,
      filter: `brn_requesteremail eq '${escapeOData(user.upn)}'`,
      orderBy: ['modifiedon desc'],
      top: 500,
    }),
    'Loading your briefing requests',
  )
  return rows.map((row) => toRequest(row, ref.profiles, ref.templates))
}

/** Every request the user's security role lets them read (review queue and overview). */
export async function loadAllRequests(ref: Reference, statusFilter?: number): Promise<BriefingRequest[]> {
  const rows = requireData(
    await Brn_requestsService.getAll({
      select: REQUEST_LIST_SELECT,
      filter: statusFilter === undefined ? undefined : `brn_status eq ${statusFilter}`,
      orderBy: ['modifiedon desc'],
      top: 2000,
    }),
    'Loading briefing requests',
  )
  return rows.map((row) => toRequest(row, ref.profiles, ref.templates))
}

export interface RequestBundle {
  request: BriefingRequest
  sources: SourceDocument[]
  activities: Activity[]
}

export async function loadRequestBundle(id: string, ref: Reference): Promise<RequestBundle> {
  const [request, sources, activities] = await Promise.all([
    Brn_requestsService.get(id, { select: REQUEST_SELECT }),
    Brn_sourcedocumentsService.getAll({
      select: SOURCE_SELECT,
      filter: `_brn_requestid_value eq ${id}`,
      orderBy: ['brn_sourcelabel asc'],
      top: 200,
    }),
    Brn_activitiesService.getAll({
      select: ACTIVITY_SELECT,
      filter: `_brn_requestid_value eq ${id}`,
      orderBy: ['createdon desc'],
      top: 500,
    }),
  ])
  const sorted = requireData(sources, 'Loading source documents')
    .map(toSource)
    .sort((a, b) => a.label.localeCompare(b.label, undefined, { numeric: true }))
  return {
    request: toRequest(requireData(request, 'Loading the briefing request'), ref.profiles, ref.templates),
    sources: sorted,
    activities: requireData(activities, 'Loading the activity timeline')
      .map(toActivity)
      .sort((a, b) => (b.createdOn ?? '').localeCompare(a.createdOn ?? '')),
  }
}

async function logActivity(
  requestId: string,
  actor: number,
  activityType: number,
  name: string,
  details?: string,
): Promise<void> {
  const now = new Date().toISOString()
  requireSuccess(
    await Brn_activitiesService.create({
      brn_name: name.slice(0, 300),
      brn_actor: actor,
      brn_activitytype: activityType,
      brn_details: details ? details.slice(0, 8000) : undefined,
      brn_startedon: now,
      brn_completedon: now,
      brn_durationseconds: 0,
      'brn_RequestId@odata.bind': `/brn_requests(${requestId})`,
    } as never),
    'Logging the activity',
  )
}

/**
 * Logs an activity after the request itself was already updated. The update stands, so a logging failure
 * is returned as a warning (shown to the user) instead of an error that would invite a repeated update.
 */
async function logActivityAfterUpdate(...args: Parameters<typeof logActivity>): Promise<string | null> {
  try {
    await logActivity(...args)
    return null
  } catch (err) {
    return `The change was saved, but the timeline entry wasn't: ${err instanceof Error ? err.message : String(err)}`
  }
}

async function updateRequest(id: string, fields: Record<string, unknown>, action: string): Promise<void> {
  requireSuccess(await Brn_requestsService.update(id, fields as never), action)
}

/** Re-reads the status so a stale page can't overwrite a change someone else (or the workflow) made. */
async function requireStatus(requestId: string, allowed: number[], action: string): Promise<Brn_requests> {
  const current = requireData(
    await Brn_requestsService.get(requestId, {
      select: ['brn_requestid', 'brn_status', 'brn_clarificationanswers', 'brn_revieweremail'],
    }),
    `${action}: reading the current status`,
  )
  const status = num(current.brn_status) ?? RequestStatus.Draft
  if (!allowed.includes(status)) {
    throw new Error(
      `${action} isn't possible: the request is now "${STATUS_LABELS[status] ?? 'Unknown'}". The page has been refreshed.`,
    )
  }
  return current
}

/** Re-checks (on the latest record) that the signed-in user is the assigned reviewer. */
function requireReviewer(current: Brn_requests, user: CurrentUser, action: string): void {
  if (!isAssignedReviewer(current.brn_revieweremail, user.upn)) {
    const reviewer = text(current.brn_revieweremail).trim()
    throw new Error(
      `${action} isn't allowed: only the assigned reviewer ${reviewer ? `(${reviewer}) ` : ''}can review this request` +
        `${reviewer ? '' : ', and none is assigned'}. You are signed in as ${user.upn}.`,
    )
  }
}

/** Thrown by submitNewRequest after the request record exists, so the page never creates a second one. */
export class SubmitError extends Error {
  readonly requestId: string

  constructor(message: string, requestId: string, cause?: unknown) {
    super(message, { cause })
    this.name = 'SubmitError'
    this.requestId = requestId
  }
}

export type SubmitProgress = (message: string) => void

/**
 * Creates the request as Draft, adds each source (text + original file), then submits it.
 * Throws if the request or a source record can't be created (SubmitError once the request exists);
 * file upload and timeline failures become warnings.
 */
export async function submitNewRequest(
  input: NewRequestInput,
  sources: PendingSource[],
  user: CurrentUser,
  progress: SubmitProgress,
): Promise<SubmitResult> {
  const warnings: string[] = []
  progress('Creating the briefing request…')
  const record: Record<string, unknown> = {
    brn_name: input.subject.trim().slice(0, 300),
    brn_status: RequestStatus.Draft,
    brn_intakechannel: IntakeChannel.BriefingStudio,
    brn_requesteremail: user.upn,
    brn_requestername: user.fullName,
    brn_recipientname: input.recipientName.trim() || undefined,
    brn_recipienttitle: input.recipientTitle.trim() || undefined,
    brn_recipientemail: input.recipientEmail.trim() || undefined,
    brn_revieweremail: input.reviewerEmail.trim() || undefined,
    brn_purpose: input.purpose.trim(),
    brn_additionalcontext: input.additionalContext.trim() || undefined,
    brn_language: input.language,
    brn_classification: input.classification,
    brn_priority: input.priority,
    brn_duedate: input.dueDate || undefined,
    brn_deliverymode: input.deliveryMode,
  }
  if (input.profileId) record['brn_ProfileId@odata.bind'] = `/brn_profiles(${input.profileId})`
  if (input.templateId) record['brn_TemplateId@odata.bind'] = `/brn_templates(${input.templateId})`
  const created = requireData(await Brn_requestsService.create(record as never), 'Creating the briefing request')
  const requestId = created.brn_requestid
  const savedAsDraft = ' The request was saved as a Draft: open it to add anything missing and submit it.'

  for (const [index, source] of sources.entries()) {
    const sourceLabel = `S${index + 1}`
    progress(`Saving ${sourceLabel} – ${source.file.name}…`)
    const extracted = source.state === 'extracted'
    const textValue = source.text.length > MAX_EXTRACTED_CHARS ? source.text.slice(0, MAX_EXTRACTED_CHARS) : source.text
    if (source.text.length > MAX_EXTRACTED_CHARS) {
      warnings.push(`${sourceLabel} (${source.file.name}): text truncated to ${MAX_EXTRACTED_CHARS.toLocaleString()} characters.`)
    }
    let documentId: string
    try {
      const doc = requireData(
        await Brn_sourcedocumentsService.create({
          brn_name: source.file.name.slice(0, 300),
          brn_sourcelabel: sourceLabel,
          brn_documenttype: source.documentType,
          brn_extractedtext: textValue || undefined,
          brn_extractionstatus: extracted
            ? ExtractionStatus.Extracted
            : source.state === 'unsupported'
              ? ExtractionStatus.NotSupported
              : ExtractionStatus.Failed,
          brn_pagecount: source.pageCount ?? undefined,
          brn_charactercount: textValue.length,
          'brn_RequestId@odata.bind': `/brn_requests(${requestId})`,
        } as never),
        `Saving source ${sourceLabel} (${source.file.name})`,
      )
      documentId = doc.brn_sourcedocumentid
    } catch (err) {
      throw new SubmitError(`${err instanceof Error ? err.message : String(err)}${savedAsDraft}`, requestId, err)
    }
    progress(`Uploading the original file for ${sourceLabel}…`)
    try {
      const uploaded = await Brn_sourcedocumentsService.upload(documentId, 'brn_file', source.file, source.file.name)
      if (!uploaded.success) throw new Error(uploaded.error?.message ?? 'File upload failed.')
    } catch (err) {
      warnings.push(
        `${sourceLabel} (${source.file.name}): the original file wasn't attached (${
          err instanceof Error ? err.message : String(err)
        }). The extracted text was saved.`,
      )
    }
  }

  progress('Submitting the request…')
  try {
    await updateRequest(
      requestId,
      { brn_status: RequestStatus.Submitted, brn_submittedon: new Date().toISOString() },
      'Submitting the request',
    )
  } catch (err) {
    throw new SubmitError(`${err instanceof Error ? err.message : String(err)}${savedAsDraft}`, requestId, err)
  }
  const logWarning = await logActivityAfterUpdate(
    requestId,
    Actor.Requester,
    ActivityType.Submitted,
    `Submitted by ${user.fullName}`,
    `Submitted from Briefing Studio with ${sources.length} source document(s).`,
  )
  if (logWarning) warnings.push(logWarning)
  return { requestId, warnings }
}

/** The result of an action on an existing request: a warning when the change saved but the timeline entry didn't. */
export type ActionWarning = string | null

/** Moves a Draft to Submitted and logs it. */
export async function submitDraft(requestId: string, user: CurrentUser, sourceCount: number): Promise<ActionWarning> {
  await requireStatus(requestId, [RequestStatus.Draft], 'Submitting')
  await updateRequest(
    requestId,
    { brn_status: RequestStatus.Submitted, brn_submittedon: new Date().toISOString(), brn_lasterror: null },
    'Submitting the request',
  )
  return logActivityAfterUpdate(
    requestId,
    Actor.Requester,
    ActivityType.Submitted,
    `Submitted by ${user.fullName}`,
    `Submitted from Briefing Studio with ${sourceCount} source document(s).`,
  )
}

function formatRoundDate(date: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

export async function sendClarificationAnswers(requestId: string, answers: string, user: CurrentUser): Promise<ActionWarning> {
  const current = await requireStatus(requestId, [RequestStatus.NeedsInfo], 'Sending answers')
  const previous = text(current.brn_clarificationanswers).trim()
  const round = (previous.match(/^Round \d+ \(/gm)?.length ?? 0) + 1
  const entry = `Round ${round} (${formatRoundDate(new Date())}):\n${answers.trim()}`
  const combined = previous ? `${previous}\n\n${entry}` : entry
  if (combined.length > 10000) {
    throw new Error(
      `Answers are too long: all rounds together must stay under 10,000 characters (now ${combined.length.toLocaleString()}).`,
    )
  }
  await updateRequest(
    requestId,
    { brn_clarificationanswers: combined, brn_status: RequestStatus.InfoProvided },
    'Sending your answers',
  )
  return logActivityAfterUpdate(
    requestId,
    Actor.Requester,
    ActivityType.ClarificationProvided,
    `Clarification provided by ${user.fullName} (round ${round})`,
    answers.trim(),
  )
}

export async function saveDraftEdits(
  requestId: string,
  noteTitle: string,
  keyMessage: string,
  sections: DraftSection[],
  user: CurrentUser,
): Promise<ActionWarning> {
  const current = await requireStatus(requestId, [RequestStatus.InReview], 'Saving the draft')
  requireReviewer(current, user, 'Saving the draft')
  const clean = sections
    .map((s) => ({ heading: s.heading.trim(), body: s.body.replace(/\s+$/g, '') }))
    .filter((s) => s.heading || s.body)
  const words = countWords(noteTitle, keyMessage, ...clean.map((s) => `${s.heading} ${s.body}`))
  await updateRequest(
    requestId,
    {
      brn_notetitle: noteTitle.trim().slice(0, 300),
      brn_keymessage: keyMessage.trim(),
      brn_draftsections: JSON.stringify(clean),
      brn_wordcount: words,
    },
    'Saving the draft',
  )
  return logActivityAfterUpdate(
    requestId,
    Actor.Reviewer,
    ActivityType.Note,
    'Draft edited by reviewer',
    `Edited by ${user.upn}. ${clean.length} section(s), ${words} words.`,
  )
}

export async function requestRevision(requestId: string, comments: string, user: CurrentUser): Promise<ActionWarning> {
  const current = await requireStatus(requestId, [RequestStatus.InReview], 'Requesting a revision')
  requireReviewer(current, user, 'Requesting a revision')
  await updateRequest(
    requestId,
    { brn_reviewercomments: comments.trim(), brn_status: RequestStatus.RevisionRequested },
    'Requesting a revision',
  )
  return logActivityAfterUpdate(
    requestId,
    Actor.Reviewer,
    ActivityType.RevisionRequested,
    `Revision requested by ${user.fullName}`,
    comments.trim(),
  )
}

export async function approveRequest(requestId: string, user: CurrentUser): Promise<ActionWarning> {
  const current = await requireStatus(requestId, [RequestStatus.InReview], 'Approving')
  requireReviewer(current, user, 'Approving')
  await updateRequest(
    requestId,
    { brn_approvedby: user.upn, brn_approvedon: new Date().toISOString(), brn_status: RequestStatus.Approved },
    'Approving the draft',
  )
  return logActivityAfterUpdate(
    requestId,
    Actor.Reviewer,
    ActivityType.Approved,
    `Approved by ${user.fullName}`,
    `Approved by ${user.upn}.`,
  )
}

export async function cancelRequest(request: BriefingRequest, user: CurrentUser, reason: string): Promise<ActionWarning> {
  await requireStatus(request.id, CANCELLABLE_STATUSES, 'Cancelling')
  await updateRequest(request.id, { brn_status: RequestStatus.Cancelled }, 'Cancelling the request')
  const isRequester = request.requesterEmail.toLowerCase() === user.upn.toLowerCase()
  return logActivityAfterUpdate(
    request.id,
    isRequester ? Actor.Requester : Actor.Reviewer,
    ActivityType.Cancelled,
    `Cancelled by ${user.fullName}`,
    reason.trim() || undefined,
  )
}
