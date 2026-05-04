import { useState } from 'react'
import { Nav, NavBack, Page, PageTitle, BtnPrimary, BtnOutline } from '../components/UI'
import { exportActieplan } from '../services/api'

// ─── Tijdschatting configuratie ───────────────────────────────────────────────
// Dit is de ENIGE plek waar de schattingsparameters staan.
// Pas hier aan om de berekening overal in de UI bij te werken.
const TIME_CONFIG = {
  minutesPerIssue: 5,    // minuten per uniek issue (veld/type combinatie)
  minutesPerRow:   0.5,  // minuten per betrokken rij/persoon
  baseMinutes:     15,   // vaste controle- en afrondingstijd per actie
  maxMinutes:      480,  // bovengrens: 8 uur
}

/**
 * Berekent de geschatte hersteltijd op basis van echte issue-data.
 * @param {Array}  issues   — array van issue-objecten met .count voor rijen
 * @param {number} divisor  — verdeel issues over N kaarten (standaard 1)
 * @returns {{ minutes, issueCount, rowCount, breakdown, label }}
 */
function estimateTime(issues = [], divisor = 1) {
  const issueCount = Math.ceil(issues.length / Math.max(divisor, 1))
  const rowCount   = Math.ceil(
    issues.reduce((s, i) => s + (i.count || 0), 0) / Math.max(divisor, 1)
  )
  const raw     = TIME_CONFIG.baseMinutes
    + issueCount * TIME_CONFIG.minutesPerIssue
    + rowCount   * TIME_CONFIG.minutesPerRow
  const minutes = Math.min(Math.round(raw), TIME_CONFIG.maxMinutes)

  const parts = []
  if (issueCount > 0) parts.push(`${issueCount} issue${issueCount !== 1 ? 's' : ''} × ${TIME_CONFIG.minutesPerIssue} min`)
  if (rowCount   > 0) parts.push(`${rowCount} rijen × ${TIME_CONFIG.minutesPerRow} min`)
  parts.push(`${TIME_CONFIG.baseMinutes} min controle`)
  const breakdown = parts.join(' + ')

  return { minutes, issueCount, rowCount, breakdown, label: formatTime(minutes) }
}

function formatTime(minutes) {
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m > 0 ? `~${h}u ${m}min` : `~${h}u`
}

// ─── Domein → schema-keys mapping ────────────────────────────────────────────
const DOMAIN_SCHEMA_KEYS = {
  Mens:             ['medewerker'],
  Werkovereenkomst: ['werkovereenkomst', 'functie'],
  Verzuim:          ['verzuim'],
}

// ─── Statische advieskaarten ──────────────────────────────────────────────────
// 'tijd' is verwijderd — de tijdschatting wordt nu berekend uit echte issue-data.
const ADVICE = {
  Werkovereenkomst: [
    {
      icon: '⚠', color: 'amber', title: 'Contracttype onvolledig',
      desc: 'Het veld "Contracttype" bevat inconsistente data. 23% van de records mist een correcte waarde volgens de KIK-V codelijst.',
      acties: [
        'Mapping aanpassen van intern contracttype naar KIK-V codelijst',
        'Validatieregel toevoegen bij invoer nieuwe contracten',
        'Bestaande records corrigeren',
      ],
    },
    {
      icon: '✕', color: 'red', title: 'Einddatum ontbreekt',
      desc: 'Het veld "Einddatum" is verplicht voor tijdelijke contracten maar ontbreekt in 45% van deze records.',
      acties: [
        'Veld toevoegen in bronsysteem',
        'Historische data aanvullen uit contractdocumenten',
        'Procesaanpassing: verplichte invoer bij nieuwe contracten',
      ],
    },
    {
      icon: '⚠', color: 'amber', title: 'FTE gedeeltelijk compleet',
      desc: 'FTE waarden zijn aanwezig maar 12% ligt buiten het toegestane bereik (0.0 - 1.0).',
      acties: [
        'Validatieregel implementeren (min: 0.0, max: 1.0)',
        'Afwijkende waarden handmatig controleren',
      ],
    },
  ],
  Mens: [
    {
      icon: '✕', color: 'red', title: 'Dubbele personeelsnummers',
      desc: 'Er zijn dubbele personeelsnummers gevonden in het systeem. Dit veroorzaakt inconsistentie in de data.',
      acties: [
        'Duplicaten identificeren en samenvoegen',
        'Unieke index toevoegen in bronsysteem',
      ],
    },
  ],
  Verzuim: [
    {
      icon: '⚠', color: 'amber', title: 'Overlappende verzuimperiodes',
      desc: 'Enkele medewerkers hebben overlappende verzuimregistraties.',
      acties: [
        'Periodes controleren en corrigeren',
        'Invoervalidatie toevoegen',
      ],
    },
  ],
}

