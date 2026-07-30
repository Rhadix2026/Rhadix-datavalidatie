"""
Cross-check-bevindingen op de algemeen/AFAS-route tellen mee in de kop
(fouten-teller) en drukken de totaalscore onder 100 — per-bestand-scores blijven
ongemoeid. Integratietest via /api/validate/upload (source=afas).
"""
import json


def _up(name, recs):
    return ("files", (name, json.dumps(recs).encode(), "application/json"))


def test_crosscheck_telt_mee_in_kop_en_score(client):
    # Medewerker: personeelsnummers 000101 + 000102 (geldige BSN's, elfproef-ok)
    med = [
        {"EmployeeId": "000101", "BSN": "111222333", "DateOfBirth": "1980-05-05",
         "Gender": "V", "EmploymentStart": "2020-01-01", "FirstName": "A",
         "BirthName": "B", "Mail": "a@zorg.nl"},
        {"EmployeeId": "000102", "BSN": "111222333", "DateOfBirth": "1985-03-03",
         "Gender": "V", "EmploymentStart": "2020-01-01", "FirstName": "C",
         "BirthName": "D", "Mail": "c@zorg.nl"},
    ]
    # Werkovereenkomst met 000999 dat NIET in Medewerker staat -> cross-check-fout
    werk = [
        {"EmployeeId": "000102", "StartDate": "2020-01-01", "ContractType": "vast"},
        {"EmployeeId": "000999", "StartDate": "2020-01-01", "ContractType": "vast"},
    ]

    r = client.post(
        "/api/validate/upload",
        files=[_up("medewerker_afas_hrm.json", med), _up("werkovereenkomst_afas_hrm.json", werk)],
        data={"source": "afas", "standard": "algemeen"},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    cc = body.get("cross_checks", [])
    assert any("niet in Medewerker" in c["label"] for c in cc)

    cc_errs = sum(1 for c in cc if c.get("severity") == "error")
    assert cc_errs >= 1

    # De kop-teller = per-bestand-fouten + cross-check-fouten (dus meegeteld)
    per_file_errs = sum(
        len([i for i in fr.get("issues", []) if i.get("severity") == "error"])
        for fr in body.get("file_results", [])
    )
    assert body["summary"]["error_count"] == per_file_errs + cc_errs

    # Totaalscore niet 100 zolang er cross-check-uitval is
    assert body["summary"]["quality"] < 100
