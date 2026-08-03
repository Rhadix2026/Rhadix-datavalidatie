import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import ScoreBadge             from '../components/dashboard/ScoreBadge'
import SectorBenchmarkWidget  from '../components/dashboard/SectorBenchmarkWidget'
import RhadixIndexGauge       from '../components/dashboard/RhadixIndexGauge'
import { getAuthToken }       from '../services/api'

const API = import.meta.env.VITE_API_URL ?? ''

async function fetchOrgDashboard({ tenantId, standard, from, to } = {}) {
  const params = new URLSearchParams()
  if (tenantId) params.set('tenant_id', tenantId)
  if (standard) params.set('standard', standard)
  if (from)     params.set('from', from)
  if (to)       params.set('to', to)
  const res = await fetch(`${API}/api/dashboard/org?${params}`, {
    headers: getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {},
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export default function OrgDashboard({ onBack, authUser, tenantId }) {
  const [data,     setData]     = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)
  const [standard, setStandard] = useState('')

  const load = (std = standard) => {
    setLoading(true)
    fetchOrgDashboard({ tenantId, standard: std || undefined })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])  // eslint-disable-line

  const handleStandard = (v) => { setStandard(v); load(v) }

  if (loading) return <Centered>Laden…</Centered>
  if (error)   return <Centered style={{ color: '#ef4444' }}>Fout: {error}</Centered>
  if (!data)   return null

  const { tenant_name, summary = {}, trend_monthly = [], by_application = [], by_user = [], top_runs = [], sector_benchmark = null } = data

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <NavBack onClick={onBack} dark />
        <div style={{ flex: 1 }}>
          <h1 style={styles.h1}>Organisatie dashboard</h1>
          <p style={styles.subtitle}>{tenant_name}</p>
        </div>
        {/* Standard filter */}
        <select
          value={standard}
          onChange={e => handleStandard(e.target.value)}
          style={styles.select}
        >
          <option value="">Alle standaarden</option>
          <option value="kikv">KIK-V</option>
          <option value="zib">ZIB</option>
          <option value="algemeen">Algemeen</option>
        </select>
      </div>

      {/* KPI cards */}
      <div style={styles.kpiRow}>
        <KpiCard label="Totaal runs"      value={summary.total_runs}    />
        <KpiCard label="Actieve gebruikers" value={summary.active_users} />
        <KpiCard label="Gem. Rhadix Index"
          value={summary.avg_score != null ? summary.avg_score.toFixed(1) : '—'}
          extra={<ScoreBadge score={summary.avg_score} />}
        />
        <KpiCard label="Gem. aanwezigheid" value={summary.avg_structural_score != null ? summary.avg_structural_score.toFixed(1) : '—'} />
        <KpiCard label="Gem. kwaliteit"    value={summary.avg_relational_score  != null ? summary.avg_relational_score.toFixed(1)  : '—'} />
        <KpiCard label="Gem. gereedheid"   value={summary.avg_use_case_score    != null ? summary.avg_use_case_score.toFixed(1)    : '—'} />
      </div>

      {/* Trend + Applications */}
      <div style={styles.midRow}>
        {/* Monthly trend chart */}
        <div style={{ ...styles.card, flex: 2, minWidth: 280 }}>
          <h3 style={styles.cardTitle}>Maandelijkse trend</h3>
          {trend_monthly.length > 1 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trend_monthly} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={v => [v?.toFixed(1), 'Gem. score']} />
                <Line type="monotone" dataKey="avg_score" stroke="var(--k-blue)" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p style={styles.muted}>Onvoldoende data voor een trendgrafiek.</p>
          )}
        </div>

        {/* By application */}
        <div style={{ ...styles.card, flex: 1, minWidth: 220 }}>
          <h3 style={styles.cardTitle}>Score per applicatie</h3>
          {by_application.length === 0
            ? <p style={styles.muted}>Geen data</p>
            : by_application.map(app => (
              <div key={app.application_id || app.application_name} style={styles.appRow}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{app.application_name}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>{app.run_count} run(s)</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <ScoreBadge score={app.avg_score} />
                  {app.latest_score != null && (
                    <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                      Laatste: {app.latest_score.toFixed(1)}
                    </div>
                  )}
                </div>
              </div>
            ))
          }
        </div>
      </div>

      {/* Users table */}
      {by_user.length > 0 && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Gebruikers overzicht</h3>
          <table style={styles.table}>
            <thead>
              <tr>
                {['Naam', 'Runs', 'Gem. score', 'Laatste run'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {by_user.map(u => (
                <tr key={u.user_id || u.full_name} style={styles.tr}>
                  <td style={styles.td}>{u.full_name}</td>
                  <td style={styles.tdC}>{u.run_count}</td>
                  <td style={styles.tdC}><ScoreBadge score={u.avg_score} /></td>
                  <td style={styles.tdC}>
                    {u.latest_run_at
                      ? new Date(u.latest_run_at).toLocaleDateString('nl-NL')
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Top runs */}
      {top_runs.length > 0 && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Top 5 hoogste scores</h3>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {top_runs.map(r => (
              <div key={r.run_id} style={styles.topRunCard}>
                <RhadixIndexGauge score={r.score} size="sm" label="" />
                <div style={{ marginTop: 6, fontSize: 12, color: '#475569', textAlign: 'center' }}>
                  <div style={{ fontWeight: 600 }}>{r.label || `Run #${r.run_id}`}</div>
                  <div style={{ color: '#94a3b8' }}>
                    {r.created_at ? new Date(r.created_at).toLocaleDateString('nl-NL') : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sector benchmark */}
      <SectorBenchmarkWidget benchmark={sector_benchmark} />
    </div>
  )
}

function KpiCard({ label, value, extra }) {
  return (
    <div style={styles.kpiCard}>
      <div style={{ fontSize: 26, fontWeight: 800, color: '#1e293b' }}>{value}</div>
      {extra && <div style={{ marginTop: 4 }}>{extra}</div>}
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
  page: { maxWidth: 1100, margin: '0 auto', padding: '24px 16px' },
  header: { display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24, flexWrap: 'wrap' },
  backBtn: {
    background: 'none', border: '1px solid #e2e8f0', borderRadius: 8,
    padding: '8px 14px', cursor: 'pointer', fontSize: 14, color: '#475569',
    marginTop: 6, whiteSpace: 'nowrap',
  },
  h1: { margin: 0, fontSize: 24, fontWeight: 800, color: '#1e293b' },
  subtitle: { margin: '4px 0 0', color: '#64748b', fontSize: 14 },
  select: {
    padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0',
    fontSize: 13, cursor: 'pointer', marginTop: 6,
  },
  kpiRow: { display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 },
  kpiCard: {
    flex: '1 1 130px', background: '#fff', border: '1px solid #e2e8f0',
    borderRadius: 12, padding: '16px 20px', minWidth: 110,
  },
  midRow: { display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap' },
  card: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '20px 24px', marginBottom: 20 },
  cardTitle: { margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#1e293b' },
  appRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '10px 0', borderBottom: '1px solid #f1f5f9',
  },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { textAlign: 'left', padding: '8px 12px', color: '#64748b', fontWeight: 600, borderBottom: '2px solid #f1f5f9' },
  tr: { borderBottom: '1px solid #f8fafc' },
  td: { padding: '10px 12px', color: '#1e293b' },
  tdC: { padding: '10px 12px', color: '#1e293b', textAlign: 'center' },
  topRunCard: {
    background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10,
    padding: '16px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center',
    minWidth: 120,
  },
  muted: { color: '#94a3b8', fontSize: 13 },
}
