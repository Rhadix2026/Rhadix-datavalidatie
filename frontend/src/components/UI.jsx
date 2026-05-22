// ─── Rhadix logo (tree + naam + subtitel) ────────────────────────────────────
export function RhadixLogo({ height = 44 }) {
  return (
    <a href="https://rhadix.nl" style={{ display: 'flex', alignItems: 'center', textDecoration: 'none' }}>
      <img src="/rhadix-logo.svg" alt="Rhadix" style={{ height, width: 'auto', objectFit: 'contain' }} />
    </a>
  )
}

// ─── Boom decoratie (herbruikbaar op hero-pagina's) ──────────────────────────
export function TreeDecoration({ opacity = 0.18, style: sx = {} }) {
  return (
    <img
      src="/rhadix-tree.svg"
      alt=""
      style={{
        position: 'absolute', bottom: 0, right: -40,
        width: '65%', maxWidth: 500,
        opacity, pointerEvents: 'none', userSelect: 'none',
        objectFit: 'contain',
        ...sx
      }}
    />
  )
}


// ─── Nav ──────────────────────────────────────────────────────────────────────
export function Nav({ right, authUser, onLogout, onAdmin, onOrgAdmin,
                      onDashboard, onOrgDashboard, onPlatformDashboard }) {
  return (
    <header style={{
      background: 'var(--blue-hero)', borderBottom: '1px solid rgba(255,255,255,.08)',
      padding: '0 32px', height: 64, display: 'flex',
      alignItems: 'center', justifyContent: 'space-between',
      position: 'sticky', top: 0, zIndex: 100,
      boxShadow: '0 2px 12px rgba(0,0,0,.25)',
    }}>
      <RhadixLogo />
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {right}
        {authUser && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Dashboard links — visible based on role */}
            {onDashboard && (
              <button onClick={onDashboard} style={_navBtn}>📊 Dashboard</button>
            )}
            {(authUser.role === 'ORG_ADMIN' || authUser.role === 'RHADIX_ADMIN') && onOrgDashboard && (
              <button onClick={onOrgDashboard} style={_navBtn}>🏢 Organisatie</button>
            )}
            {authUser.role === 'RHADIX_ADMIN' && onPlatformDashboard && (
              <button onClick={onPlatformDashboard} style={_navBtn}>🌐 Platform</button>
            )}
            {/* Admin / beheer links */}
            {authUser.role === 'RHADIX_ADMIN' && onAdmin && (
              <button onClick={onAdmin} style={{
                background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
                borderRadius: 'var(--radius)', padding: '5px 12px',
                color: '#fff', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                fontFamily: 'var(--font)', letterSpacing: '.03em',
              }}>Admin</button>
            )}
            {authUser.role === 'ORG_ADMIN' && onOrgAdmin && (
              <button onClick={onOrgAdmin} style={{
                background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.2)',
                borderRadius: 'var(--radius)', padding: '5px 12px',
                color: '#fff', fontSize: 12, fontWeight: 700, cursor: 'pointer',
                fontFamily: 'var(--font)', letterSpacing: '.03em',
              }}>Beheer</button>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 30, height: 30, borderRadius: '50%',
                background: 'rgba(255,255,255,.15)', border: '1.5px solid rgba(255,255,255,.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, fontWeight: 700, color: '#fff',
              }}>
                {(authUser.full_name || authUser.email || '?')[0].toUpperCase()}
              </div>
              <span style={{ fontSize: 13, color: 'rgba(255,255,255,.8)', fontWeight: 500, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {authUser.full_name || authUser.email}
              </span>
            </div>
            {onLogout && (
              <button onClick={onLogout} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'rgba(255,255,255,.6)', fontSize: 13, fontFamily: 'var(--font)',
                padding: '4px 0',
              }}>Uitloggen</button>
            )}
          </div>
        )}
      </div>
    </header>
  )
}

const _navBtn = {
  background: 'rgba(255,255,255,.08)', border: '1px solid rgba(255,255,255,.15)',
  borderRadius: 'var(--radius)', padding: '5px 11px',
  color: 'rgba(255,255,255,.85)', fontSize: 12, fontWeight: 600, cursor: 'pointer',
  fontFamily: 'var(--font)', letterSpacing: '.02em',
}

export function NavLink({ children, onClick }) {
  return (
    <button onClick={onClick} style={{
      background: 'none', border: 'none', cursor: 'pointer',
      fontSize: 14, color: 'rgba(255,255,255,.75)', fontFamily: 'var(--font)',
      fontWeight: 500, padding: '4px 0',
    }}>{children}</button>
  )
}

