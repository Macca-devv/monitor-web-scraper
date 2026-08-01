from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from monitor_watch.models import QualificationStatus, StockStatus
from monitor_watch.qualification import QualificationPolicy, qualify
from monitor_watch.retailers.ple import PleCollector


def _observation():
    path = Path(__file__).parent / "fixtures" / "ple_32gr93u.html"
    return PleCollector().parse(
        path.read_text(encoding="utf-8"),
        "https://www.ple.com.au/products/661692/lg-ultragear-32gr93u-b-32-4k-144hz-ips-monitor",
        datetime(2026, 8, 2, tzinfo=UTC),
    )[0]


def test_unknown_or_provisional_values_cannot_qualify() -> None:
    observation = _observation()
    result = qualify(
        observation,
        QualificationPolicy(
            Decimal("1200"),
            False,
            established_retailer=True,
            approved_models=frozenset({observation.canonical_model}),
        ),
    )
    assert result.qualification_status is QualificationStatus.REJECTED
    assert "threshold_not_approved" in result.rejection_reasons
    assert "stock_not_available" in result.rejection_reasons


def test_threshold_qualification_with_complete_evidence() -> None:
    observation = _observation()
    seed = next(iter(observation.field_evidence.values()))
    evidence = {
        key: seed
        for key in (
            "advertised_model",
            "price_aud",
            "condition",
            "stock_status",
            "seller",
            "australian_stock",
            "manufacturer_warranty_years",
        )
    }
    candidate = observation.model_copy(
        update={
            "stock_status": StockStatus.IN_STOCK,
            "australian_stock": True,
            "delivery_aud": Decimal("0"),
            "field_evidence": evidence,
        }
    )
    policy = QualificationPolicy(
        Decimal("1200"),
        True,
        established_retailer=True,
        approved_models=frozenset({candidate.canonical_model}),
    )
    assert qualify(candidate, policy).qualification_status is QualificationStatus.QUALIFIED
