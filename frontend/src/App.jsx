import { useState } from 'react'
import Landing                 from './pages/Landing'
import SelectSystems           from './pages/SelectSystems'
import Upload                  from './pages/Upload'
import Beschikbaarheid         from './pages/Beschikbaarheid'
import BeschikbaarheidsRapport from './pages/BeschikbaarheidsRapport'
import KikvReadinessRapport    from './pages/KikvReadinessRapport'
import ManagementRapport       from './pages/ManagementRapport'
import ConceptMappingRapport   from './pages/ConceptMappingRapport'
import Dashboard               from './pages/Dashboard'
import ZibDashboard            from './pages/ZibDashboard'
import AlgemeenDashboard       from './pages/AlgemeenDashboard'
import ActualityDashboard      from './pages/ActualityDashboard'
import TraceabilityDrilldown   from './pages/TraceabilityDrilldown'
import KIKVProfileImport      from './pages/KIKVProfileImport'
import KIKVReadinessMatrix    from './pages/KIKVReadinessMatrix'
import { Advies, Actieplan }   from './pages/Advies'
import Stap2Resultaat          from './pages/Stap2Resultaat'
import ReconciliationDashboard from './pages/reconciliation/ReconciliationDashboard'

// ── Workflow ──────────────────────────────────────────────────────────────────
// landing → systems (keuze standaard + bronsysteem)
//   → upload → [prescan] → beschikbaarheid → dashboard [kikv] of zib_dashboard [zib]
//   → [actuality] → [rapport_*] → advies → actieplan
//
// standard: 'kikv' | 'zib'  — gekozen in SelectSystems, bewaard tot nieuwe scan