export function NavBack({ onClick, dark }) {
  return (
    <button onClick={onClick} style={{
      background: dark ? 'rgba(0,0,0,.06)' : 'rgba(255,255,255,.22)',
      border: dark ? '1px solid rgba(0,0,0,.15)' : '1.5px solid rgba(255,255,255,.7)',
      borderRadius: 'var(--radius)', padding: '5px 14px',
      cursor: 'pointer', fontSize: 13,
      color: dark ? 'var(--text2)' : '#ffffff',
      fontFamily: 'var(--font)',
      display: 'flex', alignItems: 'center', gap: 4,
      fontWeight: 700, letterSpacing: '.03em',
      textShadow: dark ? 'none' : '0 0 8px rgba(255,255,255,.4)',
    }}>← Terug</button>
  )
}

// ─── Page wrapper ─────────────────────────────────────────────────────────────
export function Page({ children }) {
  return (
    <div className="page-container">
      {children}
    </div>
  )
}

// ─── Page title ───────────────────────────────────────────────────────────────
export function PageTitle({ title, sub, badge }) {
  return (
    <div style={{ marginBottom: 28 }}>
      {badge && (
        <div style={{
          display: 'inline-flex', alignItems: 'center',
          background: 'var(--blue-light)', color: 'var(--blue)',
          fontSize: 12, fontWeight: 600, padding: '4px 12px',
          borderRadius: 20, marginBottom: 12,
        }}>{badge}</div>
      )}
      <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 6 }}>{title}</h1>
      {sub && <p style={{ fontSize: 14, color: 'var(--text3)', lineHeight: 1.5 }}>{sub}</p>}
    </div>
  )
}

// ─── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, style = {}, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: '#fff', borderRadius: 'var(--radius-lg)',
      border: '1px solid var(--border)', padding: '20px 24px',
      boxShadow: 'var(--shadow)', cursor: onClick ? 'pointer' : undefined,
      ...style,
    }}>{children}</div>
  )
}

