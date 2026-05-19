/**
 * RhadixIndexGauge — circular gauge for the Rhadix Index score.
 * Props:
 *   score   {number|null}  0–100
 *   size    {'sm'|'md'|'lg'}  default 'md'
 *   label   {string}  label below score, default 'Rhadix Index'
 */
export default function RhadixIndexGauge({ score, size = 'md', label = 'Rhadix Index' }) {
  const pct    = score != null ? Math.max(0, Math.min(100, score)) : 0
  const radius = size === 'lg' ? 70 : size === 'sm' ? 36 : 52
  const stroke = size === 'lg' ? 10 : size === 'sm' ? 6 : 8
  const circ   = 2 * Math.PI * radius
  const offset = circ - (pct / 100) * circ

  const color =
    score == null  ? '#94a3b8' :
    score >= 90    ? '#22c55e' :
    score >= 75    ? '#84cc16' :
    score >= 60    ? '#f59e0b' :
                     '#ef4444'

  const dim = (radius + stroke) * 2 + 4
  const cx  = dim / 2
  const fontSize = size === 'lg' ? 28 : size === 'sm' ? 14 : 20

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <svg width={dim} height={dim} style={{ transform: 'rotate(-90deg)' }}>
        {/* Track */}
        <circle
          cx={cx} cy={cx} r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={stroke}
        />
        {/* Progress */}
        <circle
          cx={cx} cy={cx} r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
        {/* Score text — counter-rotate so it reads correctly */}
        <text
          x={cx} y={cx}
          textAnchor="middle"
          dominantBaseline="central"
          style={{
            transform: `rotate(90deg)`,
            transformOrigin: `${cx}px ${cx}px`,
            fontSize: fontSize,
            fontWeight: 700,
            fill: color,
          }}
        >
          {score != null ? Math.round(score) : '—'}
        </text>
      </svg>
      {label && (
        <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>{label}</span>
      )}
    </div>
  )
}
