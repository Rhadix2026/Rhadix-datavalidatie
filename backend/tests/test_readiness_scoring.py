"""
test_readiness_scoring.py — De rekenregels van de Readiness Checks.

Deze tests leggen de vastgestelde scoring vast als baseline. Ze horen te falen
zodra iemand aan de grenswaarden, de weging of de afronding komt zonder dat dat
een bewuste, opgedragen wijziging is.

Over de gevraagde grenswaarden 39/40, 59/60 en 79/80
----------------------------------------------------
Die drie ondergrenzen zijn als **totaalscore onbereikbaar**. Een totaalscore is
het gemiddelde van vijf dimensiescores, en een dimensiescore is altijd
n ÷ 9 × 100 afgerond — dat levert slechts tien mogelijke waarden op
(0, 11, 22, 33, 44, 56, 67, 78, 89, 100). Van de 101 denkbare totalen komen er
daardoor maar 62 werkelijk voor; 39, 59 en 81 horen daar niet bij.

De grenzen worden daarom op twee niveaus getoetst:

1. `band()` en `categorie()` rechtstreeks op 39/40, 59/60 en 79/80 — dat is de
   regel zoals hij in de code staat, los van bereikbaarheid;
2. met échte antwoorden op de hoogste *bereikbare* score onder elke grens en op
   de grens zelf: 38 → 40, 58 → 60, 78 → 80. Daarmee staat vast dat de
   categorie precies daar omslaat.
"""
import pytest

from app.services.readiness_content import INHOUD
from app.services import readiness_scoring as S


# ── Hulp ──────────────────────────────────────────────────────────────────────

def vector(punten_per_dimensie):
    """Bouwt vijftien antwoorden uit vijf dimensietotalen (elk 0 t/m 9).

    Een dimensietotaal wordt zo gelijkmatig mogelijk over de drie vragen
    verdeeld, zodat de vector ook bruikbaar is voor de rapportlogica.
    """
    uit = []
    for totaal in punten_per_dimensie:
        assert 0 <= totaal <= 9
        basis, rest = divmod(totaal, 3)
        uit += [basis + (1 if i < rest else 0) for i in range(3)]
    return uit


ALLE_CHECKS = list(INHOUD["checks"].keys())


# ── Structuur ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("check", ALLE_CHECKS)
def test_vijf_dimensies_van_drie_vragen(check):
    dims = INHOUD["checks"][check]["dims"]
    assert len(dims) == S.AANTAL_DIMENSIES == 5
    for d in dims:
        assert len(d["q"]) == S.VRAGEN_PER_DIMENSIE == 3
        assert len(d["findings"]) == 3, "één aandachtspunt per vraag"
        assert len(d["strengths"]) == 3, "één sterk punt per vraag"
    assert sum(len(d["q"]) for d in dims) == S.AANTAL_VRAGEN == 15


def test_antwoordmogelijkheden_ongewijzigd():
    assert INHOUD["answers"] == [
        ["Aantoonbaar geregeld", 3],
        ["Grotendeels geregeld", 2],
        ["Beperkt geregeld", 1],
        ["Nee / onbekend", 0],
    ]


def test_bandgrenzen_ongewijzigd():
    assert INHOUD["cats"] == [
        [0, 39, "Basis op orde brengen"],
        [40, 59, "In ontwikkeling"],
        [60, 79, "Goed op weg"],
        [80, 100, None],
    ]


# ── Uitersten ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("check", ALLE_CHECKS)
def test_alles_nul(check):
    u = S.bereken(check, [0] * 15)
    assert u.totaal == 0
    assert [d.score for d in u.dimensies] == [0, 0, 0, 0, 0]
    assert u.categorie == "Basis op orde brengen"
    assert u.band == 0
    assert u.duiding == INHOUD["checks"][check]["meaning"][0]


@pytest.mark.parametrize("check", ALLE_CHECKS)
def test_alles_maximaal(check):
    u = S.bereken(check, [3] * 15)
    assert u.totaal == 100
    assert [d.score for d in u.dimensies] == [100] * 5
    assert u.categorie == INHOUD["checks"][check]["top"]
    assert u.categorie in ("Datagereed", "KIK-V-gereed")
    assert u.band == 3
    assert u.duiding == INHOUD["checks"][check]["meaning"][3]


# ── Grenswaarden ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("score, verwachte_band", [
    (0, 0), (39, 0),        # bovengrens van de eerste band
    (40, 1), (59, 1),       # tweede band
    (60, 2), (79, 2),       # derde band
    (80, 3), (100, 3),      # bovenste band
])
def test_band_op_de_grenswaarden(score, verwachte_band):
    assert S.band(score) == verwachte_band


