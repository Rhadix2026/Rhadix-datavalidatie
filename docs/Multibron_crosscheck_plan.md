# Plan — Multi-bron upload + cross-checks in de Datavalidatie-flow

**Doel:** op het scherm "Datavalidatie — kies je bron" meerdere bronsystemen tegelijk kunnen
kiezen, bestanden per bron uploaden in één run, en naast de bestaande generieke validatie
óók **cross-checks tussen bronnen** draaien. De happy-flow-set dient als voorbeeld/testdata.

---

## 1. Huidige situatie (kort)

- **"Kies je bron" is enkelvoudig:** je klikt één bronsysteem aan (AFAS HRM, Nedap/ONS, Exact,
  ChipSoft, …) en gaat direct naar upload. Meerdere bestanden mogen, maar ze worden allemaal
  aan één bron gekoppeld.
- **De Reconciliation Engine doet al multi-file cross-checks:** batch-upload, auto-herkenning
  per bestandsnaam, en reconciliatie tegen indicatoren (SPARQL/berekeningsregels). De happy-flow
  voorbeeldset zit daar al in.
- **Het fundament ligt er:** het canonieke model (doelarchitectuur Stap 1) houdt al
  `source_type` + `record_type` per bestand bij. En de happy-flow-bestanden zijn al per bron
  gesuffixt: `_afas_hrm` (AFAS HRM), `_ons` (Nedap ONS), `_afas_fin` (AFAS Financieel).

**Conclusie:** we hoeven niet veel nieuws te verzinnen — vooral bestaande bouwstenen (canoniek
model + reconciliatie) combineren en zichtbaar maken in de hoofdflow.

---

## 2. Voorstel — UI/flow

1. **"Kies je bron" wordt meervoudig.** Bronkaarten worden aanvinkbaar (checkbox/selectie i.p.v.
   direct doorklikken). Onderaan een knop "Verder met N bronnen".
2. **Upload per bron.** Op het uploadscherm één zone per gekozen bron, met de bronnaam als label,
   zodat elk bestand aan de juiste bron hangt (i.p.v. alles aan één bron). Automatische herkenning
   op bestandsnaam blijft als hulp.
3. **Eén run, twee lagen resultaat:**
   - **Per bron:** de bestaande generieke validatie (compleetheid, formaten, codelijsten) — ongewijzigd.
   - **Over bronnen heen:** een nieuw **cross-check-overzicht** (zie §3).
4. **Voorbeeld laden:** knop "Laad happy-flow (3 bronnen)" die de voorbeeldset verdeelt over
   AFAS HRM / Nedap ONS / AFAS Financieel — één klik om de flow te demonstreren.

---

## 3. Cross-checks — twee opties (met happy-flow-voorbeelden)

De happy-flow leent zich goed voor concrete cross-checks tussen bronnen:

| Cross-check | Bron A | Bron B | Wat het aantoont |
|---|---|---|---|
| Medewerkeraantal consistent | `medewerker_afas_hrm` | `medewerker_ons` | Zelfde populatie in HR-bron en ONS? |
| HR ↔ financieel | actieve werkovereenkomsten (`werkovereenkomst_afas_hrm`) | loonkosten-boekingen (`financieleboeking_afas_fin`) | Zijn er loonkosten zonder dienstverband of andersom? |
| Cliënt ↔ contract | `client_ons` | `contracten` | Cliënten zonder contract / contracten zonder cliënt |
| Vestigingen | `vestiging_ons` | boekingen per WLZ-kostenplaats (`wlzkostenplaats_afas_fin`) | Kostenplaatsen die niet naar een bekende vestiging herleiden |
| Sleutelkoppeling | personeelsnummer in HR | personeelsnummer in `verzuim_*` | Verzuim op onbekende medewerker |

### Optie A — Bestaande Reconciliation Engine hergebruiken (aanbevolen)
De cross-check-motor onder de nieuwe upload = de bestaande batch-reconciliatie. Voordelen: het
werkt al, is getest op de happy-flow, en de indicator-/berekeningsregels zijn declaratief (YAML) —
nieuwe cross-checks toevoegen = een regel toevoegen, geen nieuwe code. We voegen een handvol
**cross-bron-indicatoren** toe (bovenstaande tabel) bovenop de bestaande per-bron-indicatoren.

- **Werk:** UI multi-select + per-bron upload; resultaten van de reconciliatie-batch tonen als
  cross-check-blok in de validatie-uitkomst; ~5 nieuwe cross-bron-regels.
- **Risico:** laag (bouwt op bestaande, geteste motor).

### Optie B — Nieuwe cross-checks in de validatiepijplijn
Cross-checks als nieuwe stap in de generieke validatielaag (Laag 2 van de doelarchitectuur),
werkend op het canonieke model met `source_type`. Voordelen: dicht op de bestaande validatie-uitkomst,
uniforme bevindingen. Nadeel: meer nieuw te bouwen (cross-record-regeltype, aggregaties over
bronnen), meer test-/ontwerptijd.

- **Werk:** nieuw cross-check-regeltype + aggregatielogica + tests; UI idem als A.
- **Risico:** middel (nieuwe motorlogica).

---

## 4. Fasering (klein en veilig)

- **Fase 1 — Multi-select + per-bron upload + per-bron validatie.** Puur de flow; nog geen
  cross-checks. Direct bruikbaar en laag risico. (Happy-flow-knop erbij.)
- **Fase 2 — Cross-checks.** Via de gekozen optie (A of B), te beginnen met 2-3 cross-checks uit
  de tabel, uitbreidbaar.
- **Fase 3 — Rapportage.** Cross-check-resultaat in het bestaande rapport/overzicht opnemen.

---

## 5. Aanbeveling

**Fase 1 nu bouwen** (multi-select "kies je bron" + per-bron upload + happy-flow-knop), en voor de
cross-checks **Optie A** (Reconciliation Engine hergebruiken) — dat geeft het snelst zichtbaar
resultaat met het laagste risico, en cross-checks worden dan declaratief (YAML) uitbreidbaar.

> Beslispunt voor Rene: akkoord met Fase 1 nu + Optie A voor de cross-checks? Of wil je Optie B
> (alles in de validatiepijplijn) — dan plan ik daar iets meer ontwerptijd voor in.
