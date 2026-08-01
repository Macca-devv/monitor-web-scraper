from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from monitor_watch.models import (
    Condition,
    OfferObservation,
    QualificationStatus,
    ReturnFreightParty,
    SourceMethod,
    StockStatus,
)
from monitor_watch.storage import (
    estimate_annual_history_bytes,
    load_partition,
    prune_partitions,
    store_daily_observation,
)


def offer(captured_at: datetime, price: str = "1099.00") -> OfferObservation:
    return OfferObservation(
        canonical_model="Dell UltraSharp U3225QE",
        advertised_model="U3225QE",
        retailer="Umart",
        seller="Umart",
        listing_url="https://example.invalid/u3225qe",
        price_aud=Decimal(price),
        delivery_aud=None,
        effective_price_aud=Decimal(price),
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
        captured_at_utc=captured_at,
        source_method=SourceMethod.JSON_LD,
        qualification_status=QualificationStatus.REJECTED,
        rejection_reasons=["threshold_not_configured"],
        parser_version="fixture-v1",
    )


def test_same_day_observation_is_replaced_and_status_preserved(tmp_path: Path) -> None:
    first = offer(datetime(2026, 8, 2, 1, tzinfo=UTC))
    second = offer(datetime(2026, 8, 2, 20, tzinfo=UTC), "999.00")
    path = store_daily_observation(
        tmp_path, first, retention_months=24, reference_date=date(2026, 8, 2)
    )
    store_daily_observation(tmp_path, second, retention_months=24, reference_date=date(2026, 8, 2))
    stored = load_partition(path)
    assert len(stored) == 1
    assert stored[0].price_aud == Decimal("999.00")
    assert stored[0].qualification_status is QualificationStatus.REJECTED
    assert stored[0].rejection_reasons == ["threshold_not_configured"]


def test_monthly_rollover_creates_separate_partitions(tmp_path: Path) -> None:
    august = store_daily_observation(
        tmp_path,
        offer(datetime(2026, 8, 31, tzinfo=UTC)),
        retention_months=24,
        reference_date=date(2026, 9, 1),
    )
    september = store_daily_observation(
        tmp_path,
        offer(datetime(2026, 9, 1, tzinfo=UTC)),
        retention_months=24,
        reference_date=date(2026, 9, 1),
    )
    assert august.name == "2026-08.json"
    assert september.name == "2026-09.json"
    assert len(load_partition(august)) == 1
    assert len(load_partition(september)) == 1


def test_retention_removes_only_expired_months(tmp_path: Path) -> None:
    for name in ("2026-05.json", "2026-06.json", "2026-07.json", "notes.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    removed = prune_partitions(tmp_path, retention_months=3, reference_date=date(2026, 8, 2))
    assert [path.name for path in removed] == ["2026-05.json"]
    assert (tmp_path / "2026-06.json").exists()
    assert (tmp_path / "notes.json").exists()


def test_documented_annual_growth_ceiling() -> None:
    assert estimate_annual_history_bytes() == 18_250_000
