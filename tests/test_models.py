from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from monitor_watch.models import (
    Condition,
    OfferObservation,
    QualificationStatus,
    ReturnFreightParty,
    SourceMethod,
    StockStatus,
)


def valid_offer() -> dict[str, object]:
    return {
        "canonical_model": "Dell G3223Q",
        "advertised_model": "G3223Q",
        "retailer": "Fixture Retailer",
        "seller": "Fixture Retailer",
        "listing_url": "https://example.invalid/g3223q",
        "price_aud": Decimal("799.00"),
        "delivery_aud": Decimal("10.00"),
        "effective_price_aud": Decimal("809.00"),
        "condition": Condition.NEW,
        "stock_status": StockStatus.IN_STOCK,
        "australian_stock": True,
        "manufacturer_warranty_years": Decimal("3"),
        "seller_warranty_years": None,
        "dead_pixel_policy": None,
        "return_window_days": 30,
        "return_freight_party": ReturnFreightParty.UNKNOWN,
        "marketplace": False,
        "grey_import": False,
        "captured_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "source_method": SourceMethod.JSON_LD,
        "qualification_status": QualificationStatus.PENDING,
        "rejection_reasons": [],
        "parser_version": "fixture-v1",
    }


def test_offer_accepts_complete_typed_observation() -> None:
    assert OfferObservation.model_validate(valid_offer()).effective_price_aud == Decimal("809.00")


def test_offer_rejects_inconsistent_effective_price() -> None:
    payload = valid_offer()
    payload["effective_price_aud"] = Decimal("799.00")
    with pytest.raises(ValidationError):
        OfferObservation.model_validate(payload)


def test_unknown_boolean_facts_remain_unknown() -> None:
    payload = valid_offer()
    payload["marketplace"] = None
    payload["grey_import"] = None
    payload["australian_stock"] = None
    observation = OfferObservation.model_validate(payload)
    assert observation.marketplace is None
    assert observation.grey_import is None
    assert observation.australian_stock is None
