"""Einkaufsliste (FR-SHP-005…010, BR-007, BR-008, BR-020, DEC-018)."""

import uuid
from datetime import date, timedelta

from tests.conftest import make_location, make_product, ok, receive

URL = "/api/v1/shopping-list"


def bb(qty, days=30, unit="base"):
    expiry = (date.today() + timedelta(days=days)).isoformat()
    return {"quantity": qty, "unit": unit, "expiry_type": "best_before", "expiry_date": expiry}


def milk(client, **extra):
    """Milch in 1-l-Packungen (Standardvariante), Mindestbestand 2 l, Ziel 6 l."""
    return make_product(
        client,
        "Milch",
        variants=[{"package_quantity": 1, "package_unit": "l", "is_default": True}],
        minimum_stock=2000,
        target_stock=6000,
        **extra,
    )


def refresh(client):
    return ok(client.post(f"{URL}/refresh"))


def items(client):
    return {i["name"]: i for i in ok(client.get(URL))["items"]}


def test_list_is_created_once_and_shared(admin_client, member_client):
    a = ok(admin_client.get(URL))
    b = ok(member_client.get(URL))
    assert a["id"] == b["id"]
    assert a["items"] == []


def test_refresh_suggests_needs_and_optional_items(admin_client):
    """FR-SHP-005/006: Bedarf mit Menge Ziel − Bestand, „nahe“ als optional."""
    kuehl = make_location(admin_client, "Kühlschrank")
    m = milk(admin_client)
    receive(admin_client, m, kuehl, [bb(1000)])  # 1 l < 2 l → Bedarf
    butter = make_product(admin_client, "Butter", base_unit="g", minimum_stock=250)
    receive(admin_client, butter, kuehl, [bb(300)])  # 300 ≤ 312,5 → nahe
    voll = make_product(admin_client, "Reis", base_unit="g", minimum_stock=500)
    receive(admin_client, voll, kuehl, [bb(5000)])
    make_product(admin_client, "Ohne Überwachung")

    res = refresh(admin_client)
    assert (res["added"], res["updated"], res["removed"]) == (2, 0, 0)
    got = {i["name"]: i for i in res["list"]["items"]}
    assert set(got) == {"Milch", "Butter"}

    milch = got["Milch"]
    assert (milch["origin"], milch["optional"], milch["status"]) == ("auto", False, "open")
    assert (milch["suggested_quantity"], milch["quantity"], milch["packages"]) == (5000, 5000, 5)
    assert (milch["available_quantity"], milch["minimum_stock"], milch["target_stock"]) == (
        1000,
        2000,
        6000,
    )
    assert milch["level_status"] == "below"
    assert milch["package"]["package_unit"] == "l"

    assert got["Butter"]["optional"] is True
    assert got["Butter"]["suggested_quantity"] is None  # ohne Ziel und Packung: Menge offen


def test_refresh_twice_creates_no_duplicates(admin_client):
    """FR-SHP-010."""
    milk(admin_client)
    assert refresh(admin_client)["added"] == 1
    again = refresh(admin_client)
    assert (again["added"], again["updated"], again["removed"]) == (0, 0, 0)
    assert len(again["list"]["items"]) == 1


