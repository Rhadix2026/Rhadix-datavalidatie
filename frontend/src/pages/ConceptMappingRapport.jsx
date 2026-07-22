import { useState } from 'react'
import { NavBack, Page, PageTitle } from '../components/UI'

const SCHEMA_LABELS = {
  medewerker: 'Medewerker',
  werkovereenkomst: 'Werkovereenkomst',
  functie: 'Functie',
  verzuim: 'Verzuim',
}

const ScoreBadge = ({ score }) => {
  const color = score >= 80 ? 'var(--green)' : score >= 60 ? 'var(--amber)' : 'var(--red)'
  const bg    = score >= 80 ? 'var(--green-light)' : score >= 60 ? 'var(--amber-light)' : 'var(--red-light)'
  return (
    <span style={{
      fontWeight: 700, fontSize: 13, padding: '3px 10px', borderRadius: 20,
      background: bg, color, display: 'inline-block',
    }}>
      {score}%
    </span>
  )
}

const ConceptTag = ({ uri, label }) => (
  <span title={uri} style={{
    fontSize: 11, fontFamily: 'monospace', padding: '2px 7px', borderRadius: 4,
    background: 'var(--blue-light)', color: 'var(--blue)',
    border: '1px solid var(--border)', display: 'inline-block', maxWidth: 280,
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'help',
  }}>
    {label || uri?.split('#')[1] || uri}
  </span>
)

// Hergebruik badge: toont in hoeveel KIK-V uitwisselprofielen het concept voorkomt
const HergebruikBadge = ({ count, total = 8, profielen = [] }) => {
  if (count === null || count === undefined) return null
  const pct = Math.round(count / total * 100)
  const color = pct >= 75 ? '#7c3aed' : pct >= 40 ? 'var(--k-blue)' : '#6b7280'
  const bg    = pct >= 75 ? '#f5f3ff' : pct >= 40 ? 'var(--k-blue-light)' : '#f9fafb'
  const tooltip = profielen.length > 0
    ? `Gebruikt in ${count}/${total} uitwisselprofielen:\n${profielen.map(p => '• ' + p).join('\n')}`
    : `Gebruikt in ${count}/${total} uitwisselprofielen`
  return (
    <span
      title={tooltip}
      style={{
        fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 20,
        background: bg, color, border: `1px solid ${color}30`,
        display: 'inline-flex', alignItems: 'center', gap: 3,
        cursor: 'help', whiteSpace: 'nowrap', flexShrink: 0,
      }}
    >
      ♻ {count}/{total}
    </span>
  )
}

