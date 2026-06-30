import React from 'react'

// Vangt render-fouten in de React-tree af zodat een component-crash geen
// volledig wit scherm geeft, maar een leesbare melding + de foutdetails.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }
  static getDerivedStateFromError(error) {
    return { error }
  }
  componentDidCatch(error, info) {
    // Zichtbaar in de console voor diagnose
    console.error('Rhadix render-fout:', error, info)
  }
  reset = () => this.setState({ error: null })
  render() {
    const { error } = this.state
    if (!error) return this.props.children
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc', padding: 24 }}>
        <div style={{ maxWidth: 640, background: '#fff', border: '1px solid #fecaca', borderRadius: 14, padding: '28px 32px', boxShadow: '0 4px 24px rgba(0,0,0,.06)' }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: '#b91c1c', marginBottom: 8 }}>Er ging iets mis bij het tonen van dit scherm</div>
          <div style={{ fontSize: 13, color: '#475569', marginBottom: 14 }}>
            De gegevens zijn verwerkt, maar de weergave liep vast. Probeer een nieuwe scan; blijft het gebeuren, deel dan onderstaande melding.
          </div>
          <pre style={{ fontSize: 12, color: '#7f1d1d', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: '10px 12px', whiteSpace: 'pre-wrap', overflowX: 'auto', margin: 0 }}>
            {String(error && (error.stack || error.message || error))}
          </pre>
          <button onClick={() => { this.reset(); window.location.reload() }}
            style={{ marginTop: 16, background: '#1F3A5F', color: '#fff', border: 'none', borderRadius: 8, padding: '9px 16px', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
            Opnieuw laden
          </button>
        </div>
      </div>
    )
  }
}
