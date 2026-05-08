import { useState } from 'react'
import { Nav, NavBack, Page, PageTitle, BtnPrimary } from '../components/UI'

// ── HRM-systemen (KIK-V) ──────────────────────────────────────────────────────
const KIKV_SYSTEMS = [
  { id: 'afas_hrm',        label: 'AFAS Profit HRM',        vendor: 'AFAS Software',  color: '#2d6be4', status: 'actief', note: 'KIK-V mapping' },
  { id: 'nedap_ons',       label: 'Nedap/ONS',              vendor: 'Nedap',           color: '#0ea5e9', status: 'actief', note: 'Referentieontwerp v6.0' },
  { id: 'exact_fin',       label: 'Exact Financial',        vendor: 'Exact Software',  color: '#10b981', status: 'actief', note: 'Referentieontwerp v6.0' },
  { id: 'afas_profit_fin', label: 'AFAS PROFIT Financieel', vendor: 'AFAS Software',   color: '#f59e0b', status: 'actief', note: 'Referentieontwerp v6.0' },
  { id: 'visma_puur',      label: 'Visma PUUR',             vendor: 'Visma',           color: '#8b5cf6', status: 'actief', note: 'Referentieontwerp v6.0' },
]

// ── EPD/ECD-systemen (ZIB's) ──────────────────────────────────────────────────
const ZIB_SYSTEMS = [
  { id: 'chipsoft_hix', label: 'ChipSoft HiX', vendor: 'ChipSoft', color: '#0ea5e9', status: 'actief', note: 'ZIB-export' },
  { id: 'epic',         label: 'Epic',         vendor: 'Epic',      color: '#2d6be4', status: 'actief', note: 'ZIB-export' },
  { id: 'nedap_ons',    label: 'Nedap/ONS',    vendor: 'Nedap',     color: '#10b981', status: 'actief', note: 'ZIB-export' },
]

// ── Standaard-keuze ────────────────────────────────────────────────────────────
const STANDARDS = [
  {
    id: 'kikv',
    label: 'KIK-V',
    fullLabel: 'Keteninformatie Kerngegevens Verbeteren',
    icon: '🏥',
    description: 'Binnen het Programma KIK-V werken informatie-vragende partijen samen aan het beter afstemmen en uitwisselen van kwaliteits-, personeels- en financiële gegevens. Rhadix valideert uw brondata tegen de KIK-V Afsprakenset — geschikt voor medewerkers, werkovereenkomsten, functies, verzuim, vestigingen en meer.',
    color: 'var(--blue)',
    bg: 'var(--blue-light)',
    border: 'var(--blue-mid)',
    systems: 'Bronsystemen',
  },
  {
    id: 'zib',
    label: 'ZIB\'s',
    fullLabel: 'Zorginformatiebouwstenen (Nictiz 2020)',
    icon: '💊',
    description: 'Valideer cliëntdata uit uw EPD/ECD tegen de ZIB-standaard van Nictiz. Geschikt voor patiëntgegevens, diagnoses, medicatie en allergieën.',
    color: '#059669',
    bg: '#f0fdf4',
    border: '#bbf7d0',
    systems: 'EPD/ECD-systemen',
  },
]

// ── Subcomponenten ─────────────────────────────────────────────────────────────
function SystemRow({ s, selected, onToggle, last }) {
  const isSelected = selected.includes(s.id)
  const isDisabled = s.status !== 'actief'
  return (
    <div
      onClick={() => !isDisabled && onToggle(s.id)}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: 14,
        padding: '16px 20px', cursor: isDisabled ? 'default' : 'pointer',
        borderBottom: last ? 'none' : '1px solid var(--border)',
        background: isSelected ? 'var(--blue-light)' : isDisabled ? '#fafafa' : '#fff',
        transition: 'background .1s', opacity: isDisabled ? 0.55 : 1,
      }}
    >
      <div style={{
        width: 22, height: 22, borderRadius: 6, flexShrink: 0, marginTop: 1,
        border: `2px solid ${isSelected ? 'var(--blue)' : 'var(--border2)'}`,
        background: isSelected ? 'var(--blue)' : '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'all .1s',
      }}>
        {isSelected && <span style={{ color: '#fff', fontSize: 13, lineHeight: 1 }}>✓</span>}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>{s.label}</span>
          <span style={{ fontSize: 11, color: 'var(--text4)' }}>{s.vendor}</span>
          {s.status === 'actief' && (
            <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 10, background: 'var(--green-light)', color: 'var(--green)', letterSpacing: '0.04em' }}>ACTIEF</span>
          )}
          {s.status === 'binnenkort' && (
            <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 10, background: 'var(--amber-light)', color: 'var(--amber)' }}>Binnenkort</span>
          )}
        </div>
        {s.note && (
          <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 3, lineHeight: 1.4 }}>{s.note}</div>
        )}
      </div>
    </div>
  )
}

