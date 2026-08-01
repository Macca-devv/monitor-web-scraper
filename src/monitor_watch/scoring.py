"""Deterministic scoring from cited factual inputs; missing facts reduce confidence."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

WEIGHTS = {
    "productivity": 30,
    "image_quality": 20,
    "connectivity": 15,
    "gaming": 10,
    "warranty": 10,
    "value": 15,
}


@dataclass(frozen=True)
class ScoreResult:
    score: Decimal | None
    confidence: Decimal
    components: dict[str, Decimal | None]


def score_monitor(
    facts: dict[str, Any], lowest_price: Decimal | None, target: Decimal | None
) -> ScoreResult:
    components: dict[str, Decimal | None] = {
        "productivity": _mean(
            _bool(facts, "flat"), _resolution(facts), _bool(facts, "flicker_free")
        ),
        "image_quality": _mean(_panel(facts), _bool(facts, "local_dimming")),
        "connectivity": _mean(
            _count(facts, "video_inputs", 3), _bool(facts, "usb_c"), _bool(facts, "kvm")
        ),
        "gaming": _refresh(facts),
        "warranty": _years(facts),
        "value": _value(lowest_price, target),
    }
    known_weight = sum(WEIGHTS[key] for key, value in components.items() if value is not None)
    if not known_weight:
        return ScoreResult(None, Decimal("0"), components)
    weighted = sum(
        Decimal(WEIGHTS[key]) * value for key, value in components.items() if value is not None
    )
    return ScoreResult(
        (weighted / Decimal(known_weight)).quantize(Decimal("0.1")),
        (Decimal(known_weight) / Decimal(100)).quantize(Decimal("0.01")),
        components,
    )


def _mean(*values: Decimal | None) -> Decimal | None:
    known = [value for value in values if value is not None]
    return sum(known, start=Decimal("0")) / Decimal(len(known)) if known else None


def _bool(facts: dict[str, Any], key: str) -> Decimal | None:
    value = facts.get(key)
    return Decimal("100") if value is True else Decimal("0") if value is False else None


def _resolution(facts: dict[str, Any]) -> Decimal | None:
    value = facts.get("resolution")
    return Decimal("100") if value == "3840x2160" else Decimal("0") if value else None


def _panel(facts: dict[str, Any]) -> Decimal | None:
    value = facts.get("panel_family")
    return (
        Decimal("100")
        if value in {"IPS", "IPS Black", "Mini-LED IPS"}
        else Decimal("0")
        if value
        else None
    )


def _refresh(facts: dict[str, Any]) -> Decimal | None:
    value = facts.get("refresh_rate_hz")
    if not isinstance(value, int | float):
        return None
    return Decimal("100") if value >= 144 else Decimal("80") if value >= 120 else Decimal("0")


def _count(facts: dict[str, Any], key: str, ideal: int) -> Decimal | None:
    value = facts.get(key)
    if not isinstance(value, int):
        return None
    return min(Decimal("100"), Decimal(value * 100) / Decimal(ideal))


def _years(facts: dict[str, Any]) -> Decimal | None:
    value = facts.get("warranty_years")
    if not isinstance(value, int | float):
        return None
    return min(Decimal("100"), Decimal(str(value)) / Decimal("3") * Decimal("100"))


def _value(price: Decimal | None, target: Decimal | None) -> Decimal | None:
    if price is None or target is None or target <= 0:
        return None
    return min(Decimal("100"), target / price * Decimal("100"))