@pytest.mark.parametrize("score, verwachte_categorie", [
    (39, "Basis op orde brengen"), (40, "In ontwikkeling"),
    (59, "In ontwikkeling"),       (60, "Goed op weg"),
    (79, "Goed op weg"),           (80, "Datagereed"),
])
def test_categorie_slaat_precies_op_de_grens_om(score, verwachte_categorie):
    assert S.categorie(score, "data") == verwachte_categorie


def test_bovenste_band_erft_de_naam_van_de_check():
    assert S.categorie(80, "data") == "Datagereed"
    assert S.categorie(80, "kikv") == "KIK-V-gereed"


@pytest.mark.parametrize("dimensiepunten, verwacht_totaal, verwachte_categorie", [
    ((0, 0, 0, 8, 9), 38, "Basis op orde brengen"),   # hoogste bereikbare score onder 40
    ((0, 0, 0, 9, 9), 40, "In ontwikkeling"),         # exact op de grens
    ((0, 0, 8, 9, 9), 58, "In ontwikkeling"),         # hoogste bereikbare score onder 60
    ((0, 0, 9, 9, 9), 60, "Goed op weg"),             # exact op de grens
    ((0, 8, 9, 9, 9), 78, "Goed op weg"),             # hoogste bereikbare score onder 80
    ((0, 9, 9, 9, 9), 80, "Datagereed"),              # exact op de grens
])
def test_grensovergang_met_echte_antwoorden(dimensiepunten, verwacht_totaal, verwachte_categorie):
    u = S.bereken("data", vector(dimensiepunten))
    assert u.totaal == verwacht_totaal
    assert u.categorie == verwachte_categorie


def test_39_59_en_79_zijn_als_totaal_onbereikbaar():
    """Legt de aanname vast waarop de vorige test rust.

    Zou de weging ooit wijzigen, dan valt deze test om en is meteen duidelijk
    dat de grenswaardetests opnieuw moeten worden bepaald.
    """
    bereikbaar = set()
    for a in range(10):
        for b in range(10):
            for c in range(10):
                for d in range(10):
                    for e in range(10):
                        u = S.bereken("data", vector((a, b, c, d, e)))
                        bereikbaar.add(u.totaal)
    assert {39, 59, 79}.isdisjoint(bereikbaar)
    assert {38, 40, 58, 60, 78, 80} <= bereikbaar
    assert len(bereikbaar) == 62


# ── Dimensiescores ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("punten, verwacht", [
    (0, 0), (1, 11), (2, 22), (3, 33), (4, 44),
    (5, 56), (6, 67), (7, 78), (8, 89), (9, 100),
])
def test_dimensiescore_per_puntentotaal(punten, verwacht):
    u = S.bereken("data", vector((punten, 0, 0, 0, 0)))
    assert u.dimensies[0].score == verwacht


def test_afronding_gaat_omhoog_zoals_in_de_browser():
    """5 van 9 is 55,56 en wordt 56 — niet 55."""
    assert S._rond(55.5555) == 56
    assert S._rond(0.5) == 1, "een half punt gaat omhoog, niet naar het even getal"
    assert S._rond(1.5) == 2
    assert S._rond(2.5) == 3


# ── Gemengde antwoorden ───────────────────────────────────────────────────────

def test_gemengde_antwoorden():
    #      dim1: 2+1+0=3      dim2: 3+3+3=9   dim3: 1+1+1=3  dim4: 2+2+2=6  dim5: 0+0+3=3
    punten = [2, 1, 0,        3, 3, 3,        1, 1, 1,       2, 2, 2,       0, 0, 3]
    u = S.bereken("kikv", punten)
    assert [d.score for d in u.dimensies] == [33, 100, 33, 67, 33]
    assert u.totaal == 53
    assert u.categorie == "In ontwikkeling"
    assert [d.index for d in u.gerangschikt] == [0, 2, 4, 3, 1]
    assert [d.index for d in u.aandachtspunten] == [0, 2]


def test_elke_dimensie_telt_even_zwaar():
    """Negen punten in één dimensie wegen niet zwaarder dan negen verspreid."""
    geconcentreerd = S.bereken("data", vector((9, 0, 0, 0, 0)))
    verspreid = S.bereken("data", vector((2, 2, 2, 2, 1)))
    assert geconcentreerd.totaal == 20
    assert verspreid.totaal == 20


# ── Rangschikking ─────────────────────────────────────────────────────────────

def test_gelijke_dimensiescores_behouden_de_schermvolgorde():
    u = S.bereken("data", vector((3, 3, 3, 3, 3)))
    assert [d.score for d in u.dimensies] == [33] * 5
    assert [d.index for d in u.gerangschikt] == [0, 1, 2, 3, 4]
    assert [d.index for d in u.aandachtspunten] == [0, 1]


