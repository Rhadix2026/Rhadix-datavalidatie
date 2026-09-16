"""
test_eigen_wachtwoord.py — een organisatiebeheerder wijzigt zijn eigen wachtwoord.

Bevinding 12 uit het bevindingenregister: "Ik kan als hoofdgebruiker van de organisatie
mijn eigen wachtwoord niet resetten. Onder gebruikersbeheer heb ik wel een reset knop
maar die werkt niet."

De oorzaak zat in de frontend: de resetknop stond voor het eigen account op `disabled`.
Er bestond wél een route om je eigen wachtwoord te wijzigen — PATCH /auth/me/password,
mét controle op het huidige wachtwoord — maar geen enkel scherm riep die aan.

Deze suite borgt de route waar dat scherm nu op steunt, in het scenario van de melding:
de rol ORG_ADMIN, op het eigen account. TestPasswordChange in test_auth.py dekt de
algemene gebruiker; hier gaat het om de beheerder en om wat er níet mag veranderen.
"""


def auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestBeheerderWijzigtEigenWachtwoord:

    def test_lukt_met_het_juiste_huidige_wachtwoord(self, client, user_org_admin, token_org_admin):
        res = client.patch(
            "/api/auth/me/password",
            json={"current_password": "Admin-Password-123!",
                  "new_password": "Nieuw-Beheer-Wachtwoord-1!"},
            headers=auth(token_org_admin),
        )
        assert res.status_code == 204, res.text

        # Het nieuwe wachtwoord werkt…
        nieuw = client.post("/api/auth/login",
                            json={"email": user_org_admin.email,
                                  "password": "Nieuw-Beheer-Wachtwoord-1!"})
        assert nieuw.status_code == 200, nieuw.text

        # …en het oude niet meer.
        oud = client.post("/api/auth/login",
                          json={"email": user_org_admin.email,
                                "password": "Admin-Password-123!"})
        assert oud.status_code == 401

    def test_lukt_niet_zonder_het_juiste_huidige_wachtwoord(self, client, token_org_admin):
        """De beveiligingsbaseline: je eigen wachtwoord wijzigen vraagt om het huidige."""
        res = client.patch(
            "/api/auth/me/password",
            json={"current_password": "niet-het-juiste", "new_password": "Nieuw-Beheer-Wachtwoord-1!"},
            headers=auth(token_org_admin),
        )
        assert res.status_code == 400

    def test_lukt_niet_zonder_sessie(self, client):
        res = client.patch(
            "/api/auth/me/password",
            json={"current_password": "Admin-Password-123!",
                  "new_password": "Nieuw-Beheer-Wachtwoord-1!"},
        )
        assert res.status_code == 401

    def test_zwak_wachtwoord_wordt_geweigerd(self, client, token_org_admin):
        res = client.patch(
            "/api/auth/me/password",
            json={"current_password": "Admin-Password-123!", "new_password": "kort"},
            headers=auth(token_org_admin),
        )
        assert res.status_code == 422


class TestGeenNevenschade:
    """Wat deze correctie niet doet."""

    def test_beheerdersreset_van_een_ander_blijft_werken(
        self, client, db, tenant_a, user_org_user, token_org_admin
    ):
        """De bestaande reset voor ándere gebruikers is ongemoeid gebleven."""
        res = client.post(
            f"/api/org/users/{user_org_user.id}/reset-password",
            json={"new_password": "Door-Beheerder-Gezet-1!"},
            headers=auth(token_org_admin),
        )
        assert res.status_code == 204, res.text

        login = client.post("/api/auth/login",
                            json={"email": user_org_user.email,
                                  "password": "Door-Beheerder-Gezet-1!"})
        assert login.status_code == 200

    def test_een_gewone_gebruiker_kan_geen_ander_wachtwoord_zetten(
        self, client, user_org_admin, token_org_user
    ):
        """Rolgrens ongewijzigd: de beheerdersroute blijft dicht voor ORG_USER."""
        res = client.post(
            f"/api/org/users/{user_org_admin.id}/reset-password",
            json={"new_password": "Mag-Niet-Lukken-123!"},
            headers=auth(token_org_user),
        )
        assert res.status_code == 403

    def test_een_beheerder_van_een_andere_organisatie_komt_er_niet_bij(
        self, client, user_org_user, token_tenant_b
    ):
        res = client.post(
            f"/api/org/users/{user_org_user.id}/reset-password",
            json={"new_password": "Mag-Niet-Lukken-123!"},
            headers=auth(token_tenant_b),
        )
        assert res.status_code in (403, 404)