// ─── Stat card ────────────────────────────────────────────────────────────────
export function StatCard({ label, value, color = 'var(--text)', sub }) {
  return (
    <div style={{ background: '#fff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
      <div style={{ fontSize: 32, fontWeight: 800, color, letterSpacing: '-0.03em', marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 13, color: 'var(--text3)' }}>{label}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text4)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

// ─── Primary button ───────────────────────────────────────────────────────────
export function BtnPrimary({ children, onClick, disabled, style: sx = {} }) {
  return (
    <button onClick={disabled ? undefined : onClick} style={{
      background: disabled ? '#93c5fd' : 'var(--blue)',
      color: '#fff', border: 'none', borderRadius: 'var(--radius)',
      padding: '10px 20px', fontSize: 14, fontWeight: 600,
      cursor: disabled ? 'not-allowed' : 'pointer',
      fontFamily: 'var(--font)', display: 'inline-flex',
      alignItems: 'center', gap: 6, transition: 'background .15s',
      ...sx,
    }}
    onMouseEnter={e => { if (!disabled) e.target.style.background = 'var(--blue-dark)' }}
    onMouseLeave={e => { if (!disabled) e.target.style.background = 'var(--blue)' }}
    >{children}</button>
  )
}

// ─── Outline button ───────────────────────────────────────────────────────────
export function BtnOutline({ children, onClick, style: sx = {} }) {
  return (
    <button onClick={onClick} style={{
      background: '#fff', color: 'var(--text2)',
      border: '1px solid var(--border2)', borderRadius: 'var(--radius)',
      padding: '9px 18px', fontSize: 14, fontWeight: 500,
      cursor: 'pointer', fontFamily: 'var(--font)',
      display: 'inline-flex', alignItems: 'center', gap: 6,
      transition: 'border-color .15s',
      ...sx,
    }}>{children}</button>
  )
}

// ─── Progress bar ─────────────────────────────────────────────────────────────
export function ProgressBar({ value, color = 'var(--blue)' }) {
  return (
    <div style={{ height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
      <div style={{ width: `${Math.min(100, value)}%`, height: '100%', background: color, borderRadius: 3, transition: 'width .4s' }} />
    </div>
  )
}

// ─── Status badge ─────────────────────────────────────────────────────────────
const STATUS = {
  Conform:      { bg: 'var(--green-light)', color: 'var(--green)' },
  Compleet:     { bg: 'var(--green-light)', color: 'var(--green)' },
  Goed:         { bg: 'var(--green-light)', color: 'var(--green)' },
  Voldoende:    { bg: 'var(--amber-light)', color: 'var(--amber)' },
  Afwijkend:    { bg: 'var(--amber-light)', color: 'var(--amber)' },
  Gedeeltelijk: { bg: 'var(--amber-light)', color: 'var(--amber)' },
  Ontbreekt:    { bg: 'var(--red-light)',   color: 'var(--red)' },
  Onvolledig:   { bg: 'var(--red-light)',   color: 'var(--red)' },
  'Onvolledig veld': { bg: 'var(--red-light)', color: 'var(--red)' },
  'Hoge prioriteit': { bg: 'var(--red-light)', color: 'var(--red)' },
}
export function StatusBadge({ status }) {
  const s = STATUS[status] || { bg: 'var(--blue-light)', color: 'var(--blue)' }
  return (
    <span style={{ fontSize: 12, fontWeight: 600, padding: '3px 10px', borderRadius: 20, background: s.bg, color: s.color, whiteSpace: 'nowrap' }}>
      {status}
    </span>
  )
}

// ─── Status icon ──────────────────────────────────────────────────────────────
export function StatusIcon({ status }) {
  if (status === 'Ontbreekt' || status === 'Onvolledig veld' || status === 'Onvolledig')
    return <span style={{ color: 'var(--red)', fontSize: 16 }}>✕</span>
  if (status === 'Afwijkend' || status === 'Gedeeltelijk')
    return <span style={{ color: 'var(--amber)', fontSize: 16 }}>⚠</span>
  return <span style={{ color: 'var(--green)', fontSize: 16 }}>✓</span>
}

// ─── Gap row ──────────────────────────────────────────────────────────────────
export function GapRow({ icon, title, sub, status, color }) {
  const bgs = { red: 'var(--red-bg)', amber: 'var(--amber-bg)', green: 'var(--green-bg)' }
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '14px 16px', borderRadius: 'var(--radius)',
      background: bgs[color] || '#fff',
      border: `1px solid ${color === 'red' ? 'var(--red-light)' : color === 'amber' ? 'var(--amber-light)' : 'var(--green-light)'}`,
      marginBottom: 8,
    }}>
      <div style={{ flexShrink: 0, fontSize: 18 }}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{title}</div>
        {sub && <div style={{ fontSize: 12, color: 'var(--text3)' }}>{sub}</div>}
      </div>
      <StatusBadge status={status} />
    </div>
  )
}

// ─── IssueTable — filterbare tabel met per-rij details ────────────────────────
import { useState as _useState } from 'react'

export function IssueTable({ rows = [], truncated = false, total = 0 }) {
  const [filter, setFilter]     = _useState('')
  const [showAll, setShowAll]   = _useState(false)
  const PAGE = 8

  if (!rows.length) return null

  const filtered = filter.trim()
    ? rows.filter(r =>
        String(r.rowNumber).includes(filter) ||
        (r.personId  || '').toLowerCase().includes(filter.toLowerCase()) ||
        (r.field     || '').toLowerCase().includes(filter.toLowerCase()) ||
        (r.currentValue  || '').toLowerCase().includes(filter.toLowerCase()) ||
        (r.message   || '').toLowerCase().includes(filter.toLowerCase())
      )
    : rows

  const visible = showAll ? filtered : filtered.slice(0, PAGE)

  const TH = ({ children, w }) => (
    <th style={{
      padding: '7px 10px', textAlign: 'left', fontSize: 11, fontWeight: 700,
      color: 'var(--text3)', background: 'var(--bg)', borderBottom: '1px solid var(--border)',
      whiteSpace: 'nowrap', width: w,
    }}>{children}</th>
  )

  const TD = ({ children, mono, muted, red }) => (
    <td style={{
      padding: '7px 10px', fontSize: 12, verticalAlign: 'top',
      borderBottom: '1px solid var(--border)',
      fontFamily: mono ? 'var(--font-mono, monospace)' : 'inherit',
      color: red ? 'var(--red)' : muted ? 'var(--text3)' : 'var(--text)',
      maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
    }}>{children || <span style={{ color: 'var(--text4)' }}>—</span>}</td>
  )

  return (
    <div style={{ marginTop: 10 }}>
      {/* filter input */}
      <div style={{ position: 'relative', marginBottom: 8 }}>
        <span style={{
          position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)',
          fontSize: 13, color: 'var(--text3)', pointerEvents: 'none',
        }}>🔍</span>
        <input
          value={filter}
          onChange={e => { setFilter(e.target.value); setShowAll(false) }}
          placeholder="Zoek op persoon, rij, veld…"
          style={{
            width: '100%', boxSizing: 'border-box',
            padding: '7px 10px 7px 32px',
            fontSize: 12, border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', fontFamily: 'var(--font)',
            background: '#fff', color: 'var(--text)', outline: 'none',
          }}
        />
      </div>

      {/* tabel */}
      <div style={{ overflowX: 'auto', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <TH w={44}>Rij</TH>
              <TH w={90}>Persoon</TH>
              <TH w={120}>Veld</TH>
              <TH w={110}>Huidige waarde</TH>
              <TH>Verwacht</TH>
              <TH>Toelichting</TH>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: '12px 10px', textAlign: 'center', color: 'var(--text3)', fontSize: 12 }}>
                  Geen resultaten voor "{filter}"
                </td>
              </tr>
            )}
            {visible.map((row, idx) => (
              <tr key={idx} style={{ background: idx % 2 === 0 ? '#fff' : 'var(--bg)' }}>
                <TD mono muted>{row.rowNumber}</TD>
                <TD mono>{row.personId}</TD>
                <TD>{row.field}</TD>
                <TD red={!row.currentValue} mono>{row.currentValue || 'leeg'}</TD>
                <TD muted>{row.expectedValue}</TD>
                <TD>{row.message}</TD>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* toon meer / minder */}
      {filtered.length > PAGE && (
        <button
          onClick={() => setShowAll(v => !v)}
          style={{
            marginTop: 6, background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 12, color: 'var(--blue)', fontFamily: 'var(--font)', padding: 0,
          }}
        >
          {showAll
            ? '▲ Minder tonen'
            : `▼ Toon alle ${filtered.length} rijen${truncated ? ` (van ${total} totaal)` : ''}`}
        </button>
      )}
      {truncated && !filter && (
        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
          Eerste {rows.length} van {total} rijen getoond — filter om specifieke rijen te vinden.
        </div>
      )}
    </div>
  )
}

// ─── ExpandableIssueRow — GapRow met uitklapbare IssueTable ───────────────────
export function ExpandableIssueRow({ icon, title, sub, status, color, issue }) {
  const [open, setOpen] = _useState(false)
  const hasRows = issue?.rows?.length > 0
  const bgs = { red: 'var(--red-bg)', amber: 'var(--amber-bg)', green: 'var(--green-bg)' }
  const borderColor = color === 'red' ? 'var(--red-light)' : color === 'amber' ? 'var(--amber-light)' : 'var(--green-light)'

  return (
    <div style={{ marginBottom: 8 }}>
      <div
        onClick={hasRows ? () => setOpen(v => !v) : undefined}
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '14px 16px', borderRadius: open ? 'var(--radius) var(--radius) 0 0' : 'var(--radius)',
          background: bgs[color] || '#fff',
          border: `1px solid ${borderColor}`,
          borderBottom: open ? 'none' : `1px solid ${borderColor}`,
          cursor: hasRows ? 'pointer' : 'default',
          userSelect: 'none',
        }}
      >
        <div style={{ flexShrink: 0, fontSize: 18 }}>{icon}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>{title}</div>
          {sub && <div style={{ fontSize: 12, color: 'var(--text3)' }}>{sub}</div>}
        </div>
        <StatusBadge status={status} />
        {hasRows && (
          <span style={{ fontSize: 13, color: 'var(--text3)', marginLeft: 8, flexShrink: 0 }}>
            {open ? '▲' : '▼'}
          </span>
        )}
      </div>

      {open && hasRows && (
        <div style={{
          padding: '12px 16px 16px',
          background: '#fff',
          border: `1px solid ${borderColor}`,
          borderTop: 'none',
          borderRadius: '0 0 var(--radius) var(--radius)',
        }}>
          <IssueTable
            rows={issue.rows}
            truncated={issue.truncated}
            total={issue.count}
          />
          {issue.allowedValues?.length > 0 && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text3)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Toegestane waarden{issue.source ? ` — ${issue.source}` : ''}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {issue.allowedValues.map((av, i) => {
                  const label = av.label || av.value || av
                  const isPermanent = av.tijdelijk === false
                  return (
                    <span key={i} style={{
                      fontSize: 12, padding: '3px 10px', borderRadius: 20,
                      background: isPermanent ? 'var(--blue-light)' : 'var(--amber-bg)',
                      color: isPermanent ? 'var(--blue)' : 'var(--amber)',
                      border: `1px solid ${isPermanent ? 'var(--blue-mid)' : 'var(--amber-light)'}`,
                      fontWeight: 500,
                    }}>
                      {label}
                    </span>
                  )
                })}
              </div>
              {issue.allowedValues.some(av => av.tijdelijk !== undefined) && (
                <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 8 }}>
                  <span style={{ background: 'var(--blue-light)', color: 'var(--blue)', border: '1px solid var(--blue-mid)', padding: '1px 7px', borderRadius: 10, fontSize: 10, fontWeight: 600, marginRight: 6 }}>permanent</span>
                  <span style={{ background: 'var(--amber-bg)', color: 'var(--amber)', border: '1px solid var(--amber-light)', padding: '1px 7px', borderRadius: 10, fontSize: 10, fontWeight: 600, marginRight: 6 }}>tijdelijk</span>
                  <span style={{ color: 'var(--text3)' }}>— tijdelijke contracten vereisen een einddatum</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Spinner ──────────────────────────────────────────────────────────────────
export function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '60px 0' }}>
      <div style={{ width: 28, height: 28, border: '2px solid var(--border)', borderTop: '2px solid var(--blue)', borderRadius: '50%', animation: 'spin .7s linear infinite' }} />
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  )
}
