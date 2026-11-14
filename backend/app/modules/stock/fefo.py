"""FEFO-Auswahl und Aufteilung von Entnahmen (FR-CNS-003, FR-CNS-005, Spez. 15.2).

Reine Funktionen ohne Datenbankzugriff, damit die Regeln isoliert testbar sind.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


class Position(Protocol):
    quantity: Decimal
    expiry_type: str
    expiry_date: date | None
    received_on: date


def is_use_by_expired(pos: Position, today: date) -> bool:
    """Überschrittenes Verbrauchsdatum: nicht mehr verwenden (Spez. 7.1, BR-011)."""
    return pos.expiry_type == "use_by" and pos.expiry_date is not None and pos.expiry_date < today


def fefo_key(pos: Position) -> tuple:
    """First Expired – First Out: früheste Haltbarkeit zuerst, Positionen ohne Datum zuletzt,
    bei Gleichstand die zuerst eingelagerte Position."""
    return (pos.expiry_date is None, pos.expiry_date or date.max, pos.received_on)


@dataclass(frozen=True)
class Allocation[T]:
    position: T
    quantity: Decimal


@dataclass(frozen=True)
class Plan[T]:
    allocations: list[Allocation[T]]
    requested: Decimal
    available: Decimal

    @property
    def sufficient(self) -> bool:
        return self.available >= self.requested


def plan_consumption[T: Position](positions: list[T], requested: Decimal, today: date) -> Plan[T]:
    """Verteilt eine Entnahmemenge nach FEFO auf Bestandspositionen.

    Positionen mit überschrittenem Verbrauchsdatum werden nicht vorgeschlagen; sie
    sollen entsorgt werden. Reicht der Bestand nicht, enthält der Plan die maximal
    mögliche Verteilung und ``sufficient`` ist ``False``.
    """
    usable = sorted(
        (p for p in positions if p.quantity > 0 and not is_use_by_expired(p, today)),
        key=fefo_key,
    )
    remaining = requested
    allocations: list[Allocation[T]] = []
    for pos in usable:
        if remaining <= 0:
            break
        take = min(pos.quantity, remaining)
        allocations.append(Allocation(pos, take))
        remaining -= take
    available = sum((p.quantity for p in usable), Decimal(0))
    return Plan(allocations, requested, available)
