def test_member_cannot_manage_users(member_client):
    assert member_client.get("/api/v1/users").status_code == 403
    r = member_client.post(
        "/api/v1/users",
        json={"username": "x1", "display_name": "X", "password": "12345678"},
    )
    assert r.status_code == 403


def test_admin_creates_user_and_username_is_unique(admin_client):
    payload = {"username": "lisa", "display_name": "Lisa", "password": "12345678"}
    r = admin_client.post("/api/v1/users", json=payload)
    assert r.status_code == 201
    assert r.json()["role"] == "member"
    assert "password_hash" not in r.json()

    r = admin_client.post("/api/v1/users", json={**payload, "username": "LISA"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "username_taken"


def test_last_admin_cannot_be_demoted(admin_client, admin):
    r = admin_client.patch(f"/api/v1/users/{admin.id}", json={"role": "member"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "last_admin"


def test_deactivated_user_loses_access(admin_client, member, member_client):
    r = admin_client.patch(f"/api/v1/users/{member.id}", json={"active": False})
    assert r.status_code == 200
    assert member_client.get("/api/v1/auth/me").status_code == 401


def test_validation_error_format(admin_client):
    r = admin_client.post("/api/v1/users", json={"username": "a", "password": "kurz"})
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation_failed"
    fields = {d["field"] for d in body["details"]}
    assert {"username", "password", "display_name"} <= fields


def test_password_is_hashed(db, admin):
    assert admin.password_hash.startswith("$argon2")
