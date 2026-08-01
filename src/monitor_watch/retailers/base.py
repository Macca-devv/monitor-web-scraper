"""Offline-first collector interface; concrete collectors arrive in Phase 2."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from monitor_watch.models import OfferObservation


class RetailerCollector(ABC):
    retailer_id: str
    parser_version: str

    @abstractmethod
    def parse(
        self,
        content: str,
        source_url: str,
        captured_at: datetime | None = None,
    ) -> Sequence[OfferObservation]:
        """Parse saved content without performing network access."""
