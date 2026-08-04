import { useState, useEffect } from 'react'
import EnvironmentBanner, { BANNER_HEIGHT } from './components/EnvironmentBanner'
import { setAuthToken, clearAuthToken, login as apiLogin, getMe } from './services/api'
import Landing                 from './pages/Landing'
import { getInitialBrand } from './brand'
import SelectSystems           from './pages/SelectSystems'
import Upload                  from './pages/Upload'
import MultiSourceValidatie    from './pages/MultiSourceValidatie'
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
import LoginScreen        from './pages/LoginScreen'
import AuthAction         from './pages/AuthAction'
import AppPortal          from './pages/AppPortal'
import PlatformLanding    from './pages/PlatformLanding'
import AdminDashboard     from './pages/AdminDashboard'
import OrgAdminDashboard  from './pages/OrgAdminDashboard'
import RsoDashboard       from './pages/RsoDashboard'
import UserDashboard      from './pages/UserDashboard'
import Taken             from './pages/Taken'
import OrgDashboard       from './pages/OrgDashboard'
import PlatformDashboard  from './pages/PlatformDashboard'

// ── Workflow ──────────────────────────────────────────────────────────────────
// landing → systems (keuze standaard + bronsysteem)
//   → upload → [prescan] → beschikbaarheid → dashboard [kikv] of zib_dashboard [zib]
//   → [actuality] → [rapport_*] → advies → actieplan
//
// standard: 'kikv' | 'zib'  — gekozen in SelectSystems, bewaard tot nieuwe scan

