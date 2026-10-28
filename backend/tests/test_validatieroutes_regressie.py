"""
test_validatieroutes_regressie.py — vaste bewaking van alle drie de validatieroutes.

De zeven baselinescenario's (B5-01 t/m B5-07) belanden **allemaal** op het
kikv-pad: `source=afas` zet de route eerst op `algemeen`, en het vangnet
schakelt door naar `kikv` omdat de financiële testbestanden geen
algemeen-sjabloon hebben. Zelfs B5-07, dat expliciet `standard=algemeen`
vraagt, komt op kikv uit. Het algemene pad was daarmee niet door de baseline
gedekt.

Deze suite dekt dat gat en bewaakt per route drie dingen:

  1. **Welke route werkelijk draait.** Twee mechanismen kunnen de keuze
     overrulen: `SOURCE_TO_STANDARD` (de bron overschrijft `standard`) en het
     vangnet (bij nul herkende bestanden). Beide worden hier vastgepind, want
     een stille routewissel maakt elke andere assertie zinloos.
  2. **De bestaande scores.** Geen enkel cijfer mag verschuiven; de waarden
     hieronder zijn de huidige en horen bij de baseline.
  3. **Het contract van de verantwoording** (B-22 richting 1), gelijk over de
     drie routes.
"""
import io

import pytest

# ── herkenbare bestanden per route ─────────────────────────────────────────

MW_KOP = ["EmployeeId", "BSN", "DateOfBirth", "FirstName", "BirthName",
          "Gender", "EmploymentStart", "Mail"]
MW_RIJ = ["1001", "123456782", "1975-11-02", "Jeroen", "Bakker", "M",
          "2018-06-15", "j@example.org"]
PAT_KOP = ["patientnummer", "bsn", "geboortedatum", "geslacht"]
PAT_RIJ = ["P001", "123456782", "1975-11-02", "M"]

CONTRACT = {"checks", "findings", "score_covers_all_findings", "explanation"}


def _csv(kop, rijen):
    return ("\n".join([";".join(kop), *[";".join(r) for r in rijen]]) + "\n").encode("utf-8")


def _upload(client, naam, inhoud, **velden):
    res = client.post(
        "/api/validate/upload",
        files=[("files", (naam, io.BytesIO(inhoud), "text/csv"))],
        data=velden,
    )
    assert res.status_code == 200, res.text[:400]
    return res.json()


# ── 1. welke route draait er werkelijk ────────────────────────────────────

@pytest.mark.parametrize("bron, verwachte_route", [
    ("afas",    "algemeen"),
    ("ons",     "algemeen"),
    ("kikv",    "kikv"),
    ("epd_ecd", "zib"),
])
def test_de_bron_bepaalt_de_route(client, bron, verwachte_route):
    """`SOURCE_TO_STANDARD` overschrijft `standard`. Dat is bestaand gedrag en
    moet zichtbaar blijven: wie `standard=kikv` meegeeft met `source=afas`
    krijgt het algemene pad."""
    naam = "patienten.csv" if verwachte_route == "zib" else "Profit_Employees.csv"
    kop, rij = (PAT_KOP, PAT_RIJ) if verwachte_route == "zib" else (MW_KOP, MW_RIJ)
    d = _upload(client, naam, _csv(kop, [rij]), source=bron, standard="kikv")
    assert d["standard"] == verwachte_route
    assert d["score_version"]["path"] == verwachte_route


def test_het_vangnet_schakelt_om_bij_nul_herkende_bestanden(client):
    """Een bestand dat het algemene pad niet herkent maar kikv wél, komt op
    kikv uit — ook als `standard=algemeen` expliciet is gevraagd. Dit is de
    reden dat de zeven baselinescenario's het algemene pad niet raken."""
    d = _upload(client, "grootboekrubriek.csv",
                _csv(["grootboekcode", "omschrijving"], [["4000", "Personeelskosten"]]),
                standard="algemeen")
    assert d["standard"] == "kikv"
    assert d["score_version"]["path"] == "kikv"


# ── 2. de algemene route, expliciet bewaakt ───────────────────────────────

def test_algemene_route_volledig_bestand(client):
    d = _upload(client, "Profit_Employees.csv", _csv(MW_KOP, [MW_RIJ]), source="afas")
    assert d["standard"] == "algemeen"
    s = d["summary"]
    assert (s["completeness"], s["quality"], s["rhadix_index"]) == (100, 100, 100)
    assert d["score_accounting"]["score_covers_all_findings"] is True


