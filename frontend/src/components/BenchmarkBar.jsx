import { useState } from 'react'
import { runBenchmark } from '../services/api'
import { MaakTakenButton } from './TaskUI'

// Welke benchmarks zijn van toepassing, op basis van de bron (val terug op standaard)
const SOURCE_BENCHMARKS = {
  afas: ['kikv'], ons: ['kikv', 'zib'],
  exact_fin: ['kikv'], afas_profit_fin: ['kikv'], visma_puur: ['kikv'],
  epd_ecd: ['zib'],
}
const STD_BENCHMARKS = { algemeen: ['kikv'], kikv: ['kikv'], zib: ['zib'] }
const LABEL = { kikv: 'KIK-V', zib: "ZIB's" }

function scoreColor(s) {
  if (s == null) return '#9ca3af'
  return s >= 85 ? '#059669' : s >= 65 ? 'var(--blue)' : s >= 50 ? '#f59e0b' : '#ef4444'
}

export default function BenchmarkBar({ result, authUser }) {
  const [busy, setBusy] = useState(null)
  const [bench, setBench] = useState(null)
  const [err, setErr] = useState(null)
  if (!result) return null

  const stds = result.standard === 'zib' ? ['zib']
    : result.standard === 'kikv' ? ['kikv']
    : (result.source && SOURCE_BENCHMARKS[result.source]) || ['kikv']

  async function go(std) {
    setBusy(std); setErr(null)
    try { const r = await runBenchmark(std); setBench({ std, r }) }
    catch (e) { setErr(e?.message || String(e)) }
    finally { setBusy(null) }
  }

  return (
    <div style={{ background: 'var(--blue-light)', border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius-xl)', padding: '16px 20px', marginTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--blue)' }}>🎯 Benchmark tegen een standaard</span>
        {stds.map(std => (
          <button key={std} onClick={() => go(std)} disabled={busy === std}
            style={{ background: '#fff', border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius)',
              padding: '7px 14px', fontSize: 13, fontWeight: 700, color: 'var(--blue)',
              cursor: busy ? 'wait' : 'pointer' }}>
            {busy === std ? 'Bezig…' : `Benchmark tegen ${LABEL[std]}`}
          </button>
        ))}
      </div>
      {err && <div style={{ marginTop: 10, fontSize: 13, color: '#ef4444' }}>Benchmark mislukt: {err}</div>}
      {bench && <BenchResult std={bench.std} r={bench.r} authUser={authUser} />}
    </div>
  )
}