// ─── Advies component ─────────────────────────────────────────────────────────
export function Advies({ domain, results, onActieplan, onGotoActieplan, onBack }) {
  const [added, setAdded] = useState([])
  const items = ADVICE[domain] || ADVICE.Werkovereenkomst

  // Echte issues voor dit domein uit de scanresultaten
  const domainSchemaKeys = DOMAIN_SCHEMA_KEYS[domain] || []
  const domainIssues = (results?.file_results || [])
    .filter(f => domainSchemaKeys.includes(f.schema_key))
    .flatMap(f => f.issues || [])

  // Domein-totaal schatting (voor header)
  const domainEstimate = estimateTime(domainIssues)
  const hasRealData    = domainIssues.length > 0

  const toggle = (i) => setAdded(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i])

  const COLOR = {
    red:   { bg: 'var(--red-bg)',   border: 'var(--red-light)',   icon: 'var(--red)'   },
    amber: { bg: 'var(--amber-bg)', border: 'var(--amber-light)', icon: 'var(--amber)' },
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Page>
        <PageTitle title={`Advies voor ${domain}`} sub="Concrete aanbevelingen om hiaten op te lossen" />

        {/* Domein-schatting banner */}
        {hasRealData && (
          <div style={{
            background: '#fff', border: '1px solid var(--border)', borderRadius: 'var(--radius-xl)',
            padding: '16px 20px', marginBottom: 20,
            display: 'flex', alignItems: 'flex-start', gap: 12,
          }}>
            <span style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>⏱</span>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 2 }}>
                Geschatte hersteltijd voor {domain}: {domainEstimate.label}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text3)' }}>
                Gebaseerd op {domainEstimate.breakdown}
              </div>
            </div>
          </div>
        )}

        {/* Actieplan-balk (zichtbaar zodra ≥1 item is toegevoegd) */}
        {added.length > 0 && (
          <div style={{
            position: 'sticky', top: 64, zIndex: 50,
            background: 'var(--blue)', color: '#fff',
            borderRadius: 'var(--radius-xl)', padding: '14px 20px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 16, boxShadow: '0 4px 16px rgba(99,102,241,.35)',
          }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              {added.length} actie{added.length !== 1 ? 's' : ''} toegevoegd aan actieplan
            </span>
            <button
              onClick={onGotoActieplan}
              style={{
                background: '#fff', color: 'var(--blue)', border: 'none',
                borderRadius: 'var(--radius)', padding: '8px 18px',
                fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
              }}
            >
              Bekijk actieplan →
            </button>
          </div>
        )}

        {items.map((item, i) => {
          // Per kaart: verdeel domeinissues gelijkmatig over de kaarten
          const cardEstimate = hasRealData
            ? estimateTime(domainIssues, items.length)
            : { label: item.color === 'red' ? '~3u' : '~2u', breakdown: 'Geen scandata beschikbaar — schatting op basis van ernstniveau' }

          const c       = COLOR[item.color] || COLOR.amber
          const isAdded = added.includes(i)

          return (
            <div key={i} style={{
              background: '#fff', borderRadius: 'var(--radius-xl)',
              border: `1px solid var(--border)`,
              borderLeft: `4px solid ${item.color === 'red' ? 'var(--red)' : 'var(--amber)'}`,
              padding: '24px', marginBottom: 16, boxShadow: 'var(--shadow)',
            }}>
              {/* Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 20, color: c.icon }}>{item.icon}</span>
                  <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>{item.title}</h3>
                </div>
                {/* Tijdschatting badge */}
                <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 12 }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--blue)' }}>{cardEstimate.label}</div>
                  <div style={{ fontSize: 11, color: 'var(--text3)' }}>geschatte tijd</div>
                </div>
              </div>

              <p style={{ fontSize: 14, color: 'var(--text2)', lineHeight: 1.6, marginBottom: 14 }}>{item.desc}</p>

              {/* Aanbevolen acties */}
              <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius)', padding: '14px 16px', marginBottom: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 8 }}>Aanbevolen actie:</div>
                <ul style={{ paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {item.acties.map((a, j) => (
                    <li key={j} style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>{a}</li>
                  ))}
                </ul>
              </div>

              {/* Tijdstoelichting */}
              <div style={{
                fontSize: 12, color: 'var(--text3)',
                padding: '8px 12px', background: 'var(--blue-light)',
                borderRadius: 'var(--radius)', marginBottom: 14,
                borderLeft: '3px solid var(--blue-mid)',
              }}>
                <strong style={{ color: 'var(--blue)' }}>Tijdschatting:</strong>{' '}
                {cardEstimate.label} — gebaseerd op {cardEstimate.breakdown}
              </div>

              <BtnPrimary
                onClick={() => {
                  if (!isAdded) {
                    toggle(i)
                    onActieplan({ ...item, estimate: cardEstimate })
                  }
                }}
                style={{ background: isAdded ? 'var(--green)' : 'var(--blue)' }}
              >
                {isAdded ? '✓ Toegevoegd aan actieplan' : 'Toevoegen aan actieplan'}
              </BtnPrimary>
            </div>
          )
        })}
      </Page>
    </div>
  )
}

