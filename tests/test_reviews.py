from datetime import date
from pathlib import Path

from monitor_watch.config import load_retailers
from monitor_watch.reviews import check_review


def test_overdue_review_fails_closed() -> None:
    retailer = next(
        item for item in load_retailers(Path("config/retailers.yaml")).retailers if item.id == "ple"
    )
    result = check_review(retailer, date(2026, 11, 3))
    assert result.allowed is False
    assert result.reason == "review_overdue"
