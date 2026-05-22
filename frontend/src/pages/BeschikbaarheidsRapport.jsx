import { useState, useEffect } from 'react'
import { Nav, NavBack, Spinner } from '../components/UI'
import { getBeschikbaarheidsRapport, exportBeschikbaarheidsRapportPdf } from '../services/api'

// ─── Status helpers ────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  aanwezig:       { label: 'Aanwezig',           color: 'var(--green)',  bg: 'var(--green-light)',  icon: '✓' },
  ontbreekt:      { label: 'Ontbreekt',           color: 'var(--red)',    bg: 'var(--red-light)',    icon: '✕' },
  niet_eenduidig: { label: 'Deels beschikbaar',  color: 'var(--amber)',  bg: 'var(--amber-light)',  icon: '⚠' },
}

function StatusChip({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.ontbreekt
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, fontWeight: 700, padding: '3px 9px',
      borderRadius: 20, whiteSpace: 'nowrap',
      background: cfg.bg, color: cfg.color,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

function ScoreRing({ score }) {
  const color = score >= 80 ? 'var(--green)' : score >= 60 ? 'var(--amber)' : 'var(--red)'
  const label = score >= 80 ? 'Uitstekend' : score >= 60 ? 'Goed' : 'Aandacht vereist'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 52, fontWeight: 800, color, letterSpacing: '-0.04em', lineHeight: 1 }}>
          {Math.round(score)}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 2 }}>van 100</div>
      </div>
      <div>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>
          Beschikbaarheidsscore
        </div>
        <div style={{ fontSize: 13, color, fontWeight: 600 }}>{label}</div>
        <div style={{ height: 6, width: 160, background: 'var(--border)', borderRadius: 3, marginTop: 8, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${Math.min(100, score)}%`, background: color, borderRadius: 3, transition: 'width .6s' }} />
        </div>
      </div>
    </div>
  )
}

// ─── Veldentabel per schema ────────────────────────────────────────────────────

function SchemaSection({ schema }) {
  const [openField, setOpenField] = useState(null)

  const uploaded = schema.file_uploaded
  const hdrColor = uploaded ? 'var(--blue)' : 'var(--text3)'

  return (
    <div style={{ marginBottom: 20 }}>
      {/* Schema header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 18px',
        background: uploaded ? 'var(--blue)' : '#94A3B8',
        borderRadius: 'var(--radius) var(--radius) 0 0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16, fontWeight: 800, color: '#fff' }}>{schema.schema_label}</span>
          {!uploaded && (
            <span style={{ fontSize: 11, background: 'rgba(255,255,255,.2)', color: '#fff', padding: '2px 8px', borderRadius: 10 }}>
              Niet aangeleverd
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {uploaded && (
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,.75)' }}>
              {schema.row_count} rijen · {schema.recognized_columns}/{schema.total_columns} kolommen herkend
            </span>
          )}
          <div style={{ fontSize: 20, fontWeight: 800, color: '#fff' }}>
            {Math.round(schema.availability_score)}%
          </div>
        </div>
      </div>

      {!uploaded ? (
        <div style={{
          padding: '14px 18px', background: '#fff',
          border: '1px solid var(--border)', borderTop: 'none',
          borderRadius: '0 0 var(--radius) var(--radius)',
          fontSize: 13, color: 'var(--text3)',
        }}>
          Geen bestand aangeleverd voor dit schema. Alle velden zijn als "Ontbreekt" geclassificeerd.
        </div>
      ) : (
        <div style={{ border: '1px solid var(--border)', borderTop: 'none', borderRadius: '0 0 var(--radius) var(--radius)', overflow: 'hidden' }}>
          {/* Tabelheader */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 72px 148px 130px 64px',
            padding: '8px 18px', background: 'var(--bg)',
            borderBottom: '1px solid var(--border)',
            fontSize: 11, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.05em',
          }}>
            <span>Veld</span>
            <span style={{ textAlign: 'center' }}>Verplicht</span>
            <span>Status</span>
            <span>Bronkolom</span>
            <span style={{ textAlign: 'center' }}>Dekking</span>
          </div>

          {schema.fields.map((field, idx) => {
            const isOpen = openField === field.field_key
            const cfg    = STATUS_CONFIG[field.status] || STATUS_CONFIG.ontbreekt
            const rowBg  = idx % 2 === 0 ? '#fff' : 'var(--bg)'

            // Toelichting tekst
            let toelichting = ''
            if (field.status === 'aanwezig') {
              toelichting = 'Veld aanwezig en herkend in het aangeleverde bestand.'
            } else if (field.status === 'ontbreekt') {
              toelichting = field.mapped_column
                ? `${field.empty_count || 0} rijen zonder waarde voor dit veld.`
                : 'Kolom niet herkend in het bestand. Controleer de kolomnaam.'
            } else {
              toelichting = `${field.invalid_count || 0} rijen bevatten afwijkende of onbekende waarden.`
            }

            const hasDetail = field.status !== 'aanwezig'

            return (
              <div key={field.field_key}>
                <div
                  onClick={hasDetail ? () => setOpenField(isOpen ? null : field.field_key) : undefined}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 72px 148px 130px 64px',
                    padding: '10px 18px',
                    background: isOpen ? 'var(--blue-light)' : rowBg,
                    borderBottom: '1px solid var(--border)',
                    cursor: hasDetail ? 'pointer' : 'default',
                    userSelect: 'none',
                    alignItems: 'center',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      {field.field_label}
                      {hasDetail && (
                        <span style={{ fontSize: 10, color: 'var(--text4)' }}>{isOpen ? '▲' : '▼'}</span>
                      )}
                    </div>
                    {field.source && (
                      <div style={{ fontSize: 11, color: 'var(--text4)', marginTop: 1 }}>{field.source}</div>
                    )}
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    {field.is_required
                      ? <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--red)' }}>Ja</span>
                      : <span style={{ fontSize: 11, color: 'var(--text3)' }}>Nee</span>}
                  </div>
                  <StatusChip status={field.status} />
                  <div style={{ fontSize: 12, fontFamily: 'var(--font-mono, monospace)', color: field.mapped_column ? 'var(--text)' : 'var(--text4)' }}>
                    {field.mapped_column || '—'}
                  </div>
                  <div style={{ textAlign: 'center', fontSize: 13, fontWeight: 700, color: field.coverage_pct >= 90 ? 'var(--green)' : field.coverage_pct >= 60 ? 'var(--amber)' : 'var(--red)' }}>
                    {field.total_rows > 0 ? `${Math.round(field.coverage_pct)}%` : '—'}
                  </div>
                </div>

                {/* Uitklap-detail */}
                {isOpen && (
                  <div style={{
                    padding: '12px 18px 14px',
                    background: 'var(--blue-light)',
                    borderBottom: '1px solid var(--border)',
                  }}>
                    <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 8 }}>
                      <strong>Toelichting:</strong> {toelichting}
                    </div>
                    <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 12, color: 'var(--text3)' }}>
                      {field.total_rows > 0 && <span>Totaal rijen: <strong>{field.total_rows}</strong></span>}
                      {field.empty_count > 0 && <span>Leeg: <strong style={{ color: 'var(--red)' }}>{field.empty_count}</strong></span>}
                      {field.invalid_count > 0 && <span>Afwijkend: <strong style={{ color: 'var(--amber)' }}>{field.invalid_count}</strong></span>}
                    </div>
                    {!field.mapped_column && field.status === 'ontbreekt' && (
                      <div style={{ marginTop: 8, fontSize: 12, color: 'var(--amber)', fontWeight: 500 }}>
                        💡 Hernoem de kolom in het exportbestand, of controleer de spelling.
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Hoofd component ──────────────────────────────────────────────────────────

export default function BeschikbaarheidsRapport({ results, systems, onBack }) {
  const [rapport,       setRapport]       = useState(null)
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState(null)
  const [orgName,       setOrgName]       = useState('')
  const [exporting,     setExporting]     = useState(false)
  const [exportError,   setExportError]   = useState(null)
  const [editingOrg,    setEditingOrg]    = useState(false)

  const runId       = results?.run_id
  const systemsStr  = (systems || []).join(',')
  const orgParam    = orgName || 'Zorginstelling'

  // Laad rapportdata via de API
  useEffect(() => {
    if (!runId) { setError('Geen scan-ID beschikbaar.'); setLoading(false); return }
    setLoading(true)
    getBeschikbaarheidsRapport(runId, orgParam, systemsStr)
      .then(data => { setRapport(data); setLoading(false) })
      .catch(e   => { setError(e.message); setLoading(false) })
  }, [runId, orgParam, systemsStr])  // eslint-disable-line

  const handleExport = async () => {
    setExporting(true)
    setExportError(null)
    try {
      await exportBeschikbaarheidsRapportPdf(runId, orgParam, systemsStr)
    } catch (e) {
      setExportError('PDF-export mislukt. Controleer of de backend bereikbaar is.')
    } finally {
      setExporting(false)
    }
  }

  // ── Loading / Error states ──
  if (loading) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Spinner />
    </div>
  )

  if (error) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <div style={{ maxWidth: 740, margin: '40px auto', padding: '0 24px' }}>
        <div style={{ background: 'var(--red-bg)', border: '1px solid var(--red-light)', borderRadius: 'var(--radius-xl)', padding: 24, color: 'var(--red)' }}>
          <strong>Fout bij laden rapport:</strong> {error}
        </div>
      </div>
    </div>
  )

  const avail = rapport.availability_summary
  const meta  = rapport.meta
  const scanDate = meta.scan_date
    ? new Date(meta.scan_date).toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' })
    : new Date().toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' })

  // Genereer conclusietekst (client-side, zelfde logica als backend)
  const score = avail.availability_score
  let conclusie
  if (score >= 80 && avail.required_missing === 0) {
    conclusie = `De beschikbaarheidsscore van ${Math.round(score)}% geeft aan dat de aangeleverde data grotendeels volledig is. Alle verplichte velden zijn aanwezig. De dataset is geschikt voor verdere validatie in stap 2.`
  } else if (score >= 60) {
    conclusie = `De beschikbaarheidsscore van ${Math.round(score)}% wijst op een gedeeltelijk complete dataset. ${avail.fields_missing} velden ontbreken en ${avail.fields_ambiguous} velden zijn deels beschikbaar. Herstel de ontbrekende velden vóór u doorgaat naar stap 2.`
  } else {
    conclusie = `De beschikbaarheidsscore van ${Math.round(score)}% geeft aan dat een groot deel van de verwachte data-elementen ontbreekt of niet herkend wordt. ${avail.fields_missing} velden ontbreken, waarvan ${avail.required_missing} verplicht. Verbetering van de databeschikbaarheid is een vereiste vóór verdere analyse.`
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>

      {/* ── Sticky topbalk ── */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 100,
        background: '#fff', borderBottom: '1px solid var(--border)',
        padding: '0 32px', height: 56,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <NavBack onClick={onBack} dark />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--blue)' }}>Rhadix</span>
            <span style={{ color: 'var(--border2)' }}>›</span>
            <span style={{ fontSize: 14, color: 'var(--text2)', fontWeight: 500 }}>Beschikbaarheidsrapport</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          {exportError && (
            <span style={{ fontSize: 12, color: 'var(--red)' }}>{exportError}</span>
          )}
          <button
            onClick={handleExport}
            disabled={exporting}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: exporting ? 'var(--border)' : 'var(--blue)',
              color: '#fff', border: 'none', borderRadius: 'var(--radius)',
              padding: '9px 16px', fontSize: 13, fontWeight: 600,
              cursor: exporting ? 'not-allowed' : 'pointer',
              fontFamily: 'var(--font)', whiteSpace: 'nowrap',
            }}
          >
            {exporting ? '⏳ Exporteren…' : '⬇ Exporteer PDF'}
          </button>
        </div>
      </div>

      {/* ── Rapportinhoud ── */}
      <div style={{ maxWidth: 860, margin: '0 auto', padding: '36px 24px 60px', width: '100%' }}>

        {/* Rapportkop */}
        <div style={{
          background: 'var(--blue-hero, var(--blue))',
          borderRadius: 'var(--radius-xl)', padding: '32px 36px', marginBottom: 24,
          color: '#fff',
        }}>
          <div style={{
            display: 'inline-flex', background: 'rgba(255,255,255,.18)',
            color: '#fff', fontSize: 11, fontWeight: 700,
            padding: '4px 12px', borderRadius: 20, marginBottom: 14, letterSpacing: '0.08em',
          }}>
            STAP 1 — BESCHIKBAARHEID VAN DATA
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 8, color: '#fff' }}>
            Rhadix Beschikbaarheidsrapport
          </h1>

          {/* Meta-rij */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20, marginTop: 16 }}>
            {[
              {
                label: 'Organisatie',
                value: editingOrg ? null : orgParam,
                edit: true,
              },
              { label: 'Bronsysteem',  value: systems?.join(', ') || meta.systems?.join(', ') || '—' },
              { label: 'Scan',         value: meta.scan_label || '—' },
              { label: 'Datum',        value: scanDate },
            ].map(item => (
              <div key={item.label}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,.55)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 3 }}>
                  {item.label}
                </div>
                {item.edit && editingOrg ? (
                  <input
                    autoFocus
                    defaultValue={orgName}
                    onBlur={e => { setOrgName(e.target.value); setEditingOrg(false) }}
                    onKeyDown={e => { if (e.key === 'Enter') { setOrgName(e.target.value); setEditingOrg(false) } }}
                    style={{
                      fontSize: 14, fontWeight: 600, background: 'rgba(255,255,255,.15)',
                      border: '1px solid rgba(255,255,255,.4)', borderRadius: 6,
                      color: '#fff', padding: '2px 8px', fontFamily: 'var(--font)',
                    }}
                  />
                ) : (
                  <div
                    onClick={item.edit ? () => setEditingOrg(true) : undefined}
                    style={{
                      fontSize: 14, fontWeight: 600, color: '#fff',
                      cursor: item.edit ? 'text' : 'default',
                      borderBottom: item.edit ? '1px dashed rgba(255,255,255,.4)' : 'none',
                      paddingBottom: item.edit ? 1 : 0,
                    }}
                    title={item.edit ? 'Klik om organisatienaam in te stellen' : undefined}
                  >
                    {item.value}
                    {item.edit && <span style={{ fontSize: 10, marginLeft: 5, opacity: 0.6 }}>✏</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Let op: stap-1-afbakening */}
        <div style={{
          background: 'var(--blue-light)', border: '1px solid var(--blue-mid)',
          borderRadius: 'var(--radius-xl)', padding: '12px 18px',
          marginBottom: 24, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 16 }}>ℹ️</span>
          <span style={{ fontSize: 13, color: 'var(--blue)', lineHeight: 1.5 }}>
            <strong>Dit rapport gaat uitsluitend over de beschikbaarheid van data.</strong>{' '}
            Datakwaliteit en KIK-V readiness worden behandeld in stap 2 (Rhadix Dashboard).
          </span>
        </div>

        {/* Samenvatting */}
        <section style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 16 }}>
            Samenvatting beschikbaarheid
          </h2>

          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border)', padding: '24px', marginBottom: 16,
            boxShadow: 'var(--shadow)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 20, marginBottom: 20 }}>
              <ScoreRing score={avail.availability_score} />

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                {[
                  { label: 'Totaal velden',       value: avail.total_fields,       color: 'var(--text)' },
                  { label: 'Aanwezig',             value: avail.fields_present,     color: 'var(--green)' },
                  { label: 'Ontbreekt',            value: avail.fields_missing,     color: 'var(--red)' },
                  { label: 'Deels beschikbaar',    value: avail.fields_ambiguous,   color: 'var(--amber)' },
                ].map(s => (
                  <div key={s.label} style={{
                    background: 'var(--bg)', borderRadius: 'var(--radius)',
                    padding: '12px 16px', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 24, fontWeight: 800, color: s.color, letterSpacing: '-0.02em' }}>{s.value}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Schema-uploadstatus */}
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Schema's aangeleverd
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {avail.schemas.map(s => (
                  <span key={s.schema_key} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 5,
                    fontSize: 12, padding: '4px 12px', borderRadius: 20, fontWeight: 600,
                    background: s.file_uploaded ? 'var(--green-light)' : 'var(--red-light)',
                    color: s.file_uploaded ? 'var(--green)' : 'var(--red)',
                  }}>
                    {s.file_uploaded ? '✓' : '✕'} {s.schema_label}
                  </span>
                ))}
              </div>
              {avail.required_missing > 0 && (
                <div style={{ marginTop: 10, fontSize: 13, color: 'var(--red)', fontWeight: 600 }}>
                  ⚠ {avail.required_missing} verplicht{avail.required_missing === 1 ? '' : 'e'} veld{avail.required_missing === 1 ? '' : 'en'} {avail.required_missing === 1 ? 'ontbreekt' : 'ontbreken'}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Per-schema veldenoverzicht */}
        <section style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 4 }}>
            Overzicht per veld
          </h2>
          <p style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 16, lineHeight: 1.5 }}>
            Klik op een rij met een afwijking om toelichting en voorbeeldgegevens te bekijken.
          </p>

          {avail.schemas.map(schema => (
            <SchemaSection key={schema.schema_key} schema={schema} />
          ))}
        </section>

        {/* Conclusie */}
        <section style={{ marginBottom: 28 }}>
          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border)', padding: '24px',
            boxShadow: 'var(--shadow)',
          }}>
            <h2 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)', marginBottom: 12 }}>Conclusie</h2>
            <p style={{ fontSize: 14, color: 'var(--text2)', lineHeight: 1.7, margin: 0 }}>{conclusie}</p>
          </div>
        </section>

        {/* Aanbevolen vervolgstappen */}
        <section>
          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border)', padding: '24px',
            boxShadow: 'var(--shadow)',
          }}>
            <h2 style={{ fontSize: 16, fontWeight: 800, color: 'var(--text)', marginBottom: 16 }}>
              Aanbevolen vervolgstappen
            </h2>

            {/* Automatische stappen op basis van rapport */}
            {avail.schemas.some(s => !s.file_uploaded) && (
              <StepCard
                nr={1} color="red"
                title="Upload ontbrekende bestanden"
                body={`De volgende schema's zijn niet aangeleverd: ${avail.schemas.filter(s => !s.file_uploaded).map(s => s.schema_label).join(', ')}. Upload deze via 'Start nieuwe scan'.`}
              />
            )}
            {avail.required_missing > 0 && (
              <StepCard
                nr={avail.schemas.some(s => !s.file_uploaded) ? 2 : 1} color="red"
                title={`${avail.required_missing} verplichte velden aanvullen`}
                body="Controleer de exportconfiguratie van uw bronsysteem. Verplichte velden moeten altijd aanwezig zijn voor een geldige KIK-V-aanlevering."
              />
            )}
            {avail.schemas.some(s => s.file_uploaded && s.total_columns > 0 && s.recognized_columns < s.total_columns) && (
              <StepCard
                nr={avail.required_missing > 0 ? 3 : avail.schemas.some(s => !s.file_uploaded) ? 2 : 1}
                color="amber"
                title="Stem kolomnamen af op KIK-V aliassen"
                body="Niet alle kolommen worden automatisch herkend. Hernoem kolommen naar de bekende aliassen of controleer de spelling."
              />
            )}
            {avail.fields_ambiguous > 0 && (
              <StepCard
                nr={4} color="amber"
                title="Controleer deels beschikbare velden"
                body={`${avail.fields_ambiguous} velden zijn aanwezig maar bevatten afwijkende waarden. Klik op de rij in de tabel hierboven voor details.`}
              />
            )}

            {/* Aanbevelingen uit rapport */}
            {rapport.recommendations.slice(0, 3).map((rec, i) => (
              <StepCard
                key={rec.recommendation_id}
                nr={5 + i} color="blue"
                title={rec.title}
                body={rec.rationale}
              />
            ))}

            <StepCard
              nr="→" color="green"
              title="Ga verder naar stap 2: Rhadix Dashboard"
              body="Na het oplossen van de beschikbaarheidsproblemen kunt u de datakwaliteit en KIK-V-conformiteit beoordelen via het Rhadix Dashboard."
            />
          </div>
        </section>

      </div>
    </div>
  )
}

function StepCard({ nr, color, title, body }) {
  const colors = {
    red:   { bg: 'var(--red-bg)',   border: 'var(--red-light)',   text: 'var(--red)'   },
    amber: { bg: 'var(--amber-bg)', border: 'var(--amber-light)', text: 'var(--amber)' },
    blue:  { bg: 'var(--blue-light)',border: 'var(--blue-mid)',   text: 'var(--blue)'  },
    green: { bg: 'var(--green-bg)', border: 'var(--green-light)', text: 'var(--green)' },
  }
  const c = colors[color] || colors.blue
  return (
    <div style={{
      display: 'flex', gap: 14, marginBottom: 12,
      padding: '14px 16px', borderRadius: 'var(--radius)',
      background: c.bg, border: `1px solid ${c.border}`,
    }}>
      <div style={{
        flexShrink: 0, width: 28, height: 28, borderRadius: '50%',
        background: c.text, color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 800,
      }}>
        {nr}
      </div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 3 }}>{title}</div>
        <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>{body}</div>
      </div>
    </div>
  )
}
