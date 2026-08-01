"""Conservative, evidence-aware offer qualification."""

from dataclasses import dataclass
from decimal import Decimal

from monitor_watch.models import Condition, OfferObservation, QualificationStatus, StockStatus


@dataclass(frozen=True)
class QualificationPolicy:
    threshold_aud: Decimal | None
    threshold_approved: bool
    minimum_warranty_years: Decimal = Decimal("3")
    established_retailer: bool = False
    approved_models: frozenset[str] = frozenset()
    require_evidence: bool = True


MANDATORY_EVIDENCE = frozenset(
    {"advertised_model", "price_aud", "condition", "stock_status", "seller", "australian_stock"}
)


def qualify(observation: OfferObservation, policy: QualificationPolicy) -> OfferObservation:
    reasons: list[str] = []
    if observation.canonical_model not in policy.approved_models:
        reasons.append("model_not_configured")
    if observation.condition is not Condition.NEW:
        reasons.append(
            "condition_not_new"
            if observation.condition is not Condition.UNKNOWN
            else "condition_unknown"
        )
    if observation.stock_status not in {StockStatus.IN_STOCK, StockStatus.AVAILABLE_TO_ORDER}:
        reasons.append(
            "stock_not_available"
            if observation.stock_status is not StockStatus.UNKNOWN
            else "stock_unknown"
        )
    if observation.australian_stock is not True:
        reasons.append(
            "australian_stock_unknown"
            if observation.australian_stock is None
            else "not_australian_stock"
        )
    if not policy.established_retailer:
        reasons.append("retailer_not_approved")
    if observation.seller is None:
        reasons.append("seller_unknown")
    if observation.marketplace is not False:
        reasons.append(
            "marketplace_unknown" if observation.marketplace is None else "marketplace_offer"
        )
    if observation.grey_import is not False:
        reasons.append("grey_import_unknown" if observation.grey_import is None else "grey_import")
    warranties = [
        value
        for value in (observation.manufacturer_warranty_years, observation.seller_warranty_years)
        if value is not None
    ]
    if not warranties:
        reasons.append("warranty_unknown")
    elif max(warranties) < policy.minimum_warranty_years:
        reasons.append("warranty_below_minimum")
    if policy.threshold_aud is None:
        reasons.append("threshold_unknown")
    elif not policy.threshold_approved:
        reasons.append("threshold_not_approved")
    elif observation.effective_price_aud > policy.threshold_aud:
        reasons.append("price_above_threshold")
    if observation.delivery_aud is None:
        reasons.append("delivery_cost_unknown")
    if policy.require_evidence:
        missing = sorted(MANDATORY_EVIDENCE - observation.field_evidence.keys())
        reasons.extend(f"missing_evidence:{field}" for field in missing)
        if warranties and not (
            {"manufacturer_warranty_years", "seller_warranty_years"}
            & observation.field_evidence.keys()
        ):
            reasons.append("missing_evidence:warranty")
    return observation.model_copy(
        update={
            "qualification_status": QualificationStatus.REJECTED
            if reasons
            else QualificationStatus.QUALIFIED,
            "rejection_reasons": reasons,
        }
    )
