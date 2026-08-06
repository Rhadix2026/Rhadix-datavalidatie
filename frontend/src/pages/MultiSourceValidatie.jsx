import { useState, useCallback, useEffect } from 'react'
import { Nav, Page, PageTitle, BtnPrimary } from '../components/UI'
import { uploadFiles, happyFlowBatch, listProfiles, profileReadiness, importProfileGitlab,
  exportKikvReadinessRapportPdf, exportBeschikbaarheidsRapportPdf, exportManagementRapportPdf } from '../services/api'
import { MaakTakenButton } from '../components/TaskUI'
import { PROFILE_CATALOG } from './KIKVProfileImport'

// Bron-metadata: label, bron-parameter voor de fase-1 validatie, en de happy-flow
// voorbeeldbestanden die bij deze bron horen (voor de één-klik demo).
const SYS = {
  afas_hrm:        { label: 'AFAS Profit HRM',        source: 'afas',    color: 'var(--blue)', happyflow: ['medewerker_afas_hrm.csv', 'werkovereenkomst_afas_hrm.csv', 'verzuim_afas_hrm.csv'] },
  afas_profit_fin: { label: 'AFAS Profit Financieel', source: 'afas',    color: '#f59e0b',     happyflow: ['financieleboeking_afas_fin.csv', 'grootboekrubriek_afas_fin.csv', 'wlzkostenplaats_afas_fin.csv'] },
  nedap_ons:       { label: 'Nedap/ONS',              source: 'ons',     color: '#0ea5e9',     happyflow: ['medewerker_ons.csv', 'werkovereenkomst_ons.csv', 'verzuim_ons.csv', 'client_ons.csv', 'functie_ons.csv', 'vestiging_ons.csv'] },
  exact_fin:       { label: 'Exact Financial',        source: null,      color: '#10b981',     happyflow: [] },
  visma_puur:      { label: 'Visma PUUR',             source: null,      color: '#8b5cf6',     happyflow: [] },
  chipsoft_hix:    { label: 'ChipSoft HiX',           source: 'epd_ecd', color: '#059669',     happyflow: [] },
  epic:            { label: 'Epic',                   source: 'epd_ecd', color: 'var(--k-blue)', happyflow: [] },
}

// Cross-checks: vergelijk indicatorwaarden (uit de reconciliatie-batch) tussen bronnen.
const CROSSCHECKS = [
  { label: 'Medewerkeraantal — AFAS HRM vs Nedap ONS', a: 'hf_medewerker_afas_count', b: 'hf_medewerker_ons_count', rel: 'eq' },
  { label: 'Werkovereenkomsten — AFAS HRM vs Nedap ONS', a: 'hf_werkovereenkomst_afas_count', b: 'hf_werkovereenkomst_ons_count', rel: 'eq' },
  { label: 'Verzuimregistraties — AFAS HRM vs Nedap ONS', a: 'hf_verzuim_afas_count', b: 'hf_verzuim_ons_count', rel: 'eq' },
  { label: 'Unieke medewerkers in werkovereenkomst ≤ medewerkeraantal (ONS)', a: 'hf_werkovereenkomst_ons_uniek_medewerker', b: 'hf_medewerker_ons_count', rel: 'lte' },
  { label: 'Financiële boekingen én HR-populatie aanwezig', a: 'hf_financieel_boekingen_count', b: 'hf_medewerker_afas_count', rel: 'both' },
]

const reportBtn = {
  background: '#fff', border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius)',
  padding: '9px 14px', color: 'var(--blue)', fontSize: 13, fontWeight: 700,
  cursor: 'pointer', fontFamily: 'var(--font)',
}

// Verzamel alle issues (met severity) recursief uit een validatie-respons.
function collectIssues(obj, acc = []) {
  if (!obj || typeof obj !== 'object') return acc
  if (Array.isArray(obj)) { obj.forEach(x => collectIssues(x, acc)); return acc }
  for (const [k, v] of Object.entries(obj)) {
    if (k === 'issues' && Array.isArray(v)) v.forEach(i => { if (i && i.severity) acc.push(i) })
    else if (v && typeof v === 'object') collectIssues(v, acc)
  }
  return acc
}

