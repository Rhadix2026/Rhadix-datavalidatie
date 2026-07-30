"""
Regressietest: de algemeen/AFAS-route moet de schema-onafhankelijke pre-scan
(telefoon E.164, IBAN, AGB/BIG e.d.) meedraaien — voorheen zat die alleen in het
KIK-V-pad, waardoor een AFAS-bron-upload (CSV én JSON) telefoon-uitval miste en
"100% goed" toonde. Tevens: JSON en CSV geven op deze route identieke uitval.
"""
import json
from app.routers.validate import parse_json_bytes, parse_csv_bytes
from app.services.algemeen_validator import validate_algemeen

RECS = [
    {"EmployeeId": "000153", "BSN": "1234567", "DateOfBirth": "1980-05-05",
     "Gender": "V", "EmploymentStart": "2022-12-17", "FirstName": "A",
     "BirthName": "b", "Mail": "a@zorg.nl", "Mobile": "06-1234567", "Phone": "geen"},
    {"EmployeeId": "000154", "BSN": "123456782", "DateOfBirth": "1990-06-14",
     "Gender": "V", "EmploymentStart": "2021-02-02", "FirstName": "B",
     "BirthName": "D", "Mail": "b@zorg.nl", "Mobile": "06-12345678", "Phone": "06-51234567"},
]


def _phone_prescan(file_result):
    return [i for i in file_result["issues"]
            if i.get("prescan") and "Telefoon" in i["message"]]


def test_algemeen_json_draait_prescan_telefoon():
    cols = list(RECS[0].keys())
    _, rows, _ = parse_json_bytes(json.dumps(RECS).encode())
    res = validate_algemeen([{"filename": "Profit_Employees.json",
                              "headers": cols, "rows": rows}])
    fr = res["file_results"][0]
    phone = _phone_prescan(fr)
    # Mobile (06-1234567 = te kort) én Phone ("geen") vallen uit op E.164
    labels = {i["message"].split(" — ")[0] for i in phone}
    assert "Mobile" in labels and "Phone" in labels


def test_algemeen_json_csv_pariteit():
    cols = list(RECS[0].keys())
    csv_text = ",".join(cols) + "\n" + "\n".join(
        ",".join(str(r[c]) for c in cols) for r in RECS)

    _, jrows, _ = parse_json_bytes(json.dumps(RECS).encode())
    _, crows, _ = parse_csv_bytes(csv_text.encode(), "Profit_Employees.csv")

    jr = validate_algemeen([{"filename": "Profit_Employees.json", "headers": cols, "rows": jrows}])
    cr = validate_algemeen([{"filename": "Profit_Employees.csv", "headers": cols, "rows": crows}])

    def sig(res):
        fr = res["file_results"][0]
        return sorted((i["message"], i["severity"], i["count"]) for i in fr["issues"])

    assert sig(jr) == sig(cr)
    assert jr["summary"]["warn_count"] == cr["summary"]["warn_count"]
