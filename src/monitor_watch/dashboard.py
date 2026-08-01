"""Build a no-server dashboard data file from validated local inputs."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from monitor_watch.config import load_monitors, load_thresholds
from monitor_watch.models import OfferObservation, QualificationStatus
from monitor_watch.scoring import score_monitor


def build_dashboard(root: Path) -> Path:
    monitors = [item for item in load_monitors(root / "config/monitors.yaml") if item.enabled]
    thresholds = load_thresholds(root / "config/thresholds.yaml")
    current = json.loads((root / "data/current.json").read_text(encoding="utf-8"))
    specs_raw = json.loads((root / "data/specifications.json").read_text(encoding="utf-8"))
    specs = {item["canonical_model"]: item for item in specs_raw["models"]}
    offers = [OfferObservation.model_validate(item) for item in current["offers"]]
    cards: list[dict[str, Any]] = []
    for monitor in monitors:
        model_offers = [item for item in offers if item.canonical_model == monitor.canonical_model]
        qualified = [
            item
            for item in model_offers
            if item.qualification_status is QualificationStatus.QUALIFIED
        ]
        rejected = [
            item
            for item in model_offers
            if item.qualification_status is QualificationStatus.REJECTED
        ]
        lowest_q = min(qualified, key=lambda item: item.effective_price_aud, default=None)
        lowest_r = min(rejected, key=lambda item: item.effective_price_aud, default=None)
        threshold = thresholds.thresholds[monitor.canonical_model]
        facts = specs.get(monitor.canonical_model, {"facts": {}, "evidence": []})
        score = score_monitor(
            facts["facts"],
            lowest_q.effective_price_aud if lowest_q else None,
            Decimal(str(threshold.buy_price_aud)) if threshold.buy_price_aud is not None else None,
        )
        cards.append(
            {
                "model": monitor.canonical_model,
                "threshold": {
                    "buy_price_aud": threshold.buy_price_aud,
                    "excellent_price_aud": threshold.excellent_price_aud,
                    "approved": threshold.approved,
                    "approved_at": threshold.approved_at.isoformat()
                    if threshold.approved_at
                    else None,
                    "approved_by": threshold.approved_by,
                    "notes": threshold.notes,
                },
                "lowest_qualified": lowest_q.model_dump(mode="json") if lowest_q else None,
                "lowest_rejected": lowest_r.model_dump(mode="json") if lowest_r else None,
                "specifications": facts,
                "score": {
                    "total": str(score.score) if score.score is not None else None,
                    "confidence": str(score.confidence),
                    "components": {
                        key: str(value) if value is not None else None
                        for key, value in score.components.items()
                    },
                },
            }
        )
    output = root / "docs/data/dashboard.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "generated_at_utc": current.get("generated_at_utc"),
        "models": cards,
        "collector_health": current["collector_health"],
        "last_successful_collection_utc": current.get("generated_at_utc"),
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
