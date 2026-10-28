import { useState } from 'react'

/**
 * ScoreVerantwoording — toont hoe een score tot stand kwam (B-22, richting 1).
 *
 * Geen nieuw cijfer. Eén regel onder de score, met de details achter een
 * uitklap. Ontbreekt `score_accounting` — een oude validatierun, of een route
 * die het nog niet levert — dan rendert dit component niets, zodat historische
 * resultaten blijven werken zonder speciale behandeling.
 *
 * Controles en bevindingen worden bewust in twee aparte blokken gezet. Eén
 * bevinding kan meerdere afgekeurde controles bundelen, en een ontbrekend veld
 * geeft een bevinding zonder uitgevoerde controles; die aantallen mogen dus
 * niet naast elkaar als vergelijkbaar worden gepresenteerd.
 */
export default function ScoreVerantwoording({ accounting, version }) {
  const [open, setOpen] = useState(false)
  if (!accounting) return null

  const checks = accounting.checks || {}
  const findings = accounting.findings || {}
  const buiten = findings.outside_score || {}
  const binnen = findings.in_score || {}
  const aantalBuiten = (buiten.errors || 0) + (buiten.warnings || 0)
  const dektAlles = accounting.score_covers_all_findings !== false
  const skipped = checks.skipped || {}

  const versieTekst = version?.version
    ? `berekening ${version.version}${version.path ? ` · route ${version.path}` : ''}`
    : 'berekening onbekend'

  const regel = (label, waarde) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '3px 0' }}>
      <span style={{ color: 'var(--text3)' }}>{label}</span>
      <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>{waarde}</span>
    </div>
  )

  const perType = (obj) => Object.entries(obj || {})
    .map(([t, n]) => `${t} (${n})`)
    .join(', ') || '—'

  return (
    <div style={{ marginTop: 10, fontSize: 12, lineHeight: 1.5 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        {!dektAlles && (
          <span
            aria-hidden="true"
            title="Er zijn bevindingen die niet in deze score zijn verwerkt"
            style={{ color: '#d97706', fontWeight: 700, flexShrink: 0 }}
          >⚠</span>
        )}
        <div style={{ color: 'var(--text2)' }}>
          {accounting.explanation}
          <button
            type="button"
            onClick={() => setOpen(o => !o)}
            style={{
              marginLeft: 8, border: 0, background: 'none', padding: 0,
              color: 'var(--blue)', cursor: 'pointer', font: 'inherit',
              textDecoration: 'underline', textUnderlineOffset: 2,
            }}
            aria-expanded={open}
          >
            {open ? 'verberg verantwoording' : 'bekijk verantwoording'}
          </button>
        </div>
      </div>

      {open && (
        <div style={{
          marginTop: 8, padding: '10px 12px', borderRadius: 8,
          background: 'var(--bg2, #f8fafc)', border: '1px solid var(--line, #e2e8f0)',
        }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Uitgevoerde controles</div>
          {regel('uitgevoerd', checks.executed ?? 'niet van toepassing op deze route')}
          {regel('geslaagd', checks.passed ?? '—')}
          {regel('afgekeurd', checks.failed ?? '—')}
          {Object.keys(skipped).length > 0 && (
            <>
              <div style={{ fontWeight: 700, margin: '8px 0 4px' }}>Overgeslagen</div>
              {skipped.empty_values !== undefined && regel('lege waarden', skipped.empty_values)}
              {skipped.fields_absent !== undefined && regel('velden niet in de kopregel', skipped.fields_absent)}
              {skipped.files_without_template !== undefined
                && regel('bestanden zonder sjabloon', skipped.files_without_template)}
            </>
          )}

          <div style={{ fontWeight: 700, margin: '8px 0 4px' }}>Vastgestelde bevindingen</div>
          {regel('in deze score verwerkt', `${binnen.errors || 0} fouten, ${binnen.warnings || 0} waarschuwingen`)}
          {regel('niet in deze score verwerkt', `${buiten.errors || 0} fouten, ${buiten.warnings || 0} waarschuwingen`)}
          {aantalBuiten > 0 && regel('waarvan', perType(buiten.by_type))}

          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--line, #e2e8f0)', color: 'var(--text3)' }}>
            {checks.note}
          </div>
          <div style={{ marginTop: 6, color: 'var(--text3)' }}>
            {versieTekst}
            {version?.formula ? <> · <code style={{ fontSize: 11 }}>{version.formula}</code></> : null}
          </div>
        </div>
      )}
    </div>
  )
}
