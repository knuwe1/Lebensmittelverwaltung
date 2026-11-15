"""Haltbarkeitsübersicht (FR-EXP-002…006) und Bestandsüberwachung (FR-SHP-001…004)."""

from datetime import date, timedelta

from tests.conftest import make_location, make_product, ok, receive


def day(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


def bb(qty, offset):
    return {
        "quantity": qty,
        "unit": "base",
        "expiry_type": "best_before",
        "expiry_date": day(offset),
    }


def ub(qty, offset):
    return {"quantity": qty, "unit": "base", "expiry_type": "use_by", "expiry_date": day(offset)}


# ------------------------------------------------------------------ Haltbarkeit


def test_stock_items_carry_expiry_status(admin_client):
    p = make_product(admin_client, "Joghurt", base_unit="piece")
    kuehl = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, kuehl, [bb(1, -2), bb(1, 0), bb(1, 3), bb(1, 30)])
    receive(admin_client, p, kuehl, [{"quantity": 1, "unit": "base", "expiry_type": "none"}])
    items = ok(admin_client.get("/api/v1/stock", params={"sort": "expiry"}))["items"]
    got = [(i["expiry_status"], i["days_until_expiry"]) for i in items]
    assert got == [("expired", -2), ("due", 0), ("expiring", 3), ("ok", 30), ("unknown", None)]
    assert {i["warning_days"] for i in items} == {7}


def test_expiring_overview_lists_only_endangered_items(admin_client):
    p = make_product(admin_client, "Joghurt", base_unit="piece")
    kuehl = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, kuehl, [bb(1, -2), bb(1, 0), bb(1, 3), bb(1, 30)])
    res = ok(admin_client.get("/api/v1/stock/expiring"))
    assert [i["expiry_status"] for i in res["items"]] == ["expired", "due", "expiring"]
    assert res["total"] == 3

    only = ok(admin_client.get("/api/v1/stock/expiring", params={"status": ["expired", "due"]}))
    assert [i["expiry_status"] for i in only["items"]] == ["expired", "due"]


def test_product_specific_warning_days_override_household_default(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    lang = make_product(admin_client, "Konserve", base_unit="piece", expiry_warning_days=60)
    kurz = make_product(admin_client, "Salat", base_unit="piece", expiry_warning_days=1)
    receive(admin_client, lang, kuehl, [bb(1, 30)])
    receive(admin_client, kurz, kuehl, [bb(1, 3)])
    res = ok(admin_client.get("/api/v1/stock/expiring"))["items"]
    assert [(i["product_name"], i["warning_days"]) for i in res] == [("Konserve", 60)]


def test_household_warning_days_are_configurable(admin_client):
    p = make_product(admin_client, "Käse", base_unit="piece")
    kuehl = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, kuehl, [bb(1, 10)])
    assert ok(admin_client.get("/api/v1/stock/expiring"))["total"] == 0
    ok(admin_client.patch("/api/v1/settings", json={"expiry_warning_days": 14}))
    assert ok(admin_client.get("/api/v1/stock/expiring"))["total"] == 1


def test_expiring_overview_filters_by_location_and_sorts(admin_client):
    keller = make_location(admin_client, "Keller")
    regal = make_location(admin_client, "Regal", keller["id"])
    kuehl = make_location(admin_client, "Kühlschrank")
    a = make_product(admin_client, "Apfelmus", base_unit="piece")
    z = make_product(admin_client, "Zwieback", base_unit="piece")
    receive(admin_client, z, regal, [bb(1, 1)])
    receive(admin_client, a, kuehl, [bb(1, 2)])

    by_date = ok(admin_client.get("/api/v1/stock/expiring"))["items"]
    assert [i["product_name"] for i in by_date] == ["Zwieback", "Apfelmus"]
    by_name = ok(admin_client.get("/api/v1/stock/expiring", params={"sort": "product"}))["items"]
    assert [i["product_name"] for i in by_name] == ["Apfelmus", "Zwieback"]
    by_loc = ok(admin_client.get("/api/v1/stock/expiring", params={"sort": "location"}))["items"]
    assert [i["location_path"] for i in by_loc] == ["Keller › Regal", "Kühlschrank"]

    in_keller = ok(admin_client.get("/api/v1/stock/expiring", params={"location_id": keller["id"]}))
    assert [i["product_name"] for i in in_keller["items"]] == ["Zwieback"]
    only_keller = ok(
        admin_client.get(
            "/api/v1/stock/expiring",
            params={"location_id": keller["id"], "include_sublocations": False},
        )
    )
    assert only_keller["total"] == 0


