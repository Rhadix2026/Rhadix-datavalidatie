import { useState, useEffect, useCallback } from 'react'
import { brandLogo } from '../brand'
import { listTasks, assignableUsers, createTask, updateTask, deleteTask } from '../services/api'
import { STATUS, PRIORITY, StatusPill } from '../components/TaskUI'

const inputStyle = {
  width: '100%', padding: '9px 12px', borderRadius: 'var(--radius)',
  border: '1px solid var(--border)', fontSize: 14, fontFamily: 'var(--font)', boxSizing: 'border-box',
}

export default function Taken({ authUser, onBack }) {
  const isAdmin = authUser?.role === 'ORG_ADMIN' || authUser?.role === 'RHADIX_ADMIN'
  const [scope, setScope]   = useState('mine')
  const [statusF, setStatusF] = useState('')
  const [tasks, setTasks]   = useState([])
  const [users, setUsers]   = useState([])
  const [showNew, setShowNew] = useState(false)
  const [nt, setNt] = useState({ title: '', description: '', priority: 'NORMAAL', due_date: '', assignee_id: '' })
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    listTasks({ scope, status: statusF })
      .then(setTasks).catch(() => setTasks([])).finally(() => setLoading(false))
  }, [scope, statusF])

  useEffect(() => { load() }, [load])
  useEffect(() => { assignableUsers().then(setUsers).catch(() => setUsers([])) }, [])

  const userName = id => (users.find(u => u.id === id)?.name) || ''

  const addTask = async () => {
    if (!nt.title.trim()) return
    await createTask({ ...nt, assignee_id: nt.assignee_id || null, due_date: nt.due_date || null })
    setNt({ title: '', description: '', priority: 'NORMAAL', due_date: '', assignee_id: '' })
    setShowNew(false); load()
  }
  const setStatus = async (t, status) => { await updateTask(t.id, { status }); load() }
  const reassign  = async (t, assignee_id) => { await updateTask(t.id, { assignee_id: assignee_id || null }); load() }
  const remove    = async (t) => { if (confirm('Taak verwijderen?')) { await deleteTask(t.id); load() } }

  const overdue = t => t.due_date && new Date(t.due_date) < new Date()
    && t.status !== 'KLAAR' && t.status !== 'GEANNULEERD'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <header style={{
        background: 'var(--blue-dark)', padding: '0 32px', height: 64, display: 'flex',
        alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100,
      }}>
        <img src={brandLogo()} alt="logo" style={{ height: 40 }} />
        <button onClick={onBack} style={{
          background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
          borderRadius: 'var(--radius)', padding: '6px 14px', color: '#fff', fontSize: 13,
          cursor: 'pointer', fontFamily: 'var(--font)',
        }}>← Terug</button>
      </header>

      <div style={{ maxWidth: 920, margin: '0 auto', padding: '32px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: 'var(--text)', margin: 0 }}>Taken</h1>
            <p style={{ fontSize: 14, color: 'var(--text3)', margin: '4px 0 0' }}>
              Wijs taken toe binnen je organisatie en volg de voortgang.
            </p>
          </div>
          <button onClick={() => setShowNew(v => !v)} style={{
            background: 'var(--rhadix-accent)', color: '#fff', border: 'none', borderRadius: 'var(--radius)',
            padding: '10px 18px', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
          }}>{showNew ? '× Sluiten' : '+ Nieuwe taak'}</button>
        </div>

        {showNew && (
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', padding: 20, marginBottom: 22 }}>
            <input autoFocus placeholder="Titel van de taak" value={nt.title}
                   onChange={e => setNt({ ...nt, title: e.target.value })} style={inputStyle} />
            <textarea placeholder="Omschrijving (optioneel)" value={nt.description}
                      onChange={e => setNt({ ...nt, description: e.target.value })}
                      style={{ ...inputStyle, marginTop: 10, minHeight: 60, resize: 'vertical' }} />
            <div style={{ display: 'flex', gap: 10, marginTop: 10, flexWrap: 'wrap' }}>
              <select value={nt.assignee_id} onChange={e => setNt({ ...nt, assignee_id: e.target.value })} style={{ ...inputStyle, flex: 1, minWidth: 160 }}>
                <option value="">— Toewijzen aan —</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
              </select>
              <select value={nt.priority} onChange={e => setNt({ ...nt, priority: e.target.value })} style={{ ...inputStyle, width: 140 }}>
                {Object.entries(PRIORITY).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
              </select>
              <input type="date" value={nt.due_date} onChange={e => setNt({ ...nt, due_date: e.target.value })} style={{ ...inputStyle, width: 160 }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
              <button onClick={addTask} style={{
                background: 'var(--blue)', color: '#fff', border: 'none', borderRadius: 'var(--radius)',
                padding: '9px 20px', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
              }}>Taak aanmaken</button>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          {[['mine', 'Mijn taken'], ['created', 'Door mij aangemaakt'], ['all', isAdmin ? 'Hele organisatie' : 'Alles van mij']].map(([k, l]) => (
            <button key={k} onClick={() => setScope(k)} style={{
              padding: '7px 14px', borderRadius: 20, fontSize: 13, fontWeight: 600, cursor: 'pointer',
              fontFamily: 'var(--font)', border: '1px solid var(--border)',
              background: scope === k ? 'var(--blue)' : '#fff', color: scope === k ? '#fff' : 'var(--text2)',
            }}>{l}</button>
          ))}
          <select value={statusF} onChange={e => setStatusF(e.target.value)} style={{ ...inputStyle, width: 180, marginLeft: 'auto' }}>
            <option value="">Alle statussen</option>
            {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>

        {loading ? (
          <div style={{ color: 'var(--text3)', padding: 40, textAlign: 'center' }}>Laden…</div>
        ) : tasks.length === 0 ? (
          <div style={{ color: 'var(--text3)', padding: 40, textAlign: 'center', background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)' }}>
            Geen taken in deze weergave.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {tasks.map(t => (
              <div key={t.id} style={{
                background: '#fff', border: '1px solid var(--border)', borderLeft: `3px solid ${overdue(t) ? 'var(--red)' : (STATUS[t.status]?.color || 'var(--border)')}`,
                borderRadius: 'var(--radius)', padding: '14px 16px', display: 'flex', gap: 14, alignItems: 'flex-start',
              }}>
                <input type="checkbox" checked={t.status === 'KLAAR'} onChange={() => setStatus(t, t.status === 'KLAAR' ? 'OPEN' : 'KLAAR')}
                       style={{ marginTop: 3, cursor: 'pointer', accentColor: 'var(--green)' }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', textDecoration: t.status === 'KLAAR' ? 'line-through' : 'none' }}>{t.title}</div>
                  {t.description && <div style={{ fontSize: 13, color: 'var(--text2)', marginTop: 3 }}>{t.description}</div>}
                  {t.source_label && <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 3 }}>🔗 {t.source_label}</div>}
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 8, flexWrap: 'wrap' }}>
                    <StatusPill status={t.status} />
                    <span style={{ fontSize: 11, fontWeight: 700, color: PRIORITY[t.priority]?.color }}>{PRIORITY[t.priority]?.label}</span>
                    {t.due_date && <span style={{ fontSize: 12, color: overdue(t) ? 'var(--red)' : 'var(--text3)' }}>📅 {new Date(t.due_date).toLocaleDateString('nl-NL')}</span>}
                    {t.created_by_name && <span style={{ fontSize: 11, color: 'var(--text3)' }}>door {t.created_by_name}</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' }}>
                  <select value={t.assignee_id || ''} onChange={e => reassign(t, e.target.value)} style={{ ...inputStyle, width: 150, padding: '5px 8px', fontSize: 12 }}>
                    <option value="">— niemand —</option>
                    {users.map(u => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
                  </select>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <select value={t.status} onChange={e => setStatus(t, e.target.value)} style={{ ...inputStyle, width: 130, padding: '5px 8px', fontSize: 12 }}>
                      {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                    </select>
                    <button onClick={() => remove(t)} title="Verwijderen" style={{
                      background: 'none', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                      color: 'var(--text3)', cursor: 'pointer', padding: '4px 9px', fontSize: 13,
                    }}>🗑</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
