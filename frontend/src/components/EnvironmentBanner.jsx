/**
 * EnvironmentBanner
 * Toont een gekleurde balk bovenaan de pagina als de app NIET in productie draait.
 * Verdwijnt automatisch in productie (VITE_RHADIX_ENV=production of leeg).
 */

const ENV = import.meta.env.VITE_RHADIX_ENV || 'production'

const ENV_CONFIG = {
  staging: {
    label:   '⚠ STAGING OMGEVING',
    sub:     'Dit is geen productie — wijzigingen hier zijn voor testdoeleinden',
    bg:      '#f59e0b',
    color:   '#1c1917',
    border:  '#d97706',
  },
  development: {
    label:   '🔧 ONTWIKKELOMGEVING',
    sub:     'Lokale development build',
    bg:      '#8b5cf6',
    color:   '#fff',
    border:  '#7c3aed',
  },
}

export default function EnvironmentBanner() {
  const cfg = ENV_CONFIG[ENV]
  if (!cfg) return null   // productie → geen banner

  return (
    <div style={{
      position:   'fixed',
      top:        0,
      left:       0,
      right:      0,
      zIndex:     9999,
      background: cfg.bg,
      borderBottom: `2px solid ${cfg.border}`,
      padding:    '6px 16px',
      display:    'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap:        12,
      boxShadow:  '0 2px 8px rgba(0,0,0,.15)',
    }}>
      <span style={{ fontWeight: 800, fontSize: 13, color: cfg.color, letterSpacing: 0.5 }}>
        {cfg.label}
      </span>
      <span style={{ fontSize: 12, color: cfg.color, opacity: 0.8 }}>
        {cfg.sub}
      </span>
    </div>
  )
}

/**
 * Hoogte van de banner in pixels — gebruik dit om content niet achter de banner te verbergen.
 * Geeft 0 terug in productie.
 */
export const BANNER_HEIGHT = ENV_CONFIG[ENV] ? 36 : 0
