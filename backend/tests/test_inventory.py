"""Inventur (FR-INV-001…009, DEC-019)."""

import uuid
from datetime import date, timedelta

from tests.conftest import make_location, make_product, ok, receive

URL = "/api/v1/inventories"
D1 = (date.today() + timedelta(days=30)).isoformat()
D2 = (date.today() + timedelta(days=60)).isoformat()


def bb(qty, expiry=D1):
    return {"quantity": qty, "unit": "base", "expiry_type": "best_before", "expiry_date": expiry}


def setup_pantry(client):
    """Vorratsschrank mit Regal; Zucker mit zwei MHD (FR-INV-009), Nudeln im Regal."""
    schrank = make_location(client, "Vorratsschrank")
    regal = make_location(client, "Regal", schrank["id"])
    kuehl = make_location(client, "Kühlschrank")
    zucker = make_product(client, "Zucker", base_unit="g")
    nudeln = make_product(client, "Nudeln", base_unit="g")
    milch = make_product(client, "Milch", base_unit="ml")
    receive(client, zucker, schrank, [bb(1000, D1), bb(1000, D2)])
    receive(client, nudeln, regal, [bb(1500)])
    receive(client, milch, kuehl, [bb(2000)])
    return {
        "schrank": schrank,
        "regal": regal,
        "kuehl": kuehl,
        "zucker": zucker,
        "nudeln": nudeln,
        "milch": milch,
    }


def start(client, location=None, sub=True, status=201):
    body = {"location_id": location["id"] if location else None, "include_sublocations": sub}
    return ok(client.post(URL, json=body), status)


def count(client, inv, item, qty, status=200):
    r = client.patch(f"{URL}/{inv['id']}/items/{item['id']}", json={"counted_quantity": qty})
    return ok(r, status)


def by_product(inv):
    return sorted(
        ((i["product_name"], i["expiry_date"], i["expected_quantity"]) for i in inv["items"]),
        key=str,
    )


def consume(client, product, qty):
    ok(
        client.post(
            "/api/v1/stock/consumptions",
            json={"product_id": product["id"], "quantity": qty},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        ),
        201,
    )


def stock_of(client, product):
    return ok(client.get(f"/api/v1/products/{product['id']}"))["stock_quantity"]


# ------------------------------------------------------------------ Start und Umfang


def test_start_scopes(admin_client):
    """FR-INV-001/002/009: einzelner Platz, mit Unterplätzen, gesamter Haushalt;
    je Haltbarkeitsdatum eine eigene Zeile."""
    s = setup_pantry(admin_client)
    only = start(admin_client, s["schrank"], sub=False)
    assert by_product(only) == [("Zucker", D1, 1000), ("Zucker", D2, 1000)]
    assert only["scope_label"] == "Vorratsschrank"
    ok(admin_client.post(f"{URL}/{only['id']}/cancel"))

    with_sub = start(admin_client, s["schrank"])
    assert [i["product_name"] for i in with_sub["items"]] == ["Zucker", "Zucker", "Nudeln"]
    assert with_sub["scope_label"] == "Vorratsschrank (mit Unterlagerplätzen)"
    ok(admin_client.post(f"{URL}/{with_sub['id']}/cancel"))

    whole = start(admin_client)
    assert whole["scope_label"] == "Gesamter Haushalt"
    assert whole["summary"] == {"total": 4, "counted": 0, "differences": 0, "conflicts": 0}


