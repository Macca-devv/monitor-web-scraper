from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monitor_watch.models import Condition, StockStatus
from monitor_watch.retailers.umart import ParserError, UmartCollector

FIXTURE = Path("tests/fixtures/umart_u3225qe.html")
URL = "https://www.umart.com.au/product/example"


def test_umart_fixture_extracts_normalised_offer() -> None:
    captured = datetime(2026, 8, 2, 1, 2, 3, tzinfo=UTC)
    offer = UmartCollector().parse(FIXTURE.read_text(encoding="utf-8"), URL, captured)[0]

    assert offer.canonical_model == "Dell UltraSharp U3225QE"
    assert offer.advertised_model == "U3225QE"
    assert offer.price_aud == Decimal("1099.00")
    assert offer.stock_status is StockStatus.IN_STOCK
    assert offer.condition is Condition.NEW
    assert offer.retailer == "Umart"
    assert offer.seller == "Umart"
    assert offer.australian_stock is True
    assert offer.manufacturer_warranty_years == Decimal("3")
    assert offer.marketplace is False
    assert offer.grey_import is False


@pytest.mark.parametrize(
    "content",
    [
        "<html></html>",
        '<script type="application/ld+json">{malformed</script>',
        '<script type="application/ld+json">{"@type":"Product"}</script>',
    ],
)
def test_umart_malformed_or_incomplete_content_fails(content: str) -> None:
    with pytest.raises(ParserError):
        UmartCollector().parse(content, URL)


def test_umart_unknown_model_fails_closed() -> None:
    content = FIXTURE.read_text(encoding="utf-8").replace("U3225QE", "UNKNOWN-MODEL")
    with pytest.raises(ParserError, match="unconfigured exact model"):
        UmartCollector().parse(content, URL)


def test_missing_australian_stock_and_warranty_remain_unknown() -> None:
    content = FIXTURE.read_text(encoding="utf-8")
    content = content.replace('"shippingDetails": {', '"unusedShippingDetails": {')
    content = content.replace("Warranty Period:", "Support term:")
    offer = UmartCollector().parse(content, URL)[0]
    assert offer.australian_stock is None
    assert offer.manufacturer_warranty_years is None
