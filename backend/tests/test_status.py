"""Regeln für Haltbarkeits- und Bestandsstatus (FR-EXP-003, FR-SHP-003/004)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.modules.stock.status import (
    ExpiryStatus,
    StockLevelStatus,
    expiry_status,
    stock_level_status,
)

TODAY = date(2026, 11, 15)


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (-1, ExpiryStatus.EXPIRED),
        (0, ExpiryStatus.DUE),
        (1, ExpiryStatus.EXPIRING),
        (7, ExpiryStatus.EXPIRING),  # Grenze der Warnfrist gehört noch dazu
        (8, ExpiryStatus.OK),
    ],
)
def test_expiry_status_traffic_light(offset, expected):
    assert expiry_status(TODAY + timedelta(days=offset), 7, TODAY) == expected


def test_expiry_status_without_date_is_unknown():
    assert expiry_status(None, 7, TODAY) == ExpiryStatus.UNKNOWN


def test_expiry_warning_days_zero_warns_only_on_the_day():
    assert expiry_status(TODAY + timedelta(days=1), 0, TODAY) == ExpiryStatus.OK
    assert expiry_status(TODAY, 0, TODAY) == ExpiryStatus.DUE


@pytest.mark.parametrize(
    ("available", "expected"),
    [  # Beispieltabelle aus FR-SHP-004: Mindestbestand 4 Liter, Faktor 1,25
        (7, StockLevelStatus.OK),
        (5, StockLevelStatus.NEAR),
        (4, StockLevelStatus.AT_MINIMUM),
        (3, StockLevelStatus.BELOW),
        (0, StockLevelStatus.BELOW),
    ],
)
def test_stock_level_status_spec_example(available, expected):
    assert stock_level_status(Decimal(available), Decimal(4), Decimal("1.25")) == expected


def test_stock_level_status_just_above_warning_range_is_ok():
    assert stock_level_status(Decimal("5.001"), Decimal(4), Decimal("1.25")) == StockLevelStatus.OK


def test_minimum_zero_means_restock_when_empty():
    assert stock_level_status(Decimal(0), Decimal(0), Decimal("1.25")) == (
        StockLevelStatus.AT_MINIMUM
    )
    assert stock_level_status(Decimal(1), Decimal(0), Decimal("1.25")) == StockLevelStatus.OK