def test_overlapping_inventories_are_rejected(admin_client):
    s = setup_pantry(admin_client)
    start(admin_client, s["schrank"])
    r = admin_client.post(URL, json={"location_id": s["regal"]["id"]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "inventory_overlap"
    assert admin_client.post(URL, json={}).status_code == 409  # Haushalt überschneidet
    start(admin_client, s["kuehl"])  # unabhängiger Lagerplatz geht


def test_permissions(admin_client, member_client, member):
    """Inventur nur für Administratoren und freigegebene Mitglieder (Spez. 3.1)."""
    s = setup_pantry(admin_client)
    r = member_client.post(URL, json={"location_id": s["kuehl"]["id"]})
    assert r.status_code == 403
    inv = start(admin_client, s["kuehl"])
    assert member_client.get(f"{URL}/{inv['id']}").status_code == 200  # Protokoll lesen
    item = inv["items"][0]
    assert (
        member_client.patch(
            f"{URL}/{inv['id']}/items/{item['id']}", json={"counted_quantity": 1}
        ).status_code
        == 403
    )
    ok(admin_client.patch(f"/api/v1/users/{member.id}", json={"can_do_inventory": True}))
    count(member_client, inv, item, 1500)


# ------------------------------------------------------------------ Zählen und Abschluss


def test_count_differences_and_complete(admin_client):
    """FR-INV-002/003/004/007: Differenzen, Korrekturbuchungen, Protokoll."""
    s = setup_pantry(admin_client)
    inv = start(admin_client, s["schrank"])
    items = {(i["product_name"], i["expiry_date"]): i for i in inv["items"]}
    count(admin_client, inv, items[("Zucker", D1)], 500)  # −500
    count(admin_client, inv, items[("Zucker", D2)], 0)  # aufgebraucht
    res = count(admin_client, inv, items[("Nudeln", D1)], 1750)  # +250
    diffs = {(i["product_name"], i["expiry_date"]): i["difference"] for i in res["items"]}
    assert diffs == {("Zucker", D1): -500, ("Zucker", D2): -1000, ("Nudeln", D1): 250}
    assert res["summary"] == {"total": 3, "counted": 3, "differences": 3, "conflicts": 0}

    done = ok(admin_client.post(f"{URL}/{inv['id']}/complete"))
    assert done["status"] == "completed" and done["completed_by_name"] == "Admin"
    assert done["transaction_id"]
    assert {i["applied_delta"] for i in done["items"]} == {-500, -1000, 250}
    assert (stock_of(admin_client, s["zucker"]), stock_of(admin_client, s["nudeln"])) == (500, 1750)

    # Aufgebrauchte Position verschwindet aus dem Bestand; Historie zeigt Korrekturen
    zucker = ok(admin_client.get("/api/v1/stock", params={"product_id": s["zucker"]["id"]}))
    assert [i["expiry_date"] for i in zucker["items"]] == [D1]
    moves = ok(
        admin_client.get(
            "/api/v1/stock/movements", params={"transaction_id": done["transaction_id"]}
        )
    )["items"]
    assert sorted(m["quantity_delta"] for m in moves) == [-1000, -500, 250]
    assert {m["movement_type"] for m in moves} == {"inventory_correction"}

    # Protokoll (FR-INV-007)
    [entry] = ok(admin_client.get(URL))
    assert (entry["status"], entry["summary"]["differences"], entry["items"]) == (
        "completed",
        3,
        None,
    )
    # Abgeschlossene Inventur ist unveränderlich
    r = admin_client.post(f"{URL}/{inv['id']}/complete")
    assert r.status_code == 422 and r.json()["error"]["code"] == "inventory_closed"
    # Korrekturen werden nicht storniert, sondern durch eine neue Inventur berichtigt
    r = admin_client.post(
        f"/api/v1/stock/transactions/{done['transaction_id']}/reversal",
        json={},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "reversal_not_supported"


def test_incomplete_inventory_and_accept_remaining(admin_client):
    s = setup_pantry(admin_client)
    inv = start(admin_client, s["schrank"])
    count(admin_client, inv, inv["items"][0], 900)
    r = admin_client.post(f"{URL}/{inv['id']}/complete")
    assert r.status_code == 422 and r.json()["error"]["code"] == "inventory_incomplete"
    rest = ok(admin_client.post(f"{URL}/{inv['id']}/accept-remaining"))
    assert rest["summary"]["counted"] == 3
    done = ok(admin_client.post(f"{URL}/{inv['id']}/complete"))
    assert done["summary"]["differences"] == 1


def test_interrupt_and_resume(admin_client):
    """FR-INV-006: Zählstände bleiben gespeichert."""
    s = setup_pantry(admin_client)
    inv = start(admin_client, s["kuehl"])
    count(admin_client, inv, inv["items"][0], 1800)
    again = ok(admin_client.get(f"{URL}/{inv['id']}"))
    assert again["items"][0]["counted_quantity"] == 1800 and again["status"] == "open"
    reset = count(admin_client, inv, inv["items"][0], None)
    assert reset["items"][0]["counted_quantity"] is None


def test_cancel_books_nothing(admin_client):
    s = setup_pantry(admin_client)
    inv = start(admin_client, s["kuehl"])
    count(admin_client, inv, inv["items"][0], 0)
    ok(admin_client.post(f"{URL}/{inv['id']}/cancel"))
    assert stock_of(admin_client, s["milch"]) == 2000
    r = admin_client.patch(
        f"{URL}/{inv['id']}/items/{inv['items'][0]['id']}", json={"counted_quantity": 1}
    )
    assert r.status_code == 422


# ------------------------------------------------------------------ Konflikte (FR-INV-008)


def test_booking_during_inventory_is_detected(admin_client):
    s = setup_pantry(admin_client)
    inv = start(admin_client, s["regal"])
    [item] = inv["items"]
    count(admin_client, inv, item, 1500)
    consume(admin_client, s["nudeln"], 500)  # zwischenzeitliche Entnahme

    seen = ok(admin_client.get(f"{URL}/{inv['id']}"))["items"][0]
    assert seen["conflict_reason"] == "changed"
    assert (seen["conflict"], seen["expected_quantity"], seen["current_quantity"]) == (
        True,
        1500,
        1000,
    )
    r = admin_client.post(f"{URL}/{inv['id']}/complete")
    assert r.status_code == 409 and r.json()["error"]["code"] == "inventory_conflict"
    assert [d["product_name"] for d in r.json()["error"]["details"]] == ["Nudeln"]
    assert stock_of(admin_client, s["nudeln"]) == 1000  # nichts überschrieben

    # Erneut zählen = erneut geprüft; neues Soll ist der aktuelle Buchbestand
    rechecked = count(admin_client, inv, item, 900)["items"][0]
    assert (rechecked["conflict"], rechecked["expected_quantity"], rechecked["difference"]) == (
        False,
        1000,
        -100,
    )
    ok(admin_client.post(f"{URL}/{inv['id']}/complete"))
    assert stock_of(admin_client, s["nudeln"]) == 900


def test_new_position_during_inventory_must_be_counted(admin_client):
    s = setup_pantry(admin_client)
    inv = start(admin_client, s["regal"])
    count(admin_client, inv, inv["items"][0], 1500)
    receive(admin_client, s["nudeln"], s["regal"], [bb(500, D2)])  # neue Position

    r = admin_client.post(f"{URL}/{inv['id']}/complete")
    assert r.status_code == 409
    assert "neu eingelagert" in r.json()["error"]["details"][0]["reason"]
    # Die neue Position wurde der Liste dauerhaft hinzugefügt
    items = ok(admin_client.get(f"{URL}/{inv['id']}"))["items"]
    new = next(i for i in items if i["expiry_date"] == D2)
    assert (new["conflict"], new["conflict_reason"], new["counted_quantity"]) == (
        True,
        "new",
        None,
    )
    # „Rest übernehmen“ darf sie nicht stillschweigend bestätigen
    ok(admin_client.post(f"{URL}/{inv['id']}/accept-remaining"))
    assert admin_client.post(f"{URL}/{inv['id']}/complete").status_code == 409
    count(admin_client, inv, new, 500)
    ok(admin_client.post(f"{URL}/{inv['id']}/complete"))
    assert stock_of(admin_client, s["nudeln"]) == 2000


# ------------------------------------------------------------------ Ergänzen (FR-INV-005)


def test_add_unrecorded_food(admin_client):
    s = setup_pantry(admin_client)
    mehl = make_product(admin_client, "Mehl", base_unit="g")
    inv = start(admin_client, s["schrank"])
    body = {"product_id": mehl["id"], "location_id": s["regal"]["id"], "counted_quantity": 2500}
    added = ok(admin_client.post(f"{URL}/{inv['id']}/items", json=body), 201)
    new = next(i for i in added["items"] if i["product_name"] == "Mehl")
    assert (new["is_new"], new["expected_quantity"], new["difference"]) == (True, 0, 2500)
    assert stock_of(admin_client, mehl) == 0  # erst nach Bestätigung

    outside = {**body, "location_id": s["kuehl"]["id"]}
    r = admin_client.post(f"{URL}/{inv['id']}/items", json=outside)
    assert r.status_code == 422 and r.json()["error"]["code"] == "location_not_in_inventory"
    existing = next(i for i in added["items"] if not i["is_new"])
    r = admin_client.delete(f"{URL}/{inv['id']}/items/{existing['id']}")
    assert r.status_code == 422

    ok(admin_client.post(f"{URL}/{inv['id']}/accept-remaining"))
    ok(admin_client.post(f"{URL}/{inv['id']}/complete"))
    assert stock_of(admin_client, mehl) == 2500
    [pos] = ok(admin_client.get("/api/v1/stock", params={"product_id": mehl["id"]}))["items"]
    assert (pos["location_path"], pos["expiry_type"]) == ("Vorratsschrank › Regal", "unknown")


def test_added_item_can_be_removed(admin_client):
    s = setup_pantry(admin_client)
    mehl = make_product(admin_client, "Mehl", base_unit="g")
    inv = start(admin_client, s["kuehl"])
    body = {"product_id": mehl["id"], "location_id": s["kuehl"]["id"], "counted_quantity": 1}
    added = ok(admin_client.post(f"{URL}/{inv['id']}/items", json=body), 201)
    new = next(i for i in added["items"] if i["is_new"])
    after = ok(admin_client.delete(f"{URL}/{inv['id']}/items/{new['id']}"))
    assert all(not i["is_new"] for i in after["items"])


def test_inventories_are_household_scoped(admin_client, app, db):
    from app.modules.users.models import Household, Role
    from app.modules.users.schemas import UserCreate
    from app.modules.users.service import create_user
    from tests.conftest import PASSWORD, _login

    s = setup_pantry(admin_client)
    inv = start(admin_client, s["kuehl"])
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
    assert nachbar.get(f"{URL}/{inv['id']}").status_code == 404
    assert nachbar.post(f"{URL}/{inv['id']}/complete").status_code == 404
    assert ok(nachbar.get(URL)) == []