def test_refresh_updates_suggestion_and_removes_obsolete_auto_items(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    m = milk(admin_client)
    refresh(admin_client)
    assert items(admin_client)["Milch"]["quantity"] == 6000
    receive(admin_client, m, kuehl, [bb(1000)])
    assert refresh(admin_client)["updated"] == 1
    assert items(admin_client)["Milch"]["quantity"] == 5000
    receive(admin_client, m, kuehl, [bb(5000)])
    assert refresh(admin_client)["removed"] == 1
    assert items(admin_client) == {}


def test_manual_items_survive_refresh_and_block_auto_duplicates(admin_client):
    """FR-SHP-007: Manuelle Positionen werden nie automatisch gelöscht; BR-020."""
    m = milk(admin_client)
    ok(admin_client.post(f"{URL}/items", json={"product_id": m["id"], "quantity": 2000}), 201)
    ok(admin_client.post(f"{URL}/items", json={"name": "Backpapier", "comment": "Rolle"}), 201)
    res = refresh(admin_client)
    assert res["added"] == 0
    got = {i["name"]: i for i in res["list"]["items"]}
    assert (got["Milch"]["origin"], got["Milch"]["quantity"]) == ("manual", 2000)
    assert (got["Backpapier"]["origin"], got["Backpapier"]["comment"]) == ("manual", "Rolle")
    assert got["Backpapier"]["product_id"] is None


def test_manually_adjusted_quantity_is_kept(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    m = milk(admin_client)
    refresh(admin_client)
    item = items(admin_client)["Milch"]
    upd = ok(admin_client.patch(f"{URL}/items/{item['id']}", json={"quantity": 3000}))
    assert (upd["quantity"], upd["quantity_adjusted"], upd["packages"]) == (3000, True, 3)

    receive(admin_client, m, kuehl, [bb(1000)])
    refresh(admin_client)
    item = items(admin_client)["Milch"]
    assert (item["suggested_quantity"], item["quantity"]) == (5000, 3000)

    # Bedarf entfallen: bearbeitete Positionen werden nicht entfernt
    receive(admin_client, m, kuehl, [bb(5000)])
    assert refresh(admin_client)["removed"] == 0
    # Zurück auf den Vorschlag
    reset = ok(admin_client.patch(f"{URL}/items/{item['id']}", json={"quantity": None}))
    assert reset["quantity_adjusted"] is False


def test_accepted_optional_item_stays_accepted(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    butter = make_product(admin_client, "Butter", base_unit="g", minimum_stock=250)
    receive(admin_client, butter, kuehl, [bb(300)])
    refresh(admin_client)
    item = items(admin_client)["Butter"]
    assert item["optional"] is True
    ok(admin_client.patch(f"{URL}/items/{item['id']}", json={"optional": False}))
    refresh(admin_client)
    assert items(admin_client)["Butter"]["optional"] is False


def test_purchased_does_not_change_stock_and_is_not_suggested_again(admin_client, member_client):
    """BR-007: „gekauft“ erhöht den Bestand nicht; FR-SHP-008: Status zentral gespeichert."""
    m = milk(admin_client)
    refresh(admin_client)
    item = items(admin_client)["Milch"]
    res = ok(member_client.patch(f"{URL}/items/{item['id']}", json={"status": "purchased"}))
    assert res["status"] == "purchased" and res["purchased_at"]
    assert ok(admin_client.get(f"/api/v1/products/{m['id']}"))["stock_quantity"] == 0
    assert items(admin_client)["Milch"]["status"] == "purchased"  # für alle sichtbar
    assert refresh(admin_client)["added"] == 0
    reopened = ok(admin_client.patch(f"{URL}/items/{item['id']}", json={"status": "open"}))
    assert (reopened["status"], reopened["purchased_at"]) == ("open", None)


def test_receipt_from_shopping_list_completes_item(admin_client):
    """FR-SHP-009 / BR-008: Erst die Einlagerung erhöht den Bestand und erledigt die Position."""
    kuehl = make_location(admin_client, "Kühlschrank")
    m = milk(admin_client)
    refresh(admin_client)
    item = items(admin_client)["Milch"]
    r = admin_client.post(
        "/api/v1/stock/receipts",
        json={
            "product_id": m["id"],
            "variant_id": m["variants"][0]["id"],
            "location_id": kuehl["id"],
            "lines": [bb(4, unit="package")],
            "shopping_list_item_id": item["id"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert ok(r, 201)["received_quantity"] == 4000
    done = items(admin_client)["Milch"]
    assert (done["status"], done["received_quantity"]) == ("done", 4000)

    # Erneut einlagern über dieselbe Position wird abgelehnt – und bucht nichts
    r = admin_client.post(
        "/api/v1/stock/receipts",
        json={
            "product_id": m["id"],
            "location_id": kuehl["id"],
            "lines": [bb(1000)],
            "shopping_list_item_id": item["id"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "shopping_item_done"
    assert ok(admin_client.get(f"/api/v1/products/{m['id']}"))["stock_quantity"] == 4000

    cleared = ok(admin_client.post(f"{URL}/clear-done"))
    assert cleared["items"] == []


def test_receipt_for_wrong_product_is_rejected_atomically(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    m = milk(admin_client)
    other = make_product(admin_client, "Sahne")
    refresh(admin_client)
    item = items(admin_client)["Milch"]
    r = admin_client.post(
        "/api/v1/stock/receipts",
        json={
            "product_id": other["id"],
            "location_id": kuehl["id"],
            "lines": [bb(200)],
            "shopping_list_item_id": item["id"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "shopping_item_mismatch"
    assert ok(admin_client.get(f"/api/v1/products/{other['id']}"))["stock_quantity"] == 0
    assert ok(admin_client.get(f"/api/v1/products/{m['id']}"))["stock_quantity"] == 0


def test_done_without_receipt_and_reopen_rules(admin_client):
    milk(admin_client)
    refresh(admin_client)
    item = items(admin_client)["Milch"]
    ok(admin_client.patch(f"{URL}/items/{item['id']}", json={"status": "done"}))
    r = admin_client.patch(f"{URL}/items/{item['id']}", json={"status": "open"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "cannot_reopen"
    # Bedarf besteht weiter → neue automatische Position
    assert refresh(admin_client)["added"] == 1


def test_adding_listed_product_reuses_open_item(admin_client):
    m = milk(admin_client)
    refresh(admin_client)
    auto = items(admin_client)["Milch"]
    res = ok(admin_client.post(f"{URL}/items", json={"product_id": m["id"], "quantity": 1000}), 201)
    assert res["id"] == auto["id"]
    assert len(items(admin_client)) == 1


def test_delete_and_validation(admin_client):
    created = ok(admin_client.post(f"{URL}/items", json={"name": "Kerzen"}), 201)
    assert admin_client.delete(f"{URL}/items/{created['id']}").status_code == 204
    assert items(admin_client) == {}
    m = milk(admin_client)
    both = admin_client.post(f"{URL}/items", json={"product_id": m["id"], "name": "x"})
    assert both.status_code == 422
    assert admin_client.post(f"{URL}/items", json={}).status_code == 422
    assert admin_client.post(f"{URL}/items", json={"name": "  "}).status_code == 422


def test_items_are_household_scoped(admin_client, app, db):
    from app.modules.users.models import Household, Role
    from app.modules.users.schemas import UserCreate
    from app.modules.users.service import create_user
    from tests.conftest import PASSWORD, _login

    created = ok(admin_client.post(f"{URL}/items", json={"name": "Kerzen"}), 201)
    other = Household(name="Nachbarn")
    db.add(other)
    db.flush()
    create_user(
        db,
        other.id,
        UserCreate(username="nachbar", display_name="N", password=PASSWORD, role=Role.ADMIN),
    )
    db.commit()
    nachbar = _login(app, "nachbar")
    assert ok(nachbar.get(URL))["items"] == []
    r = nachbar.patch(f"{URL}/items/{created['id']}", json={"status": "purchased"})
    assert r.status_code == 404
    assert nachbar.delete(f"{URL}/items/{created['id']}").status_code == 404


def test_shopping_list_requires_login(anon):
    assert anon.get(URL).status_code == 401
