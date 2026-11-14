import threading
import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, make_location, make_product, ok, receive

D1, D2 = "2026-11-20", "2026-11-27"


def _milk(client):
    return make_product(client, variants=[{"package_quantity": 1, "package_unit": "l"}])


def test_ac001_receive_three_packs(member_client, admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    res = receive(
        member_client, milch, kuehl,
        [{"quantity": 3, "expiry_type": "best_before", "expiry_date": D2}],
        variant_id=milch["variants"][0]["id"],
    )  # fmt: skip
    assert res["received_quantity"] == 3000
    assert res["product"]["stock_quantity"] == 3000
    [item] = res["stock_items"]
    assert (item["quantity"], item["expiry_date"], item["location_path"]) == (
        3000,
        D2,
        "Kühlschrank",
    )


def test_stk003_different_dates_are_separate_positions(admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    res = receive(
        admin_client, milch, kuehl,
        [
            {"quantity": 1, "expiry_type": "best_before", "expiry_date": D1},
            {"quantity": 2, "expiry_type": "best_before", "expiry_date": D2},
        ],
        variant_id=milch["variants"][0]["id"],
    )  # fmt: skip
    assert sorted(i["quantity"] for i in res["stock_items"]) == [1000, 2000]
    stock = ok(admin_client.get("/api/v1/stock", params={"sort": "expiry"}))
    assert [i["expiry_date"] for i in stock["items"]] == [D1, D2]


def test_stk006_identical_receipt_is_added_to_position(admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    line = [{"quantity": 1, "expiry_type": "best_before", "expiry_date": D1}]
    vid = milch["variants"][0]["id"]
    first = receive(admin_client, milch, kuehl, line, variant_id=vid)
    second = receive(admin_client, milch, kuehl, line, variant_id=vid)
    assert first["stock_items"][0]["id"] == second["stock_items"][0]["id"]
    assert second["stock_items"][0]["quantity"] == 2000
    assert ok(admin_client.get("/api/v1/stock"))["total"] == 1


def test_ac013_duplicate_request_books_once(admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    key = str(uuid.uuid4())
    body = {
        "product_id": milch["id"],
        "variant_id": milch["variants"][0]["id"],
        "location_id": kuehl["id"],
        "lines": [{"quantity": 2}],
    }
    r1 = admin_client.post("/api/v1/stock/receipts", json=body, headers={"Idempotency-Key": key})
    r2 = admin_client.post("/api/v1/stock/receipts", json=body, headers={"Idempotency-Key": key})
    assert r1.status_code == r2.status_code == 201
    assert r2.headers["idempotent-replayed"] == "true"
    assert r1.json() == r2.json()
    assert ok(admin_client.get(f"/api/v1/products/{milch['id']}"))["stock_quantity"] == 2000

    # gleicher Schlüssel, anderer Inhalt → abgewiesen
    body["lines"] = [{"quantity": 5}]
    r3 = admin_client.post("/api/v1/stock/receipts", json=body, headers={"Idempotency-Key": key})
    assert r3.status_code == 422
    assert r3.json()["error"]["code"] == "idempotency_key_reused"


def test_idempotency_key_required(admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    r = admin_client.post(
        "/api/v1/stock/receipts",
        json={
            "product_id": milch["id"],
            "location_id": kuehl["id"],
            "lines": [{"quantity": 1, "unit": "base"}],
        },
    )
    assert r.json()["error"]["code"] == "idempotency_key_missing"


def test_failed_booking_can_be_retried_with_same_key(admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    key = str(uuid.uuid4())
    # Packungsangabe ohne Variante → fachlicher Fehler, nichts wird gespeichert
    r = admin_client.post(
        "/api/v1/stock/receipts",
        json={"product_id": milch["id"], "location_id": kuehl["id"], "lines": [{"quantity": 1}]},
        headers={"Idempotency-Key": key},
    )
    assert r.json()["error"]["code"] == "variant_required"
    res = receive(
        admin_client,
        milch,
        kuehl,
        [{"quantity": 1}],
        variant_id=milch["variants"][0]["id"],
        key=key,
    )
    assert res["received_quantity"] == 1000


def test_concurrent_duplicates_book_once(app, admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    key = str(uuid.uuid4())
    body = {
        "product_id": milch["id"],
        "variant_id": milch["variants"][0]["id"],
        "location_id": kuehl["id"],
        "lines": [{"quantity": 1}],
    }
    results = []

    def send():
        c = TestClient(app)
        c.post("/api/v1/auth/login", json={"username": "admin", "password": PASSWORD})
        results.append(
            c.post("/api/v1/stock/receipts", json=body, headers={"Idempotency-Key": key})
        )

    threads = [threading.Thread(target=send) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(r.status_code == 201 for r in results), [r.text for r in results]
    assert ok(admin_client.get(f"/api/v1/products/{milch['id']}"))["stock_quantity"] == 1000


def test_concurrent_receipts_merge_without_lost_updates(app, admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    vid = milch["variants"][0]["id"]

    def send():
        c = TestClient(app)
        c.post("/api/v1/auth/login", json={"username": "admin", "password": PASSWORD})
        receive(c, milch, kuehl, [{"quantity": 1}], variant_id=vid)

    threads = [threading.Thread(target=send) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stock = ok(admin_client.get("/api/v1/stock"))
    assert stock["total"] == 1
    assert stock["items"][0]["quantity"] == 8000


def test_expiry_validation(admin_client):
    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    r = admin_client.post(
        "/api/v1/stock/receipts",
        json={
            "product_id": milch["id"],
            "location_id": kuehl["id"],
            "lines": [{"quantity": 1, "unit": "base", "expiry_type": "use_by"}],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 422
    # Fehlendes Datum verhindert die Einlagerung nicht (FR-STK-004)
    res = receive(
        admin_client, milch, kuehl, [{"quantity": 1, "unit": "base", "expiry_type": "unknown"}]
    )
    assert res["stock_items"][0]["expiry_type"] == "unknown"


def test_fractional_pieces_allowed(admin_client):
    gurke = make_product(admin_client, name="Gurke", base_unit="piece")
    loc = make_location(admin_client, "Kühlschrank")
    res = receive(admin_client, gurke, loc, [{"quantity": 0.5, "unit": "base"}])
    assert res["received_quantity"] == 0.5


def test_receipt_defaults(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    vorrat = make_location(admin_client, "Vorrat")
    milch = make_product(
        admin_client,
        variants=[
            {"package_quantity": 1, "package_unit": "l", "is_default": True},
            {"package_quantity": 500, "package_unit": "ml"},
        ],
        default_shelf_life_days=10,
    )
    d = ok(admin_client.get("/api/v1/stock/receipt-defaults", params={"product_id": milch["id"]}))
    default_variant = next(v["id"] for v in milch["variants"] if v["is_default"])
    assert d["variant_id"] == default_variant
    assert d["location_id"] is None
    assert d["expiry_date"] == (date.today() + timedelta(days=10)).isoformat()

    small = next(v["id"] for v in milch["variants"] if not v["is_default"])
    receive(admin_client, milch, vorrat, [{"quantity": 1}], variant_id=small)
    d = ok(admin_client.get("/api/v1/stock/receipt-defaults", params={"product_id": milch["id"]}))
    assert (d["variant_id"], d["location_id"]) == (small, vorrat["id"])

    ok(
        admin_client.patch(
            f"/api/v1/products/{milch['id']}", json={"default_location_id": kuehl["id"]}
        )
    )
    d = ok(admin_client.get("/api/v1/stock/receipt-defaults", params={"product_id": milch["id"]}))
    assert d["location_id"] == kuehl["id"]


def test_movement_is_recorded(admin_client, db):
    from sqlalchemy import select

    from app.modules.stock.models import StockMovement

    milch = _milk(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    receive(admin_client, milch, kuehl, [{"quantity": 3}], variant_id=milch["variants"][0]["id"])
    [m] = db.scalars(select(StockMovement)).all()
    assert (m.movement_type, float(m.quantity), float(m.quantity_delta)) == ("receipt", 3000, 3000)
    assert str(m.target_location_id) == kuehl["id"]
