# Stap 2 — Generieke controles, profielen, rapportage & reconciliatie

_Implementatieplan Rhadix Datavalidatie · doelarchitectuur · 6 juli 2026_
_Uitgangspunt: Stap 1 (canoniek model) is klaar op staging. Vangnet: 227+ tests groen._

---

## 1. Doel

Stap 1 leverde één ingest met een canoniek model (bronherkenning, concept-mapping, genormaliseerde waarden). Stap 2 zet daar de controles op: **generieke controles die één keer bestaan** en op het canonieke model draaien (Laag 2), met de standaarden (KIK-V, ZIB) als **declaratieve profielen** (Laag 3). Zo verdwijnt het "3× fixen"-probleem. In dit plan krijgen ook **rapportage** en **reconciliatie** expliciet hun plek in de architectuur.

## 2. De gelaagde doelarchitectuur — met rapportage en reconciliatie

| Laag / onderdeel | Wat | Status |
|---|---|---|
| **Laag 1 — Ingest & canoniek model** | Bronherkenning, concept-mapping, normalisatie | Klaar (Stap 1) |
| **Laag 2 — Generieke controles** | Herbruikbare checks (verplicht veld, datum, BSN, codelijst, formaat) op het canonieke model | Stap 2 |
| **Laag 3 — Conformiteit/benchmark-profielen** | KIK-V, ZIB, Algemeen als declaratieve regelsets (verplichte concepten, toegestane waarden, berekeningsregels) | Stap 2 |
| **Laag 4 — Rhadix Index** | Scoringslaag bovenop laag 2+3 (twee pijlers) | Stap 3 |
| **Rapportage** (dwarslaag) | Leest de uitkomsten van laag 2/3/4 en maakt rapporten (beschikbaarheid, KIK-V readiness, management) — JSON + PDF | Bestaat; krijgt een **eigen tegel/overzicht** |
| **Reconciliatie** (aparte module) | "SPARQL loslaten op de data": RDF-triples uit het canonieke model, berekenings-/uitwisselregels, happy-flow batch | Bestaat; blijft **aparte module**, sluit aan op Laag 1/2 (semantisch) |

Belangrijk inzicht uit het ADR: de semantische controles (Laag 2) bouwen voort op de bestaande reconciliatie/RDF/SPARQL-laag. Reconciliatie en de generieke controles delen dus straks hetzelfde canonieke model als bron.

## 3. Stap 2 — kern: generieke controles + declaratieve profielen

### 3.1 Laag 2 — generieke controles
Eén `controls`-module met herbruikbare checks die op een `CanonicalFile` werken en een uniforme bevinding opleveren (veld, type, ernst, voorbeelden, herleidbaar naar bronkolom/onbewerkte waarde):

- `required` — is een verplicht concept aanwezig?
- `date` — kalendergeldige datum (hergebruikt `dataquality`).
- `bsn` — elfproef.
- `codelist` — waarde binnen een toegestane lijst (bv. verzuimsoort).
- `format` — e-mail, postcode, getal, geslacht.

De checks lezen `cell.value` (genormaliseerd) en kennen de ernst uit het profiel.

### 3.2 Laag 3 — declaratieve profielen
Per standaard/recordtype een declaratieve regelset (YAML/py-data): welke concepten verplicht zijn, welk type/codelijst geldt, en welke berekeningsregels. KIK-V en ZIB worden omgezet van code naar profiel; Algemeen is al dicht bij een profiel. **Nieuwe standaard = nieuw profiel, geen nieuwe app.**

### 3.3 Slices (incrementeel, pariteit als vangnet)
- **Slice 2.1 — Controls-fundament.** `controls`-module met de generieke checks + uniforme bevinding. Unit-tests; nog geen validator omgezet.
- **Slice 2.2 — Profielschema + één profiel.** Declaratief profielformaat + eerste profiel (bv. Algemeen `employees`); generieke run erop, pariteit met de huidige uitkomst.
- **Slice 2.3 — KIK-V & ZIB naar profielen.** Bestaande regels omzetten; per recordtype pariteitstest oude-vs-nieuwe bevindingen op de bestaande testbestanden.
- **Slice 2.4 — Omschakelen.** De endpoints laten de generieke controle-laag draaien; oude validator-code uitfaseren zodra pariteit over de hele suite bewezen is.

## 4. Rapportage — eigen tegel/overzicht

**Nu:** drie rapporttypen (beschikbaarheid, KIK-V readiness, management) als JSON + PDF, gebouwd uit een `ValidationRun` (`reports.py` + `report_builder.py` + `report_pdf_template.py`). Ze zijn nu bereikbaar via losse knoppen ná een scan; er is geen centraal overzicht.

**Voorstel:** een **Rapportage-tegel** in de app met een overzicht van beschikbare rapporten per scan (`ValidationRun`): datum, standaard, organisatie, en per rij de knoppen JSON/PDF voor elk beschikbaar rapporttype. Technisch: een nieuwe overzichtspagina die `GET /api/history` (runs) combineert met `GET /api/reports/{run_id}/types`; download via de bestaande report-endpoints. Positionering: rapportage is een dwarslaag die de uitkomsten van Laag 2/3/4 consumeert — de tegel is puur presentatie, geen nieuwe rekenlogica.

## 5. Reconciliatie — aparte module

**Nu:** volwaardig pakket `app/reconciliation/` (rule-, calculation- en reconciliation-engine, `rdf_store` met Fuseki/rdflib-fallback, YAML happy-flow-regels), eigen router `/api/reconciliation`, eigen `ReconciliationDashboard`, en app-slug-gated (`reconciliation-engine`).

**Voorstel:** reconciliatie blijft een **zelfstandige module met eigen tegel**, maar gaat expliciet het **canonieke model** van Laag 1 als bron gebruiken (RDF-triples uit `CanonicalFile` i.p.v. eigen parsing). Zo delen de generieke controles (Laag 2, semantisch) en reconciliatie dezelfde genormaliseerde data. Toegang blijft via de app-slug; de module houdt zijn eigen roadmap (berekenings-/uitwisselregels, SPARQL).

## 6. Risico's en aandachtspunten

- **Pariteit boven snelheid:** eerst pariteitstests (oude vs. nieuwe bevindingen) per recordtype, dán omschakelen. Verschillen expliciet maken.
- **Bevinding-formaat:** de generieke bevinding moet 1-op-1 te mappen zijn op wat de frontend (dashboards, traceability-drilldown) en de rapporten nu verwachten.
- **Geen gedragswijziging tijdens de bouw:** slices 2.1–2.3 draaien naast de bestaande validators; pas 2.4 schakelt om.
- **Reconciliatie-koppeling:** het overzetten naar het canonieke model apart en pariteit-getest doen, los van de controle-omschakeling.

## 7. Definition of done (Stap 2)

- Eén generieke controle-laag draait op het canonieke model; KIK-V/ZIB/Algemeen als declaratieve profielen.
- Pariteit bewezen op de bestaande testbestanden; volledige suite groen; geen functionele wijziging voor de gebruiker.
- Rapportage heeft een eigen overzichts-tegel; reconciliatie is een duidelijk afgebakende module op het canonieke model.
- Fundament staat voor **Stap 3** (Rhadix Index v2.0 als scoringslaag).
