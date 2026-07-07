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
  suresync: {
    name: 'SureSync',
    sub: 'Databeschikbaarheid in de zorg',
    logo: '/suresync-logo-light.svg',   // officieel logo (lichte variant voor donkere balk)
    logoLight: '/suresync-logo-light.svg',
    logoColor: '/suresync-logo.svg',
    wordmark: 'SureSync',
  },
}

export function currentBrand() {
  try { return document.documentElement.dataset.brand || 'rhadix' } catch { return 'rhadix' }
}

export function getInitialBrand() {
  try {
    const p = new URLSearchParams(window.location.search).get('brand')
    if (p === 'suresync' || p === 'rhadix') return p
    const s = sessionStorage.getItem('rhadix:brand')
    if (s === 'suresync' || s === 'rhadix') return s
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
