import { useState, useRef, useCallback } from 'react'
import { Nav, NavBack, Page, PageTitle, BtnPrimary } from '../components/UI'
import { uploadFiles } from '../services/api'

export default function Upload({ systems, onNext, onBack }) {
  const [files, setFiles]     = useState([])
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading]  = useState(false)
  const [error, setError]      = useState(null)
  const inputRef               = useRef()

  const addFiles = useCallback((newFiles) => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...[...newFiles].filter(f => !existing.has(f.name))]
    })
  }, [])

  const onDrop = e => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }

  const submit = async () => {
    if (!files.length) return
    setLoading(true); setError(null)
    try {
      const result = await uploadFiles(files, `Scan — ${systems.join(', ')}`)
      onNext(result)
    } catch (e) {
      setError('Upload mislukt. Controleer of de backend actief is.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Page>
        <PageTitle
          title="Upload databestanden"
          sub="Upload uw data-export of koppel via API"
        />

        {/* Drop zone */}
        <div
          onDrop={onDrop}
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onClick={() => inputRef.current.click()}
          style={{
            border: `2px dashed ${dragging ? 'var(--blue)' : '#c9d0db'}`,
            borderRadius: 'var(--radius-xl)', padding: '52px 24px',
            textAlign: 'center', cursor: 'pointer', transition: 'all .2s',
            background: dragging ? 'var(--blue-light)' : '#fff', marginBottom: 12,
          }}
        >
          <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" multiple
            style={{ display: 'none' }} onChange={e => addFiles(e.target.files)} />
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 14px', display: 'block' }}>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text2)', marginBottom: 4 }}>
            Sleep bestanden hierheen of klik om te uploaden
          </p>
          <p style={{ fontSize: 13, color: 'var(--text3)' }}>CSV, XML of JSON bestanden</p>
        </div>

        {/* Uploaded files */}
        {files.map(f => (
          <div key={f.name} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '13px 16px', background: '#fff', borderRadius: 'var(--radius)',
            border: '1px solid var(--border)', marginBottom: 8,
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--blue)" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span style={{ flex: 1, fontSize: 14, color: 'var(--text)', fontWeight: 500 }}>{f.name}</span>
            <span style={{ fontSize: 13, color: 'var(--green)', fontWeight: 600 }}>✓ Gereed</span>
            <button onClick={() => setFiles(p => p.filter(x => x.name !== f.name))}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', fontSize: 18 }}>×</button>
          </div>
        ))}

        {error && (
          <div style={{ padding: '10px 14px', background: 'var(--red-bg)', border: '1px solid var(--red-light)', borderRadius: 'var(--radius)', color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>{error}</div>
        )}

        {files.length > 0 && (
          <BtnPrimary onClick={submit} disabled={loading} style={{ marginTop: 8, width: '100%', justifyContent: 'center', padding: '13px' }}>
            {loading ? 'Analyseren…' : 'Start Stap 1: Beschikbaarheid →'}
          </BtnPrimary>
        )}
      </Page>
    </div>
  )
}
