"""
test_readiness_mail.py — De mailer-uitbreiding en de twee Readiness-mails.

Twee dingen staan hier op het spel:

1. **Regressie.** De mailer wordt platformbreed gebruikt voor taken,
   wachtwoordreset, uitnodigingen en verificatie. De drie nieuwe parameters
   zijn optioneel; zonder die parameters moet er letterlijk hetzelfde bericht
   uit komen als voorheen.
2. **De nieuwe mails.** Bijlage, afzendernaam en Reply-To moeten kloppen, en de
   signaalmail mag het volledige rapport niet meesturen.

Er wordt nooit werkelijk verzonden: de SMTP-laag is vervangen door een
opvangfunctie die het samengestelde bericht bewaart.
"""
import pytest

from app.services import mailer
from app.services import readiness_mail as rm
from app.services.readiness_pdf import bouw_pdf
from app.services.readiness_rapport import bouw
from app.services.readiness_scoring import bereken


@pytest.fixture
def smtp(monkeypatch):
    """Zet mail aan en vangt het samengestelde bericht op."""
    for sleutel, waarde in [
        ("MAIL_ENABLED", "true"), ("SMTP_HOST", "smtp.test"), ("SMTP_PORT", "587"),
        ("SMTP_USER", "u"), ("SMTP_PASSWORD", "p"),
        ("SMTP_FROM", "noreply@rhadix.nl"), ("SMTP_FROM_NAME", "Rhadix"),
    ]:
        monkeypatch.setenv(sleutel, waarde)
    monkeypatch.delenv("SMTP_REPLY_TO", raising=False)

    berichten = []

    class NepServer:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def ehlo(self):
            pass

        def starttls(self, context=None):
            pass

        def login(self, *_):
            pass

        def send_message(self, msg):
            berichten.append(msg)

    monkeypatch.setattr(mailer.smtplib, "SMTP", lambda *a, **k: NepServer())
    return berichten


@pytest.fixture
def rapport():
    u = bereken("data", [2, 1, 0, 3, 3, 3, 1, 1, 1, 2, 2, 2, 0, 0, 3])
    return bouw(u, naam="Jan de Vries", organisatie="Zorggroep Voorbeeld")


# ── Regressie: bestaande aanroepen veranderen niet ────────────────────────────

def test_bestaande_aanroep_blijft_gelijk(smtp):
    assert mailer.send_email("a@b.nl", "Onderwerp", "<p>Hallo</p>") is True
    msg = smtp[0]
    assert msg["From"] == "Rhadix <noreply@rhadix.nl>"
    assert msg["To"] == "a@b.nl"
    assert msg["Subject"] == "Onderwerp"
    assert msg["Reply-To"] is None
    assert not msg.iter_attachments() or list(msg.iter_attachments()) == []
    typen = [d.get_content_type() for d in msg.walk() if not d.is_multipart()]
    assert typen == ["text/plain", "text/html"]


def test_bestaande_taakmail_blijft_gelijk(smtp):
    assert mailer.notify_task_assigned("a@b.nl", "Anna", "Bob", "Controleer dossier") is True
    msg = smtp[0]
    assert msg["From"] == "Rhadix <noreply@rhadix.nl>"
    assert list(msg.iter_attachments()) == []


def test_reply_to_uit_de_omgeving_blijft_werken(smtp, monkeypatch):
    monkeypatch.setenv("SMTP_REPLY_TO", "support@rhadix.nl")
    mailer.send_email("a@b.nl", "X", "<p>y</p>")
    assert smtp[0]["Reply-To"] == "support@rhadix.nl"


def test_mail_uit_blijft_een_no_op(monkeypatch):
    monkeypatch.setenv("MAIL_ENABLED", "false")
    assert mailer.send_email("a@b.nl", "X", "<p>y</p>") is False


# ── De nieuwe parameters ──────────────────────────────────────────────────────

def test_bijlage_komt_correct_mee(smtp):
    mailer.send_email("a@b.nl", "Met bijlage", "<p>zie bijlage</p>",
                      attachments=[("rapport.pdf", b"%PDF-1.4 test", "application", "pdf")])
    bijlagen = list(smtp[0].iter_attachments())
    assert len(bijlagen) == 1
    assert bijlagen[0].get_filename() == "rapport.pdf"
    assert bijlagen[0].get_content_type() == "application/pdf"
    assert bijlagen[0].get_payload(decode=True) == b"%PDF-1.4 test"


def test_meerdere_bijlagen(smtp):
    mailer.send_email("a@b.nl", "X", "<p>y</p>", attachments=[
        ("een.pdf", b"%PDF-1", "application", "pdf"),
        ("twee.txt", b"tekst", "text", "plain"),
    ])
    assert [b.get_filename() for b in smtp[0].iter_attachments()] == ["een.pdf", "twee.txt"]


def test_afzendernaam_per_mail(smtp):
    mailer.send_email("a@b.nl", "X", "<p>y</p>", from_name="Rhoderlanden Groep")
    assert smtp[0]["From"] == "Rhoderlanden Groep <noreply@rhadix.nl>"


def test_from_adres_blijft_het_geverifieerde_domein(smtp):
    """De weergavenaam mag wijzigen, het adres niet — DMARC staat op strikte
    alignment, dus het From-domein moet rhadix.nl blijven."""
    mailer.send_email("a@b.nl", "X", "<p>y</p>", from_name="Rhoderlanden Groep")
    assert "noreply@rhadix.nl" in smtp[0]["From"]
    assert "rhoderlandengroep.nl" not in smtp[0]["From"]


