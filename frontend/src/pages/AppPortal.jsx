import { BANNER_HEIGHT } from '../components/EnvironmentBanner'
import { TreeDecoration } from '../components/UI'

// Per-omgeving instelbaar via VITE_*; fallback = staging-server.
const UITVRAAG_URL    = import.meta.env.VITE_UITVRAAG_URL    || 'http://46.224.224.26:5177'
const DATASTATION_URL = import.meta.env.VITE_DATASTATION_URL || 'http://46.224.224.26:5176'

function AppCard({ accent, accentBg, accentText, mark, laag, naam, omschrijving, badge, actie, onClick, disabled }) {
  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)',
      padding: '18px 20px', background: '#fff', display: 'flex', flexDirection: 'column',
      opacity: disabled ? 0.7 : 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10, flexShrink: 0, background: accentBg, color: accentText,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15, fontWeight: 800,
        }}>{mark}</div>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: accent, letterSpacing: '.3px' }}>{laag}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 8 }}>
            {naam}
            {badge && <span style={{ fontSize: 10, fontWeight: 700, background: accentBg, color: accentText, padding: '2px 7px', borderRadius: 999 }}>{badge}</span>}
          </div>
        </div>
      </div>
      <p style={{ margin: '0 0 14px', fontSize: 13, color: 'var(--text3)', lineHeight: 1.55, flex: 1 }}>{omschrijving}</p>
      <button onClick={disabled ? undefined : onClick} disabled={disabled} style={{
        alignSelf: 'flex-start', border: disabled ? '1px solid var(--border2)' : 'none',
        background: disabled ? '#fff' : accent, color: disabled ? 'var(--text3)' : '#fff',
        borderRadius: 'var(--radius)', padding: '9px 16px', fontSize: 14, fontWeight: 600,
        fontFamily: 'var(--font)', cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'inline-flex', alignItems: 'center', gap: 6,
      }}>{actie}</button>
    </div>
  )
}

export default function AppPortal({ onLogin }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'stretch', background: 'var(--bg)', paddingTop: BANNER_HEIGHT }}>

      {/* Links — branding + KIK-V-context */}
      <div style={{ flex: 1, background: 'var(--blue-hero)', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
        <div style={{ padding: '32px 48px 0', flexShrink: 0 }}>
          <a href="https://rhadix.nl" style={{ display: 'inline-block', textDecoration: 'none' }} title="Terug naar rhadix.nl">
            <img src="/rhadix-logo.jpg" alt="Rhadix" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
          </a>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 48px 90px', position: 'relative', zIndex: 1 }}>
          <span style={{ display: 'inline-flex', alignSelf: 'flex-start', background: 'rgba(111,168,208,.25)', color: 'rgba(168,197,224,.95)', fontSize: 11, fontWeight: 700, letterSpacing: '1.5px', padding: '5px 12px', borderRadius: 99, marginBottom: 22, textTransform: 'uppercase' }}>KIK-V · federatief datastelsel</span>
          <h1 style={{ fontWeight: 800, fontSize: 34, color: '#fff', lineHeight: 1.2, letterSpacing: '-0.02em', marginBottom: 16, maxWidth: 460 }}>
            Eén platform, <span style={{ color: 'var(--rhadix-accent)' }}>drie applicaties</span>
          </h1>
          <p style={{ fontSize: 15, color: 'rgba(168,197,224,.85)', lineHeight: 1.65, maxWidth: 430, marginBottom: 22 }}>
            De data blijft bij de zorgaanbieder; alleen de gevalideerde vraag reist via het vertrouwd netwerk.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', fontSize: 12.5, color: 'rgba(168,197,224,.9)' }}>
            <span style={{ fontWeight: 700, color: '#fff' }}>Ketenpartij</span>
            <span>→ vraag →</span>
            <span style={{ padding: '2px 8px', border: '1px solid rgba(255,255,255,.25)', borderRadius: 99 }}>vertrouwd netwerk</span>
            <span>→ antwoord ←</span>
            <span style={{ fontWeight: 700, color: '#fff' }}>Zorgaanbieder</span>
          </div>
        </div>
        <TreeDecoration opacity={0.12} style={{ position: 'absolute', bottom: -30, right: -20, transform: 'scale(6)' }} />
      </div>

      {/* Rechts — applicatiekeuze */}
      <div style={{ width: 460, background: '#fff', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '48px 40px', borderLeft: '1px solid var(--border)', overflowY: 'auto' }}>
        <div style={{ marginBottom: 22 }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text)', marginBottom: 6 }}>Kies een applicatie</h2>
          <p style={{ fontSize: 14, color: 'var(--text3)' }}>De drie Rhadix-applicaties binnen het KIK-V-stelsel.</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <AppCard accent="var(--green)" accentBg="var(--green-light)" accentText="#0F6E56"
            mark="DV" laag="BIJ DE BRON · DATAKWALITEIT" naam="Rhadix Datavalidatie"
            omschrijving="Pre-screening: is de datahuishouding van de zorgaanbieder klaar om gevalideerde vragen te beantwoorden?"
            actie="Inloggen →" onClick={onLogin} />
          <AppCard accent="var(--blue)" accentBg="var(--blue-light)" accentText="var(--blue-dark)"
            mark="U" laag="AFNEMERSKANT" naam="Rhadix Uitvraag"
            omschrijving="Gevalideerde vragen stellen aan zorgaanbieders en de antwoorden inzien, vergelijken en analyseren."
            actie="Inloggen →" onClick={() => { window.location.href = UITVRAAG_URL }} />
          <AppCard accent="var(--amber)" accentBg="var(--amber-light)" accentText="#854F0B"
            mark="DS" laag="BIJ DE BRON · REKENKRACHT" naam="Rhadix Datastation"
            omschrijving="Het datastation berekent het antwoord lokaal (SPARQL/Fuseki) bij de zorgaanbieder."
            actie="Inloggen →" onClick={() => { window.location.href = DATASTATION_URL }} />
        </div>
      </div>
    </div>
  )
}
