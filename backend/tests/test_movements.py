import threading
import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, make_location, make_product, ok, receive

D1, D2 = "2027-11-20", "2027-11-27"


def post(client, path, body, status=201, key=None):
    r = client.post(
        f"/api/v1/stock/{path}", json=body, headers={"Idempotency-Key": key or str(uuid.uuid4())}
    )
    assert r.status_code == status, r.text
    return r.json()


def total(client, product):
    return ok(client.get(f"/api/v1/products/{product['id']}"))["stock_quantity"]


def stock(client, **params):
    return ok(client.get("/api/v1/stock", params=params))["items"]


def bbd(qty, d, unit="base"):
    return {"quantity": qty, "unit": unit, "expiry_type": "best_before", "expiry_date": d}


# ------------------------------------------------------------------ Verbrauch


def test_ac004_partial_consumption_and_history(admin_client):
    zucker = make_product(admin_client, name="Zucker", base_unit="g")
    schrank = make_location(admin_client, "Vorratsschrank")
    receive(admin_client, zucker, schrank, [{"quantity": 1000, "unit": "base"}])
    res = post(admin_client, "consumptions", {"product_id": zucker["id"], "quantity": 250})
    assert res["product"]["stock_quantity"] == 750
    hist = ok(admin_client.get("/api/v1/stock/movements", params={"product_id": zucker["id"]}))
    assert [m["movement_type"] for m in hist["items"]] == ["consumption", "receipt"]
    assert hist["items"][0]["quantity_delta"] == -250
    assert hist["items"][0]["source_location_path"] == "Vorratsschrank"
    assert hist["items"][0]["created_by_name"] == "Admin"


def test_ac005_plan_suggests_earliest_and_later_remains(admin_client):
    milch = make_product(admin_client)
    kuehl = make_location(admin_client, "Kühlschrank")
    receive(admin_client, milch, kuehl, [bbd(1000, D2), bbd(1000, D1)])
    plan = ok(
        admin_client.get(
            "/api/v1/stock/consumption-plan", params={"product_id": milch["id"], "quantity": 1000}
        )
    )
    assert plan["sufficient"] is True
    [alloc] = plan["allocations"]
    assert alloc["stock_item"]["expiry_date"] == D1
    post(
        admin_client,
        "consumptions",
        {
            "product_id": milch["id"],
            "allocations": [
                {
                    "stock_item_id": alloc["stock_item"]["id"],
                    "quantity": 1000,
                    "expected_version": alloc["stock_item"]["version"],
                }
            ],
        },
    )
    assert [i["expiry_date"] for i in stock(admin_client)] == [D2]


def test_cns005_server_splits_by_fefo(admin_client):
    p = make_product(admin_client, name="Mehl", base_unit="g")
    loc = make_location(admin_client, "Schrank")
    receive(admin_client, p, loc, [bbd(200, D1), bbd(500, D2)])
    res = post(admin_client, "consumptions", {"product_id": p["id"], "quantity": 350})
    by_date = {i["expiry_date"]: i["quantity"] for i in res["stock_items"]}
    assert by_date == {D1: 0, D2: 350}
    assert [i["quantity"] for i in stock(admin_client)] == [350]


def test_consume_in_packages(admin_client):
    milch = make_product(admin_client, variants=[{"package_quantity": 1, "package_unit": "l"}])
    vid = milch["variants"][0]["id"]
    loc = make_location(admin_client, "Kühlschrank")
    receive(admin_client, milch, loc, [{"quantity": 3}], variant_id=vid)
    post(
        admin_client,
        "consumptions",
        {"product_id": milch["id"], "quantity": 2, "unit": "package", "variant_id": vid},
    )
    assert total(admin_client, milch) == 1000


def test_cns006_cannot_go_negative(admin_client):
    p = make_product(admin_client, name="Eier", base_unit="piece")
    loc = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, loc, [{"quantity": 2, "unit": "base"}])
    err = post(admin_client, "consumptions", {"product_id": p["id"], "quantity": 3}, status=409)
    assert err["error"]["code"] == "insufficient_stock"
    assert err["error"]["details"]["available"] == 2

    item = stock(admin_client)[0]
    err = post(
        admin_client,
        "consumptions",
        {"product_id": p["id"], "allocations": [{"stock_item_id": item["id"], "quantity": 5}]},
        status=409,
    )
    assert err["error"]["code"] == "insufficient_stock"
    assert total(admin_client, p) == 2


def test_expired_use_by_not_available_for_plan(admin_client):
    hack = make_product(admin_client, name="Hackfleisch", base_unit="g")
    loc = make_location(admin_client, "Kühlschrank")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    receive(
        admin_client,
        hack,
        loc,
        [{"quantity": 500, "unit": "base", "expiry_type": "use_by", "expiry_date": yesterday}],
    )
    err = post(
        admin_client, "consumptions", {"product_id": hack["id"], "quantity": 100}, status=409
    )
    assert err["error"]["details"]["available"] == 0