export default function App() {
  const [step, setStep]                 = useState('login')
  const [entry, setEntry]               = useState('landing')  // 'landing' | 'login'
  const [brand, setBrand]               = useState(getInitialBrand)   // 'rhadix' | 'suresync' (white-label, staging)
  const [authUser, setAuthUser]         = useState(null)   // { id, email, role, tenant_id, tenant_name }
  const [booting, setBooting]           = useState(true)   // cookie-auto-login (SSO) op mount
  const [authAction, setAuthAction]     = useState(() => {
    try {
      const p = new URLSearchParams(window.location.search)
      const action = p.get('action'), token = p.get('token')
      if (token && ['reset', 'invite', 'verify'].includes(action)) return { action, token }
    } catch { /* ignore */ }
    return null
  })
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
  const [profilesBackStep, setProfilesBackStep]   = useState('systems')
  const [readinessMatrix, setReadinessMatrix]       = useState(null)
  const [readinessProfile, setReadinessProfile]     = useState(null)

  // ── Phase 3 dashboard ─────────────────────────────────────────────────────
  const [dashboardTenantId,   setDashboardTenantId]   = useState(null)
  const [dashboardTenantName, setDashboardTenantName] = useState(null)

  // ── Auth ──────────────────────────────────────────────────────────────────
  const handleLogin = async (email, password) => {
    const { access_token } = await apiLogin(email, password)
    setAuthToken(access_token)
    const user = await getMe()
    setAuthUser(user)
    setStep('portal')   // na inloggen: kies een applicatie
  }

  const clearAuthAction = () => {
    try { window.history.replaceState({}, '', window.location.pathname) } catch { /* ignore */ }
    setAuthAction(null)
    setEntry('login')
  }

  const handleLogout = () => {
    clearAuthToken()
    setAuthUser(null)
    setStep('login')
  }

  // Re-login when token expires mid-session
  useEffect(() => {
    const handler = () => handleLogout()
    window.addEventListener('rhadix:unauthorized', handler)
    return () => window.removeEventListener('rhadix:unauthorized', handler)
  }, [])

  // SSO-boot: bij binnenkomst (bv. 'Terug naar platform' vanuit een andere app) automatisch
  // inloggen met het centrale rhadix_sso-cookie en direct het portaal ('kies een applicatie') tonen.
  useEffect(() => {
    let alive = true
    getMe()
      .then(user => { if (alive && user) { setAuthUser(user); setStep('portal') } })
      .catch(() => {})
      .finally(() => { if (alive) setBooting(false) })
    return () => { alive = false }
  }, [])

  // 'Terug naar platform'-knop in de balk -> terug naar het portaal (kies een applicatie).
  useEffect(() => {
    const goPortal = () => setStep('portal')
    window.addEventListener('rhadix:platform', goPortal)
    return () => window.removeEventListener('rhadix:platform', goPortal)
  }, [])

  // White-label merk-laag: zet data-brand op <html> zodat het palet (index.css) volgt.
  useEffect(() => { document.documentElement.dataset.brand = brand }, [brand])
  const changeBrand = (b) => {
    try { sessionStorage.setItem('rhadix:brand', b) } catch { /* ignore */ }
    setBrand(b)
  }

  // ── SSO-boot bezig: kort laadscherm i.p.v. flikkering naar login/landing ──
  if (booting && !authAction && !authUser) {
    return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', color: 'var(--text3)', fontFamily: 'var(--font)' }}>Bezig met inloggen…</div>
  }

  // ── Auth-actie via e-maillink (reset/invite/verify): vóór alles, ook indien uitgelogd ──
  if (authAction) {
    return <AuthAction action={authAction.action} token={authAction.token} onDone={clearAuthAction} />
  }

  // ── Guard: not authenticated ──────────────────────────────────────────────
  if (!authUser) {
    if (entry === 'login') {
      return <LoginScreen onLogin={handleLogin} onBack={() => setEntry('landing')} brand={brand} onBrandChange={changeBrand} />
    }
    return <PlatformLanding onLogin={() => setEntry('login')} brand={brand} onBrandChange={changeBrand} />
  }

  const completeUpload = (result) => {
    setActiveScanResult(result)
    setScanSessionActive(true)
    setStep1Completed(true)
    setStep2Completed(false)
    setScanHistory(prev => [
      { run_id: result.run_id, label: result.label ?? 'Scan', created_at: result.created_at },
      ...prev,
    ])
    const _std = result.standard || standard
    if (_std === 'zib') {
      setStep('zib_dashboard')
    } else if (_std === 'algemeen') {
      setStep('algemeen_dashboard')
    } else {
      setStep('beschikbaarheid')
    }
  }

  const safeGoToDashboard = () => {
    if (!scanSessionActive) { setStep('systems'); return }
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
      const API   = import.meta.env.VITE_API_URL ?? ''
      const token = (await import('./services/api')).getAuthToken()

      // Stuur alleen de velden die de readiness-analyzer nodig heeft (niet de volledige scan).
      // Dit voorkomt grote POST-bodies (concept_mapping, all_issues, etc. zijn niet nodig).
      const payload = {
        score:             activeScanResult.score,
        structural_score:  activeScanResult.structural_score,
        relational_score:  activeScanResult.relational_score,
        use_case_score:    activeScanResult.use_case_score,
        files_summary:     (activeScanResult.files_summary || []).map(f => ({
          schema_key: f.schema_key,
          field_map:  f.field_map,
          mapping:    f.mapping,
          issues:     f.issues,
        })),
        relational_fk:     activeScanResult.relational_fk     || [],
        indicator_results: activeScanResult.indicator_results || [],
      }

      const resp  = await fetch(`${API}/api/profiles/${encodeURIComponent(filename)}/readiness`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(activeScanResult),
      })
      if (!resp.ok) {
        const detail = await resp.text().catch(() => `HTTP ${resp.status}`)
        throw new Error(`HTTP ${resp.status}: ${detail}`)
      }
      const matrix = await resp.json()
      setReadinessMatrix(matrix)
      setReadinessProfile(profile?.name || filename)
      setStep('readiness')
    } catch (err) {
      console.error('[openReadiness]', err)
      alert('Gereedheidsanalyse mislukt: ' + err.message)
    }
  }

  // Reconciliation Engine is alleen zichtbaar als de gebruiker de app-slug heeft
  const canReconciliation = !authUser
    || authUser.role === 'RHADIX_ADMIN'
    || (authUser.assigned_app_slugs || []).includes('reconciliation-engine')

  return (
    <>
      <EnvironmentBanner />
      {/* Verschuif content naar beneden als de banner zichtbaar is */}
      {BANNER_HEIGHT > 0 && <div style={{ height: BANNER_HEIGHT }} />}

      {step === 'portal' && (
        <AppPortal
          onLogin={() => setStep('systems')}
          brand={brand} onBrandChange={changeBrand}
          authUser={authUser}
          onTasks={() => setStep('tasks')}
          onDashboard={() => setStep('user_dashboard')}
          onAdmin={authUser?.role === 'RHADIX_ADMIN' ? () => setStep('admin') : null}
          onOrgAdmin={authUser?.role === 'ORG_ADMIN' ? () => setStep('org_admin') : null}
          onRsoAdmin={authUser?.role === 'RSO_ADMIN' ? () => setStep('rso_admin') : null}
          onLogout={handleLogout}
          onReconciliation={canReconciliation ? () => setStep('reconciliation') : null}
        />
      )}


      {step === 'admin' && (
        <AdminDashboard onBack={() => setStep('systems')} />
      )}

      {step === 'rso_admin' && (
        <RsoDashboard onBack={() => setStep('portal')} authUser={authUser} />
      )}

      {step === 'tasks' && (
        <Taken authUser={authUser} onBack={() => setStep('portal')} />
      )}

      {step === 'org_admin' && (
        <OrgAdminDashboard onBack={() => setStep('systems')} authUser={authUser} />
      )}

      {step === 'systems' && (
        <SelectSystems
          key={scanKey}
          onNext={(sel, std) => {
            setSystems(sel)
            setStandard(std || 'kikv')
            setStep((sel || []).length >= 1 ? 'multi_validatie' : 'upload')
          }}
          onBack={() => setStep('portal')}
          authUser={authUser}
          onDashboard={() => setStep('user_dashboard')}
          onAdmin={authUser?.role === 'RHADIX_ADMIN' ? () => setStep('admin') : null}
          onOrgAdmin={authUser?.role === 'ORG_ADMIN' ? () => setStep('org_admin') : null}
          onRsoAdmin={authUser?.role === 'RSO_ADMIN' ? () => setStep('rso_admin') : null}
          onOrgDashboard={(authUser?.role === 'ORG_ADMIN' || authUser?.role === 'RHADIX_ADMIN') ? () => setStep('org_dashboard') : null}
          onPlatformDashboard={authUser?.role === 'RHADIX_ADMIN' ? () => setStep('platform_dashboard') : null}
          onLogout={handleLogout}
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

      {step === 'multi_validatie' && (
        <MultiSourceValidatie
          systems={systems}
          authUser={authUser}
          onLogout={handleLogout}
          onBack={() => setStep('systems')}
          onProfiles={(scanResult) => { setActiveScanResult(scanResult); openProfiles('multi_validatie') }}
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
          onReconciliation={canReconciliation ? () => setStep('reconciliation') : null}
          onHome={() => setStep('systems')}
          authUser={authUser}
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
          onHome={() => setStep('systems')}
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
          onBack={() => setStep('systems')}
          onHome={() => setStep('systems')}
          authUser={authUser}
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
          onBack={() => setStep('systems')}
          onHome={() => setStep('systems')}
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

      {/* ── Phase 3 Dashboards ── */}
      {step === 'user_dashboard' && (
        <UserDashboard
          onBack={() => setStep('systems')}
          authUser={authUser}
        />
      )}

      {step === 'org_dashboard' && (
        <OrgDashboard
          onBack={() => setStep('systems')}
          authUser={authUser}
          tenantId={dashboardTenantId || undefined}
        />
      )}

      {step === 'platform_dashboard' && (
        <PlatformDashboard
          onBack={() => setStep('systems')}
          onOrgDrilldown={(tenantId, tenantName) => {
            setDashboardTenantId(tenantId)
            setDashboardTenantName(tenantName)
            setStep('org_dashboard')
          }}
        />
      )}

      {/* ── Reconciliation Engine ── */}
      {step === 'reconciliation' && (
        <ReconciliationDashboard
          onBack={() => setStep('portal')}
          authUser={authUser}
          onLogout={handleLogout}
        />
      )}

    </>
  )
}
