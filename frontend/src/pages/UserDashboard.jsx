import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import RhadixIndexGauge from '../components/dashboard/RhadixIndexGauge'
import ScoreBadge       from '../components/dashboard/ScoreBadge'
import { getAuthToken } from '../services/api'
import { NavBack } from '../components/UI'

const API = import.meta.env.VITE_API_URL ?? ''

async function fetchDashboardMe() {
  const res = await fetch(`${API}/api/dashboard/me`, {
    headers: { Authorization: `Bearer ${getAuthToken()}` },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export default function UserDashboard({ onBack, authUser }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    fetchDashboardMe()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Centered><div className="spinner" />Laden…</Centered>
  if (error)   return <Centered style={{ color: '#ef4444' }}>Fout: {error}</Centered>
  if (!data)   return null

  const { full_name, total_runs, latest_run, trend, by_standard } = data
  const standards = Object.entries(by_standard || {})

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <NavBack onClick={onBack} dark />
        <div>
          <h1 style={styles.h1}>Mijn dashboard</h1>
          <p style={styles.subtitle}>{full_name || authUser?.email}</p>
        </div>
      </div>

      {/* Top row: gauge + latest run */}
      <div style={styles.topRow}>
        <div style={styles.gaugeCard}>
          <RhadixIndexGauge score={latest_run?.score} size="lg" label="Laatste Rhadix Index" />
          <div style={{ marginTop: 12, textAlign: 'center' }}>
            <ScoreBadge score={latest_run?.score} />
          </div>
          {latest_run && (
            <div style={styles.latestMeta}>
              <span>{latest_run.standard?.toUpperCase()}</span>
              <span>{new Date(latest_run.created_at).toLocaleDateString('nl-NL')}</span>
            </div>
          )}
        </div>

        {/* Subscores */}
        <div style={styles.subscoresCard}>
          <h3 style={styles.cardTitle}>Subscores — laatste run</h3>
          {latest_run ? (
            <div style={styles.subScoreGrid}>
              <SubScoreBar label="Data aanwezigheid"  score={latest_run.structural_score} />
              <SubScoreBar label="Data kwaliteit"     score={latest_run.relational_score} />
              <SubScoreBar label="Gereedheid"         score={latest_run.use_case_score}   />
            </div>
          ) : (
            <p style={styles.muted}>Nog geen runs</p>
          )}
          <div style={styles.summaryRow}>
            <Kpi label="Totaal runs" value={total_runs} />
            {standards.map(([std, v]) => (
              <Kpi key={std} label={`${std.toUpperCase()} gem.`} value={v.avg_score != null ? v.avg_score.toFixed(1) : '—'} />
            ))}
          </div>
        </div>
      </div>

      {/* Trend chart */}
      {trend.length > 1 && (
        <div style={styles.chartCard}>
          <h3 style={styles.cardTitle}>Rhadix Index trend</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trend} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
              <XAxis
                dataKey="created_at"
                tickFormatter={v => new Date(v).toLocaleDateString('nl-NL', { month: 'short', day: 'numeric' })}
                tick={{ fontSize: 11 }}
              />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v) => [v?.toFixed(1), 'Score']}
                labelFormatter={v => new Date(v).toLocaleDateString('nl-NL')}
              />
              <ReferenceLine y={75} stroke="#84cc16" strokeDasharray="4 4" label={{ value: 'Goed', fontSize: 10 }} />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function SubScoreBar({ label, score }) {
  const pct   = score != null ? Math.min(100, Math.max(0, score)) : 0
  const color =
    score == null ? '#94a3b8' :
    score >= 90   ? '#22c55e' :
    score >= 75   ? '#84cc16' :
    score >= 60   ? '#f59e0b' :
                    '#ef4444'
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
        <span style={{ color: '#475569' }}>{label}</span>
        <span style={{ fontWeight: 600, color }}>{score != null ? score.toFixed(1) : '—'}</span>
      </div>
      <div style={{ background: '#f1f5f9', borderRadius: 4, height: 8 }}>
        <div style={{ width: `${pct}%`, height: 8, borderRadius: 4, background: color, transition: 'width .5s ease' }} />
      </div>
    </div>
  )
}

function Kpi({ label, value }) {
  return (
    <div style={{ textAlign: 'center', flex: 1 }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1e293b' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#64748b' }}>{label}</div>
    </div>
  )
}

function Centered({ children, style = {} }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200, gap: 12, ...style }}>
      {children}
    </div>
  )
}

const styles = {
  page: { maxWidth: 960, margin: '0 auto', padding: '24px 16px' },
  header: { display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 28 },
  backBtn: {
    background: 'none', border: '1px solid #e2e8f0', borderRadius: 8,
    padding: '8px 14px', cursor: 'pointer', fontSize: 14, color: '#475569',
    marginTop: 6, whiteSpace: 'nowrap',
  },
  h1: { margin: 0, fontSize: 26, fontWeight: 800, color: '#1e293b' },
  subtitle: { margin: '4px 0 0', color: '#64748b', fontSize: 14 },
  topRow: { display: 'flex', gap: 20, marginBottom: 20, flexWrap: 'wrap' },
  gaugeCard: {
    flex: '0 0 220px', background: '#fff', border: '1px solid #e2e8f0',
    borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center',
  },
  subscoresCard: {
    flex: 1, minWidth: 280, background: '#fff', border: '1px solid #e2e8f0',
    borderRadius: 12, padding: 24,
  },
  cardTitle: { margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#1e293b' },
  subScoreGrid: { marginBottom: 20 },
  summaryRow: { display: 'flex', gap: 8, borderTop: '1px solid #f1f5f9', paddingTop: 16 },
  latestMeta: {
    display: 'flex', gap: 12, fontSize: 12, color: '#94a3b8', marginTop: 10,
    justifyContent: 'center',
  },
  chartCard: {
    background: '#fff', border: '1px solid #e2e8f0',
    borderRadius: 12, padding: 24,
  },
  muted: { color: '#94a3b8', fontSize: 13 },
}