def test_algemene_route_ontbrekende_verplichte_velden(client):
    """Vier van de acht verplichte velden: completeness halveert, quality blijft
    100. Dat is bestaand gedrag en de aanleiding van B-22."""
    kop = ["EmployeeId", "BSN", "DateOfBirth", "Gender"]
    d = _upload(client, "Profit_Employees.csv",
                _csv(kop, [["1001", "123456782", "1975-11-02", "M"]]), source="afas")
    s = d["summary"]
    assert (s["completeness"], s["quality"], s["rhadix_index"]) == (50, 100, 50)
    a = d["score_accounting"]
    assert a["score_covers_all_findings"] is False
    assert a["findings"]["outside_score"]["by_type"] == {"missing_field": 4}


def test_algemene_route_ongeldige_waarde_verlaagt_de_kwaliteit(client):
    slecht = list(MW_RIJ); slecht[1] = "1234567"      # faalt de elfproef
    d = _upload(client, "Profit_Employees.csv", _csv(MW_KOP, [MW_RIJ, slecht]), source="afas")
    assert d["summary"]["quality"] == 94
    a = d["score_accounting"]
    assert a["findings"]["in_score"]["errors"] == 1
    assert a["checks"]["failed"] == 1


def test_algemene_route_onherkend_bestand_valt_uit_het_gemiddelde(client):
    """Bestaand gedrag, blootgelegd bij B-22: een goed bestand plus een
    onherkend bestand geeft nog steeds 100. Het onherkende bestand wordt nu
    wel geteld."""
    res = client.post(
        "/api/validate/upload",
        files=[
            ("files", ("Profit_Employees.csv", io.BytesIO(_csv(MW_KOP, [MW_RIJ])), "text/csv")),
            ("files", ("Onbekend.csv", io.BytesIO(_csv(["a", "b"], [["1", "2"]])), "text/csv")),
        ],
        data={"source": "afas"},
    )
    assert res.status_code == 200, res.text[:300]
    d = res.json()
    assert d["summary"]["quality"] == 100
    assert d["score_accounting"]["checks"]["skipped"]["files_without_template"] == 1


# ── 3. de kikv- en zib-route ──────────────────────────────────────────────

def test_kikv_route_zonder_bevindingen(client):
    d = _upload(client, "Profit_Employees.csv", _csv(MW_KOP, [MW_RIJ]), source="kikv")
    assert d["standard"] == "kikv"
    assert d["score"] == 100.0
    assert d["total_errors"] == 0 and d["total_warns"] == 0
    assert "fouten x 5" in d["score_version"]["formula"]


def test_zib_route_levert_een_index(client):
    d = _upload(client, "patienten.csv", _csv(PAT_KOP, [PAT_RIJ]), source="epd_ecd")
    assert d["standard"] == "zib"
    assert isinstance(d["score"], (int, float))
    assert d["score_version"]["path"] == "zib"
    assert "rhadix-index" in d["score_version"]["formula"]


# ── 4. het contract is gelijk over de drie routes ─────────────────────────

@pytest.mark.parametrize("bron, naam, kop, rij", [
    ("afas",    "Profit_Employees.csv", MW_KOP,  MW_RIJ),
    ("kikv",    "Profit_Employees.csv", MW_KOP,  MW_RIJ),
    ("epd_ecd", "patienten.csv",        PAT_KOP, PAT_RIJ),
])
def test_contract_per_route(client, bron, naam, kop, rij):
    d = _upload(client, naam, _csv(kop, [rij]), source=bron)
    a = d["score_accounting"]
    v = d["score_version"]
    assert CONTRACT.issubset(a)
    assert set(a["checks"]) == {"executed", "passed", "failed", "skipped", "note"}
    assert set(a["findings"]) == {"in_score", "outside_score"}
    assert set(a["findings"]["in_score"]) == {"errors", "warnings", "by_type"}
    assert v["version"] and v["path"] and v["formula"]
    assert "geen vergelijkbare aantallen" in a["checks"]["note"]


@pytest.mark.parametrize("bron, naam, kop, rij", [
    ("afas",    "Profit_Employees.csv", MW_KOP,  MW_RIJ),
    ("kikv",    "Profit_Employees.csv", MW_KOP,  MW_RIJ),
    ("epd_ecd", "patienten.csv",        PAT_KOP, PAT_RIJ),
])
def test_toelichting_belooft_nooit_foutloosheid(client, bron, naam, kop, rij):
    d = _upload(client, naam, _csv(kop, [rij]), source=bron)
    tekst = d["score_accounting"]["explanation"].lower()
    for woord in ("foutloos", "geen fouten", "volledig correct", "alles klopt", "perfect"):
        assert woord not in tekst, f"{woord!r} staat in: {tekst}"
