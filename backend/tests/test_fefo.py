from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.modules.stock.fefo import plan_consumption

TODAY = date(2026, 11, 18)


@dataclass
class P:
    name: str
    quantity: Decimal
    expiry_type: str = "best_before"
    expiry_date: date | None = None
    received_on: date = date(2026, 11, 1)


def names(plan):
    return [(a.position.name, a.quantity) for a in plan.allocations]


def test_ac005_earliest_expiry_first():
    a = P("A", Decimal(1000), expiry_date=date(2026, 11, 20))
    b = P("B", Decimal(1000), expiry_date=date(2026, 11, 27))
    plan = plan_consumption([b, a], Decimal(1000), TODAY)
    assert names(plan) == [("A", 1000)]


def test_cns005_split_across_positions():
    a = P("A", Decimal(200), expiry_date=date(2026, 12, 1))
    b = P("B", Decimal(500), expiry_date=date(2027, 1, 1))
    plan = plan_consumption([a, b], Decimal(350), TODAY)
    assert names(plan) == [("A", 200), ("B", 150)]
    assert plan.sufficient


def test_cns004_partial():
    zucker = P("Zucker", Decimal(1000))
    plan = plan_consumption([zucker], Decimal(250), TODAY)
    assert names(plan) == [("Zucker", 250)]


def test_without_date_last_and_received_order_breaks_ties():
    no_date = P("ohne", Decimal(1), expiry_type="none")
    unknown = P("unbekannt", Decimal(1), expiry_type="unknown", received_on=date(2026, 10, 1))
    old = P("alt", Decimal(1), expiry_date=date(2027, 1, 1), received_on=date(2026, 9, 1))
    new = P("neu", Decimal(1), expiry_date=date(2027, 1, 1), received_on=date(2026, 11, 1))
    plan = plan_consumption([no_date, new, unknown, old], Decimal(4), TODAY)
    assert [a.position.name for a in plan.allocations] == ["alt", "neu", "unbekannt", "ohne"]


def test_expired_use_by_is_never_suggested_but_expired_bbd_is():
    expired_use_by = P("Hack", Decimal(500), expiry_type="use_by", expiry_date=date(2026, 11, 17))
    today_use_by = P("Hack heute", Decimal(500), expiry_type="use_by", expiry_date=TODAY)
    expired_bbd = P("Joghurt", Decimal(1), expiry_date=date(2026, 11, 1))
    plan = plan_consumption([expired_use_by, today_use_by], Decimal(600), TODAY)
    assert names(plan) == [("Hack heute", 500)]
    assert not plan.sufficient
    assert plan.available == 500
    assert names(plan_consumption([expired_bbd], Decimal(1), TODAY)) == [("Joghurt", 1)]


def test_insufficient_reports_available():
    plan = plan_consumption([P("A", Decimal("0.5"))], Decimal(1), TODAY)
    assert not plan.sufficient
    assert plan.available == Decimal("0.5")
    assert names(plan) == [("A", Decimal("0.5"))]