def test_version_conflict_is_detected(admin_client, member_client):
    p = make_product(admin_client, name="Butter", base_unit="g")
    loc = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, loc, [{"quantity": 250, "unit": "base"}])
    item = stock(admin_client)[0]
    post(member_client, "consumptions", {"product_id": p["id"], "quantity": 50})
    err = post(
        admin_client,
        "consumptions",
        {
            "product_id": p["id"],
            "allocations": [
                {"stock_item_id": item["id"], "quantity": 50, "expected_version": item["version"]}
            ],
        },
        status=409,
    )
    assert err["error"]["code"] == "stock_changed"
    assert total(admin_client, p) == 200


def test_ac012_concurrent_consumption_of_last_piece(app, admin_client):
    p = make_product(admin_client, name="Joghurt", base_unit="piece")
    loc = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, loc, [{"quantity": 1, "unit": "base"}])
    results = []

    def take():
        c = TestClient(app)
        c.post("/api/v1/auth/login", json={"username": "admin", "password": PASSWORD})
        results.append(
            c.post(
                "/api/v1/stock/consumptions",
                json={"product_id": p["id"], "quantity": 1},
                headers={"Idempotency-Key": str(uuid.uuid4())},
            )
        )

    threads = [threading.Thread(target=take) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409, 409, 409]
    assert all(
        r.json()["error"]["code"] == "insufficient_stock" for r in results if r.status_code == 409
    )
    assert total(admin_client, p) == 0


# ------------------------------------------------------------------ Entsorgung


def test_cns008_disposal_with_reason(admin_client):
    p = make_product(admin_client, name="Salat", base_unit="piece")
    loc = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, loc, [{"quantity": 2, "unit": "base"}])
    item = stock(admin_client)[0]
    post(
        admin_client,
        "disposals",
        {
            "product_id": p["id"],
            "reason": "spoiled",
            "allocations": [{"stock_item_id": item["id"], "quantity": 2}],
        },
    )
    assert total(admin_client, p) == 0
    [m] = ok(admin_client.get("/api/v1/stock/movements", params={"movement_type": "disposal"}))[
        "items"
    ]
    assert (m["reason"], m["quantity"]) == ("spoiled", 2)
    assert (
        ok(admin_client.get("/api/v1/stock/movements", params={"movement_type": "consumption"}))[
            "total"
        ]
        == 0
    )


# ------------------------------------------------------------------ Umlagerung


def test_ac009_partial_transfer_keeps_total_and_expiry(admin_client):
    milch = make_product(admin_client)
    vorrat = make_location(admin_client, "Vorratsraum")
    kuehl = make_location(admin_client, "Kühlschrank")
    receive(admin_client, milch, vorrat, [bbd(6000, D1)])
    item = stock(admin_client)[0]
    res = post(
        admin_client,
        "transfers",
        {
            "stock_item_id": item["id"],
            "quantity": 3000,
            "target_location_id": kuehl["id"],
            "expected_version": item["version"],
        },
    )
    assert res["product"]["stock_quantity"] == 6000
    by_loc = {i["location_path"]: (i["quantity"], i["expiry_date"]) for i in stock(admin_client)}
    assert by_loc == {"Vorratsraum": (3000, D1), "Kühlschrank": (3000, D1)}
    moves = ok(
        admin_client.get(
            "/api/v1/stock/movements", params={"transaction_id": res["transaction_id"]}
        )
    )
    assert sorted(m["movement_type"] for m in moves["items"]) == ["transfer_in", "transfer_out"]


def test_whole_transfer_moves_position_and_merges(admin_client):
    milch = make_product(admin_client)
    a = make_location(admin_client, "A")
    b = make_location(admin_client, "B")
    receive(admin_client, milch, a, [bbd(1000, D1)])
    item = stock(admin_client)[0]
    post(
        admin_client,
        "transfers",
        {"stock_item_id": item["id"], "quantity": 1000, "target_location_id": b["id"]},
    )
    [moved] = stock(admin_client)
    assert (moved["id"], moved["location_path"]) == (item["id"], "B")

    # gleiche Merkmale am Ziel → zusammengeführt
    receive(admin_client, milch, a, [bbd(500, D1)])
    src = next(i for i in stock(admin_client) if i["location_path"] == "A")
    post(
        admin_client,
        "transfers",
        {"stock_item_id": src["id"], "quantity": 500, "target_location_id": b["id"]},
    )
    [merged] = stock(admin_client)
    assert merged["quantity"] == 1500


def test_transfer_validation(admin_client):
    milch = make_product(admin_client)
    a = make_location(admin_client, "A")
    receive(admin_client, milch, a, [bbd(1000, D1)])
    item = stock(admin_client)[0]
    err = post(
        admin_client,
        "transfers",
        {"stock_item_id": item["id"], "quantity": 100, "target_location_id": a["id"]},
        status=422,
    )
    assert err["error"]["code"] == "same_location"
    b = make_location(admin_client, "B")
    err = post(
        admin_client,
        "transfers",
        {"stock_item_id": item["id"], "quantity": 2000, "target_location_id": b["id"]},
        status=409,
    )
    assert err["error"]["code"] == "insufficient_stock"


# ------------------------------------------------------------------ Storno


