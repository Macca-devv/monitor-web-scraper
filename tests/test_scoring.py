from decimal import Decimal

from monitor_watch.scoring import WEIGHTS, score_monitor


def test_weights_total_one_hundred_and_score_is_deterministic() -> None:
    assert sum(WEIGHTS.values()) == 100
    facts = {
        "flat": True,
        "resolution": "3840x2160",
        "panel_family": "IPS",
        "refresh_rate_hz": 144,
    }
    first = score_monitor(facts, Decimal("600"), Decimal("600"))
    assert first == score_monitor(facts, Decimal("600"), Decimal("600"))
    assert first.score is not None
    assert first.confidence < Decimal("1")


def test_unknown_is_not_scored_as_zero() -> None:
    result = score_monitor({}, None, None)
    assert result.score is None
    assert result.confidence == 0
    assert all(value is None for value in result.components.values())