export default function App() {
  const [step, setStep]                 = useState('landing')
  const [systems, setSystems]           = useState([])
  const [standard, setStandard]         = useState('kikv')
  const [scanKey, setScanKey]           = useState(0)
  const [activeDomain, setActiveDomain] = useState('Werkovereenkomst')
  const [actieItems, setActieItems]     = useState([])

  const [activeScanResult, setActiveScanResult]   = useState(null)
  const [scanSessionActive, setScanSessionActive] = useState(false)

  const [step1Completed, setStep1Completed] = useState(false)
  const [step2Completed, setStep2Completed] = useState(false)

  const [scanHistory, setScanHistory] = useState([])
  const [rapportBeschikbaarheidBack, setRapportBeschikbaarheidBack] = useState('beschikbaarheid')

  // Vanwaar we terugkeren naar het actuality-dashboard
  const [actualityBackStep, setActualityBackStep] = useState('dashboard')
  const [profilesBackStep, setProfilesBackStep]   = useState('landing')
  const [readinessMatrix, setReadinessMatrix]       = useState(null)
  const [readinessProfile, setReadinessProfile]     = useState(null)

  const completeUpload = (result) => {
    setActiveScanResult(result)
    setScanSessionActive(true)
    setStep1Completed(true)
    setStep2Completed(false)
    setScanHistory(prev => [
      { run_id: result.run_id, label: result.label ?? 'Scan', created_at: result.created_at },
      ...prev,
    ])
    if (standard === 'zib') {
      setStep('zib_dashboard')
    } else if (standard === 'algemeen') {
      setStep('algemeen_dashboard')
    } else {
      setStep('beschikbaarheid')
    }
  }

  const safeGoToDashboard = () => {
    if (!scanSessionActive) { setStep('landing'); return }
    setStep2Completed(true)
    setStep('stap2_resultaat')
  }

  const goToDashboardFinal = () => {
    setStep('dashboard')
  }

  const startNewScan = () => {
    setActiveScanResult(null)
    setScanSessionActive(false)
    setStep1Completed(false)
    setStep2Completed(false)
    setSystems([])
    setStandard('kikv')
    setActieItems([])
    setScanKey(k => k + 1)
    setStep('systems')
  }

  const addActie = (item) => setActieItems(prev => {
    if (prev.find(x => x.title === item.title)) return prev
    return [...prev, item]
  })

  const openBeschikbaarheidsRapport = (backTo) => {
    setRapportBeschikbaarheidBack(backTo)
    setStep('rapport_beschikbaarheid')
  }

  const openActuality = (backTo) => {
    setActualityBackStep(backTo)
    setStep('actuality')
  }

  const openTraceability = (backTo) => {
    setActualityBackStep(backTo)   // hergebruik same back-state
    setStep('traceability')
  }

  const openProfiles = (backTo) => {
    setProfilesBackStep(backTo)
    setStep('profiles')
  }

  const conceptMapping = activeScanResult?.concept_mapping || []

  const openReadiness = async (filename, profile) => {
    if (!activeScanResult) { alert('Upload eerst een bronbestand om de gereedheidsmatrix te berekenen.'); return }
    try {
      const API = import.meta.env.VITE_API_URL ?? ''
      const resp = await fetch(`${API}/api/profiles/${encodeURIComponent(filename)}/readiness`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeScanResult),
      })
      if (!resp.ok) throw new Error(await resp.text())
      const matrix = await resp.json()
      setReadinessMatrix(matrix)
      setReadinessProfile(profile?.name || filename)
      setStep('readiness')
    } catch (err) {
      alert('Gereedheidsanalyse mislukt: ' + err.message)
    }
  }

  return (
    <>
      {step === 'landing' && (
        <Landing onStart={() => setStep('systems')} onProfiles={() => openProfiles('landing')} onReconciliation={() => setStep('reconciliation')} />
      )}

      {step === 'systems' && (
        <SelectSystems
          key={scanKey}
          onNext={(sel, std) => {
            setSystems(sel)
            setStandard(std || 'kikv')
            setStep('upload')
          }}
          onBack={() => setStep('landing')}
        />
      )}

      {step === 'upload' && (
        <Upload
          systems={systems}
          standard={standard}
          onNext={completeUpload}
          onBack={() => setStep('systems')}
        />
      )}

      {/* ── KIK-V flow ── */}
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
          onBack={() => setStep('beschikbaarheid')}
          onAdvies={(domain) => { setActiveDomain(domain); setStep('advies') }}
          onBeschikbaarheidsRapport={() => openBeschikbaarheidsRapport('dashboard')}
          onKikvRapport={() => setStep('rapport_kikv_readiness')}
          onManagementRapport={() => setStep('rapport_management')}
          onConceptMapping={() => setStep('rapport_concept_mapping')}
          onActuality={() => openActuality('dashboard')}
          onTraceability={() => openTraceability('dashboard')}
          onProfiles={() => openProfiles('dashboard')}
          onReconciliation={() => setStep('reconciliation')}
        />
      )}
      {step === 'stap2_resultaat' && (
        <Stap2Resultaat
          results={activeScanResult}
          onContinue={goToDashboardFinal}
          onBack={() => setStep('beschikbaarheid')}
        />
      )}

      {step === 'rapport_concept_mapping' && (
        <ConceptMappingRapport
          conceptMapping={conceptMapping}
          onBack={() => setStep('dashboard')}
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

      {/* ── Algemeen flow ── */}
      {step === 'algemeen_dashboard' && (
        <AlgemeenDashboard
          results={activeScanResult}
          onNewScan={startNewScan}
        />
      )}

      {/* ── ZIB flow ── */}
      {step === 'zib_dashboard' && (
        <ZibDashboard
          results={activeScanResult}
          onNewScan={startNewScan}
          onActuality={() => openActuality('zib_dashboard')}
          onTraceability={() => openTraceability('zib_dashboard')}
          onProfiles={() => openProfiles('zib_dashboard')}
        />
      )}

      {/* ── Actualiteit (gedeeld door KIK-V en ZIB) ── */}
      {step === 'actuality' && (
        <ActualityDashboard
          results={activeScanResult}
          onBack={() => setStep(actualityBackStep)}
        />
      )}

      {/* ── Traceerbaarheid (gedeeld door KIK-V en ZIB) ── */}
      {step === 'traceability' && (
        <TraceabilityDrilldown
          results={activeScanResult}
          onBack={() => setStep(actualityBackStep)}
        />
      )}
      {/* ── KIK-V Gereedheidsmatrix ── */}
      {step === 'readiness' && (
        <KIKVReadinessMatrix
          matrix={readinessMatrix}
          profileName={readinessProfile}
          onBack={() => setStep('profiles')}
        />
      )}

      {/* ── KIK-V Profielimport ── */}
      {step === 'profiles' && (
        <KIKVProfileImport
          onBack={() => setStep(profilesBackStep)}
          onAnalyze={openReadiness}
          scanResult={activeScanResult}
        />
      )}

      {/* ── Reconciliation Engine ── */}
      {step === 'reconciliation' && (
        <ReconciliationDashboard
          onBack={() => setStep('landing')}
        />
      )}

    </>
  )
}
