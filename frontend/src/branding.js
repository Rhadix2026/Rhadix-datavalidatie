// branding.js — pas de effectieve look-and-feel toe (kleuren + logo + wordmerk).
import { createContext } from 'react'

// Context met de effectieve branding ({ preset, primary_color, accent_color, wordmark, logoUrl }).
export const BrandingContext = createContext(null)

// ── kleur-helpers ────────────────────────────────────────────────────────────
function hexToRgb(hex) {
  if (!hex) return null
  let h = hex.replace('#', '')
  if (h.length === 3) h = h.split('').map(c => c + c).join('')
  if (h.length !== 6) return null
  const n = parseInt(h, 16)
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }
}
function toHex({ r, g, b }) {
  const c = v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')
  return `#${c(r)}${c(g)}${c(b)}`
}
// mix kleur richting target (#fff of #000) met factor 0..1
function mix(hex, target, amount) {
  const a = hexToRgb(hex), b = hexToRgb(target)
  if (!a || !b) return hex
  return toHex({ r: a.r + (b.r - a.r) * amount, g: a.g + (b.g - a.g) * amount, b: a.b + (b.b - a.b) * amount })
}

// Bouw de logo-URL uit de backend-payload (logo_tenant_id + logo_version).
export function logoUrlFor(branding) {
  if (!branding || !branding.logo_tenant_id) return null
  const v = branding.logo_version ? `?v=${branding.logo_version}` : ''
  return `/api/branding/${branding.logo_tenant_id}/logo${v}`
}

const VARS = ['--blue', '--blue-dark', '--blue-hero', '--blue-light', '--blue-mid',
              '--k-blue', '--k-blue-strong', '--k-blue-light', '--k-blue-mid']

// Zet (of wis) de CSS-variabelen op <html> op basis van de branding.
export function applyBrandingColors(branding) {
  const root = document.documentElement
  const primary = branding && branding.primary_color
  const accent  = (branding && branding.accent_color) || primary
  if (!primary) {
    VARS.forEach(v => root.style.removeProperty(v))   // terug naar index.css :root
    return
  }
  const dark  = mix(primary, '#000000', 0.18)
  const light = mix(primary, '#ffffff', 0.90)
  const midc  = mix(primary, '#ffffff', 0.55)
  root.style.setProperty('--blue', primary)
  root.style.setProperty('--blue-dark', dark)
  root.style.setProperty('--blue-hero', accent)
  root.style.setProperty('--blue-light', light)
  root.style.setProperty('--blue-mid', midc)
  root.style.setProperty('--k-blue', primary)
  root.style.setProperty('--k-blue-strong', dark)
  root.style.setProperty('--k-blue-light', light)
  root.style.setProperty('--k-blue-mid', midc)
}
