import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar } from 'recharts'
import ScoreBadge   from '../components/dashboard/ScoreBadge'
import { getAuthToken } from '../services/api'

const API = import.meta.env.VITE_API_URL ?? ''

async function fetchAdminDashboard({ standard, period } = {}) {
  const params = new URLSearchParams()
  if (standard) params.set('standard', standard)
  if (period)   params.set('period', period)
  const res = await fetch(`${API}/api/dashboard/admin?${params}`, {
    headers: getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {},
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export default function PlatformDashboard({ onBack, onOrgDrilldown }) {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [standard, setStandard] = useState('')
  const [sortKey,  setSortKey]  = useState('avg_score')

  const load = (std = standard) => {
    setLoading(true)
    fetchAdminDashboard({ standard: std || undefined })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])  // eslint-disable-line

  const handleStandard = (v) => { setStandard(v); load(v) }

  if (loading) return <Centered>Laden…</Centered>
  if (error)   return <Centered style={{ color: '#ef4444' }}>Fout: {error}</Centered>
  if (!data)   return null

  const { platform_summary, per_tenant, trend_platform_monthly, benchmark } = data

  const sortedTenants = [...(per_tenant || [])].sort((a, b) => {
    if (sortKey === 'avg_score') return (b.avg_score ?? -1) - (a.avg_score ?? -1)
    if (sortKey === 'run_count') return b.run_count - a.run_count
    if (sortKey === 'name')      return a.tenant_name.localeCompare(b.tenant_name)
    return 0
  })

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <NavBack onClick={onBack} dark />
        <div style={{ flex: 1 }}>
          <h1 style={styles.h1}>Platform dashboard</h1>
          <p style={styles.subtitle}>RHADIX_ADMIN — cross-organisatie overzicht</p>
        </div>
        <select value={standard} onChange={e => handleStandard(e.target.value)} style={styles.select}>
          <option value="">Alle standaarden</option>
          <option value="kikv">KIK-V</option>
          <option value="zib">ZIB</option>
          <option value="algemeen">Algemeen</option>
        </select>
      </div>

      {/* Platform KPI's */}
      <div style={styles.kpiRow}>
        <KpiCard label="Totaal organisaties"      value={platform_summary.total_tenants} />
        <KpiCard label="Actief deze periode"      value={platform_summary.active_tenants_this_period} />
        <KpiCard label="Totaal runs"              value={platform_summary.total_runs} />
        <KpiCard
          label="Platform gem. score"
          value={platform_summary.platform_avg_score != null ? platform_summary.platform_avg_score.toFixed(1) : '—'}
          extra={<ScoreBadge score={platform_summary.platform_avg_score} />}
        />
        {benchmark && (
          <>
            <KpiCard label="Mediaan (p50)"    value={benchmark.percentile_50?.toFixed(1) ?? '—'} />
            <KpiCard label="Beste org"        value={benchmark.top_performer?.avg_score?.toFixed(1) ?? '—'}
              sub={benchmark.top_performer?.tenant_name}
            />
          </>
        )}
      </div>

      {/* Trend chart */}
      {trend_platform_monthly?.length > 1 && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Platform trend (maandelijks)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trend_platform_monthly} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v, n) => [typeof v === 'number' ? v.toFixed(1) : v, n === 'avg_score' ? 'Gem. score' : 'Runs']} />
              <Line type="monotone" dataKey="avg_score"  stroke="var(--k-blue)" strokeWidth={2} dot={{ r: 4 }} name="avg_score" />
              <Line type="monotone" dataKey="run_count"  stroke="#94a3b8" strokeWidth={1} strokeDasharray="4 4" dot={false} yAxisId={0} name="run_count" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Benchmark distribution */}
      {benchmark && benchmark.participant_count > 0 && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Score distributie — alle organisaties</h3>
          <div style={styles.benchmarkRow}>
            <BenchmarkBar label="Onvoldoende (<60)" value={scoreCount(per_tenant, 0, 60)}  color="#ef4444" />
            <BenchmarkBar label="Voldoende (60–74)" value={scoreCount(per_tenant, 60, 75)} color="#f59e0b" />
            <BenchmarkBar label="Goed (75–89)"      value={scoreCount(per_tenant, 75, 90)} color="#84cc16" />
            <BenchmarkBar label="Uitstekend (≥90)"  value={scoreCount(per_tenant, 90, 101)} color="#22c55e" />
          </div>
          <div style={styles.pctRow}>
            {[
              ['p25', benchmark.percentile_25],
              ['p50 (mediaan)', benchmark.percentile_50],
              ['p75', benchmark.percentile_75],
              ['Laagste', benchmark.min_score],
              ['Hoogste', benchmark.max_score],
            ].map(([l, v]) => (
              <div key={l} style={styles.pctCard}>
                <div style={{ fontSize: 18, fontWeight: 700 }}>{v != null ? v.toFixed(1) : '—'}</div>
                <div style={{ fontSize: 11, color: '#64748b' }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tenant table */}
      <div style={styles.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ ...styles.cardTitle, margin: 0 }}>Alle organisaties</h3>
          <select value={sortKey} onChange={e => setSortKey(e.target.value)} style={styles.select}>
            <option value="avg_score">Sorteer: score ↓</option>
            <option value="run_count">Sorteer: runs ↓</option>
            <option value="name">Sorteer: naam</option>
          </select>
        </div>
        <table style={styles.table}>
          <thead>
            <tr>
              {['Organisatie', 'Runs', 'Gem. score', 'Licentie', 'Laatste run', ''].map(h => (
                <th key={h} style={styles.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedTenants.map(t => (
              <tr key={t.tenant_id} style={styles.tr}>
                <td style={styles.td}>{t.tenant_name}</td>
                <td style={styles.tdC}>{t.run_count}</td>
                <td style={styles.tdC}><ScoreBadge score={t.avg_score} /></td>
                <td style={styles.tdC}>
                  <LicensePill status={t.license_status} until={t.license_valid_until} />
                </td>
                <td style={styles.tdC}>
                  {t.latest_run_at ? new Date(t.latest_run_at).toLocaleDateString('nl-NL') : '—'}
                </td>
                <td style={styles.tdC}>
                  {onOrgDrilldown && (
                    <button
                      onClick={() => onOrgDrilldown(t.tenant_id, t.tenant_name)}
                      style={styles.drillBtn}
                    >
                      Details →
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function scoreCount(tenants, min, max) {
  return (tenants || []).filter(t => t.avg_score != null && t.avg_score >= min && t.avg_score < max).length
}

function BenchmarkBar({ label, value, color }) {
  return (
    <div style={{ textAlign: 'center', flex: 1 }}>
      <div style={{ fontSize: 28, fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{label}</div>
    </div>
  )
}

function LicensePill({ status, until }) {
  const cfg =
    status === 'active'  ? { bg: '#dcfce7', color: '#16a34a', label: 'Actief' } :
    status === 'verlopen' ? { bg: '#fee2e2', color: '#dc2626', label: 'Verlopen' } :
                            { bg: '#f1f5f9', color: '#64748b', label: 'Geen' }
  return (
    <span style={{ ...styles.pill, background: cfg.bg, color: cfg.color }}>
      {cfg.label}{until && status === 'active' ? ` t/m ${new Date(until).toLocaleDateString('nl-NL', { year: '2-digit', month: 'short' })}` : ''}
    </span>
  )
}

function KpiCard({ label, value, extra, sub }) {
  return (
    <div style={styles.kpiCard}>
      <div style={{ fontSize: 26, fontWeight: 800, color: '#1e293b' }}>{value}</div>
      {extra && <div style={{ marginTop: 4 }}>{extra}</div>}
      {sub   && <div style={{ fontSize: 11, color: 'var(--k-blue)', marginTop: 2, fontWeight: 600 }}>{sub}</div>}
      <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>{label}</div>
    </div>
  )
}

function Centered({ children, style = {} }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200, ...style }}>
      {children}
    </div>
  )
}

const styles = {
  page: { maxWidth: 1200, margin: '0 auto', padding: '24px 16px' },
  header: { display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24, flexWrap: 'wrap' },
  backBtn: {
    background: 'none', border: '1px solid #e2e8f0', borderRadius: 8,
    padding: '8px 14px', cursor: 'pointer', fontSize: 14, color: '#475569',
    marginTop: 6, whiteSpace: 'nowrap',
  },
  h1: { margin: 0, fontSize: 24, fontWeight: 800, color: '#1e293b' },
  subtitle: { margin: '4px 0 0', color: '#64748b', fontSize: 14 },
  select: { padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13, cursor: 'pointer', marginTop: 6 },
  kpiRow: { display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 },
  kpiCard: {
    flex: '1 1 130px', background: '#fff', border: '1px solid #e2e8f0',
    borderRadius: 12, padding: '16px 20px', minWidth: 110,
  },
  card: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px', marginBottom: 20 },
  cardTitle: { margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#1e293b' },
  benchmarkRow: { display: 'flex', gap: 8, marginBottom: 20, borderBottom: '1px solid #f1f5f9', paddingBottom: 20 },
  pctRow: { display: 'flex', gap: 12, flexWrap: 'wrap' },
  pctCard: { background: '#f8fafc', borderRadius: 8, padding: '10px 16px', textAlign: 'center', flex: '1 1 80px' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '8px 12px', color: '#64748b', fontWeight: 600, borderBottom: '2px solid #f1f5f9' },
  tr: { borderBottom: '1px solid #f8fafc' },
  td: { padding: '10px 12px', color: '#1e293b' },
  tdC: { padding: '10px 12px', color: '#1e293b', textAlign: 'center' },
  pill: { display: 'inline-block', padding: '2px 8px', borderRadius: 999, fontSize: 12, fontWeight: 600 },
  drillBtn: {
    background: 'none', border: '1px solid #e2e8f0', borderRadius: 6,
    padding: '4px 10px', cursor: 'pointer', fontSize: 12, color: 'var(--k-blue)',
  },
}
