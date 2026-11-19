import { useState } from 'react'
import { countWords, type DraftSection } from '../domain'
import { IconDown, IconTrash, IconUp } from '../icons'
import { Message } from './Shared'

export interface DraftEdits {
  noteTitle: string
  keyMessage: string
  sections: DraftSection[]
}

interface Keyed extends DraftSection {
  key: string
}

export function DraftEditor({
  initial,
  saving,
  error,
  onSave,
  onCancel,
}: {
  initial: DraftEdits
  saving: boolean
  error: string | null
  onSave: (edits: DraftEdits) => void
  onCancel: () => void
}) {
  const [noteTitle, setNoteTitle] = useState(initial.noteTitle)
  const [keyMessage, setKeyMessage] = useState(initial.keyMessage)
  const [sections, setSections] = useState<Keyed[]>(() =>
    initial.sections.map((s) => ({ ...s, key: crypto.randomUUID() })),
  )

  const update = (key: string, patch: Partial<DraftSection>) =>
    setSections((previous) => previous.map((s) => (s.key === key ? { ...s, ...patch } : s)))
  const move = (index: number, delta: number) =>
    setSections((previous) => {
      const next = [...previous]
      const target = index + delta
      if (target < 0 || target >= next.length) return previous
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })

  const words = countWords(noteTitle, keyMessage, ...sections.map((s) => `${s.heading} ${s.body}`))

  return (
    <div className="draftEditor">
      <div className="field">
        <label htmlFor="edit-title">Note title</label>
        <input id="edit-title" maxLength={300} value={noteTitle} onChange={(e) => setNoteTitle(e.target.value)} disabled={saving} />
      </div>
      <div className="field">
        <label htmlFor="edit-key">Key message</label>
        <textarea id="edit-key" maxLength={2000} value={keyMessage} onChange={(e) => setKeyMessage(e.target.value)} disabled={saving} />
      </div>
      <p className="muted small">
        Section text is plain: start a line with “- ” for a bullet and keep citations such as [S1].
      </p>
      {sections.map((section, index) => (
        <div className="sectionEdit" key={section.key}>
          <div className="sectionEdit__bar">
            <input
              aria-label={`Heading of section ${index + 1}`}
              className="sectionEdit__heading"
              value={section.heading}
              placeholder="Section heading"
              onChange={(e) => update(section.key, { heading: e.target.value })}
              disabled={saving}
            />
            <button type="button" className="iconBtn" title="Move up" aria-label="Move section up" disabled={saving || index === 0} onClick={() => move(index, -1)}>
              <IconUp size={16} />
            </button>
            <button
              type="button"
              className="iconBtn"
              title="Move down"
              aria-label="Move section down"
              disabled={saving || index === sections.length - 1}
              onClick={() => move(index, 1)}
            >
              <IconDown size={16} />
            </button>
            <button
              type="button"
              className="iconBtn danger"
              title="Remove section"
              aria-label="Remove section"
              disabled={saving}
              onClick={() => setSections((previous) => previous.filter((s) => s.key !== section.key))}
            >
              <IconTrash size={16} />
            </button>
          </div>
          <textarea
            aria-label={`Body of section ${index + 1}`}
            className="sectionEdit__body"
            value={section.body}
            onChange={(e) => update(section.key, { body: e.target.value })}
            disabled={saving}
          />
        </div>
      ))}
      <button
        type="button"
        className="btn outline"
        disabled={saving}
        onClick={() => setSections((previous) => [...previous, { key: crypto.randomUUID(), heading: '', body: '' }])}
      >
        + Add section
      </button>
      {error ? <Message kind="error">{error}</Message> : null}
      <div className="editorActions">
        <span className="muted small">{words.toLocaleString()} words</span>
        <div className="inline">
          <button type="button" className="btn" onClick={onCancel} disabled={saving}>
            Discard changes
          </button>
          <button
            type="button"
            className="btn primary"
            disabled={saving}
            onClick={() => onSave({ noteTitle, keyMessage, sections: sections.map(({ heading, body }) => ({ heading, body })) })}
          >
            {saving ? 'Saving…' : 'Save draft'}
          </button>
        </div>
      </div>
    </div>
  )
}