def test_reply_to_per_mail_overschrijft_de_omgeving(smtp, monkeypatch):
    monkeypatch.setenv("SMTP_REPLY_TO", "support@rhadix.nl")
    mailer.send_email("a@b.nl", "X", "<p>y</p>", reply_to="info@rhoderlandengroep.nl")
    assert smtp[0]["Reply-To"] == "info@rhoderlandengroep.nl"


# ── De mail aan de bezoeker ───────────────────────────────────────────────────

def test_rapportmail_volledig(smtp, rapport):
    pdf = bouw_pdf(rapport)
    assert rm.verstuur_rapport(rapport, "jan@voorbeeld.nl", pdf) is True

    msg = smtp[0]
    assert msg["To"] == "jan@voorbeeld.nl"
    assert msg["From"] == "Rhoderlanden Groep <noreply@rhadix.nl>"
    assert msg["Reply-To"] == "info@rhoderlandengroep.nl"
    assert msg["Subject"] == "Uw Data Readiness-rapport — 53 van 100"

    bijlagen = list(msg.iter_attachments())
    assert len(bijlagen) == 1
    assert bijlagen[0].get_content_type() == "application/pdf"
    assert bijlagen[0].get_payload(decode=True)[:5] == b"%PDF-"
    assert bijlagen[0].get_filename() == "readiness-rapport-data-zorggroep-voorbeeld.pdf"


def test_rapportmail_bevat_de_kernuitslag(rapport):
    html = rm.rapport_html(rapport)
    assert ">53<" in html
    assert "In ontwikkeling" in html
    for naam, score in rapport.dimensies:
        assert naam.replace("&", "&amp;") in html
        assert f"<b>{score}</b>" in html
    assert "indicatief rapport" in html.lower()
    assert "worden niet bewaard" in html


def test_rapportmail_noemt_het_rapport_indicatief(rapport):
    html = rm.rapport_html(rapport)
    assert "indicatief readiness-rapport op basis van uw antwoorden" in html.lower()


def test_bestandsnaam_is_veilig(rapport):
    rapport.organisatie = "Zorg & Welzijn / Twente B.V."
    naam = rm.bestandsnaam(rapport)
    assert naam == "readiness-rapport-data-zorg-welzijn-twente-b-v.pdf"
    assert all(c.isalnum() or c in "-." for c in naam)


def test_bestandsnaam_blijft_geldig_bij_rare_organisatienaam(rapport):
    rapport.organisatie = "???"
    assert rm.bestandsnaam(rapport) == "readiness-rapport-data-organisatie.pdf"


# ── De signaalmail ────────────────────────────────────────────────────────────

def test_signaalmail_heeft_geen_bijlage(smtp, rapport):
    assert rm.verstuur_signaal(rapport, "jan@voorbeeld.nl") is True
    msg = smtp[0]
    assert list(msg.iter_attachments()) == [], "het volledige rapport gaat intern niet mee"


def test_signaalmail_bevat_precies_de_afgesproken_gegevens(smtp, rapport):
    rm.verstuur_signaal(rapport, "jan@voorbeeld.nl")
    msg = smtp[0]
    assert msg["To"] == "info@rhoderlandengroep.nl"
    assert msg["Reply-To"] == "jan@voorbeeld.nl", "antwoorden gaat naar de aanvrager"
    assert msg["Subject"] == "Readiness-aanvraag: Zorggroep Voorbeeld — Data 53/100"

    html = rm.signaal_html(rapport, "jan@voorbeeld.nl")
    for verwacht in ("Jan de Vries", "Zorggroep Voorbeeld", "jan@voorbeeld.nl",
                     "Data Readiness Check", "53 van 100", "In ontwikkeling"):
        assert verwacht in html
    # de twee belangrijkste aandachtspunten
    zwak = [d.naam for d in bereken("data", rapport_antwoorden()).aandachtspunten]
    for naam in zwak:
        assert naam.replace("&", "&amp;") in html


def rapport_antwoorden():
    return [2, 1, 0, 3, 3, 3, 1, 1, 1, 2, 2, 2, 0, 0, 3]


def test_adressen_zijn_instelbaar(smtp, rapport, monkeypatch):
    monkeypatch.setenv("READINESS_INTERN_ADRES", "readiness@rhoderlandengroep.nl")
    monkeypatch.setenv("READINESS_REPLY_TO", "advies@rhoderlandengroep.nl")
    rm.verstuur_signaal(rapport, "jan@voorbeeld.nl")
    assert smtp[0]["To"] == "readiness@rhoderlandengroep.nl"
    rm.verstuur_rapport(rapport, "jan@voorbeeld.nl", b"%PDF-1.4")
    assert smtp[1]["Reply-To"] == "advies@rhoderlandengroep.nl"


def test_html_ontsnapt_ingevoerde_tekst(rapport):
    """Naam en organisatie komen van een publiek formulier; ze mogen geen HTML
    in de mail kunnen injecteren."""
    rapport.naam = '<script>alert("x")</script>'
    rapport.organisatie = "A & B <b>"
    html = rm.rapport_html(rapport)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "A &amp; B &lt;b&gt;" in html