def test_expired_items_stay_in_stock(admin_client):
    """FR-EXP-005: Kein automatisches Ausbuchen nach Ablauf."""
    p = make_product(admin_client, "Hackfleisch", base_unit="g")
    kuehl = make_location(admin_client, "Kühlschrank")
    receive(admin_client, p, kuehl, [ub(500, -3)])
    [item] = ok(admin_client.get("/api/v1/stock"))["items"]
    assert (item["quantity"], item["expiry_status"]) == (500, "expired")


def test_expiry_data_is_household_scoped(admin_client, app, db):
    from app.modules.users.models import Household, Role
    from app.modules.users.schemas import UserCreate
    from app.modules.users.service import create_user
    from tests.conftest import PASSWORD, _login

    p = make_product(admin_client, "Joghurt", base_unit="piece")
    receive(admin_client, p, make_location(admin_client, "Kühlschrank"), [bb(1, 0)])

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
    assert ok(nachbar.get("/api/v1/stock/expiring"))["total"] == 0


# ------------------------------------------------------------------ Bestandsüberwachung


def _levels(client, **params):
    return {
        row["product_name"]: row for row in ok(client.get("/api/v1/stock/levels", params=params))
    }


def test_levels_follow_spec_example(admin_client):
    """FR-SHP-004, Beispiel: Mindestbestand 4 l, Warnfaktor 1,25 → Warnbereich 5 l."""
    kuehl = make_location(admin_client, "Kühlschrank")
    for name, liters in [("A", 7), ("B", 5), ("C", 4), ("D", 3)]:
        p = make_product(admin_client, name, minimum_stock=4000, target_stock=6000)
        receive(admin_client, p, kuehl, [bb(liters * 1000, 30)])
    rows = ok(admin_client.get("/api/v1/stock/levels"))
    assert [(r["product_name"], r["status"]) for r in rows] == [
        ("D", "below"),
        ("C", "at_minimum"),
        ("B", "near"),
        ("A", "ok"),
    ]
    assert {r["warning_threshold"] for r in rows} == {5000}


def test_products_without_minimum_are_not_monitored(admin_client):
    """FR-SHP-001: Kein Mindestbestand = keine Überwachung, nicht „Mindestbestand 0“."""
    make_product(admin_client, "Ohne Grenze")
    make_product(admin_client, "Leer überwacht", minimum_stock=1000)
    rows = _levels(admin_client)
    assert set(rows) == {"Leer überwacht"}
    assert (rows["Leer überwacht"]["available_quantity"], rows["Leer überwacht"]["status"]) == (
        0,
        "below",
    )


def test_expired_use_by_is_not_available_but_expired_best_before_is(admin_client):
    """FR-EXP-006 / BR-010 / BR-011."""
    kuehl = make_location(admin_client, "Kühlschrank")
    hack = make_product(admin_client, "Hackfleisch", base_unit="g", minimum_stock=400)
    receive(admin_client, hack, kuehl, [ub(500, -1), ub(300, 2)])
    nudeln = make_product(admin_client, "Nudeln", base_unit="g", minimum_stock=400)
    receive(admin_client, nudeln, kuehl, [bb(600, -100)])

    rows = _levels(admin_client)
    assert (
        rows["Hackfleisch"]["physical_quantity"],
        rows["Hackfleisch"]["available_quantity"],
    ) == (
        800,
        300,
    )
    assert rows["Hackfleisch"]["status"] == "below"
    assert rows["Nudeln"]["available_quantity"] == 600
    assert rows["Nudeln"]["status"] == "ok"


def test_warning_factor_is_configurable(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    p = make_product(admin_client, "Milch", minimum_stock=2000)
    receive(admin_client, p, kuehl, [bb(3000, 30)])
    assert _levels(admin_client)["Milch"]["status"] == "ok"
    ok(admin_client.patch("/api/v1/settings", json={"stock_warning_factor": "1.5"}))
    row = _levels(admin_client)["Milch"]
    assert (row["status"], row["warning_threshold"]) == ("near", 3000)


def test_levels_status_filter_and_inactive_products(admin_client):
    kuehl = make_location(admin_client, "Kühlschrank")
    make_product(admin_client, "Leer", minimum_stock=1)
    voll = make_product(admin_client, "Voll", minimum_stock=1)
    receive(admin_client, voll, kuehl, [bb(10, 30)])
    alt = make_product(admin_client, "Ausgelistet", minimum_stock=1)
    ok(admin_client.patch(f"/api/v1/products/{alt['id']}", json={"active": False}))

    assert set(_levels(admin_client, status=["below", "at_minimum"])) == {"Leer"}
    assert set(_levels(admin_client)) == {"Leer", "Voll"}


def test_levels_require_login(anon):
    assert anon.get("/api/v1/stock/levels").status_code == 401
    assert anon.get("/api/v1/stock/expiring").status_code == 401


def test_unknown_sort_is_rejected(admin_client):
    r = admin_client.get("/api/v1/stock/expiring", params={"sort": "quatsch"})
    assert r.status_code == 422, r.text
