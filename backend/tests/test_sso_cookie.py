"""Verifieert de cookie-fallback: /auth/me werkt met alleen het rhadix_sso-cookie."""

def test_me_via_cookie(client, token_org_user, user_org_user):
    # geen Authorization-header, alleen het centrale cookie
    res = client.get("/api/auth/me", cookies={"rhadix_sso": token_org_user})
    assert res.status_code == 200, res.text
    assert res.json()["email"] == user_org_user.email

def test_me_no_creds_401(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401

def test_optional_endpoint_accepts_cookie(client, token_org_user):
    # bearer blijft ook werken
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_org_user}"})
    assert res.status_code == 200