// ── Hoofdcomponent ─────────────────────────────────────────────────────────────
export default function SelectSystems({ onNext, onBack }) {
  const [step, setStep]         = useState('standard')   // 'standard' | 'systems'
  const [standard, setStandard] = useState(null)
  const [selected, setSelected] = useState([])

  const toggle = (id) => setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const chooseStandard = (std) => {
    setStandard(std)
    setSelected([])
    setStep('systems')
  }

  const systems    = standard === 'zib' ? ZIB_SYSTEMS : KIKV_SYSTEMS
  const actief     = systems.filter(s => s.status === 'actief')
  const binnenkort = systems.filter(s => s.status === 'binnenkort')

  // ── Stap 1: Standaard kiezen ────────────────────────────────────────────────
  if (step === 'standard') {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
        <Nav right={<NavBack onClick={onBack} />} />
        <Page>
          <PageTitle
            title="Kies een gegevensstandaard"
            sub="Rhadix valideert uw data tegen de gekozen standaard"
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
            {STANDARDS.map(std => (
              <div
                key={std.id}
                onClick={() => chooseStandard(std.id)}
                style={{
                  background: '#fff', borderRadius: 'var(--radius-xl)',
                  border: `2px solid var(--border)`, padding: '28px 24px',
                  cursor: 'pointer', transition: 'all .15s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = std.color
                  e.currentTarget.style.background = std.bg
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border)'
                  e.currentTarget.style.background = '#fff'
                }}
              >
                <div style={{ fontSize: 36, marginBottom: 12 }}>{std.icon}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 22, fontWeight: 800, color: std.color, letterSpacing: '-0.02em' }}>{std.label}</span>
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', marginBottom: 10 }}>{std.fullLabel}</div>
                <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5, marginBottom: 14 }}>{std.description}</div>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  fontSize: 12, fontWeight: 600, color: std.color,
                  background: std.bg, border: `1px solid ${std.border}`,
                  padding: '5px 12px', borderRadius: 20,
                }}>
                  {std.systems} →
                </div>
              </div>
            ))}
          </div>

        </Page>
      </div>
    )
  }

  // ── Stap 2: Systeem kiezen ──────────────────────────────────────────────────
  const std = STANDARDS.find(s => s.id === standard)
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={() => setStep('standard')} />} />
      <Page>
        {/* Standaard-indicator */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: std.bg, border: `1px solid ${std.border}`,
          color: std.color, fontSize: 13, fontWeight: 700,
          padding: '6px 14px', borderRadius: 20, marginBottom: 20,
        }}>
          {std.icon} {std.label} — {std.fullLabel}
        </div>

        <PageTitle
          title="Selecteer bronsysteem"
          sub={`Kies het bronsysteem waaruit uw data afkomstig is`}
        />

        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 8 }}>
          Ondersteunde systemen
        </div>
        <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)', overflow: 'hidden', marginBottom: 20 }}>
          {actief.map((s, i) => (
            <SystemRow key={s.id} s={s} selected={selected} onToggle={toggle} last={i === actief.length - 1} />
          ))}
        </div>


        <BtnPrimary
          onClick={() => onNext(selected, standard)}
          disabled={!selected.length}
          style={{ width: '100%', justifyContent: 'center', padding: '13px' }}
        >
          Volgende →
        </BtnPrimary>
      </Page>
    </div>
  )
}
