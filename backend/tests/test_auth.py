from tests.conftest import PASSWORD


def test_health(anon):
    assert anon.get("/api/v1/health").json() == {"status": "ok"}


def test_login_sets_httponly_cookie_and_me_works(anon, admin):
    r = anon.post("/api/v1/auth/login", json={"username": "Admin", "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["role"] == "admin"
    assert "access_token" not in r.json()
    assert "httponly" in r.headers["set-cookie"].lower()
    assert anon.get("/api/v1/auth/me").json()["username"] == "admin"


def test_wrong_password_uses_uniform_error(anon, admin):
    r = anon.post("/api/v1/auth/login", json={"username": "admin", "password": "falsch"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_login"
    r = anon.post("/api/v1/auth/login", json={"username": "gibtsnicht", "password": "x"})
    assert r.json()["error"]["code"] == "invalid_login"


def test_protected_endpoint_requires_login(anon):
    r = anon.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"


def test_password_change_invalidates_other_sessions(app, admin_client):
    from fastapi.testclient import TestClient

    other = TestClient(app)
    other.post("/api/v1/auth/login", json={"username": "admin", "password": PASSWORD})
    assert other.get("/api/v1/auth/me").status_code == 200

    r = admin_client.post(
        "/api/v1/auth/password",
        json={"current_password": PASSWORD, "new_password": "neues-passwort"},
    )
    assert r.status_code == 204
    assert admin_client.get("/api/v1/auth/me").status_code == 200
    assert other.get("/api/v1/auth/me").status_code == 401


def test_logout(admin_client):
    admin_client.post("/api/v1/auth/logout")
    assert admin_client.get("/api/v1/auth/me").status_code == 401