// ─── Actieplan component ──────────────────────────────────────────────────────
export function Actieplan({ items, results, onDashboard, onBack }) {
  const [checked,   setChecked]   = useState([])
  const [exporting, setExporting] = useState(false)
  const [exportErr, setExportErr] = useState(null)

  const handleExport = async () => {
    setExporting(true)
    setExportErr(null)
    try {
      await exportActieplan(items, results?.run_id ?? null)
    } catch (e) {
      setExportErr('Export mislukt. Controleer of de backend bereikbaar is.')
      console.error(e)
    } finally {
      setExporting(false)
    }
  }

  // Bereken totaal op basis van per-item schattingen (transparante optelling)
  const totalMinutes = items.reduce((sum, item) => {
    return sum + (item.estimate?.minutes ?? (item.color === 'red' ? 45 : 30))
  }, 0)

  // Bouw de uitlegzin op
  const totalIssues = items.reduce((s, item) => s + (item.estimate?.issueCount ?? 0), 0)
  const totalRows   = items.reduce((s, item) => s + (item.estimate?.rowCount   ?? 0), 0)
  const breakdownParts = []
  if (totalIssues > 0) breakdownParts.push(`${totalIssues} issues × ${TIME_CONFIG.minutesPerIssue} min`)
  if (totalRows   > 0) breakdownParts.push(`${totalRows} rijen × ${TIME_CONFIG.minutesPerRow} min`)
  if (items.length > 0) breakdownParts.push(`${items.length} × ${TIME_CONFIG.baseMinutes} min controle`)
  const totalBreakdown = breakdownParts.length > 0
    ? breakdownParts.join(' + ')
    : `${items.length} acties op basis van ernstniveau`

  const impact = items.length >= 2 ? 'Hoog' : items.length === 1 ? 'Gemiddeld' : 'Laag'

  const toggle = (i) => setChecked(prev => prev.includes(i) ? prev.filter(x => x !== i) : [...prev, i])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={
        <div style={{ display: 'flex', gap: 16 }}>
          <button onClick={onDashboard} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: 'var(--text2)', fontFamily: 'var(--font)', fontWeight: 500 }}>Dashboard</button>
          <NavBack onClick={onBack} />
        </div>
      } />
      <Page>
        <PageTitle title="Actieplan" sub="Uw geprioriteerde implementatie-roadmap" />

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 16 }}>
          {/* Actieve taken */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--blue)', letterSpacing: '-0.02em', marginBottom: 4 }}>
              {Math.max(1, items.length)}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text3)' }}>Actieve taken</div>
          </div>

          {/* Geschatte tijd — met uitlegzin */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)', gridColumn: items.length > 0 ? 'auto' : 'auto' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 4 }}>
              {formatTime(Math.max(totalMinutes, TIME_CONFIG.baseMinutes))}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 6 }}>Geschatte tijd</div>
            {items.length > 0 && (
              <div style={{ fontSize: 11, color: 'var(--text3)', lineHeight: 1.5 }}>
                {totalBreakdown}
              </div>
            )}
          </div>

          {/* Impact */}
          <div style={{ background: '#fff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--green)', letterSpacing: '-0.02em', marginBottom: 4 }}>
              {impact}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text3)' }}>Impact</div>
          </div>
        </div>

        {/* Tijdstoelichting banner */}
        {items.length > 0 && (
          <div style={{
            background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
            borderRadius: 'var(--radius-xl)', padding: '14px 18px', marginBottom: 16,
            display: 'flex', alignItems: 'flex-start', gap: 10,
          }}>
            <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>⏱</span>
            <div style={{ fontSize: 13, color: 'var(--blue)', lineHeight: 1.6 }}>
              <strong>Geschatte tijd: {formatTime(Math.max(totalMinutes, TIME_CONFIG.baseMinutes))}</strong>
              {' — '}gebaseerd op {totalBreakdown}.
            </div>
          </div>
        )}

        {/* Taken */}
        <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', padding: '24px', marginBottom: 16, boxShadow: 'var(--shadow)' }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 14 }}>Te voltooien taken</div>

          {(items.length === 0
            ? [{ title: 'Einddatum veld implementeren', estimate: { label: '~2u', breakdown: 'Voorbeeldtaak' }, color: 'red' }]
            : items
          ).map((item, i) => {
            const tijdLabel = item.estimate?.label ?? (item.color === 'red' ? '~45 min' : '~30 min')
            return (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '14px', borderRadius: 'var(--radius)',
                border: '1px solid var(--border)', marginBottom: 8,
                background: checked.includes(i) ? 'var(--green-bg)' : '#fff',
              }}>
                <div onClick={() => toggle(i)} style={{
                  width: 22, height: 22, borderRadius: '50%',
                  border: `2px solid ${checked.includes(i) ? 'var(--green)' : 'var(--border2)'}`,
                  background: checked.includes(i) ? 'var(--green)' : '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', flexShrink: 0,
                }}>
                  {checked.includes(i) && <span style={{ color: '#fff', fontSize: 12 }}>✓</span>}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: checked.includes(i) ? 'var(--text3)' : 'var(--text)', textDecoration: checked.includes(i) ? 'line-through' : 'none' }}>
                    {item.title || `${item.label || 'Taak'} oplossen`}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 3 }}>
                    <span style={{ fontSize: 12, color: 'var(--text3)' }}>⏱ {tijdLabel}</span>
                    <span style={{ fontSize: 11, background: 'var(--red-light)', color: 'var(--red)', padding: '1px 7px', borderRadius: 20, fontWeight: 600 }}>
                      {item.color === 'red' ? 'Hoge prioriteit' : 'Gemiddelde prioriteit'}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}

          <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap', alignItems: 'center' }}>
            <BtnOutline onClick={onBack}>Meer acties toevoegen</BtnOutline>
            <BtnPrimary
              onClick={handleExport}
              disabled={exporting || items.length === 0}
              style={{ opacity: (exporting || items.length === 0) ? 0.6 : 1 }}
            >
              {exporting ? 'Bezig met exporteren…' : '⬇ Exporteer actieplan als PDF'}
            </BtnPrimary>
          </div>
          {exportErr && (
            <div style={{ marginTop: 10, fontSize: 13, color: 'var(--red)' }}>{exportErr}</div>
          )}
        </div>
      </Page>
    </div>
  )
}
