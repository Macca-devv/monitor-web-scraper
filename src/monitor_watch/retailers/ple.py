"""PLE product parser using its public schema.org Product JSON-LD."""

from collections.abc import Sequence
from datetime import datetime

from pydantic import HttpUrl

from monitor_watch.models import FieldEvidence, OfferObservation
from monitor_watch.retailers.umart import ParserError, UmartCollector


class PleCollector(UmartCollector):
    retailer_id = "ple"
    retailer_name = "PLE Computers"
    parser_version = "ple-jsonld-v1"

    def parse(
        self, content: str, source_url: str, captured_at: datetime | None = None
    ) -> Sequence[OfferObservation]:
        observations = super().parse(content, source_url, captured_at)
        result: list[OfferObservation] = []
        for observation in observations:
            evidence = dict(observation.field_evidence)
            evidence["australian_stock"] = FieldEvidence(
                source_url=HttpUrl(source_url),
                source_path=(
                    "Product.offers.seller.name; retailer configured as Australian stockist"
                ),
                captured_at_utc=observation.captured_at_utc,
            )
            result.append(
                observation.model_copy(
                    update={"australian_stock": True, "field_evidence": evidence}
                )
            )
        return result


__all__ = ["ParserError", "PleCollector"]