def test_bij_deels_gelijke_scores_wint_de_laagste_index():
    #        dim0=33  dim1=0  dim2=33  dim3=100  dim4=0
    u = S.bereken("data", vector((3, 0, 3, 9, 0)))
    assert [d.index for d in u.gerangschikt] == [1, 4, 0, 2, 3]
    assert [d.index for d in u.aandachtspunten] == [1, 4]


def test_aandachtspunten_zijn_de_twee_laagste():
    u = S.bereken("data", vector((9, 1, 9, 2, 9)))
    assert [d.index for d in u.aandachtspunten] == [1, 3]
    assert u.aandachtspunten[0].score <= u.aandachtspunten[1].score


# ── "Weet ik niet" bij KIK-V ──────────────────────────────────────────────────

def test_weet_ik_niet_bestaat_alleen_bij_kikv_datastation():
    kikv = INHOUD["checks"]["kikv"]["dims"]
    extras = [(i, d["extra"]) for i, d in enumerate(kikv) if d.get("extra")]
    assert extras == [(4, {"idx": 0, "label": "Weet ik niet"})]
    assert all(d.get("extra") is None for d in INHOUD["checks"]["data"]["dims"])


def test_weet_ik_niet_telt_als_nul_punten():
    """De extra optie levert 0 punten op, net als 'Nee / onbekend'."""
    zonder = S.bereken("kikv", vector((9, 9, 9, 9, 9)))
    #  dimensie 5, vraag 1 op 0 punten (weet ik niet) in plaats van 3
    met = list(vector((9, 9, 9, 9, 9)))
    met[12] = 0
    uit = S.bereken("kikv", met)
    assert zonder.dimensies[4].score == 100
    assert uit.dimensies[4].score == 67
    assert uit.totaal == 93


def test_antwoordlabel_toont_beide_mogelijkheden_bij_nul():
    """Bij 0 punten op die ene vraag is achteraf niet vast te stellen of de
    bezoeker 'Nee / onbekend' of 'Weet ik niet' koos — de browser stuurt alleen
    het puntenaantal mee. De bijlage toont daarom beide."""
    assert S.antwoordlabel_voor_vraag("kikv", 12, 0) == "Nee / onbekend / Weet ik niet"
    assert S.antwoordlabel_voor_vraag("kikv", 12, 3) == "Aantoonbaar geregeld"
    assert S.antwoordlabel_voor_vraag("kikv", 13, 0) == "Nee / onbekend"
    assert S.antwoordlabel_voor_vraag("data", 12, 0) == "Nee / onbekend"


# ── Afgeleide teksten ─────────────────────────────────────────────────────────

def test_interpretatie_gebruikt_low_onder_en_high_boven_de_grens():
    laag = S.bereken("data", vector((0, 9, 9, 9, 9))).dimensies[0]
    hoog = S.bereken("data", vector((9, 0, 0, 0, 0))).dimensies[0]
    assert S.interpretatie(laag).endswith(laag.definitie["low"])
    assert S.interpretatie(hoog).endswith(hoog.definitie["high"])
    assert S.interpretatie(laag).startswith(S.BANDWOORD[0])
    assert S.interpretatie(hoog).startswith(S.BANDWOORD[3])


@pytest.mark.parametrize("punten, sterk", [
    ((3, 3, 3), True),    # 100, alle antwoorden 3
    ((3, 3, 2), True),    # 89, alle antwoorden >= 2
    ((3, 3, 1), False),   # 78, maar één antwoord onder 2
    ((2, 2, 2), True),    # 67, precies op de drempel
    ((3, 2, 1), False),   # 67, maar niet alle antwoorden >= 2
    ((2, 2, 1), False),   # 56
])
def test_sterk_punt_vereist_score_en_bodem(punten, sterk):
    u = S.bereken("data", list(punten) + [0] * 12)
    assert S.is_sterk_punt(u.dimensies[0]) is sterk


# ── Invoervalidatie ───────────────────────────────────────────────────────────

def test_onbekende_check_wordt_geweigerd():
    with pytest.raises(ValueError, match="Onbekende check"):
        S.bereken("onbekend", [0] * 15)


@pytest.mark.parametrize("aantal", [0, 14, 16, 30])
def test_verkeerd_aantal_antwoorden_wordt_geweigerd(aantal):
    with pytest.raises(ValueError, match="Verwacht 15 antwoorden"):
        S.bereken("data", [0] * aantal)


@pytest.mark.parametrize("waarde", [-1, 4, 99])
def test_antwoord_buiten_de_schaal_wordt_geweigerd(waarde):
    punten = [0] * 15
    punten[7] = waarde
    with pytest.raises(ValueError, match="Antwoord 8"):
        S.bereken("data", punten)
