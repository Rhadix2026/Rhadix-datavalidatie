import { useState, useEffect } from 'react'
import { assignableUsers, createTasksBulk, listTasks, updateTask } from '../services/api'

export const STATUS = {
  OPEN:           { label: 'Open',           color: 'var(--blue)',  bg: 'var(--blue-light)' },
  IN_BEHANDELING: { label: 'In behandeling', color: 'var(--amber)', bg: 'var(--amber-light)' },
  KLAAR:          { label: 'Klaar',          color: 'var(--green)', bg: 'var(--green-light)' },
  GEANNULEERD:    { label: 'Geannuleerd',    color: 'var(--text3)', bg: 'var(--border)' },
}
export const PRIORITY = {
  LAAG:    { label: 'Laag',    color: 'var(--text3)' },
  NORMAAL: { label: 'Normaal', color: 'var(--blue)' },
  HOOG:    { label: 'Hoog',    color: 'var(--red)' },
}

export function StatusPill({ status }) {
  const s = STATUS[status] || STATUS.OPEN
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: '2px 9px', borderRadius: 20,
      color: s.color, background: s.bg, whiteSpace: 'nowrap',
    }}>{s.label}</span>
  )
}

const overlay = {
  position: 'fixed', inset: 0, background: 'rgba(15,23,42,.45)', zIndex: 1000,
  display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
}
const modal = {
  background: '#fff', borderRadius: 'var(--radius-xl)', padding: 28, width: 'min(520px, 94vw)',
  boxShadow: '0 12px 40px rgba(0,0,0,.25)', maxHeight: '88vh', overflowY: 'auto',
}
const inputStyle = {
  width: '100%', padding: '9px 12px', borderRadius: 'var(--radius)',
  border: '1px solid var(--border)', fontSize: 14, fontFamily: 'var(--font)', boxSizing: 'border-box',
}

/**
 * Herbruikbare knop: maak van een set bevindingen taken en wijs ze toe.
 * items: [{ title, source_label?, priority? }]
 */
