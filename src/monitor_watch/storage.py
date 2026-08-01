"""Bounded monthly JSON history with one observation per retailer/model/UTC day."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import TypeAdapter

from monitor_watch.models import CollectorHealth, OfferObservation

_OBSERVATIONS = TypeAdapter(list[OfferObservation])


def estimate_annual_history_bytes(
    monitors: int = 5,
    retailers: int = 4,
    days: int = 365,
    estimated_bytes_per_observation: int = 2500,
) -> int:
    return monitors * retailers * days * estimated_bytes_per_observation


def _partition_path(root: Path, captured_at: datetime) -> Path:
    return root / f"{captured_at.astimezone(UTC):%Y-%m}.json"


def _key(observation: OfferObservation) -> tuple[str, str, date]:
    return (
        observation.retailer.casefold(),
        observation.canonical_model.casefold(),
        observation.captured_at_utc.astimezone(UTC).date(),
    )


def store_daily_observation(
    root: Path,
    observation: OfferObservation,
    *,
    retention_months: int,
    reference_date: date | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = _partition_path(root, observation.captured_at_utc)
    existing = load_partition(path)
    replacement_key = _key(observation)
    retained = [item for item in existing if _key(item) != replacement_key]
    retained.append(observation)
    retained.sort(key=lambda item: item.captured_at_utc)
    payload = {
        "schema_version": 1,
        "observations": [item.model_dump(mode="json") for item in retained],
    }
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    prune_partitions(root, retention_months, reference_date or datetime.now(UTC).date())
    return path


def load_partition(path: Path) -> list[OfferObservation]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1 or not isinstance(raw.get("observations"), list):
        raise ValueError(f"invalid history partition: {path}")
    return _OBSERVATIONS.validate_python(raw["observations"])


def prune_partitions(root: Path, retention_months: int, reference_date: date) -> list[Path]:
    if retention_months < 1:
        raise ValueError("retention_months must be positive")
    reference_index = reference_date.year * 12 + reference_date.month - 1
    oldest_index = reference_index - retention_months + 1
    removed: list[Path] = []
    for path in root.glob("????-??.json"):
        try:
            year, month = (int(part) for part in path.stem.split("-"))
        except ValueError:
            continue
        if year * 12 + month - 1 < oldest_index:
            path.unlink()
            removed.append(path)
    return removed


def update_current(
    path: Path, observations: list[OfferObservation], health: CollectorHealth
) -> None:
    """Replace current rows for observed retailer/model pairs and retailer health."""
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    existing = _OBSERVATIONS.validate_python(raw.get("offers", []))
    keys = {(item.retailer.casefold(), item.canonical_model.casefold()) for item in observations}
    retained = [
        item
        for item in existing
        if (item.retailer.casefold(), item.canonical_model.casefold()) not in keys
    ]
    retained.extend(observations)
    retained.sort(key=lambda item: (item.canonical_model.casefold(), item.retailer.casefold()))
    health_rows = [
        item
        for item in raw.get("collector_health", [])
        if str(item.get("retailer", "")).casefold() != health.retailer.casefold()
    ]
    health_rows.append(health.model_dump(mode="json"))
    health_rows.sort(key=lambda item: str(item["retailer"]).casefold())
    payload = {
        "schema_version": 1,
        "generated_at_utc": health.checked_at_utc.isoformat(),
        "offers": [item.model_dump(mode="json") for item in retained],
        "collector_health": health_rows,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
