"""Explicit, bounded command-line entry points."""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import HttpUrl

from monitor_watch.alerts import GitHubIssueClient, create_if_missing, evaluate_offer
from monitor_watch.config import load_automation, load_monitors, load_retailers, load_thresholds
from monitor_watch.dashboard import build_dashboard
from monitor_watch.http import FetchError, FetchPolicy, fetch_html
from monitor_watch.models import CollectorHealth, CollectorStatus, OfferObservation
from monitor_watch.qualification import QualificationPolicy, qualify
from monitor_watch.retailers.ple import PleCollector
from monitor_watch.retailers.umart import ParserError, UmartCollector
from monitor_watch.reviews import check_review
from monitor_watch.storage import load_partition, store_daily_observation, update_current

ROOT = Path(__file__).resolve().parents[2]
COLLECTORS = {"umart": UmartCollector, "ple": PleCollector}


def _collect(retailer_id: str, model_name: str, write: bool) -> int:
    config = load_retailers(ROOT / "config/retailers.yaml")
    monitors = load_monitors(ROOT / "config/monitors.yaml")
    thresholds = load_thresholds(ROOT / "config/thresholds.yaml")
    automation = load_automation(ROOT / "config/automation.yaml")
    retailer = next((item for item in config.retailers if item.id == retailer_id), None)
    monitor = next(
        (
            item
            for item in monitors
            if model_name.casefold()
            in {
                item.canonical_model.casefold(),
                (item.model_number or "").casefold(),
                *(alias.casefold() for alias in item.aliases),
            }
        ),
        None,
    )
    if retailer is None or not retailer.enabled or retailer.id not in COLLECTORS:
        print("ERROR: retailer is not enabled", file=sys.stderr)
        return 2
    review = check_review(
        retailer,
        datetime.now(UTC).date(),
        automation.automation.retailer_review_grace_days,
    )
    if not review.allowed:
        print(f"ERROR: retailer policy review is not current: {review.reason}", file=sys.stderr)
        return 2
    if monitor is None or monitor.canonical_model not in retailer.urls:
        print("ERROR: model has no configured product URL", file=sys.stderr)
        return 2
    url = retailer.urls[monitor.canonical_model]
    checked_at = datetime.now(UTC)
    print(f"LIVE NETWORK ACTIVITY: one bounded GET request to {url}", file=sys.stderr)
    try:
        content = fetch_html(
            url,
            FetchPolicy(
                config.user_agent,
                config.request_timeout_seconds,
                config.response_size_limit_bytes,
                config.maximum_transient_retries,
            ),
        )
        raw = COLLECTORS[retailer.id]().parse(content, url, checked_at)
        threshold = thresholds.thresholds[monitor.canonical_model]
        observations = [
            qualify(
                item,
                QualificationPolicy(
                    Decimal(str(threshold.buy_price_aud))
                    if threshold.buy_price_aud is not None
                    else None,
                    threshold.approved,
                    Decimal(str(thresholds.qualification.minimum_warranty_years)),
                    retailer.established_australian_retailer
                    or retailer.approved_direct_manufacturer,
                    frozenset(item.canonical_model for item in monitors if item.enabled),
                    thresholds.qualification.require_field_evidence,
                ),
            )
            for item in raw
        ]
        health = CollectorHealth(
            retailer=retailer.name,
            status=CollectorStatus.SUCCESS,
            checked_at_utc=checked_at,
            source_url=HttpUrl(url),
            observations=len(observations),
        )
    except (FetchError, ParserError, ValueError) as exc:
        code = exc.code if isinstance(exc, FetchError) else "parser_error"
        health = CollectorHealth(
            retailer=retailer.name,
            status=CollectorStatus.FAILED,
            checked_at_utc=checked_at,
            source_url=HttpUrl(url),
            observations=0,
            error_code=code,
            error_message=str(exc),
        )
        print(health.model_dump_json(indent=2), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "collector_health": health.model_dump(mode="json"),
                "observations": [item.model_dump(mode="json") for item in observations],
                "write_requested": write,
            },
            indent=2,
        )
    )
    if write:
        for observation in observations:
            path = store_daily_observation(
                ROOT / "data/history",
                observation,
                retention_months=config.history_retention_months,
            )
            print(f"WROTE: {path}", file=sys.stderr)
        update_current(ROOT / "data/current.json", observations, health)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="monitor-watch")
    commands = parser.add_subparsers(dest="command")
    for name in ("smoke", "collect"):
        command = commands.add_parser(name, help="perform one explicit live product request")
        command.add_argument("--retailer", required=True, choices=sorted(COLLECTORS))
        command.add_argument("--model", required=True)
        command.add_argument("--write", action="store_true")
    commands.add_parser("dashboard", help="rebuild static dashboard data")
    commands.add_parser("validate", help="validate all configuration and evidence data")
    collect_all = commands.add_parser("collect-all", help="explicitly collect all configured pages")
    collect_all.add_argument("--write", action="store_true")
    explain = commands.add_parser("explain", help="explain a current offer")
    explain.add_argument("--retailer", required=True)
    explain.add_argument("--model", required=True)
    alerts = commands.add_parser("evaluate-alerts", help="evaluate current offers")
    alerts.add_argument("--dry-run", action="store_true", default=True)
    alerts.add_argument("--live", action="store_true")
    commands.add_parser("check-retailer-reviews", help="check legal/robots review dates")
    commands.add_parser("automation-output", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.command in {"smoke", "collect"}:
        return _collect(args.retailer, args.model, args.write)
    if args.command == "collect-all":
        config = load_retailers(ROOT / "config/retailers.yaml")
        collection_results = [
            _collect(retailer.id, model, args.write)
            for retailer in config.retailers
            if retailer.enabled and retailer.id in COLLECTORS
            for model in retailer.urls
        ]
        return max(collection_results, default=0)
    if args.command == "explain":
        current = json.loads((ROOT / "data/current.json").read_text(encoding="utf-8"))
        offers = [
            item
            for item in current["offers"]
            if item["retailer"].casefold() == args.retailer.casefold()
            and item["canonical_model"].casefold() == args.model.casefold()
        ]
        if not offers:
            print("No current matching observation.")
            return 1
        print(json.dumps(offers, indent=2))
        return 0
    if args.command == "evaluate-alerts":
        config = load_retailers(ROOT / "config/retailers.yaml")
        thresholds = load_thresholds(ROOT / "config/thresholds.yaml")
        automation = load_automation(ROOT / "config/automation.yaml")
        current = json.loads((ROOT / "data/current.json").read_text(encoding="utf-8"))
        retailer_by_name = {item.name: item for item in config.retailers}
        candidates = []
        for raw in current["offers"]:
            offer = OfferObservation.model_validate(raw)
            retailer = retailer_by_name.get(offer.retailer)
            threshold = thresholds.thresholds.get(offer.canonical_model)
            if threshold is not None:
                candidate = evaluate_offer(
                    offer,
                    threshold,
                    retailer_enabled=bool(retailer and retailer.enabled),
                    price_band_aud=automation.automation.alert_price_band_aud,
                )
                if candidate is not None:
                    candidates.append(candidate)
        print(json.dumps([candidate.__dict__ for candidate in candidates], indent=2))
        if not args.live:
            return 0
        if not automation.automation.create_price_alerts:
            print("ERROR: create_price_alerts is disabled", file=sys.stderr)
            return 2
        token = os.environ.get("GITHUB_TOKEN")
        repository = os.environ.get("GITHUB_REPOSITORY")
        if not token or not repository:
            print("ERROR: GITHUB_TOKEN and GITHUB_REPOSITORY are required", file=sys.stderr)
            return 2
        client = GitHubIssueClient(repository, token)
        for candidate in candidates:
            create_if_missing(candidate, client)
        return 0
    if args.command == "check-retailer-reviews":
        config = load_retailers(ROOT / "config/retailers.yaml")
        automation = load_automation(ROOT / "config/automation.yaml")
        review_results = [
            check_review(
                retailer,
                datetime.now(UTC).date(),
                automation.automation.retailer_review_grace_days,
            )
            for retailer in config.retailers
            if retailer.enabled
        ]
        for result in review_results:
            print(f"{result.retailer_id}: {result.reason}")
        return 0 if all(result.allowed for result in review_results) else 1
    if args.command == "automation-output":
        settings = load_automation(ROOT / "config/automation.yaml").automation
        output = os.environ.get("GITHUB_OUTPUT")
        lines = [
            f"commit_observations={str(settings.commit_observations).lower()}",
            f"create_price_alerts={str(settings.create_price_alerts).lower()}",
            f"publish_dashboard={str(settings.publish_dashboard).lower()}",
        ]
        if output:
            with Path(output).open("a", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
        else:
            print("\n".join(lines))
        return 0
    if args.command == "dashboard":
        print(build_dashboard(ROOT))
        return 0
    if args.command == "validate":
        monitors = load_monitors(ROOT / "config/monitors.yaml")
        retailers = load_retailers(ROOT / "config/retailers.yaml")
        thresholds = load_thresholds(ROOT / "config/thresholds.yaml")
        load_automation(ROOT / "config/automation.yaml")
        specifications = json.loads((ROOT / "data/specifications.json").read_text(encoding="utf-8"))
        active_models = {item.canonical_model for item in monitors if item.enabled}
        if set(thresholds.thresholds) != active_models:
            raise ValueError("threshold models must exactly match active models")
        spec_models = {item["canonical_model"] for item in specifications["models"]}
        if spec_models != active_models:
            raise ValueError("specification models must exactly match active models")
        for item in specifications["models"]:
            facts = set(item["facts"])
            supported = {field for evidence in item["evidence"] for field in evidence["supports"]}
            if not facts <= supported:
                raise ValueError(f"uncited specification facts: {item['canonical_model']}")
        for retailer in retailers.retailers:
            if not set(retailer.urls) <= active_models:
                raise ValueError(f"retailer has URL for inactive model: {retailer.id}")
        current = json.loads((ROOT / "data/current.json").read_text(encoding="utf-8"))
        for raw in current["offers"]:
            OfferObservation.model_validate(raw)
        for partition in (ROOT / "data/history").glob("????-??.json"):
            load_partition(partition)
        print("configuration and evidence data valid")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
