from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monitor_watch.models import StockStatus
from monitor_watch.retailers.ple import ParserError, PleCollector

FIXTURE = Path(__file__).parent / "fixtures" / "ple_32gr93u.html"
URL = "https://www.ple.com.au/products/661692/lg-ultragear-32gr93u-b-32-4k-144hz-ips-monitor"


def test_ple_fixture_extracts_exact_offer() -> None:
    observation = PleCollector().parse(
        FIXTURE.read_text(encoding="utf-8"), URL, datetime(2026, 8, 2, tzinfo=UTC)
    )[0]
    assert observation.canonical_model == "LG UltraGear 32GR93U-B"
    assert observation.advertised_model == "32GR93U-B"
    assert observation.price_aud == Decimal("799.00")
    assert observation.stock_status is StockStatus.OUT_OF_STOCK
    assert observation.seller == "PLE Computers"
    assert observation.retailer == "PLE Computers"
    assert observation.australian_stock is True
    assert observation.manufacturer_warranty_years == Decimal("3")
    assert "australian_stock" in observation.field_evidence


@pytest.mark.parametrize(
    "content", ["", "<html></html>", '<script type="application/ld+json">{}</script>']
)
def test_ple_reports_incomplete_content(content: str) -> None:
    with pytest.raises(ParserError):
        PleCollector().parse(content, URL)
