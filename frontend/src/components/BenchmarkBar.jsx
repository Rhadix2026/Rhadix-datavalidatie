import { useState } from 'react'
import { runBenchmark } from '../services/api'

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

export default function BenchmarkBar({ result }) {
  const [busy, setBusy] = useState(null)
  const [bench, setBench] = useState(null)
  const [err, setErr] = useState(null)
  if (!result) return null

  const stds = (result.source && SOURCE_BENCHMARKS[result.source]) || STD_BENCHMARKS[result.standard] || ['kikv']

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
      {bench && <BenchResult std={bench.std} r={bench.r} />}
    </div>
  )
}

function BenchResult({ std, r }) {
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
      {fileResults.map((fr, i) => {
        const idx = fr.rhadix_index != null ? fr.rhadix_index : null
        const issues = (fr.issues || []).length
        return (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', padding: '6px 0', fontSize: 13 }}>
            <span>{fr.filename} <span className="muted" style={{ color: 'var(--text3)' }}>· {fr.schema_key || '—'}</span></span>
            <span style={{ color: 'var(--text3)' }}>{idx != null ? `index ${Math.round(idx)}` : ''} · {issues} bevinding{issues === 1 ? '' : 'en'}</span>
          </div>
        )
      })}
    </div>
  )
}
