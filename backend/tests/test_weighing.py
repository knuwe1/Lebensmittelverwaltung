from decimal import Decimal as D

import pytest

from app.core.errors import ValidationFailed
from app.modules.stock.weighing import compute_weighing


def test_single_open_package():
    r = compute_weighing(D(1000), D(750))
    assert (r.open_before, r.net, r.consumption, r.remaining_total) == (1000, 750, 250, 750)


def test_tare_is_subtracted():
    r = compute_weighing(D(1000), D(755), D(1000), D(5))
    assert (r.net, r.consumption) == (750, 250)


def test_example_from_spec_discussion():
    # 2650 g bei 1-kg-Packungen = 2 volle + 650 g offen; gewogen 400 g → 250 g Verbrauch
    r = compute_weighing(D(2650), D(400), D(1000))
    assert (r.full_packages, r.open_before, r.consumption, r.remaining_total) == (2, 650, 250, 2400)


def test_exact_multiple_counts_one_package_as_open():
    r = compute_weighing(D(3000), D(900), D(1000))
    assert (r.full_packages, r.open_before, r.consumption) == (2, 1000, 100)


def test_position_smaller_than_package():
    r = compute_weighing(D(400), D(150), D(1000))
    assert (r.full_packages, r.open_before, r.consumption) == (0, 400, 250)


def test_nothing_used():
    assert compute_weighing(D(650), D(650)).consumption == 0


def test_heavier_than_expected_rejected():
    with pytest.raises(ValidationFailed) as e:
        compute_weighing(D(2650), D(700), D(1000))
    assert e.value.code == "weight_above_expected"


def test_below_tare_rejected():
    with pytest.raises(ValidationFailed) as e:
        compute_weighing(D(500), D(3), D(1000), D(5))
    assert e.value.code == "below_tare"


# ------------------------------------------------------------------ API


def _sugar(client, tare=None):
    from tests.conftest import make_location, make_product

    p = make_product(
        client,
        name="Zucker",
        base_unit="g",
        weigh_remaining=True,
        variants=[{"package_quantity": 1, "package_unit": "kg", "tare_weight": tare}],
    )
    loc = make_location(client, "Vorratsschrank")
    return p, loc


def _weigh(client, item, measured, status=201, **extra):
    import uuid

    r = client.post(
        "/api/v1/stock/weighings",
        json={"stock_item_id": item["id"], "measured_weight": measured, **extra},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == status, r.text
    return r.json()


def test_api_weighing_books_difference_with_tare(admin_client):
    from tests.conftest import ok, receive

    p, loc = _sugar(admin_client, tare=5)
    assert p["weigh_remaining"] is True
    assert p["variants"][0]["tare_weight"] == 5
    receive(admin_client, p, loc, [{"quantity": 3}], variant_id=p["variants"][0]["id"])
    receive(admin_client, p, loc, [{"quantity": 350, "unit": "base"}], variant_id=None)
    item = next(i for i in ok(admin_client.get("/api/v1/stock"))["items"] if i["variant_id"])

    preview = ok(
        admin_client.get(
            "/api/v1/stock/weighing-preview",
            params={"stock_item_id": item["id"], "measured_weight": 655},
        )
    )
    assert (preview["full_packages"], preview["open_before"], preview["net"]) == (2, 1000, 650)
    assert preview["consumption"] == 350

    res = _weigh(admin_client, item, 655, expected_version=item["version"])
    assert res["quantity"] == 350
    hist = ok(admin_client.get("/api/v1/stock/movements", params={"movement_type": "consumption"}))
    [m] = hist["items"]
    assert m["reason"] == "weighed"
    assert m["comment"] == "Restmenge gewogen: 650 g (abgelesen 655 g, Leergewicht 5 g)"

    # zweites Wiegen: 2 volle + 650 g offen → gewogen 405 g (inkl. 5 g Tüte) → 250 g
    item = ok(admin_client.get("/api/v1/stock", params={"product_id": p["id"]}))["items"]
    item = next(i for i in item if i["variant_id"])
    assert _weigh(admin_client, item, 405)["quantity"] == 250


def test_api_weighing_rules(admin_client):
    from tests.conftest import category_id, ok, receive

    p, loc = _sugar(admin_client)
    receive(admin_client, p, loc, [{"quantity": 1}], variant_id=p["variants"][0]["id"])
    item = ok(admin_client.get("/api/v1/stock"))["items"][0]
    assert _weigh(admin_client, item, 1200, status=422)["error"]["code"] == "weight_above_expected"
    assert _weigh(admin_client, item, 1000, status=422)["error"]["code"] == "no_consumption"
    _weigh(admin_client, item, 600)
    assert (
        _weigh(admin_client, item, 500, status=409, expected_version=item["version"])["error"][
            "code"
        ]
        == "stock_changed"
    )

    r = admin_client.post(
        "/api/v1/products",
        json={
            "name": "Milch",
            "category_id": category_id(admin_client),
            "base_unit": "ml",
            "weigh_remaining": True,
        },
    )
    assert r.json()["error"]["code"] == "weigh_requires_gram"


def test_weighing_can_be_reversed(admin_client):
    from tests.conftest import ok, receive

    p, loc = _sugar(admin_client)
    receive(admin_client, p, loc, [{"quantity": 1}], variant_id=p["variants"][0]["id"])
    item = ok(admin_client.get("/api/v1/stock"))["items"][0]
    res = _weigh(admin_client, item, 700)
    r = admin_client.post(
        f"/api/v1/stock/transactions/{res['transaction_id']}/reversal",
        json={},
        headers={"Idempotency-Key": "reverse-weighing-1"},
    )
    assert r.status_code == 201
    assert ok(admin_client.get(f"/api/v1/products/{p['id']}"))["stock_quantity"] == 1000
