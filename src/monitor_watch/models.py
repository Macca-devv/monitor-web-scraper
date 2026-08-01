"""Strict domain models. Unknown facts remain explicit rather than truthy."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(StrEnum):
    NEW = "new"
    FACTORY_SECOND = "factory_second"
    REFURBISHED = "refurbished"
    USED = "used"
    UNKNOWN = "unknown"


class StockStatus(StrEnum):
    IN_STOCK = "in_stock"
    AVAILABLE_TO_ORDER = "available_to_order"
    BACKORDER = "backorder"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


class ReturnFreightParty(StrEnum):
    RETAILER = "retailer"
    CUSTOMER = "customer"
    SHARED = "shared"
    UNKNOWN = "unknown"


class QualificationStatus(StrEnum):
    QUALIFIED = "qualified"
    REJECTED = "rejected"
    PENDING = "pending"


class SourceMethod(StrEnum):
    JSON_LD = "json_ld"
    EMBEDDED_DATA = "embedded_data"
    STATIC_HTML = "static_html"
    MANUAL = "manual"


class CollectorStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class CollectorHealth(StrictModel):
    retailer: str
    status: CollectorStatus
    checked_at_utc: datetime
    source_url: HttpUrl
    observations: int = Field(ge=0)
    error_code: str | None = None
    error_message: str | None = None


class FieldEvidence(StrictModel):
    source_url: HttpUrl
    source_path: str = Field(min_length=1)
    captured_at_utc: datetime


class OfferObservation(StrictModel):
    canonical_model: str = Field(min_length=1)
    advertised_model: str = Field(min_length=1)
    retailer: str = Field(min_length=1)
    seller: str | None
    listing_url: HttpUrl
    price_aud: Decimal = Field(ge=0)
    delivery_aud: Decimal | None = Field(default=None, ge=0)
    effective_price_aud: Decimal = Field(ge=0)
    condition: Condition
    stock_status: StockStatus
    australian_stock: bool | None
    manufacturer_warranty_years: Decimal | None = Field(default=None, ge=0)
    seller_warranty_years: Decimal | None = Field(default=None, ge=0)
    dead_pixel_policy: str | None
    return_window_days: int | None = Field(default=None, ge=0)
    return_freight_party: ReturnFreightParty
    marketplace: bool | None
    grey_import: bool | None
    captured_at_utc: datetime
    source_method: SourceMethod
    qualification_status: QualificationStatus = QualificationStatus.PENDING
    rejection_reasons: list[str] = Field(default_factory=list)
    parser_version: str = Field(min_length=1)
    field_evidence: dict[str, FieldEvidence] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_effective_price(self) -> "OfferObservation":
        if self.delivery_aud is not None:
            expected = self.price_aud + self.delivery_aud
            if self.effective_price_aud != expected:
                raise ValueError("effective price must equal item price plus known delivery")
        if self.captured_at_utc.tzinfo is None:
            raise ValueError("captured_at_utc must be timezone-aware")
        return self


class MonitorConfig(StrictModel):
    canonical_model: str
    manufacturer: str
    model_number: str | None
    aliases: list[str]
    enabled: bool
    placeholder: bool
    notes: str | None = None
    expected_specifications: dict[str, object]
