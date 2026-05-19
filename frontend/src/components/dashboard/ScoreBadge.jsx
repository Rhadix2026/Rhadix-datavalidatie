/**
 * ScoreBadge — inline coloured score chip.
 */
export default function ScoreBadge({ score }) {
  if (score == null) return <span style={styles.unknown}>—</span>
  const { bg, color, label } =
    score >= 90 ? { bg: '#dcfce7', color: '#16a34a', label: 'Uitstekend' } :
    score >= 75 ? { bg: '#ecfccb', color: '#65a30d', label: 'Goed' } :
    score >= 60 ? { bg: '#fef3c7', color: '#d97706', label: 'Voldoende' } :
                  { bg: '#fee2e2', color: '#dc2626', label: 'Onvoldoende' }
  return (
    <span style={{ ...styles.base, background: bg, color }}>
      {Math.round(score)} — {label}
    </span>
  )
}

const styles = {
  base: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 999,
    fontSize: 13,
    fontWeight: 600,
  },
  unknown: {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: 999,
    fontSize: 13,
    color: '#94a3b8',
  },
}
