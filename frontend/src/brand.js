// ─── Merk-laag (white-label) ─────────────────────────────────────────────────
// Default = Rhadix (productie verandert niets). 'suresync' = white-label demo,
// alleen zichtbaar op staging. Palet zit in index.css onder :root[data-brand=...].
// LET OP: SureSync-kleuren/logo zijn VOORLOPIG (wachten op officiële brand guide).
export const BRANDS = {
  rhadix: {
    name: 'Rhadix',
    sub: 'KIK-V · federatief datastelsel',
    logo: '/rhadix-logo.jpg',     // afbeelding
    wordmark: null,
  },
  kikv: {
    name: 'KIK-V',
    sub: 'Keteninformatie Kwaliteit Verpleeghuiszorg',
    logo: '/kikv-logo.png',
    wordmark: null,
  },
}

export function currentBrand() {
  try { return document.documentElement.dataset.brand || 'rhadix' } catch { return 'rhadix' }
}

export function getInitialBrand() {
  // Alternatieve skins (suresync/kikv) alleen buiten productie — productie blijft Rhadix.
  const isProd = (import.meta?.env?.VITE_RHADIX_ENV === 'production')
  const allowed = isProd ? ['rhadix'] : ['rhadix', 'kikv']
  try {
    const p = new URLSearchParams(window.location.search).get('brand')
    if (allowed.includes(p)) return p
    const s = sessionStorage.getItem('rhadix:brand')
    if (allowed.includes(s)) return s
  } catch { /* ignore */ }
  return 'rhadix'
}

// Logo voor het huidige merk (leest data-brand op <html>, fallback rhadix).
export function brandLogo() {
  let key = 'rhadix'
  try { key = document.documentElement.dataset.brand || 'rhadix' } catch { /* ignore */ }
  const b = BRANDS[key] || BRANDS.rhadix
  return b.logo || '/rhadix-logo.jpg'
}
