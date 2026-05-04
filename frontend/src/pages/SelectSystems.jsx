import { useState } from 'react'
import { Nav, NavBack, Page, PageTitle, BtnPrimary } from '../components/UI'

const SYSTEMS = [
  { id: 'afas_hrm',         label: 'AFAS Profit HRM',      vendor: 'AFAS Software',   color: '#2d6be4', status: 'actief',  note: 'Volledige KIK-V mapping, directe export via GetConnector' },
  { id: 'nedap_ons',        label: 'Nedap ONS',             vendor: 'Nedap',            color: '#0ea5e9', status: 'actief',  note: 'Referentieontwerp v6.0 — camelCase kolomnamen, contracttype-vertaling ingebouwd' },
  { id: 'nmbrs',            label: 'NMBRS',                  vendor: 'Visma',            color: '#8b5cf6', status: 'binnenkort', note: 'Referentieontwerp in ontwikkeling' },
  { id: 'exact',            label: 'Exact Online',           vendor: 'Exact',            color: '#10b981', status: 'binnenkort', note: 'Referentieontwerp in ontwikkeling' },
  { id: 'visma',            label: 'Visma',                  vendor: 'Visma',            color: '#f59e0b', status: 'binnenkort', note: 'Referentieontwerp in ontwikkeling' },
  { id: 'sap',              label: 'SAP SuccessFactors',     vendor: 'SAP',              color: '#ef4444', status: 'binnenkort', note: 'Referentieontwerp in ontwikkeling' },
  { id: 'unit4',            label: 'Unit4',                  vendor: 'Unit4',            color: '#6366f1', status: 'binnenkort', note: 'Referentieontwerp in ontwikkeling' },
  { id: 'raet',             label: 'Raet / Youforce',        vendor: 'Visma',            color: '#64748b', status: 'binnenkort', note: 'Referentieontwerp in ontwikkeling' },
]

export default function SelectSystems({ onNext, onBack, initialSelected = [] }) {
  const [selected, setSelected] = useState(initialSelected)

  const toggle = (s) => {
    if (s.status !== 'actief') return
    setSelected(prev => prev.includes(s.id) ? prev.filter(x => x !== s.id) : [...prev, s.id])
  }

  const actief    = SYSTEMS.filter(s => s.status === 'actief')
  const binnenkort = SYSTEMS.filter(s => s.status === 'binnenkort')

  const SystemRow = ({ s, last }) => {
    const isSelected  = selected.includes(s.id)
    const isDisabled  = s.status !== 'actief'
    return (
      <div
        onClick={() => toggle(s)}
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
            <span style={{ fontSize: 11, color: 'var(--text4)', fontWeight: 400 }}>{s.vendor}</span>
            {s.status === 'actief' && (
              <span style={{
                fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 10,
                background: 'var(--green-light)', color: 'var(--green)', letterSpacing: '0.04em',
              }}>ACTIEF</span>
            )}
            {s.status === 'binnenkort' && (
              <span style={{
                fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 10,
                background: 'var(--amber-light)', color: 'var(--amber)',
              }}>Binnenkort</span>
            )}
          </div>
          {s.note && (
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 3, lineHeight: 1.4 }}>
              {s.note}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Nav right={<NavBack onClick={onBack} />} />
      <Page>
        <PageTitle
          title="Selecteer bronsysteem"
          sub="Kies het systeem waaruit uw HRM-data afkomstig is"
        />

        {/* Actieve systemen */}
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em',
          textTransform: 'uppercase', marginBottom: 8 }}>
          Ondersteunde systemen
        </div>
        <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)',
          overflow: 'hidden', marginBottom: 20 }}>
          {actief.map((s, i) => <SystemRow key={s.id} s={s} last={i === actief.length - 1} />)}
        </div>

        {/* Binnenkort */}
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em',
          textTransform: 'uppercase', marginBottom: 8 }}>
          In ontwikkeling
        </div>
        <div style={{ background: '#fff', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border)',
          overflow: 'hidden', marginBottom: 24 }}>
          {binnenkort.map((s, i) => <SystemRow key={s.id} s={s} last={i === binnenkort.length - 1} />)}
        </div>

        <BtnPrimary onClick={() => onNext(selected)} disabled={!selected.length}
          style={{ width: '100%', justifyContent: 'center', padding: '13px' }}>
          Volgende →
        </BtnPrimary>
      </Page>
    </div>
  )
}
