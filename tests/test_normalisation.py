from decimal import Decimal

import pytest

from monitor_watch.models import Condition
from monitor_watch.normalisation import classify_condition, matches_model, parse_aud


@pytest.mark.parametrize("advertised", ["32GR93U-B", "32GR93U", "32GR93U-B.AAU"])
def test_approved_model_alias_matching(advertised: str) -> None:
    assert matches_model(advertised, "32GR93U-B", ["32GR93U", "32GR93U-B.AAU"])


def test_combined_or_ambiguous_model_does_not_match() -> None:
    assert not matches_model("32GR93U / 32GQ950", "32GR93U-B", ["32GR93U"])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("A$799", "799.00"), ("$1,299.95", "1299.95"), ("AUD 900", "900.00")],
)
def test_parse_aud(raw: str, expected: str) -> None:
    assert parse_aud(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["from $799", "$799-$999", "USD 799", "call for price"])
def test_ambiguous_price_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_aud(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Brand new", Condition.NEW),
        ("Factory second", Condition.FACTORY_SECOND),
        ("Manufacturer refurbished", Condition.REFURBISHED),
        ("Pre-owned", Condition.USED),
        ("Great condition", Condition.UNKNOWN),
    ],
)
def test_condition_classification(raw: str, expected: Condition) -> None:
    assert classify_condition(raw) is expected
