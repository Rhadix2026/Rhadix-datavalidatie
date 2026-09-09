/**
 * AppToewijzing — één bediening voor het toewijzen en intrekken van applicaties.
 *
 * Gebruikt door de drie beheerschermen die dezelfde handeling uitvoeren op een ander
 * object: AdminDashboard en RsoDashboard op een ORGANISATIE, OrgAdminDashboard op een
 * GEBRUIKER. Dat niveauverschil blijft bestaan — het zit in het autorisatiemodel, en
 * elk scherm houdt zijn eigen endpoints en zijn eigen rechten. Wat gelijk wordt
 * getrokken is uitsluitend de bediening en de tekst.
 *
 * Vóór deze component waren er drie manieren om toe te wijzen (een modal, een
 * verborgen keuzelijst en knoppen) en drie manieren om in te trekken, waarvan één
 * zonder enige bevestiging. Zie bevinding 16 en 17 in het bevindingenregister.
 *
 * De regels eronder staan in lib/appToewijzing.js en zijn daar getest.
 */
import {
  beschikbareApps,
  bevestigingIntrekken,
  kopToegewezen,
  kopBeschikbaar,
  naarItems,
  tekstLeeg,
  NIVEAU_GEBRUIKER,
} from '../lib/appToewijzing'

const kopStijl = {
  fontSize: 12, fontWeight: 700, color: 'var(--text3)',
  textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10,
}

const chipStijl = {
  display: 'inline-flex', alignItems: 'center', gap: 8, background: '#e0f2fe',
  borderRadius: 20, padding: '5px 10px 5px 14px', fontSize: 13, fontWeight: 600,
  color: '#0369a1',
}

const toevoegStijl = {
  display: 'inline-flex', alignItems: 'center', gap: 6, background: 'var(--blue)',
  color: '#fff', border: 'none', borderRadius: 20, padding: '6px 14px',
  fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: 'var(--font)',
}

/**
 * @param {Array}   toegewezen  huidige toewijzingen (rijen uit de API)
 * @param {Array}   aanbod      wat toegewezen mág worden voor dit object
 * @param {string}  doelNaam    naam van de organisatie of gebruiker, voor de bevestiging
 * @param {string}  niveau      NIVEAU_ORGANISATIE of NIVEAU_GEBRUIKER
 * @param {boolean} bezig       zet de knoppen op slot tijdens een aanroep
 * @param {Function} onToewijzen  (applicationId) => void
 * @param {Function} onIntrekken  (applicationId) => void — pas na bevestiging
 */
export default function AppToewijzing({
  toegewezen = [],
  aanbod = [],
  doelNaam,
  niveau = NIVEAU_GEBRUIKER,
  bezig = false,
  onToewijzen,
  onIntrekken,
}) {
  const huidig = naarItems(toegewezen)
  const beschikbaar = beschikbareApps(toegewezen, aanbod)

  const intrekken = (item) => {
    if (!window.confirm(bevestigingIntrekken(item.naam, doelNaam))) return
    onIntrekken(item.applicationId)
  }

  return (
    <div>
      <div style={kopStijl}>{kopToegewezen(niveau)}</div>

      {huidig.length === 0 ? (
        <p style={{ fontSize: 13, color: 'var(--text3)', margin: '0 0 16px' }}>{tekstLeeg(niveau)}</p>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {huidig.map(item => (
            <span key={item.applicationId} style={chipStijl}>
              {item.naam}
              <button
                onClick={() => intrekken(item)}
                disabled={bezig}
                title={`Toegang tot ${item.naam} intrekken`}
                aria-label={`Toegang tot ${item.naam} intrekken`}
                style={{
                  background: 'none', border: 'none', cursor: bezig ? 'not-allowed' : 'pointer',
                  color: '#94a3b8', fontSize: 16, lineHeight: 1, padding: 0,
                }}
              >×</button>
            </span>
          ))}
        </div>
      )}

      {beschikbaar.length > 0 && (
        <>
          <div style={kopStijl}>{kopBeschikbaar(niveau)}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {beschikbaar.map(item => (
              <button
                key={item.applicationId}
                onClick={() => onToewijzen(item.applicationId)}
                disabled={bezig}
                title={`${item.naam} toewijzen`}
                style={{ ...toevoegStijl, opacity: bezig ? 0.6 : 1, cursor: bezig ? 'not-allowed' : 'pointer' }}
              >+ {item.naam}</button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