const FieldRow = ({ field, info, last }) => {
  const [open, setOpen] = useState(false)
  const hasIssues = info.issues_sample?.length > 0
  const pct = info.mapping_pct ?? 100

  return (
    <>
      <div
        onClick={() => hasIssues && setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '12px 20px', cursor: hasIssues ? 'pointer' : 'default',
          borderBottom: last && !open ? 'none' : '1px solid var(--border)',
          background: open ? 'var(--blue-light)' : '#fff',
        }}
      >
        {/* Status icon */}
        <div style={{
          width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14,
          background: pct === 100 ? 'var(--green-light)' : pct >= 60 ? 'var(--amber-light)' : 'var(--red-light)',
          color:      pct === 100 ? 'var(--green)'       : pct >= 60 ? 'var(--amber)'       : 'var(--red)',
        }}>
          {pct === 100 ? '✓' : '!'}
        </div>

        {/* Veldnaam + concept */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text)' }}>
              {field}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text3)' }}>→</span>
            <ConceptTag uri={info.concept_uri} label={info.concept_label} />
            <HergebruikBadge
              count={info.hergebruik_count}
              total={info.hergebruik_total}
              profielen={info.hergebruik_profielen}
            />
          </div>
          <div style={{ fontSize: 11, color: 'var(--text4)', marginTop: 2 }}>
            Kolom: <em>{info.col_name}</em>
            &nbsp;·&nbsp;
            {info.mapped_rows} / {info.mapped_rows + info.unmapped_rows} rijen gemapped
          </div>
        </div>

        {/* Score */}
        <ScoreBadge score={pct} />
        {hasIssues && (
          <span style={{ fontSize: 12, color: 'var(--text3)', marginLeft: 4 }}>
            {open ? '▲' : '▼'}
          </span>
        )}
      </div>

      {/* Issues detail */}
      {open && hasIssues && (
        <div style={{
          background: '#fff8f8', borderBottom: last ? 'none' : '1px solid var(--border)',
          padding: '10px 20px 14px 60px',
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--red)', marginBottom: 6 }}>
            Mapping-problemen (max. 3 voorbeelden)
          </div>
          {info.issues_sample.map((s, i) => (
            <div key={i} style={{
              background: '#fff', border: '1px solid var(--border)',
              borderRadius: 6, padding: '8px 12px', marginBottom: 6, fontSize: 12,
            }}>
              <strong>Rij {s.row}</strong> — waarde: <code style={{ color: 'var(--blue)' }}>«{s.value}»</code>
              <ul style={{ margin: '4px 0 0 16px', padding: 0, color: 'var(--text2)' }}>
                {s.issues.map((iss, j) => <li key={j}>{iss}</li>)}
              </ul>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

const SchemaCard = ({ result }) => {
  const { schema, fields, summary } = result
  const score = summary.mapping_score

  return (
    <div style={{
      background: '#fff', borderRadius: 'var(--radius-xl)',
      border: '1px solid var(--border)', overflow: 'hidden', marginBottom: 20,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 20px', borderBottom: '1px solid var(--border)',
        background: 'var(--bg)',
      }}>
        <div>
          <span style={{ fontWeight: 700, fontSize: 15 }}>
            {SCHEMA_LABELS[schema] || schema}
          </span>
          <span style={{ fontSize: 12, color: 'var(--text3)', marginLeft: 10 }}>
            {summary.mapped_fields}/{summary.total_fields} velden volledig gemapped
          </span>
        </div>
        <ScoreBadge score={score} />
      </div>

      {/* Velden */}
      {Object.entries(fields).map(([field, info], i, arr) => (
        <FieldRow
          key={field}
          field={field}
          info={info}
          last={i === arr.length - 1}
        />
      ))}
    </div>
  )
}

export default function ConceptMappingRapport({ conceptMapping = [], onBack }) {
  const totalScore = conceptMapping.length
    ? Math.round(conceptMapping.reduce((s, r) => s + r.summary.mapping_score, 0) / conceptMapping.length)
    : null

  const handlePrint = () => window.print()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      {/* Sticky topbalk */}
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
            <span style={{ fontSize: 14, color: 'var(--text2)', fontWeight: 500 }}>Concept-mapping</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <button onClick={handlePrint} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'var(--blue)', color: '#fff', border: 'none',
            borderRadius: 'var(--radius)', padding: '9px 16px', fontSize: 13, fontWeight: 600,
            cursor: 'pointer', fontFamily: 'var(--font)', whiteSpace: 'nowrap',
          }}>
            ⬇ Exporteer PDF
          </button>
        </div>
      </div>
      <Page>
        <PageTitle
          title="Stap 2 — Concept-mapping"
          sub="Kunnen de velden worden gemapped naar KIK-V ontologieconcepten?"
        />

        {/* Totaalscore */}
        {totalScore !== null && (
          <div style={{
            background: '#fff', borderRadius: 'var(--radius-xl)',
            border: '1px solid var(--border)', padding: '18px 24px',
            display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24,
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, fontWeight: 800,
              background: totalScore >= 80 ? 'var(--green-light)' : totalScore >= 60 ? 'var(--amber-light)' : 'var(--red-light)',
              color:      totalScore >= 80 ? 'var(--green)'       : totalScore >= 60 ? 'var(--amber)'       : 'var(--red)',
            }}>
              {totalScore}%
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>
                {totalScore >= 80 ? 'Data grotendeels KIK-V mappable' : totalScore >= 60 ? 'Partieel KIK-V mappable' : 'Mapping-issues gevonden'}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text3)', marginTop: 2 }}>
                Gemiddeld concept-mapping percentage over {conceptMapping.length} schema('s)
              </div>
            </div>
          </div>
        )}

        {/* Uitleg */}
        <div style={{
          background: 'var(--blue-light)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-xl)', padding: '14px 18px', marginBottom: 16,
          fontSize: 13, color: 'var(--text2)', lineHeight: 1.6,
        }}>
          <strong>Wat controleert stap 2?</strong> Per veld wordt gecontroleerd of de waarde gemapped kan worden
          naar het bijbehorende KIK-V ontologieconcept (ONZ-ontologie). Klik op een veld met issues voor details.
          De concept-URI verwijst naar de formele definitie in de KIK-V standaard.
        </div>

        {/* Hergebruik legenda */}
        <div style={{
          background: '#faf5ff', border: '1px solid #e9d5ff',
          borderRadius: 'var(--radius-xl)', padding: '12px 18px', marginBottom: 24,
          fontSize: 12, color: '#6b7280', lineHeight: 1.6,
          display: 'flex', alignItems: 'flex-start', gap: 12,
        }}>
          <div style={{ fontSize: 20, lineHeight: 1, flexShrink: 0, marginTop: 2 }}>♻</div>
          <div>
            <strong style={{ color: '#7c3aed' }}>Hergebruik-indicator</strong>
            {' '}— het getal naast elk concept toont in hoeveel van de 8 KIK-V uitwisselprofielen
            dit concept voorkomt (bron: <em>kik-v-publicatieplatform.nl/kik-v-concepten</em>).{' '}
            <span style={{ color: '#7c3aed', fontWeight: 600 }}>Paars</span> = hoog hergebruik (≥75%),{' '}
            <span style={{ color: 'var(--k-blue)', fontWeight: 600 }}>blauw</span> = gemiddeld,{' '}
            <span style={{ color: '#6b7280', fontWeight: 600 }}>grijs</span> = laag.
            Hover over het badge voor de volledige profielenlijst.
          </div>
        </div>

        {/* Schema-kaarten */}
        {conceptMapping.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text3)', padding: '60px 0', fontSize: 14 }}>
            Geen concept-mapping resultaten beschikbaar.
            <br />Upload eerst bestanden via de hoofdpagina.
          </div>
        ) : (
          conceptMapping.map((result, i) => (
            <SchemaCard key={i} result={result} />
          ))
        )}
      </Page>
    </div>
  )
}