// Eén uitklapbare bestandsrij met zijn KIK-V/ZIB-bevindingen — zelfde in-/uitklap
// look als de bevindingskaarten in de hoofdscan.
function BenchFileRow({ fr }) {
  const [open, setOpen] = useState(false)
  const issues = fr.issues || []
  const idx = fr.rhadix_index != null ? fr.rhadix_index : null
  return (
    <div style={{ borderTop: '1px solid var(--border)' }}>
      <div onClick={() => issues.length && setOpen(o => !o)}
           style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10,
                    padding: '7px 0', fontSize: 13, cursor: issues.length ? 'pointer' : 'default' }}>
        <span>{fr.filename} <span style={{ color: 'var(--text3)' }}>· {fr.schema_key || '—'}</span></span>
        <span style={{ color: 'var(--text3)', display: 'flex', alignItems: 'center', gap: 8 }}>
          {idx != null ? `index ${Math.round(idx)}` : ''} · {issues.length} bevinding{issues.length === 1 ? '' : 'en'}
          {issues.length > 0 && <span style={{ fontSize: 11 }}>{open ? '▲' : '▼'}</span>}
        </span>
      </div>
      {open && issues.map((iss, j) => {
        const isError = iss.severity === 'error'
        const rows = iss.rows || []
        return (
          <div key={j} style={{ margin: '0 0 6px', border: `1px solid ${isError ? '#fca5a5' : '#fde68a'}`,
                                borderRadius: 'var(--radius)', background: isError ? '#fff5f5' : '#fffbeb', padding: '8px 12px' }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 12 }}>{isError ? '🔴' : '🟡'}</span>
              <span style={{ flex: 1, fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>{iss.fieldLabel ? `${iss.fieldLabel} — ` : ''}{iss.label}</span>
              <span style={{ fontSize: 11, color: 'var(--text3)', fontWeight: 600 }}>{iss.count}x</span>
            </div>
            {iss.detail && <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 3 }}>{iss.detail}</div>}
            {rows.length > 0 && (
              <div style={{ maxHeight: 180, overflowY: 'auto', marginTop: 6 }}>
                {rows.slice(0, 50).map((rd, k) => (
                  <div key={k} style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 2 }}>
                    Rij {rd.rowNumber}{rd.personId ? ` · ${rd.personId}` : ''}: <code style={{ background: '#f3f4f6', padding: '1px 5px', borderRadius: 4 }}>{rd.currentValue || 'leeg'}</code>
                    {rd.expectedValue ? <span style={{ color: 'var(--text3)' }}> → {rd.expectedValue}</span> : null}
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function BenchResult({ std, r, authUser }) {
  // Niets herkend → geen misleidende score, maar een actie-gerichte melding
  if (r.recognized === false || (Array.isArray(r.file_results) && r.file_results.length === 0)) {
    return (
      <div style={{ marginTop: 14, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 'var(--radius)', padding: '14px 16px' }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#92400e', marginBottom: 4 }}>
          Geen {std === 'zib' ? 'ZIB' : 'KIK-V'}-bestanden herkend
        </div>
        <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>
          {r.note || 'Geen van de aangeleverde bestanden kon aan een schema gekoppeld worden. Controleer de bestands- of kolomnamen.'}
        </div>
        {Array.isArray(r.uploaded_files) && r.uploaded_files.length > 0 && (
          <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 8 }}>
            Aangeleverd: {r.uploaded_files.join(', ')}
          </div>
        )}
      </div>
    )
  }
  const score = r.score
  const dataverzuim = r.dataverzuim != null ? r.dataverzuim : (score != null ? Math.round((100 - score) * 10) / 10 : null)
  const fileResults = r.file_results || []
  return (
    <div style={{ marginTop: 14, background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)' }}>Resultaat — {std === 'zib' ? "ZIB's" : 'KIK-V'}</span>
        <span style={{ fontSize: 26, fontWeight: 900, color: scoreColor(score) }}>{score != null ? Math.round(score) : '—'}<span style={{ fontSize: 13, color: 'var(--text3)' }}> /100</span></span>
        {dataverzuim != null && <span style={{ fontSize: 12, color: 'var(--text3)' }}>dataverzuim {Math.round(dataverzuim)}</span>}
        {r.total_errors != null && <span style={{ fontSize: 12, color: 'var(--text3)' }}>{r.total_errors} errors · {r.total_warns} waarschuwingen</span>}
      </div>
      {fileResults.map((fr, i) => <BenchFileRow key={i} fr={fr} />)}

      {/* Vervolgstap: bevindingen omzetten in taken (zelfde als de hoofdscan) */}
      {authUser && (() => {
        const items = fileResults.flatMap(fr => (fr.issues || []).map(iss => ({
          title: (iss.fieldLabel ? `${iss.fieldLabel} — ` : '') + iss.label,
          description: [
            `Bestand: ${fr.filename} (${fr.schema_key || '—'})`,
            `Standaard: ${std === 'zib' ? "ZIB's" : 'KIK-V'}`,
            iss.count ? `Aantal: ${iss.count}` : null,
            iss.detail || null,
            (iss.rows || []).length ? 'Voorbeelden:' : null,
            ...(iss.rows || []).map(rd =>
              `  rij ${rd.rowNumber}${rd.personId ? ' · ' + rd.personId : ''}: ${rd.currentValue || 'leeg'}` +
              (rd.expectedValue ? ` → ${rd.expectedValue}` : '')),
          ].filter(Boolean).join('\n'),
          source_label: `${fr.filename}${iss.count ? ' — ' + iss.count + '×' : ''}`,
          priority: iss.severity === 'error' ? 'HOOG' : 'NORMAAL',
        })))
        return items.length > 0 && (
          <div style={{ marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
            <MaakTakenButton
              buttonLabel={`✓ Maak taken van ${std === 'zib' ? "ZIB" : 'KIK-V'}-bevindingen`}
              sourceType={std === 'zib' ? 'zib_benchmark' : 'kikv_benchmark'}
              items={items}
            />
          </div>
        )
      })()}
    </div>
  )
}
