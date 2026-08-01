from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from monitor_watch.alerts import create_if_missing, evaluate_offer
from monitor_watch.config import Threshold
from monitor_watch.models import (
    Condition,
    FieldEvidence,
    OfferObservation,
    QualificationStatus,
    ReturnFreightParty,
    SourceMethod,
    StockStatus,
)


def _threshold(approved: bool = True) -> Threshold:
    return Threshold(
        buy_price_aud=900,
        excellent_price_aud=800,
        approved=approved,
        approved_at=datetime(2026, 8, 2, tzinfo=UTC) if approved else None,
        approved_by="owner" if approved else None,
        notes="test",
    )


def _offer() -> OfferObservation:
    evidence = FieldEvidence(
        source_url="https://example.invalid/g3223q",
        source_path="fixture",
        captured_at_utc=datetime(2026, 8, 2, tzinfo=UTC),
    )
    field_evidence = {
        key: evidence
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
    return OfferObservation(
        canonical_model="Dell G3223Q",
        advertised_model="G3223Q",
        retailer="Fixture Retailer",
        seller="Fixture Retailer",
        listing_url="https://example.invalid/g3223q",
        price_aud=Decimal("799"),
        delivery_aud=Decimal("0"),
        effective_price_aud=Decimal("799"),
        condition=Condition.NEW,
        stock_status=StockStatus.IN_STOCK,
        australian_stock=True,
        manufacturer_warranty_years=Decimal("3"),
        seller_warranty_years=None,
        dead_pixel_policy=None,
        return_window_days=None,
        return_freight_party=ReturnFreightParty.UNKNOWN,
        marketplace=False,
        grey_import=False,
        captured_at_utc=datetime(2026, 8, 2, tzinfo=UTC),
        source_method=SourceMethod.JSON_LD,
        qualification_status=QualificationStatus.QUALIFIED,
        rejection_reasons=[],
        parser_version="fixture-v1",
        field_evidence=field_evidence,
    )


def test_provisional_threshold_cannot_alert() -> None:
    assert (
        evaluate_offer(_offer(), _threshold(False), retailer_enabled=True, price_band_aud=25)
        is None
    )


def test_approved_threshold_requires_audit_metadata() -> None:
    with pytest.raises(ValidationError):
        Threshold(
            buy_price_aud=900,
            excellent_price_aud=800,
            approved=True,
            approved_at=None,
            approved_by=None,
            notes="invalid",
        )


@pytest.mark.parametrize("change", ["unknown_warranty", "unknown_delivery", "rejected", "disabled"])
def test_incomplete_or_ineligible_offer_cannot_alert(change: str) -> None:
    offer = _offer()
    enabled = True
    if change == "unknown_warranty":
        offer = offer.model_copy(update={"manufacturer_warranty_years": None})
    elif change == "unknown_delivery":
        offer = offer.model_copy(update={"delivery_aud": None})
    elif change == "rejected":
        offer = offer.model_copy(update={"qualification_status": QualificationStatus.REJECTED})
    else:
        enabled = False
    assert evaluate_offer(offer, _threshold(), retailer_enabled=enabled, price_band_aud=25) is None


def test_duplicate_issue_detection_and_body_escaping() -> None:
    offer = _offer().model_copy(update={"canonical_model": "<script>alert(1)</script>\nmodel"})
    candidate = evaluate_offer(offer, _threshold(), retailer_enabled=True, price_band_aud=25)
    assert candidate is not None
    assert "<script>" not in candidate.body
    assert "&lt;script&gt;" in candidate.body
    assert "\nmodel" not in candidate.title

    class Client:
        def __init__(self) -> None:
            self.created = 0

        def list_open_issue_bodies(self) -> list[str]:
            return [candidate.body]

        def create_issue(self, title: str, body: str, labels: list[str]) -> None:
            self.created += 1

    client = Client()
    assert create_if_missing(candidate, client) is False
    assert client.created == 0
