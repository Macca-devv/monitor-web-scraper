"""Pure alert evaluation plus a narrow, injectable GitHub Issues integration."""

import html
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from urllib.parse import quote

from monitor_watch.config import Threshold
from monitor_watch.models import OfferObservation, QualificationStatus


@dataclass(frozen=True)
class AlertCandidate:
    key: str
    title: str
    body: str
    label: str = "price-alert"


class IssueClient(Protocol):
    def list_open_issue_bodies(self) -> list[str]: ...

    def create_issue(self, title: str, body: str, labels: list[str]) -> None: ...


def evaluate_offer(
    offer: OfferObservation,
    threshold: Threshold,
    *,
    retailer_enabled: bool,
    price_band_aud: int,
) -> AlertCandidate | None:
    if not retailer_enabled or offer.qualification_status is not QualificationStatus.QUALIFIED:
        return None
    if not threshold.approved or threshold.approved_at is None or not threshold.approved_by:
        return None
    if threshold.buy_price_aud is None or offer.effective_price_aud > Decimal(
        str(threshold.buy_price_aud)
    ):
        return None
    if offer.delivery_aud is None or not _warranty_known(offer):
        return None
    required = {
        "advertised_model",
        "price_aud",
        "condition",
        "stock_status",
        "seller",
        "australian_stock",
    }
    if not required <= offer.field_evidence.keys():
        return None
    band = int(offer.effective_price_aud // price_band_aud) * price_band_aud
    raw_key = f"{offer.canonical_model}|{offer.retailer}|{band}"
    key = quote(raw_key, safe="")
    safe_model = _safe(offer.canonical_model)
    safe_retailer = _safe(offer.retailer)
    body = "\n".join(
        [
            f"<!-- monitor-watch:{key} -->",
            "## Qualified Australian monitor offer",
            "",
            f"- Model: {safe_model}",
            f"- Retailer: {safe_retailer}",
            f"- Item price: AUD {offer.price_aud}",
            f"- Delivery: AUD {offer.delivery_aud}",
            f"- Effective price: AUD {offer.effective_price_aud}",
            f"- Condition: {_safe(offer.condition.value)}",
            f"- Stock: {_safe(offer.stock_status.value)}",
            f"- Warranty: {_safe(_warranty_text(offer))}",
            f"- Captured: {offer.captured_at_utc.isoformat()}",
            f"- Source: <{offer.listing_url}>",
            "",
            "All mandatory qualification fields carried source evidence at evaluation time.",
        ]
    )
    return AlertCandidate(
        key, f"Price alert: {safe_model} at AUD {offer.effective_price_aud}", body
    )


def create_if_missing(candidate: AlertCandidate, client: IssueClient) -> bool:
    marker = f"<!-- monitor-watch:{candidate.key} -->"
    if any(marker in body for body in client.list_open_issue_bodies()):
        return False
    client.create_issue(candidate.title, candidate.body, [candidate.label])
    return True


class GitHubIssueClient:
    def __init__(self, repository: str, token: str) -> None:
        self.api = f"https://api.github.com/repos/{repository}"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "monitor-watch-au/0.2",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def list_open_issue_bodies(self) -> list[str]:
        payload = self._request("GET", "/issues?state=open&labels=price-alert&per_page=100")
        return [str(item.get("body") or "") for item in payload if isinstance(item, dict)]

    def create_issue(self, title: str, body: str, labels: list[str]) -> None:
        self._request("POST", "/issues", {"title": title, "body": body, "labels": labels})

    def _request(
        self, method: str, path: str, body: dict[str, object] | None = None
    ) -> list[object]:
        data = json.dumps(body).encode() if body is not None else None
        # The base is constructed locally as an HTTPS api.github.com URL.
        request = urllib.request.Request(  # noqa: S310
            self.api + path, data=data, headers=self.headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
                decoded: object = json.loads(response.read(1_000_000))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("GitHub issue API request failed") from exc
        return decoded if isinstance(decoded, list) else []


def _safe(value: str) -> str:
    return html.escape(value.replace("\r", " ").replace("\n", " "), quote=True)


def _warranty_known(offer: OfferObservation) -> bool:
    return offer.manufacturer_warranty_years is not None or offer.seller_warranty_years is not None


def _warranty_text(offer: OfferObservation) -> str:
    value = offer.manufacturer_warranty_years or offer.seller_warranty_years
    return f"{value} years" if value is not None else "unknown"
