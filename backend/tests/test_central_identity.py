"""
Fase 1 — centrale identiteit: borgt RS256/JWKS + verrijkte token-claims.
HS256 blijft de default; deze test schakelt tijdelijk RS256 in via env + reload.
"""
import importlib, os
import app.auth.security as security

PRIV = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC4qgucRL6fu13F
XdlKDEEuKW/zJ1L0KBlLKAZto34LN3f737AvpFZ41pFEYtn2EaKlKKPWDDKXFQf+
PXESaeERjUXtZDkFWU5k1MdkDU9mNdN/AJ7ugbdFLU/dxOWOEkN1dysywLyZSez4
lVGI7lKo8HyxAloa9SeA3FbHrdAnUceIv2W8SRJzNqEsXQEVd+UEAUO806GCcEqx
4PK6yhsV2uKgeeDDM6s+YXUoS7e64J6r6UYLOzUi1KHAO69U1TdQQodMwfXyvv/p
SWdj78NuYij6lRNxN9iyf+Q2NcLzAGTJgOkRXUVdVszdRMLWBq84mXmikvo6euJo
wsig4G8lAgMBAAECggEAALv1+qKB7kNb4Hn162osbeAFOoD0biqR+3i4eO8DnAqC
4bWCzyzLhmg//nbtyF8I4CCtvQw57GEBo6EpdyvG7uyLE7ne74CQfgbFJZc62JtI
cMnQAqAg2j/zCdgLg+hoywhYZR/zKq90GSP2sqOfyzdi5qTmi9CPUABQRlAxvC2w
ADzRzfhAlWtMC0ni1Km85iWhctamNY+kx4YrqHib5GzDWybq1A6+pIIqjS9YQGB0
TmLYFjmJtVi0looafoJi76Tes3HliOju1fwCbZAQJ7uHDNqAfvuO5+qTB6m0RRed
Fr36evhdEL4SM9uaXY+Wsr7d0IqHOvYVfwfj/Um2YQKBgQD6j3v8sn29cNju/t3/
8RcyfdYIMsq3jm1HAFxhWNgSRsOjKpd0mSKidJ3Q8MCYJjLABFKDU/EktAEJg+/P
o7uTc4dbocbYL1tusDhtT01HK+WVRHD52Um0kuCVGunJCzWj/SSmFpiiSZUg8ciV
8XyPQ1+jEb4FW4hj/6Dyj8AAMQKBgQC8rFX7FX3LMHCZRxcTTjW30oQMz/ccNxJh
f20HTPqcQHcbKC9BKVb913hC/ermzLsr3FRhkW79Y4Wp5bUgUDEXKRkAPXg7/Z8X
XyIlh0MemboC6uMdgIQ8w6fXCIcUd75sB/ysTB5sUeYKKLJosoQoU3WCE0BXKYXP
v/1f9ip1NQKBgQDUsB2wWJdRysvqu+AYlT96tcSMOwlHHRh3z7+bRr5LbVQ+WjYs
XJ1Ax7r7FJJ31Nz5j/G21vd4j2/d8ugLGtJsDQJWbxIKitCTOfT8HPfdNU7yESHR
hHgDVzZae3j+FozXAlgswDuabtmvGG6LkWyJc8hn9PSXOaaiM+kcXZe+0QKBgEKg
+Zw58rqW2KzIljWTIRVRmqCLsNCeAje8MFyrqrUTbvyALG/ukXIDbcz6rsHi+xZ6
MLJkEbYaN1HQdS58I1nygYm8K4HEBzLRvdVS9zkPQMlW+e2pPQnYbqVZtZpczzqH
d4vBNd067uoXhSnEITe8gXr2IXqmh0LeojQJUuUhAoGATtX3Aod0bgKMJBD1WEeQ
EmKamafCcntLl4sS3CGsS7MxWqhOQmTaDa4W2eu5k+jmjNnoWgzxGeEG4mEAw9ey
3kCeTbKHn7bgLT8euieJeADQR74zL+P9D6nKHEdNapQO9Kf/dZf0G+3pynL79XrF
fMn8FEprhBtt7nYgRKXK29A=
-----END PRIVATE KEY-----"""
PUB = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuKoLnES+n7tdxV3ZSgxB
Lilv8ydS9CgZSygGbaN+Czd3+9+wL6RWeNaRRGLZ9hGipSij1gwylxUH/j1xEmnh
EY1F7WQ5BVlOZNTHZA1PZjXTfwCe7oG3RS1P3cTljhJDdXcrMsC8mUns+JVRiO5S
qPB8sQJaGvUngNxWx63QJ1HHiL9lvEkSczahLF0BFXflBAFDvNOhgnBKseDyusob
FdrioHngwzOrPmF1KEu3uuCeq+lGCzs1ItShwDuvVNU3UEKHTMH18r7/6UlnY+/D
bmIo+pUTcTfYsn/kNjXC8wBkyYDpEV1FXVbM3UTC1gavOJl5opL6OnriaMLIoOBv
JQIDAQAB
-----END PUBLIC KEY-----"""


def _reload_with(env):
    for k, v in env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    importlib.reload(security)


def test_rs256_sign_verify_en_jwks():
    orig = {k: os.environ.get(k) for k in ("JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY")}
    try:
        _reload_with({"JWT_PRIVATE_KEY": PRIV, "JWT_PUBLIC_KEY": PUB})
        assert security.USE_RS256 is True
        tok = security.create_access_token({"sub": "u1", "role": "ORG_USER", "apps": ["kikv-validator"]})
        # header is RS256
        from jose import jwt as _jwt
        assert _jwt.get_unverified_header(tok)["alg"] == "RS256"
        # decode via publieke sleutel werkt + iss-claim aanwezig
        payload = security.decode_access_token(tok)
        assert payload["sub"] == "u1"
        assert payload["apps"] == ["kikv-validator"]
        assert payload["iss"] == "suresync-id"
        # JWKS bevat 1 sleutel met kid
        jwks = security.get_jwks()
        assert len(jwks["keys"]) == 1
        assert jwks["keys"][0]["kid"] == "suresync-id-1"
        assert jwks["keys"][0]["kty"] == "RSA"
    finally:
        _reload_with(orig)


def test_hs256_default_blijft_werken():
    # Zonder RSA-sleutels: HS256, en token decodeert nog steeds.
    assert security.USE_RS256 is False
    tok = security.create_access_token({"sub": "u2"})
    from jose import jwt as _jwt
    assert _jwt.get_unverified_header(tok)["alg"] == "HS256"
    assert security.decode_access_token(tok)["sub"] == "u2"
