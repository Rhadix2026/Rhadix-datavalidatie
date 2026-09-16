import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'

document.documentElement.dataset.env = import.meta.env.VITE_RHADIX_ENV || 'production'

// Browser-terug na uitloggen mag geen ingelogd scherm meer tonen. Een pagina die
// de browser uit zijn back/forward-cache haalt wordt niet opnieuw opgebouwd: de
// sessiecontrole bij het opstarten wordt dan overgeslagen en het oude scherm komt
// terug zoals het was. Opnieuw laden dwingt die controle af.
window.addEventListener('pageshow', (e) => { if (e.persisted) window.location.reload() })

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
)