function evalCheck(c, vals) {
  const a = vals[c.a], b = vals[c.b]
  if (a == null || b == null) return { status: 'na', a, b }
  if (c.rel === 'eq')   return { status: a === b ? 'ok' : 'fail', a, b }
  if (c.rel === 'lte')  return { status: a <= b ? 'ok' : 'fail', a, b }
  if (c.rel === 'both') return { status: (a > 0 && b > 0) ? 'ok' : 'fail', a, b }
  return { status: 'na', a, b }
}

export default function MultiSourceValidatie({ systems = [], onBack, authUser, onLogout, onProfiles }) {
  const sysList = systems.filter(id => SYS[id])
  const [filesBySource, setFilesBySource] = useState({})   // { systemId: File[] }
  const [loading, setLoading] = useState(false)
  const [phase, setPhase]     = useState('')
  const [error, setError]     = useState(null)
  const [result, setResult]   = useState(null)
  const [benchmark, setBenchmark]     = useState(null)   // { std, result }
  const [benchmarking, setBenchmarking] = useState(false)
  const [benchErr, setBenchErr]       = useState(null)
  const [reportErr, setReportErr]     = useState(null)
  const [profiles, setProfiles]       = useState([])
  const [upSel, setUpSel]             = useState('')
  const [upResult, setUpResult]       = useState(null)
  const [upBusy, setUpBusy]           = useState(false)
  const [upErr, setUpErr]             = useState(null)
  const [impBusy, setImpBusy]         = useState(false)
  const [impMsg, setImpMsg]           = useState(null)
  useEffect(() => { if (benchmark && !profiles.length) listProfiles().then(setProfiles).catch(() => {}) }, [benchmark])

  const addFiles = useCallback((sid, list) => {
    setFilesBySource(prev => {
      const existing = new Set((prev[sid] || []).map(f => f.name))
      const merged = [...(prev[sid] || []), ...[...list].filter(f => !existing.has(f.name))]
      return { ...prev, [sid]: merged }
    })
  }, [])

  const removeFile = (sid, name) =>
    setFilesBySource(prev => ({ ...prev, [sid]: (prev[sid] || []).filter(f => f.name !== name) }))

  const totalFiles = () => Object.values(filesBySource).reduce((n, arr) => n + arr.length, 0)

  const loadHappyFlow = async () => {
    setError(null); setLoading(true); setPhase('Voorbeeldset laden…')
    try {
      const next = {}
      for (const sid of sysList) {
        const names = SYS[sid].happyflow
        const arr = []
        for (const name of names) {
          const r = await fetch(`/kikv-voorbeeldset/${name}?v=${import.meta.env.VITE_APP_VERSION || 'dev'}`)
          if (!r.ok) continue
          const blob = await r.blob()
          arr.push(new File([blob], name, { type: 'text/csv' }))
        }
        if (arr.length) next[sid] = arr
      }
      setFilesBySource(next)
      if (!Object.keys(next).length) setError('Geen voorbeeldbestanden voor de gekozen bronnen (AFAS HRM, AFAS Financieel en/of Nedap ONS geven de beste demo).')
    } catch (e) {
      setError('Kon voorbeeldset niet laden: ' + (e?.message || e))
    } finally { setLoading(false); setPhase('') }
  }

  const submit = async () => {
    if (!totalFiles()) return
    setLoading(true); setError(null); setResult(null)
    try {
      // 1) Per bron: generieke validatie
      const perSource = {}
      for (const sid of sysList) {
        const arr = filesBySource[sid] || []
        if (!arr.length) { perSource[sid] = { files: 0, errors: 0, warnings: 0, empty: true }; continue }
        setPhase(`Valideren — ${SYS[sid].label}…`)
        const res = await uploadFiles(arr, `Multi-bron — ${SYS[sid].label}`, 'algemeen', 30, SYS[sid].source)
        const issues = collectIssues(res)
        perSource[sid] = {
          files: arr.length,
          errors: issues.filter(i => i.severity === 'error').length,
          warnings: issues.filter(i => i.severity === 'warning').length,
        }
      }
      // 2) Cross-checks via de reconciliatie-batch over álle bestanden
      setPhase('Cross-checks berekenen…')
      const allFiles = Object.values(filesBySource).flat()
      const batch = await happyFlowBatch(allFiles)
      const vals = {}
      ;(batch.all_results || []).forEach(r => {
        if (r.indicator_id != null && r.expected_value != null) vals[r.indicator_id] = r.expected_value
      })
      const cross = CROSSCHECKS
        .map(c => ({ ...c, ...evalCheck(c, vals) }))
        .filter(c => c.status !== 'na')  // alleen tonen als beide waarden er zijn
      setResult({ perSource, cross, batch })
    } catch (e) {
      const msg = e?.message || String(e)
      setError('Validatie mislukt: ' + (msg.length > 220 ? msg.slice(0, 220) + '…' : msg))
    } finally { setLoading(false); setPhase('') }
  }

  const runBench = async (std) => {
    if (!totalFiles()) return
    setBenchmarking(true); setBenchErr(null); setBenchmark(null)
    try {
      const allFiles = Object.values(filesBySource).flat()
      const res = await uploadFiles(allFiles, `Benchmark ${std.toUpperCase()} — multi-bron`, std, 30)
      setBenchmark({ std, result: res })
    } catch (e) {
      const msg = e?.message || String(e)
      setBenchErr('Benchmark mislukt: ' + (msg.length > 220 ? msg.slice(0, 220) + '…' : msg))
    } finally { setBenchmarking(false) }
  }

  const dlReport = async (fn) => {
    setReportErr(null)
    try { await fn() }
    catch (e) { setReportErr('Rapport niet beschikbaar voor deze scan: ' + (e?.message || e)) }
  }

  const toetsUP = async () => {
    if (!upSel || !benchmark?.result) return
    setUpBusy(true); setUpErr(null); setUpResult(null)
    try { setUpResult(await profileReadiness(upSel, benchmark.result)) }
    catch (e) { setUpErr('Toets mislukt: ' + (e?.message || e)) }
    finally { setUpBusy(false) }
  }

  const ververs = async () => {
    setImpBusy(true); setImpMsg(null)
    let ok = 0
    try {
      for (const e of PROFILE_CATALOG.filter(x => !x.comingSoon)) {
        try { await importProfileGitlab(e); ok++ } catch { /* profiel overslaan */ }
      }
      const list = await listProfiles().catch(() => [])
      setProfiles(list)
      setImpMsg(`${ok} uitwisselprofiel(en) opgehaald op de laatste versie.`)
    } catch (e) { setImpMsg('Ophalen mislukt: ' + (e?.message || e)) }
    finally { setImpBusy(false) }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav authUser={authUser} onLogout={onLogout} onHome={onBack} onBack={onBack} />
      <Page>
        <PageTitle
          title={sysList.length > 1 ? "Multi-bron validatie" : "Datavalidatie"}
          sub={sysList.length > 1
            ? "Upload per bron de bestanden. We valideren elke bron generiek en doen cross-checks over de bronnen heen."
            : "Upload de bestanden. We valideren generiek en je kunt benchmarken tegen KIK-V of de ZIB's."}
        />

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
          <button onClick={loadHappyFlow} disabled={loading} style={{
            background: 'var(--blue)', border: 'none', borderRadius: 'var(--radius)', padding: '9px 16px',
            color: '#fff', fontSize: 13, fontWeight: 700, cursor: loading ? 'default' : 'pointer', fontFamily: 'var(--font)', opacity: loading ? 0.6 : 1,
          }}>📦 Laad happy-flow voorbeeldset</button>
          <span style={{ fontSize: 12, color: 'var(--text3)', alignSelf: 'center' }}>Synthetische implementatie-twin — verdeeld over de gekozen bronnen, geen echte cliëntgegevens.</span>
        </div>

        {/* Upload per bron */}
        <div style={{ display: 'grid', gridTemplateColumns: sysList.length > 1 ? '1fr 1fr' : '1fr', gap: 14, marginBottom: 20 }}>
          {sysList.map(sid => {
            const arr = filesBySource[sid] || []
            const ps = result?.perSource?.[sid]
            return (
              <div key={sid} style={{ background: '#fff', border: `2px solid var(--border)`, borderRadius: 'var(--radius-xl)', padding: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 3, background: SYS[sid].color }} />
                  <span style={{ fontSize: 15, fontWeight: 800, color: SYS[sid].color }}>{SYS[sid].label}</span>
                  <span style={{ fontSize: 12, color: 'var(--text4)' }}>{arr.length} bestand(en)</span>
                </div>
                <label style={{
                  display: 'block', border: '2px dashed #c9d0db', borderRadius: 'var(--radius)', padding: '18px 12px',
                  textAlign: 'center', cursor: 'pointer', fontSize: 13, color: 'var(--text3)', background: 'var(--bg)',
                }}>
                  <input type="file" accept=".csv,.xlsx,.xls,.xml,.json" multiple style={{ display: 'none' }}
                    onChange={e => addFiles(sid, e.target.files)} />
                  Sleep of klik — bestanden voor {SYS[sid].label}
                </label>
                {arr.map(f => (
                  <div key={f.name} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', marginTop: 8, background: 'var(--bg)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                    <span style={{ flex: 1, fontSize: 13, color: 'var(--text)' }}>{f.name}</span>
                    <button onClick={() => removeFile(sid, f.name)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', fontSize: 16 }}>×</button>
                  </div>
                ))}
                {ps && !ps.empty && (
                  <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: ps.errors ? 'var(--red)' : 'var(--green)', background: ps.errors ? 'var(--red-bg)' : '#ecfdf5', border: `1px solid ${ps.errors ? 'var(--red-light)' : '#bbf7d0'}`, padding: '3px 10px', borderRadius: 20 }}>{ps.errors} fouten</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#b45309', background: '#fffbeb', border: '1px solid #fde68a', padding: '3px 10px', borderRadius: 20 }}>{ps.warnings} waarschuwingen</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {error && <div style={{ padding: '10px 14px', background: 'var(--red-bg)', border: '1px solid var(--red-light)', borderRadius: 'var(--radius)', color: 'var(--red)', fontSize: 13, marginBottom: 12 }}>{error}</div>}
        {loading && <div style={{ padding: '10px 14px', background: 'var(--blue-light)', border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius)', color: 'var(--blue)', fontSize: 13, marginBottom: 12, fontWeight: 600 }}>{phase || 'Bezig…'}</div>}

        {!loading && totalFiles() > 0 && (
          <BtnPrimary onClick={submit} style={{ width: '100%', justifyContent: 'center', padding: '13px', marginBottom: 20 }}>
            Valideren + cross-checks ({totalFiles()} bestanden) →
          </BtnPrimary>
        )}

        {/* Cross-check resultaat */}
        {result && (
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', padding: 20, marginBottom: 24 }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)', marginBottom: 4 }}>🔗 Cross-checks tussen bronnen</div>
            <div style={{ fontSize: 12.5, color: 'var(--text3)', marginBottom: 14 }}>Vergelijkingen op basis van de reconciliatie-indicatoren. Alleen checks waarvoor beide bronnen data leverden worden getoond.</div>
            {result.cross.length === 0 && (
              <div style={{ fontSize: 13, color: 'var(--text3)' }}>Geen cross-checks mogelijk met de aangeleverde bronnen — kies bijvoorbeeld AFAS HRM én Nedap ONS voor de medewerker-/werkovereenkomst-vergelijkingen.</div>
            )}
            {result.cross.map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 0', borderTop: i ? '1px solid var(--border)' : 'none' }}>
                <span style={{ fontSize: 18 }}>{c.status === 'ok' ? '✅' : '⚠️'}</span>
                <span style={{ flex: 1, fontSize: 13.5, color: 'var(--text)' }}>{c.label}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)', whiteSpace: 'nowrap' }}>{c.a} <span style={{ color: 'var(--text4)' }}>vs</span> {c.b}</span>
                <span style={{ fontSize: 12, fontWeight: 800, color: c.status === 'ok' ? 'var(--green)' : '#b45309', minWidth: 64, textAlign: 'right' }}>{c.status === 'ok' ? 'OK' : 'Afwijking'}</span>
              </div>
            ))}
          </div>
        )}

        {/* Benchmark tegen standaard */}
        {totalFiles() > 0 && (
          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)', padding: 20, marginBottom: 24 }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)', marginBottom: 4 }}>🎯 Benchmark tegen standaard</div>
            <div style={{ fontSize: 12.5, color: 'var(--text3)', marginBottom: 14 }}>Toets de aangeleverde data tegen KIK-V of de ZIB's (conformiteit + score over alle bronnen).</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
              <button onClick={() => runBench('kikv')} disabled={benchmarking} style={{
                background: 'var(--blue)', border: 'none', borderRadius: 'var(--radius)', padding: '10px 18px',
                color: '#fff', fontSize: 13.5, fontWeight: 700, cursor: benchmarking ? 'default' : 'pointer', fontFamily: 'var(--font)', opacity: benchmarking ? 0.6 : 1,
              }}>Benchmark tegen KIK-V</button>
              <button onClick={() => runBench('zib')} disabled={benchmarking} style={{
                background: '#fff', border: '1px solid var(--blue-mid)', borderRadius: 'var(--radius)', padding: '10px 18px',
                color: 'var(--blue)', fontSize: 13.5, fontWeight: 700, cursor: benchmarking ? 'default' : 'pointer', fontFamily: 'var(--font)', opacity: benchmarking ? 0.6 : 1,
              }}>Benchmark tegen ZIB</button>
              {benchmarking && <span style={{ fontSize: 12.5, color: 'var(--blue)', alignSelf: 'center', fontWeight: 600 }}>Bezig…</span>}
            </div>
            {benchErr && <div style={{ padding: '10px 14px', background: 'var(--red-bg)', border: '1px solid var(--red-light)', borderRadius: 'var(--radius)', color: 'var(--red)', fontSize: 13 }}>{benchErr}</div>}
            {benchmark && (() => {
              const b = benchmark.result || {}
              const per = {}
              ;(b.file_results || []).forEach(fr => {
                const k = fr.schema_key || 'onbekend'
                per[k] = per[k] || { err: 0, warn: 0 }
                per[k].err += fr.error_count || 0
                per[k].warn += fr.warn_count || 0
              })
              const score = b.score != null ? b.score : null
              const scoreColor = score == null ? 'var(--text3)' : score >= 80 ? 'var(--green)' : score >= 50 ? '#b45309' : 'var(--red)'
              return (
                <div style={{ marginTop: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 14, flexWrap: 'wrap' }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text2)' }}>Resultaat {benchmark.std.toUpperCase()}:</div>
                    {score != null && <div style={{ fontSize: 30, fontWeight: 900, color: scoreColor }}>{score}<span style={{ fontSize: 15, color: 'var(--text3)' }}>/100</span></div>}
                    <div style={{ fontSize: 13, color: 'var(--red)', fontWeight: 700 }}>{b.total_errors ?? 0} fouten</div>
                    <div style={{ fontSize: 13, color: '#b45309', fontWeight: 700 }}>{b.total_warns ?? 0} waarschuwingen</div>
                  </div>
                  {Object.keys(per).length > 0 && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                      {Object.entries(per).map(([k, v]) => (
                        <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'var(--bg)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                          <span style={{ flex: 1, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{k}</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: v.err ? 'var(--red)' : 'var(--green)' }}>{v.err} fouten</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: '#b45309' }}>{v.warn} waarsch.</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {(b.file_results || []).length === 0 && (
                    <div style={{ fontSize: 13, color: 'var(--text3)' }}>Geen {benchmark.std.toUpperCase()}-herkende bestanden in deze set.</div>
                  )}
                  {Array.isArray(b.actuality) && b.actuality.some(a => a.primary_col) && (
                    <div style={{ marginTop: 14, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                      <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text2)', marginBottom: 4 }}>📅 Actualiteit t.o.v. de Uitwisselkalender</div>
                      <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 10 }}>Per recordtype: hoeveel records binnen de maximale leeftijd van het uitwisselprofiel vallen.</div>
                      {b.actuality.filter(a => a.primary_col && a.total_records).map((a, i) => {
                        const tot = a.total_records, within = a.actual_count || 0
                        const pct = tot ? Math.round(within / tot * 100) : 0
                        const ok = pct >= 90
                        return (
                          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', borderTop: i ? '1px solid var(--border)' : 'none', fontSize: 12.5 }}>
                            <span>{ok ? '✅' : '⚠️'}</span>
                            <span style={{ flex: 1, color: 'var(--text)' }}>{a.schema_key || a.filename} <span style={{ color: 'var(--text3)' }}>· {within}/{tot} binnen norm ({pct}%)</span></span>
                            {a.kikv_norm && <span style={{ fontSize: 11.5, color: 'var(--text3)', whiteSpace: 'nowrap' }}>{a.kikv_norm.label} ≤{a.kikv_norm.max_age_days}d</span>}
                          </div>
                        )
                      })}
                      <div style={{ marginTop: 6, fontSize: 11.5, color: 'var(--text3)' }}>Peildatum: {(b.actuality.find(a => a.reference_date) || {}).reference_date || '—'}. Norm per uitwisselprofiel: Zorgkantoren ≤90d, VWS/NZa ≤548d, IGJ ≤180d.</div>
                    </div>
                  )}
                  {b.run_id && (
                    <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                      <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text2)', marginBottom: 8 }}>Rapportage & opvolging</div>
                      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                        <button onClick={() => dlReport(() => exportKikvReadinessRapportPdf(b.run_id))} style={reportBtn}>📄 KIK-V readiness (PDF)</button>
                        <button onClick={() => dlReport(() => exportBeschikbaarheidsRapportPdf(b.run_id))} style={reportBtn}>📄 Beschikbaarheid (PDF)</button>
                        <button onClick={() => dlReport(() => exportManagementRapportPdf(b.run_id))} style={reportBtn}>📄 Management (PDF)</button>
                        {authUser && (
                          <MaakTakenButton
                            buttonLabel="✓ Maak taken van bevindingen"
                            sourceType="datavalidatie"
                            sourceRef={b.run_id != null ? String(b.run_id) : null}
                            items={(b.file_results || []).flatMap(fr => (fr.issues || []).map(iss => ({
                              title: iss.label + (iss.count > 1 ? ` (${iss.count}\u00d7)` : ''),
                              source_label: fr.schema_key,
                              priority: iss.severity === 'error' ? 'HOOG' : 'NORMAAL',
                            })))}
                          />
                        )}
                      </div>
                      {reportErr && <div style={{ marginTop: 8, fontSize: 12.5, color: 'var(--red)' }}>{reportErr}</div>}
                      <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text3)' }}>Taken worden toegewezen aan een gebruiker van je organisatie; die krijgt een e-mailnotificatie.</div>
                      <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                        <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text2)', marginBottom: 8 }}>Uitwisselprofiel toetsen — kunnen alle indicatoren beantwoord worden?</div>

                        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                          <select value={upSel} onChange={e => setUpSel(e.target.value)} style={{ padding: '8px 12px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', fontSize: 13, fontFamily: 'var(--font)', minWidth: 300, background: '#fff' }}>
                            <option value="">— Kies een uitwisselprofiel —</option>
                            {profiles.map(p => <option key={p.filename} value={p.filename}>{(p.name || p.filename)}{p.indicator_count ? ` (${p.indicator_count} indicatoren)` : ''}</option>)}
                          </select>
                          <button onClick={toetsUP} disabled={!upSel || upBusy} style={{ ...reportBtn, opacity: (!upSel || upBusy) ? 0.6 : 1 }}>{upBusy ? 'Bezig…' : 'Toets uitwisselprofiel'}</button>
                          <button onClick={ververs} disabled={impBusy} style={{ ...reportBtn, opacity: impBusy ? 0.6 : 1 }} title="Haal de laatste versie van alle uitwisselprofielen uit GitLab">{impBusy ? 'Ophalen…' : '⟳ Ververs uit GitLab'}</button>
                          {onProfiles && (
                            <button onClick={() => onProfiles(benchmark.result)} style={reportBtn} title="Open de volledige profielbibliotheek: importeer profielen en lees alle indicatoren door">📚 Uitgebreid: profielbibliotheek</button>
                          )}
                        </div>
                        {impMsg && <div style={{ marginTop: 8, fontSize: 12.5, color: 'var(--text3)' }}>{impMsg}</div>}
                        {upErr && <div style={{ marginTop: 8, fontSize: 12.5, color: 'var(--red)' }}>{upErr}</div>}
                        {upResult && (() => {
                          const sc = upResult.profile_readiness_score || 0
                          const col = sc >= 90 ? 'var(--green)' : sc >= 50 ? '#b45309' : 'var(--red)'
                          return (
                            <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
                              <div style={{ fontSize: 26, fontWeight: 900, color: col }}>{Math.round(sc)}<span style={{ fontSize: 14, color: 'var(--text3)' }}>%</span></div>
                              <div style={{ fontSize: 13, color: 'var(--green)', fontWeight: 700 }}>{upResult.fully_computable} volledig</div>
                              <div style={{ fontSize: 13, color: '#b45309', fontWeight: 700 }}>{upResult.partially_computable} gedeeltelijk</div>
                              <div style={{ fontSize: 13, color: 'var(--red)', fontWeight: 700 }}>{upResult.blocked} geblokkeerd</div>
                              <div style={{ fontSize: 12.5, color: 'var(--text3)' }}>van {upResult.total_indicators} indicatoren</div>
                            </div>
                          )
                        })()}
                        {upResult && Array.isArray(upResult.heatmap) && (
                          <div style={{ marginTop: 12, maxHeight: 300, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
                            {upResult.heatmap.map((ind, i) => {
                              const st = ind.readiness
                              const icon = st === 'fully' ? '✅' : st === 'partially' ? '🟡' : '🔴'
                              const doms = Object.entries(ind).filter(([k, v]) => !['indicator_id', 'title', 'readiness'].includes(k) && (v === 'blocked' || v === 'partially'))
                              return (
                                <div key={i} style={{ padding: '8px 12px', borderTop: i ? '1px solid var(--border)' : 'none', fontSize: 12.5 }}>
                                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                                    <span>{icon}</span>
                                    <span style={{ flex: 1, color: 'var(--text)' }}>{ind.title || ind.indicator_id}</span>
                                  </div>
                                  {doms.length > 0 && (
                                    <div style={{ marginLeft: 24, marginTop: 2, fontSize: 11.5, color: 'var(--text3)' }}>
                                      probleem bij: {doms.map(([k, v]) => `${k} (${v === 'blocked' ? 'ontbreekt' : 'deels'})`).join(', ')}
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        )}
                        {upResult && Array.isArray(upResult.top_blocking_fields) && upResult.top_blocking_fields.length > 0 && (
                          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text3)' }}>
                            <b>Belangrijkste ontbrekende velden:</b> {upResult.top_blocking_fields.slice(0, 8).map(f => (typeof f === 'string' ? f : (f.field || f.name || JSON.stringify(f)))).join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })()}
          </div>
        )}
      </Page>
    </div>
  )
}
