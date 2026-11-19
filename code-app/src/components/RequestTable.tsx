import type { BriefingRequest } from '../domain'
import { formatDateTime } from '../format'
import { DueDate, PriorityPill, StatusPill } from './Shared'
import { CLOSED_STATUSES } from '../domain'

export function RequestTable({
  requests,
  open,
  showRequester = false,
  emptyText,
}: {
  requests: BriefingRequest[]
  open: (id: string) => void
  showRequester?: boolean
  emptyText: string
}) {
  if (requests.length === 0) return <div className="empty">{emptyText}</div>
  return (
    <div className="tableWrap">
      <table className="requestTable">
        <thead>
          <tr>
            <th>Request</th>
            <th>Status</th>
            <th>Template</th>
            <th>{showRequester ? 'Requester' : 'Recipient'}</th>
            <th>Priority</th>
            <th>Due</th>
            <th className="hide-md">Updated</th>
          </tr>
        </thead>
        <tbody>
          {requests.map((request) => (
            <tr key={request.id} className="clickRow" onClick={() => open(request.id)}>
              <td className="cellMain">
                <button
                  type="button"
                  className="rowButton"
                  onClick={(event) => {
                    event.stopPropagation()
                    open(request.id)
                  }}
                >
                  <span className="mono">{request.number || 'New'}</span>
                  <span className="truncate" title={request.subject}>
                    {request.subject || '(no subject)'}
                  </span>
                </button>
              </td>
              <td>
                <StatusPill status={request.status} />
              </td>
              <td className="truncateCell" title={request.templateName}>
                {request.templateName || <span className="muted">—</span>}
              </td>
              <td className="truncateCell">
                {showRequester ? (
                  <span title={request.requesterEmail}>{request.requesterName || request.requesterEmail}</span>
                ) : request.recipientName ? (
                  <span title={request.recipientTitle}>
                    {request.recipientName}
                    {request.recipientTitle ? <small className="muted"> · {request.recipientTitle}</small> : null}
                  </span>
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td>
                <PriorityPill priority={request.priority} />
              </td>
              <td>
                <DueDate value={request.dueDate} closed={CLOSED_STATUSES.includes(request.status)} />
              </td>
              <td className="muted small hide-md">{formatDateTime(request.modifiedOn)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
