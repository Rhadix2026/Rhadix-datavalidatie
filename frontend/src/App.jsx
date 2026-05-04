import { useState } from 'react'
import Landing                 from './pages/Landing'
import SelectSystems           from './pages/SelectSystems'
import Upload                  from './pages/Upload'
import Beschikbaarheid         from './pages/Beschikbaarheid'
import BeschikbaarheidsRapport from './pages/BeschikbaarheidsRapport'
import KikvReadinessRapport    from './pages/KikvReadinessRapport'
import ManagementRapport       from './pages/ManagementRapport'
import Dashboard               from './pages/Dashboard'
import { Advies, Actieplan }   from './pages/Advies'

// Stappen: landing → systems → upload → beschikbaarheid → [rapport_beschikbaarheid]
//          → dashboard → [rapport_kikv_readiness | rapport_management] → advies → actieplan
//
// Workflow-state:
//   step1Completed   — true zodra de scan voltooid is (na completeUpload)
//   step2Completed   — true zodra de gebruiker expliciet "Start Stap 2" heeft geklikt
//                      (= navigatie naar Dashboard). Bepaalt welke rapporten beschikbaar zijn.
//
// Rapportnavigatie:
//   rapportBeschikbaarheidBack — 'beschikbaarheid' | 'dashboard'
//   Zorgt dat de ← Terug-knop in BeschikbaarheidsRapport naar de juiste pagina gaat,
//   afhankelijk van waar het rapport is geopend.

export default function App() {
  const [step, setStep]                 = useState('landing')
  const [systems, setSystems]           = useState([])
  const [scanKey, setScanKey]           = useState(0)
  const [activeDomain, setActiveDomain] = useState('Werkovereenkomst')
  const [actieItems, setActieItems]     = useState([])

  // Scan-resultaat — uitsluitend gevuld na upload in deze sessie
  const [activeScanResult, setActiveScanResult]   = useState(null)
  const [scanSessionActive, setScanSessionActive] = useState(false)

  // Workflow-voortgang
  const [step1Completed, setStep1Completed] = useState(false)
  const [step2Completed, setStep2Completed] = useState(false)

  // Scanhistorie
  const [scanHistory, setScanHistory] = useState([])

  // Navigatiebron voor BeschikbaarheidsRapport
  const [rapportBeschikbaarheidBack, setRapportBeschikbaarheidBack] = useState('beschikbaarheid')

  /** Enige plek waar een actief scanresultaat wordt gezet (na stap 1) */
  const completeUpload = (result) => {
    setActiveScanResult(result)
    setScanSessionActive(true)
    setStep1Completed(true)
    setStep2Completed(false)   // nieuwe scan = stap 2 nog niet gedaan
    setScanHistory(prev => [
      { run_id: result.run_id, label: result.label ?? 'Scan', created_at: result.created_at },
      ...prev,
    ])
    setStep('beschikbaarheid')
  }

  /** Navigatie naar Dashboard = stap 2 gestart */
  const safeGoToDashboard = () => {
    if (!scanSessionActive) { setStep('landing'); return }
    setStep2Completed(true)
    setStep('dashboard')
  }

  /** Reset alles voor een nieuwe scan */
  const startNewScan = () => {
    setActiveScanResult(null)
    setScanSessionActive(false)
    setStep1Completed(false)
    setStep2Completed(false)
    setSystems([])
    setActieItems([])
    setScanKey(k => k + 1)
    setStep('systems')
  }

  const addActie = (item) => setActieItems(prev => {
    if (prev.find(x => x.title === item.title)) return prev
    return [...prev, item]
  })

  /** Open BeschikbaarheidsRapport — registreert waar we vandaan komen */
  const openBeschikbaarheidsRapport = (backTo) => {
    setRapportBeschikbaarheidBack(backTo)
    setStep('rapport_beschikbaarheid')
  }

  return (
    <>
      {step === 'landing' && (
        <Landing onStart={() => setStep('systems')} />
      )}
      {step === 'systems' && (
        <SelectSystems
          key={scanKey}
          onNext={(sel) => { setSystems(sel); setStep('upload') }}
          onBack={() => setStep('landing')}
        />
      )}
      {step === 'upload' && (
        <Upload
          systems={systems}
          onNext={completeUpload}
          onBack={() => setStep('systems')}
        />
      )}
      {step === 'beschikbaarheid' && (
        <Beschikbaarheid
          results={activeScanResult}
          systems={systems}
          step1Completed={step1Completed}
          step2Completed={step2Completed}
          onNext={safeGoToDashboard}
          onBack={() => setStep('upload')}
          onRapport={() => openBeschikbaarheidsRapport('beschikbaarheid')}
        />
      )}
      {step === 'rapport_beschikbaarheid' && (
        <BeschikbaarheidsRapport
          results={activeScanResult}
          systems={systems}
          onBack={() => setStep(rapportBeschikbaarheidBack)}
        />
      )}
      {step === 'dashboard' && (
        <Dashboard
          results={activeScanResult}
          scanHistory={scanHistory}
          step1Completed={step1Completed}
          step2Completed={step2Completed}
          onNewScan={startNewScan}
          onAdvies={(domain) => { setActiveDomain(domain); setStep('advies') }}
          onBeschikbaarheidsRapport={() => openBeschikbaarheidsRapport('dashboard')}
          onKikvRapport={() => setStep('rapport_kikv_readiness')}
          onManagementRapport={() => setStep('rapport_management')}
        />
      )}
      {step === 'rapport_kikv_readiness' && (
        <KikvReadinessRapport
          results={activeScanResult}
          systems={systems}
          onBack={() => setStep('dashboard')}
        />
      )}
      {step === 'rapport_management' && (
        <ManagementRapport
          results={activeScanResult}
          systems={systems}
          onBack={() => setStep('dashboard')}
        />
      )}
      {step === 'advies' && (
        <Advies
          domain={activeDomain}
          results={activeScanResult}
          onActieplan={addActie}
          onGotoActieplan={() => setStep('actieplan')}
          onBack={() => setStep('dashboard')}
        />
      )}
      {step === 'actieplan' && (
        <Actieplan
          items={actieItems}
          results={activeScanResult}
          onDashboard={safeGoToDashboard}
          onBack={() => setStep('advies')}
        />
      )}
    </>
  )
}
