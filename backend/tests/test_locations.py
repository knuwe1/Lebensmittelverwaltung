from tests.conftest import make_location, make_product, ok, receive


def test_hierarchy_paths_and_unique_names(admin_client):
    kueche = make_location(admin_client, "Küche")
    kuehl = make_location(admin_client, "Kühlschrank", kueche["id"])
    fach = make_location(admin_client, "Oberes Fach", kuehl["id"])
    assert fach["path"] == "Küche › Kühlschrank › Oberes Fach"

    # gleicher Name unter anderem Elternteil erlaubt, unter demselben nicht
    keller = make_location(admin_client, "Keller")
    make_location(admin_client, "Kühlschrank", keller["id"])
    r = admin_client.post(
        "/api/v1/locations", json={"name": "Kühlschrank", "parent_id": kueche["id"]}
    )
    assert r.status_code == 409
    # auch auf oberster Ebene eindeutig
    assert admin_client.post("/api/v1/locations", json={"name": "Küche"}).status_code == 409


def test_member_cannot_manage_locations(member_client):
    assert member_client.post("/api/v1/locations", json={"name": "X"}).status_code == 403


def test_move_and_cycle_protection(admin_client):
    a = make_location(admin_client, "A")
    b = make_location(admin_client, "B", a["id"])
    c = make_location(admin_client, "C", b["id"])
    r = admin_client.patch(f"/api/v1/locations/{a['id']}", json={"parent_id": c["id"]})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "location_cycle"

    moved = ok(admin_client.patch(f"/api/v1/locations/{c['id']}", json={"parent_id": None}))
    assert moved["path"] == "C"
    renamed = ok(admin_client.patch(f"/api/v1/locations/{b['id']}", json={"name": "B neu"}))
    assert renamed["path"] == "A › B neu"


def test_delete_rules(admin_client):
    kueche = make_location(admin_client, "Küche")
    schrank = make_location(admin_client, "Schrank", kueche["id"])
    leer = make_location(admin_client, "Leer")

    # mit Unterlagerplätzen → blockiert
    r = admin_client.delete(f"/api/v1/locations/{kueche['id']}")
    assert r.json()["error"]["code"] == "location_has_children"

    # mit Bestand → blockiert, inkl. Auflistung
    milch = make_product(admin_client)
    receive(admin_client, milch, schrank, [{"quantity": 500, "unit": "base"}])
    r = admin_client.delete(f"/api/v1/locations/{schrank['id']}")
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "location_has_stock"
    assert err["details"][0]["product_name"] == "Milch 3,5 %"

    # ohne Historie → physisch gelöscht
    assert ok(admin_client.delete(f"/api/v1/locations/{leer['id']}")) == {"result": "deleted"}


def test_location_filter_includes_sublocations(admin_client):
    kueche = make_location(admin_client, "Küche")
    kuehl = make_location(admin_client, "Kühlschrank", kueche["id"])
    keller = make_location(admin_client, "Keller")
    milch = make_product(admin_client)
    receive(admin_client, milch, kuehl, [{"quantity": 1000, "unit": "base"}])
    receive(admin_client, milch, keller, [{"quantity": 500, "unit": "base"}])

    stock = ok(admin_client.get("/api/v1/stock", params={"location_id": kueche["id"]}))
    assert stock["total"] == 1
    assert stock["items"][0]["location_path"] == "Küche › Kühlschrank"
    flat = ok(
        admin_client.get(
            "/api/v1/stock",
            params={"location_id": kueche["id"], "include_sublocations": False},
        )
    )
    assert flat["total"] == 0
    found = ok(admin_client.get("/api/v1/products", params={"location_id": keller["id"]}))
    assert [p["name"] for p in found["items"]] == ["Milch 3,5 %"]
