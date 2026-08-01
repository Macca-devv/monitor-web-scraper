"""Enforce periodic legal and technical retailer reviews."""

from dataclasses import dataclass
from datetime import date, timedelta

from monitor_watch.config import RetailerConfig


@dataclass(frozen=True)
class ReviewResult:
    retailer_id: str
    allowed: bool
    reason: str


def check_review(retailer: RetailerConfig, today: date, grace_days: int = 0) -> ReviewResult:
    if not retailer.enabled:
        return ReviewResult(retailer.id, False, "collector_disabled")
    if retailer.review_status != "approved":
        return ReviewResult(retailer.id, False, "review_not_approved")
    if today > retailer.review_due + timedelta(days=grace_days):
        return ReviewResult(retailer.id, False, "review_overdue")
    return ReviewResult(retailer.id, True, "review_current")
