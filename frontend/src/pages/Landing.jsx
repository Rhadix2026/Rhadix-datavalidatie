import { Nav } from '../components/UI'

export default function Landing({ onStart }) {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />

      <div style={{ flex: 1, display: 'flex', alignItems: 'stretch' }}>
        {/* Left hero */}
        <div style={{
          flex: 1, background: 'var(--blue-hero)',
          padding: '72px 64px', display: 'flex',
          flexDirection: 'column', justifyContent: 'center',
        }}>
          {/* Logo in hero */}
          <div style={{ marginBottom: 36 }}>
            <img
              src="/rhadix-logo.png"
              alt="Rhadix"
              style={{ height: 56, objectFit: 'contain' }}
              onError={e => {
                e.target.style.display = 'none'
                e.target.nextSibling.style.display = 'block'
              }}
            />
            <span style={{
              display: 'none',
              fontFamily: 'var(--font-brand)', fontWeight: 800,
              fontSize: 32, color: '#fff', letterSpacing: '4px',
            }}>RHADIX</span>
          </div>

          <div style={{
            display: 'inline-flex', background: 'rgba(111,168,208,.25)',
            color: 'var(--rhadix-accent)', fontSize: 12, fontWeight: 600,
            padding: '6px 14px', borderRadius: 20, marginBottom: 24,
            alignSelf: 'flex-start', border: '1px solid rgba(111,168,208,.3)',
          }}>
            De readiness scan voor zorgdata
          </div>

          <h1 style={{
            fontFamily: 'var(--font)',
            fontSize: 38, fontWeight: 800, color: '#fff',
            lineHeight: 1.2, letterSpacing: '-0.02em', marginBottom: 20, maxWidth: 480,
          }}>
            Inzicht in data-gereedheid voor zorginstellingen
          </h1>

          <p style={{ fontSize: 15, color: 'rgba(168,197,224,.85)', lineHeight: 1.65, marginBottom: 40, maxWidth: 460 }}>
            Analyseer de gereedheid van uw zorgdata voor uitwisseling via moderne standaarden. Van mapping tot implementatie in weken in plaats van maanden.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <button onClick={onStart} style={{
              background: 'var(--rhadix-accent)', color: '#fff',
              border: 'none', borderRadius: 'var(--radius)', padding: '13px 28px',
              fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
              display: 'flex', alignItems: 'center', gap: 8,
              boxShadow: '0 4px 16px rgba(111,168,208,.35)',
            }}>
              Start nieuwe scan →
            </button>
          </div>
        </div>

        {/* Right: Hoe het werkt */}
        <div style={{
          width: 340, background: '#fff', padding: '48px 36px',
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          borderLeft: '1px solid var(--border)',
        }}>
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
            textTransform: 'uppercase', color: 'var(--rhadix-sub)', marginBottom: 24,
            fontFamily: 'var(--font-brand)',
          }}>
            Hoe het werkt
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {[
              { step: '1', label: 'Kies gegevensstandaard & bronsysteem' },
              { step: '2', label: 'Upload uw brondata' },
              { step: '3', label: 'Bekijk beschikbaarheidsrapport' },
              { step: '4', label: 'Ontvang advies & actiepunten' },
            ].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div style={{
                  width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
                  background: 'var(--blue-light)', border: '1.5px solid var(--blue-mid)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 12, fontWeight: 800, color: 'var(--blue)',
                }}>{s.step}</div>
                <span style={{ fontSize: 14, color: 'var(--text2)', fontWeight: 500, lineHeight: 1.35 }}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
