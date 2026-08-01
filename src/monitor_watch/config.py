"""Configuration loading with schema validation."""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import TypeAdapter, model_validator

from monitor_watch.models import MonitorConfig, StrictModel


class RetailerConfig(StrictModel):
    id: str
    name: str
    established_australian_retailer: bool
    approved_direct_manufacturer: bool
    enabled: bool
    strategy: str
    parser_version: str | None = None
    urls: dict[str, str]
    review_status: str
    reviewed_at: date
    review_due: date


class RetailersConfig(StrictModel):
    schema_version: int
    user_agent: str
    request_timeout_seconds: float
    response_size_limit_bytes: int
    minimum_request_interval_seconds: float
    maximum_transient_retries: int
    history_retention_months: int
    retailers: list[RetailerConfig]
    seller_exclusions: dict[str, list[str]]
    approved_marketplace_sellers: list[str]


class Threshold(StrictModel):
    buy_price_aud: float | None
    excellent_price_aud: float | None
    approved: bool = False
    approved_at: datetime | None
    approved_by: str | None
    notes: str

    @model_validator(mode="after")
    def validate_approval(self) -> "Threshold":
        if self.approved and (self.approved_at is None or not self.approved_by):
            raise ValueError("approved thresholds require approved_at and approved_by")
        return self


class QualificationConfig(StrictModel):
    allowed_conditions: list[str]
    allowed_stock_statuses: list[str]
    require_australian_stock: bool
    require_clear_australian_warranty: bool
    reject_marketplace: bool
    reject_grey_import: bool
    minimum_warranty_years: float
    require_field_evidence: bool


class ThresholdsConfig(StrictModel):
    schema_version: int
    currency: str
    thresholds: dict[str, Threshold]
    qualification: QualificationConfig


class AutomationSettings(StrictModel):
    commit_observations: bool
    create_price_alerts: bool
    publish_dashboard: bool
    update_existing_alerts: bool
    retailer_review_grace_days: int
    alert_price_band_aud: int


class AutomationConfig(StrictModel):
    schema_version: int
    automation: AutomationSettings


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"configuration root must be a mapping: {path}")
    return value


def load_monitors(path: Path) -> list[MonitorConfig]:
    raw = _read_yaml(path)
    if raw.get("schema_version") != 1:
        raise ValueError("unsupported monitors configuration schema")
    return TypeAdapter(list[MonitorConfig]).validate_python(raw.get("monitors"))


def load_retailers(path: Path) -> RetailersConfig:
    config = RetailersConfig.model_validate(_read_yaml(path))
    if config.schema_version != 1:
        raise ValueError("unsupported retailers configuration schema")
    return config


def load_thresholds(path: Path) -> ThresholdsConfig:
    config = ThresholdsConfig.model_validate(_read_yaml(path))
    if config.schema_version != 1 or config.currency != "AUD":
        raise ValueError("unsupported thresholds configuration")
    return config


def load_automation(path: Path) -> AutomationConfig:
    config = AutomationConfig.model_validate(_read_yaml(path))
    if config.schema_version != 1:
        raise ValueError("unsupported automation configuration")
    return config
