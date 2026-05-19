/**
 * SectorBenchmarkWidget — anonymised sector benchmark bar for ORG_ADMIN.
 * Shows the organisation's percentile position on a p25/p50/p75 scale.
 */
export default function SectorBenchmarkWidget({ benchmark }) {
  if (!benchmark) {
    return (
      <div style={styles.card}>
        <h3 style={styles.title}>Sectorvergelijking</h3>
        <p style={styles.muted}>
          Onvoldoende data voor een anonieme benchmark (minimaal 5 organisaties vereist).
        </p>
      </div>
    )
  }

  const { sector_avg_score, percentile_25, percentile_50, percentile_75,
          your_score, your_percentile, participant_count, standard } = benchmark

  // Position of "your score" on the 0–100 bar as a percentage
  const yourPos = your_percentile != null
    ? Math.max(2, Math.min(98, your_percentile))
    : null

  const scoreColor =
    your_score == null  ? '#94a3b8' :
    your_score >= 90    ? '#22c55e' :
    your_score >= 75    ? '#84cc16' :
    your_score >= 60    ? '#f59e0b' :
                          '#ef4444'

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h3 style={styles.title}>Sectorvergelijking</h3>
        <span style={styles.badge}>{(standard || 'kikv').toUpperCase()} · {participant_count} org.</span>
      </div>
      <p style={styles.muted}>
        Anoniem — geen namen van andere organisaties worden getoond.
      </p>

      {/* Percentile bar */}
      <div style={{ marginTop: 16, marginBottom: 8 }}>
        <div style={styles.barTrack}>
          {/* Coloured zones */}
          <div style={{ ...styles.zone, left: '0%',   width: '25%', background: '#fee2e2' }} />
          <div style={{ ...styles.zone, left: '25%',  width: '25%', background: '#fef3c7' }} />
          <div style={{ ...styles.zone, left: '50%',  width: '25%', background: '#ecfccb' }} />
          <div style={{ ...styles.zone, left: '75%',  width: '25%', background: '#dcfce7' }} />

          {/* Percentile markers */}
          {[25, 50, 75].map(p => (
            <div key={p} style={{ ...styles.marker, left: `${p}%` }}>
              <div style={styles.markerLine} />
              <span style={styles.markerLabel}>p{p}</span>
            </div>
          ))}

          {/* Your position needle */}
          {yourPos != null && (
            <div style={{ ...styles.needle, left: `${yourPos}%` }}>
              <div style={{ ...styles.needleLine, borderColor: scoreColor }} />
              <div style={{ ...styles.needleDot, background: scoreColor }} />
              <span style={{ ...styles.needleLabel, color: scoreColor }}>
                uw score
              </span>
            </div>
          )}
        </div>

        {/* Axis labels */}
        <div style={styles.axisRow}>
          <span>0</span>
          <span>25</span>
          <span>50</span>
          <span>75</span>
          <span>100</span>
        </div>
      </div>

      {/* Stats row */}
      <div style={styles.statsRow}>
        <Stat label="Uw score"       value={your_score  != null ? your_score.toFixed(1)        : '—'} color={scoreColor} />
        <Stat label="Sectorgemiddelde" value={sector_avg_score != null ? sector_avg_score.toFixed(1) : '—'} />
        <Stat label="Uw percentiel"  value={your_percentile != null ? `${your_percentile}e`     : '—'} />
        <Stat label="p50 (mediaan)"  value={percentile_50 != null ? percentile_50.toFixed(1)    : '—'} />
      </div>
    </div>
  )
}

function Stat({ label, value, color = '#1e293b' }) {
  return (
    <div style={{ textAlign: 'center', flex: 1 }}>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{label}</div>
    </div>
  )
}

const styles = {
  card: {
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 12,
    padding: '20px 24px',
    marginTop: 24,
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  title:  { margin: 0, fontSize: 16, fontWeight: 700, color: '#1e293b' },
  badge:  {
    fontSize: 12, fontWeight: 600, color: '#64748b',
    background: '#f1f5f9', padding: '3px 10px', borderRadius: 999,
  },
  muted:  { fontSize: 12, color: '#94a3b8', margin: '6px 0 0' },
  barTrack: {
    position: 'relative',
    height: 28,
    borderRadius: 6,
    overflow: 'visible',
    background: '#f1f5f9',
  },
  zone: { position: 'absolute', top: 0, height: '100%' },
  marker: { position: 'absolute', top: 0, transform: 'translateX(-50%)' },
  markerLine: { width: 1, height: 28, background: '#cbd5e1', margin: '0 auto' },
  markerLabel: { fontSize: 10, color: '#94a3b8', display: 'block', textAlign: 'center', marginTop: 2 },
  needle: { position: 'absolute', top: 0, transform: 'translateX(-50%)', zIndex: 2 },
  needleLine: { width: 2, height: 28, borderLeft: '2px dashed', margin: '0 auto' },
  needleDot: { width: 10, height: 10, borderRadius: '50%', margin: '-5px auto 0' },
  needleLabel: { fontSize: 11, fontWeight: 700, display: 'block', textAlign: 'center', marginTop: 4, whiteSpace: 'nowrap' },
  axisRow: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 10, color: '#94a3b8', marginTop: 4, padding: '0 0',
  },
  statsRow: { display: 'flex', gap: 8, marginTop: 20, borderTop: '1px solid #f1f5f9', paddingTop: 16 },
}
