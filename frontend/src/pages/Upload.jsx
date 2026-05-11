import { useState, useRef, useCallback, useEffect } from 'react'
import { Nav, NavBack, Page, PageTitle, BtnPrimary } from '../components/UI'
import { uploadFiles } from '../services/api'

const SCAN_STEPS = [
  { pct: 15, label: 'Bestanden inlezen…',                        icon: '📂' },
  { pct: 40, label: 'Pre-scan: formaat-validatie (BSN, IBAN, datum, postcode…)', icon: '🔍' },
  { pct: 70, label: 'Validatie tegen standaard…',                icon: '📋' },
  { pct: 90, label: 'Resultaten verwerken…',                     icon: '⚙️' },
]

function UploadProgress({ step }) {
  const cfg = SCAN_STEPS[Math.min(step, SCAN_STEPS.length - 1)]
  return (
    <div style={{ marginTop: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
          {cfg.icon} {cfg.label}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text3)', fontWeight: 600 }}>{cfg.pct}%</span>
      </div>
      <div style={{ height: 8, background: 'var(--border)', borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 4,
          background: 'linear-gradient(90deg, var(--blue) 0%, #6366f1 100%)',
          width: `${cfg.pct}%`, transition: 'width .6s ease',
        }} />
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap' }}>
        {SCAN_STEPS.map((s, i) => (
          <span key={i} style={{
            fontSize: 11, padding: '3px 9px', borderRadius: 20,
            background: i <= step ? 'var(--blue-light)' : 'var(--bg)',
            color: i <= step ? 'var(--blue)' : 'var(--text4)',
            border: `1px solid ${i <= step ? 'var(--blue-mid)' : 'var(--border)'}`,
            fontWeight: i === step ? 700 : 500,
            transition: 'all .3s',
          }}>
            {i < step ? '✓ ' : ''}{s.label.split(':')[0].replace('…', '')}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function Upload({ systems, standard = 'kikv', onNext, onBack }) {
  const [files, setFiles]       = useState([])
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading]   = useState(false)
  const [scanStep, setScanStep] = useState(0)
  const [error, setError]       = useState(null)
  const inputRef                = useRef()
  const stepTimers              = useRef([])

  const addFiles = useCallback((newFiles) => {
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...[...newFiles].filter(f => !existing.has(f.name))]
    })
  }, [])

  const onDrop = e => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }

  const submit = async () => {
    if (!files.length) return
    setLoading(true); setError(null); setScanStep(0)

    // Animeer de stappen tijdens het wachten op de server
    const delays = [400, 1400, 2800]
    stepTimers.current = delays.map((d, i) =>
      setTimeout(() => setScanStep(i + 1), d)
    )

    try {
      const result = await uploadFiles(files, `Scan — ${systems.join(', ')}`, standard)
      stepTimers.current.forEach(clearTimeout)
      setScanStep(SCAN_STEPS.length - 1)
      setTimeout(() => onNext(result), 300)
    } catch (e) {
      stepTimers.current.forEach(clearTimeout)
      const msg = e?.message || String(e)
      setError(`Upload mislukt: ${msg.length > 200 ? msg.slice(0, 200) + '…' : msg}`)
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Page>
        <PageTitle
          title="Upload databestanden"
          sub={
            standard === 'zib'      ? 'Upload uw EPD/ECD-export (Patient, Probleem, Medicatie, Allergie)' :
            standard === 'algemeen' ? 'Upload uw AFAS Profit XML-export of Nedap ONS CSV-export' :
                                      'Upload uw HRM data-export of koppel via API'
          }
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
          <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls,.xml" multiple
            style={{ display: 'none' }} onChange={e => addFiles(e.target.files)} />
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 14px', display: 'block' }}>
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text2)', marginBottom: 4 }}>
            Sleep bestanden hierheen of klik om te uploaden
          </p>
          <p style={{ fontSize: 13, color: 'var(--text3)' }}>CSV, XML (AFAS Profit) of Excel bestanden</p>
        </div>

        {/* Testdata downloads */}
        <div style={{
          background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
          borderRadius: 'var(--radius-xl)', padding: '16px 20px', marginBottom: 16,
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--blue)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            📦 Voorbeelddata — pak de ZIP uit en lees eerst de README
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <a
              href="/rhadix-testdata-kikv.zip"
              download
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 7,
                background: '#fff', border: '1px solid var(--blue-mid)',
                borderRadius: 'var(--radius)', padding: '8px 16px',
                fontSize: 13, fontWeight: 600, color: 'var(--blue)',
                textDecoration: 'none', boxShadow: '0 1px 4px rgba(0,0,0,.05)',
              }}
            >
              ⬇ KIK-V testbestanden
            </a>
            <a
              href="/rhadix-testdata-zib.zip"
              download
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 7,
                background: '#fff', border: '1px solid var(--blue-mid)',
                borderRadius: 'var(--radius)', padding: '8px 16px',
                fontSize: 13, fontWeight: 600, color: 'var(--blue)',
                textDecoration: 'none', boxShadow: '0 1px 4px rgba(0,0,0,.05)',
              }}
            >
              ⬇ ZIB testbestanden
            </a>
            <a
              href="/rhadix-testdata-ons.zip"
              download
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 7,
                background: '#fff', border: '1px solid var(--blue-mid)',
                borderRadius: 'var(--radius)', padding: '8px 16px',
                fontSize: 13, fontWeight: 600, color: 'var(--blue)',
                textDecoration: 'none', boxShadow: '0 1px 4px rgba(0,0,0,.05)',
              }}
            >
              ⬇ ONS testbestanden
            </a>
          </div>
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

        {loading && <UploadProgress step={scanStep} />}

        {files.length > 0 && !loading && (
          <BtnPrimary onClick={submit} disabled={loading} style={{ marginTop: 8, width: '100%', justifyContent: 'center', padding: '13px' }}>
            Start Stap 1: Beschikbaarheid →
          </BtnPrimary>
        )}
      </Page>
    </div>
  )
}