def test_reverse_consumption_restores_stock(admin_client):
    p = make_product(admin_client, name="Reis", base_unit="g")
    loc = make_location(admin_client, "Schrank")
    receive(admin_client, p, loc, [{"quantity": 1000, "unit": "base"}])
    res = post(admin_client, "consumptions", {"product_id": p["id"], "quantity": 1000})
    assert total(admin_client, p) == 0
    rev = post(
        admin_client, f"transactions/{res['transaction_id']}/reversal", {"comment": "Versehen"}
    )
    assert rev["product"]["stock_quantity"] == 1000
    hist = ok(admin_client.get("/api/v1/stock/movements", params={"product_id": p["id"]}))["items"]
    assert [m["movement_type"] for m in hist] == ["reversal", "consumption", "receipt"]
    assert hist[1]["reversed"] is True
    assert hist[0]["reverses_movement_id"] == hist[1]["id"]
    # Originalbewegung unverändert
    assert hist[1]["quantity_delta"] == -1000

    err = post(admin_client, f"transactions/{res['transaction_id']}/reversal", {}, status=409)
    assert err["error"]["code"] == "already_reversed"
    err = post(admin_client, f"transactions/{rev['transaction_id']}/reversal", {}, status=422)
    assert err["error"]["code"] == "reversal_of_reversal"


def test_reverse_receipt_blocked_when_stock_used(admin_client):
    p = make_product(admin_client, name="Nudeln", base_unit="g")
    loc = make_location(admin_client, "Schrank")
    rec = receive(admin_client, p, loc, [{"quantity": 500, "unit": "base"}])
    post(admin_client, "consumptions", {"product_id": p["id"], "quantity": 200})
    err = post(admin_client, f"transactions/{rec['transaction_id']}/reversal", {}, status=409)
    assert err["error"]["code"] == "reversal_not_possible"
    assert total(admin_client, p) == 300


def test_reverse_whole_transfer_moves_back(admin_client):
    milch = make_product(admin_client)
    a = make_location(admin_client, "A")
    b = make_location(admin_client, "B")
    receive(admin_client, milch, a, [bbd(1000, D1)])
    item = stock(admin_client)[0]
    res = post(
        admin_client,
        "transfers",
        {"stock_item_id": item["id"], "quantity": 1000, "target_location_id": b["id"]},
    )
    post(admin_client, f"transactions/{res['transaction_id']}/reversal", {})
    [back] = stock(admin_client)
    assert (back["location_path"], back["quantity"]) == ("A", 1000)


def test_reverse_partial_transfer(admin_client):
    milch = make_product(admin_client)
    a = make_location(admin_client, "A")
    b = make_location(admin_client, "B")
    receive(admin_client, milch, a, [bbd(1000, D1)])
    item = stock(admin_client)[0]
    res = post(
        admin_client,
        "transfers",
        {"stock_item_id": item["id"], "quantity": 400, "target_location_id": b["id"]},
    )
    post(admin_client, f"transactions/{res['transaction_id']}/reversal", {})
    assert [(i["location_path"], i["quantity"]) for i in stock(admin_client)] == [("A", 1000)]


# ------------------------------------------------------------------ Sonstiges


def test_location_with_history_is_deactivated(admin_client):
    p = make_product(admin_client, name="Salz", base_unit="g")
    loc = make_location(admin_client, "Alt")
    receive(admin_client, p, loc, [{"quantity": 100, "unit": "base"}])
    post(admin_client, "consumptions", {"product_id": p["id"], "quantity": 100})
    assert ok(admin_client.delete(f"/api/v1/locations/{loc['id']}")) == {"result": "deactivated"}
    hist = ok(admin_client.get("/api/v1/stock/movements"))["items"]
    assert all(m["source_location_path"] in (None, "Alt") for m in hist)


def test_recent_products(admin_client, member_client):
    a = make_product(admin_client, name="Apfel", base_unit="piece")
    b = make_product(admin_client, name="Birne", base_unit="piece")
    loc = make_location(admin_client, "Korb")
    receive(admin_client, a, loc, [{"quantity": 5, "unit": "base"}])
    receive(admin_client, b, loc, [{"quantity": 1, "unit": "base"}])
    post(member_client, "consumptions", {"product_id": a["id"], "quantity": 1})
    post(member_client, "consumptions", {"product_id": b["id"], "quantity": 1})
    recent = ok(member_client.get("/api/v1/stock/recent-products"))
    assert [p["name"] for p in recent] == ["Apfel"]  # Birne hat keinen Bestand mehr
    assert ok(admin_client.get("/api/v1/stock/recent-products")) == []


def test_duplicate_consumption_request_books_once(admin_client):
    p = make_product(admin_client, name="Kaffee", base_unit="g")
    loc = make_location(admin_client, "Schrank")
    receive(admin_client, p, loc, [{"quantity": 500, "unit": "base"}])
    key = str(uuid.uuid4())
    body = {"product_id": p["id"], "quantity": 100}
    post(admin_client, "consumptions", body, key=key)
    post(admin_client, "consumptions", body, key=key)
    assert total(admin_client, p) == 400
