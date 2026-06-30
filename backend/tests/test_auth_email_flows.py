"""Tests voor de e-mail-auth-flows: wachtwoord-reset, uitnodiging, verificatie."""
from datetime import timedelta

from app.auth.router import issue_token, consume_token
from app.models.auth_models import AuthToken, User


def _login(client, email, pw):
    return client.post("/api/auth/login", json={"email": email, "password": pw})


class TestForgotPassword:
    def test_unknown_email_returns_204(self, client):
        r = client.post("/api/auth/forgot-password", json={"email": "niemand@nergens.nl"})
        assert r.status_code == 204

    def test_known_email_creates_reset_token(self, client, db, user_org_user):
        r = client.post("/api/auth/forgot-password", json={"email": user_org_user.email})
        assert r.status_code == 204
        toks = db.query(AuthToken).filter(AuthToken.user_id == user_org_user.id,
                                          AuthToken.purpose == "reset").all()
        assert len(toks) == 1
        assert toks[0].used_at is None


class TestResetPassword:
    def test_valid_token_sets_new_password(self, client, db, user_org_user):
        raw = issue_token(db, user_org_user, "reset", timedelta(minutes=60))
        new_pw = "Nieuw-Wachtwoord-1!"
        r = client.post("/api/auth/reset-password", json={"token": raw, "new_password": new_pw})
        assert r.status_code == 204
        # oude werkt niet meer, nieuwe wel
        assert _login(client, user_org_user.email, "Correct-Password-123!").status_code == 401
        assert _login(client, user_org_user.email, new_pw).status_code == 200

    def test_token_is_single_use(self, client, db, user_org_user):
        raw = issue_token(db, user_org_user, "reset", timedelta(minutes=60))
        client.post("/api/auth/reset-password", json={"token": raw, "new_password": "Nieuw-Wachtwoord-1!"})
        r2 = client.post("/api/auth/reset-password", json={"token": raw, "new_password": "Anders-Wachtwoord-2!"})
        assert r2.status_code == 400

    def test_expired_token_rejected(self, client, db, user_org_user):
        raw = issue_token(db, user_org_user, "reset", timedelta(minutes=-5))
        r = client.post("/api/auth/reset-password", json={"token": raw, "new_password": "Nieuw-Wachtwoord-1!"})
        assert r.status_code == 400

    def test_weak_password_rejected(self, client, db, user_org_user):
        raw = issue_token(db, user_org_user, "reset", timedelta(minutes=60))
        r = client.post("/api/auth/reset-password", json={"token": raw, "new_password": "zwak"})
        assert r.status_code == 422

    def test_invalid_token_rejected(self, client):
        r = client.post("/api/auth/reset-password", json={"token": "onzin", "new_password": "Nieuw-Wachtwoord-1!"})
        assert r.status_code == 400


class TestInviteSetPassword:
    def test_invite_token_activates_and_sets_password(self, client, db, tenant_a):
        import uuid
        from app.auth.security import hash_password
        u = User(id=uuid.uuid4(), tenant_id=tenant_a.id, email="invited@tenant-a.nl",
                 password_hash=None, role=__import__("app.models.auth_models", fromlist=["UserRole"]).UserRole.ORG_USER,
                 is_active=True, email_verified=False)
        db.add(u); db.commit(); db.refresh(u)
        raw = issue_token(db, u, "invite", timedelta(days=7))
        r = client.post("/api/auth/set-password", json={"token": raw, "password": "Eerste-Wachtwoord-1!"})
        assert r.status_code == 204
        db.refresh(u)
        assert u.email_verified is True
        assert _login(client, "invited@tenant-a.nl", "Eerste-Wachtwoord-1!").status_code == 200

    def test_reset_token_cannot_be_used_as_invite(self, client, db, user_org_user):
        raw = issue_token(db, user_org_user, "reset", timedelta(minutes=60))
        r = client.post("/api/auth/set-password", json={"token": raw, "password": "Eerste-Wachtwoord-1!"})
        assert r.status_code == 400


class TestVerifyEmail:
    def test_verify_marks_email_verified(self, client, db, user_org_user):
        user_org_user.email_verified = False
        db.commit()
        raw = issue_token(db, user_org_user, "verify", timedelta(hours=24))
        r = client.post("/api/auth/verify-email", json={"token": raw})
        assert r.status_code == 204
        db.refresh(user_org_user)
        assert user_org_user.email_verified is True