export function MaakTakenButton({ items = [], sourceType = 'handmatig', sourceRef = null,
                                  buttonLabel = '✓ Maak taken', onDone }) {
  const [open, setOpen]     = useState(false)
  const [users, setUsers]   = useState([])
  const [assignee, setAssignee] = useState('')
  const [busy, setBusy]     = useState(false)
  const [done, setDone]     = useState(null)
  const [selected, setSelected] = useState(() => new Set())
  const allSelected = items.length > 0 && selected.size === items.length
  const toggle = (i) => setSelected(prev => { const n = new Set(prev); n.has(i) ? n.delete(i) : n.add(i); return n })
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(items.map((_, i) => i)))

  useEffect(() => {
    if (open) {
      assignableUsers().then(setUsers).catch(() => setUsers([]))
      setSelected(new Set(items.map((_, i) => i)))
    }
  }, [open])

  const submit = async () => {
    const chosen = items.filter((_, i) => selected.has(i))
    if (!chosen.length) return
    setBusy(true)
    try {
      const res = await createTasksBulk({
        items: chosen.map(it => ({ title: it.title, source_label: it.source_label || null,
                                   priority: it.priority || 'NORMAAL' })),
        assignee_id: assignee || null, source_type: sourceType, source_ref: sourceRef,
      })
      setDone(res.created)
      onDone && onDone(res)
    } catch (e) {
      alert('Aanmaken mislukt: ' + e.message)
    } finally { setBusy(false) }
  }

  if (!items.length) return null
  return (
    <>
      <button onClick={() => { setOpen(true); setDone(null) }} style={{
        background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)',
        padding: '9px 16px', fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
      }}>{buttonLabel} ({items.length})</button>

      {open && (
        <div style={overlay} onClick={() => !busy && setOpen(false)}>
          <div style={modal} onClick={e => e.stopPropagation()}>
            {done == null ? (
              <>
                <h3 style={{ margin: '0 0 6px', fontSize: 18, color: 'var(--text)' }}>Taken aanmaken</h3>
                <p style={{ margin: '0 0 16px', fontSize: 13, color: 'var(--text3)' }}>
                  Er worden <b>{selected.size}</b> van {items.length} bevindingen als taak aangemaakt.
                </p>
                <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--text2)' }}>Toewijzen aan</label>
                <select value={assignee} onChange={e => setAssignee(e.target.value)} style={{ ...inputStyle, marginTop: 6 }}>
                  <option value="">— Niemand (later toewijzen) —</option>
                  {users.map(u => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
                </select>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, fontSize: 12.5, fontWeight: 700, color: 'var(--text2)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={allSelected} onChange={toggleAll} />
                  Alles selecteren ({selected.size}/{items.length})
                </label>
                <div style={{
                  marginTop: 8, maxHeight: 200, overflowY: 'auto', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)', padding: 6, fontSize: 12, color: 'var(--text2)',
                }}>
                  {items.slice(0, 200).map((it, i) => (
                    <label key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '5px 4px', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}>
                      <input type="checkbox" checked={selected.has(i)} onChange={() => toggle(i)} style={{ marginTop: 2 }} />
                      <span>{it.title}{it.source_label ? <span style={{ color: 'var(--text3)' }}> — {it.source_label}</span> : null}</span>
                    </label>
                  ))}
                  {items.length > 200 && <div style={{ paddingTop: 6, color: 'var(--text3)' }}>…en nog {items.length - 200}</div>}
                </div>
                <div style={{ display: 'flex', gap: 10, marginTop: 18, justifyContent: 'flex-end' }}>
                  <button onClick={() => setOpen(false)} disabled={busy} style={btnGhost}>Annuleren</button>
                  <button onClick={submit} disabled={busy || selected.size === 0} style={{ ...btnPrimary, opacity: (busy || selected.size === 0) ? 0.6 : 1 }}>{busy ? 'Bezig…' : `Aanmaken (${selected.size})`}</button>
                </div>
              </>
            ) : (
              <>
                <h3 style={{ margin: '0 0 8px', fontSize: 18, color: 'var(--green)' }}>✓ {done} taken aangemaakt</h3>
                <p style={{ fontSize: 13, color: 'var(--text3)' }}>Je vindt ze terug onder “Mijn taken”.</p>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
                  <button onClick={() => setOpen(false)} style={btnPrimary}>Sluiten</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}

const btnPrimary = {
  background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)',
  padding: '9px 18px', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
}
const btnGhost = {
  background: 'transparent', color: 'var(--text2)', border: '1px solid var(--border)',
  borderRadius: 'var(--radius)', padding: '9px 18px', fontSize: 14, cursor: 'pointer', fontFamily: 'var(--font)',
}

/** Compacte "Mijn taken"-widget voor op het dashboard/landing. */
export function MijnTakenWidget({ onOpen }) {
  const [tasks, setTasks] = useState(null)

  const load = () => listTasks({ scope: 'mine' })
    .then(ts => setTasks(ts.filter(t => t.status === 'OPEN' || t.status === 'IN_BEHANDELING')))
    .catch(() => setTasks([]))
  useEffect(() => { load() }, [])

  const toggle = async (t) => {
    await updateTask(t.id, { status: t.status === 'KLAAR' ? 'OPEN' : 'KLAAR' })
    load()
  }

  return (
    <div style={{
      background: '#fff', borderRadius: 'var(--radius-xl)', padding: '18px 20px', marginBottom: 24,
      border: '1px solid var(--border)', boxShadow: '0 2px 12px rgba(0,0,0,.06)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase',
          color: 'var(--rhadix-sub)', fontFamily: 'var(--font-brand)',
        }}>Mijn taken</span>
        <button onClick={onOpen} style={{
          background: 'none', border: 'none', color: 'var(--blue)', fontSize: 12,
          fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
        }}>Alle taken →</button>
      </div>
      {tasks == null ? (
        <div style={{ fontSize: 13, color: 'var(--text3)' }}>Laden…</div>
      ) : tasks.length === 0 ? (
        <div style={{ fontSize: 13, color: 'var(--text3)' }}>Geen openstaande taken 🎉</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {tasks.slice(0, 5).map(t => (
            <div key={t.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
              <input type="checkbox" checked={false} onChange={() => toggle(t)}
                     style={{ marginTop: 3, cursor: 'pointer', accentColor: 'var(--blue)' }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 500, lineHeight: 1.3 }}>{t.title}</div>
                {t.source_label && <div style={{ fontSize: 11, color: 'var(--text3)' }}>{t.source_label}</div>}
              </div>
              {t.priority === 'HOOG' && <span style={{ fontSize: 10, color: 'var(--red)', fontWeight: 700 }}>HOOG</span>}
            </div>
          ))}
          {tasks.length > 5 && (
            <button onClick={onOpen} style={{
              background: 'none', border: 'none', color: 'var(--text3)', fontSize: 12,
              cursor: 'pointer', textAlign: 'left', padding: '4px 0', fontFamily: 'var(--font)',
            }}>+ {tasks.length - 5} meer…</button>
          )}
        </div>
      )}
    </div>
  )
}
