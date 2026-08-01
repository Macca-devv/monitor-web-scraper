"""Umart product parser using schema.org Product JSON-LD."""

import json
import re
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from monitor_watch.models import (
    Condition,
    FieldEvidence,
    OfferObservation,
    QualificationStatus,
    ReturnFreightParty,
    SourceMethod,
    StockStatus,
)
from monitor_watch.normalisation import parse_aud
from monitor_watch.retailers.base import RetailerCollector


class ParserError(ValueError):
    """Structured product data was missing or unsafe to interpret."""


def _json_objects(value: object) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, list):
            yield from (item for item in graph if isinstance(item, dict))
    elif isinstance(value, list):
        yield from (item for item in value if isinstance(item, dict))


class UmartCollector(RetailerCollector):
    retailer_id = "umart"
    retailer_name = "Umart"
    parser_version = "umart-jsonld-v1"

    def parse(
        self,
        content: str,
        source_url: str,
        captured_at: datetime | None = None,
    ) -> Sequence[OfferObservation]:
        soup = BeautifulSoup(content, "html.parser")
        products: list[dict[str, Any]] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                decoded: object = json.loads(script.get_text())
            except (json.JSONDecodeError, TypeError):
                continue
            products.extend(
                item for item in _json_objects(decoded) if item.get("@type") == "Product"
            )
        if len(products) != 1:
            raise ParserError(f"expected exactly one Product JSON-LD object, found {len(products)}")

        product = products[0]
        offers = product.get("offers")
        if not isinstance(offers, dict):
            raise ParserError("Product offers must be a single object")
        model = product.get("mpn")
        name = product.get("name")
        currency = offers.get("priceCurrency")
        raw_price = offers.get("price")
        if not isinstance(model, str) or not model.strip():
            raise ParserError("missing exact manufacturer part number")
        if not isinstance(name, str) or not name.strip():
            raise ParserError("missing product name")
        if currency != "AUD" or not isinstance(raw_price, str | int | float):
            raise ParserError("missing unambiguous AUD offer price")

        price = parse_aud(f"AUD {raw_price}")
        observed_at = captured_at or datetime.now(UTC)
        evidence = {
            key: FieldEvidence(
                source_url=HttpUrl(source_url),
                source_path=path,
                captured_at_utc=observed_at,
            )
            for key, path in {
                "advertised_model": "Product.mpn",
                "price_aud": "Product.offers.price + priceCurrency",
                "condition": "Product.offers.itemCondition",
                "stock_status": "Product.offers.availability",
                "seller": "Product.offers.seller.name",
            }.items()
        }
        if self._australian_stock(offers) is not None:
            evidence["australian_stock"] = FieldEvidence(
                source_url=HttpUrl(source_url),
                source_path="Product.offers.shippingDetails.shippingDestination.addressCountry",
                captured_at_utc=observed_at,
            )
        warranty = self._warranty_years(soup.get_text(" ", strip=True))
        if warranty is not None:
            evidence["manufacturer_warranty_years"] = FieldEvidence(
                source_url=HttpUrl(source_url),
                source_path="visible page text: Warranty Period",
                captured_at_utc=observed_at,
            )
        return [
            OfferObservation(
                canonical_model=self._canonical_model(model),
                advertised_model=model,
                retailer=self.retailer_name,
                seller=self.retailer_name,
                listing_url=HttpUrl(source_url),
                price_aud=price,
                delivery_aud=None,
                effective_price_aud=price,
                condition=self._condition(offers.get("itemCondition")),
                stock_status=self._stock(offers.get("availability")),
                australian_stock=self._australian_stock(offers),
                manufacturer_warranty_years=warranty,
                seller_warranty_years=None,
                dead_pixel_policy=None,
                return_window_days=None,
                return_freight_party=ReturnFreightParty.UNKNOWN,
                marketplace=False,
                grey_import=False,
                captured_at_utc=observed_at,
                source_method=SourceMethod.JSON_LD,
                qualification_status=QualificationStatus.PENDING,
                rejection_reasons=[],
                parser_version=self.parser_version,
                field_evidence=evidence,
            )
        ]

    @staticmethod
    def _canonical_model(model: str) -> str:
        known = {
            "32GR93U-B": "LG UltraGear 32GR93U-B",
            "U3225QE": "Dell UltraSharp U3225QE",
        }
        try:
            return known[model.strip().upper()]
        except KeyError as exc:
            raise ParserError(f"unconfigured exact model: {model!r}") from exc

    @staticmethod
    def _condition(value: object) -> Condition:
        if value == "https://schema.org/NewCondition":
            return Condition.NEW
        return Condition.UNKNOWN

    @staticmethod
    def _stock(value: object) -> StockStatus:
        mapping = {
            "https://schema.org/InStock": StockStatus.IN_STOCK,
            "https://schema.org/PreOrder": StockStatus.AVAILABLE_TO_ORDER,
            "https://schema.org/BackOrder": StockStatus.BACKORDER,
            "https://schema.org/OutOfStock": StockStatus.OUT_OF_STOCK,
        }
        if not isinstance(value, str):
            return StockStatus.UNKNOWN
        return mapping.get(value, StockStatus.UNKNOWN)

    @staticmethod
    def _warranty_years(text: str) -> Decimal | None:
        match = re.search(
            r"(?:Warranty\s+Period\s*:?\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*Year(?:s)?\s+Warranty)",
            text,
            re.I,
        )
        return Decimal(next(group for group in match.groups() if group)) if match else None

    @staticmethod
    def _australian_stock(offers: dict[str, Any]) -> bool | None:
        shipping = offers.get("shippingDetails")
        if not isinstance(shipping, dict):
            return None
        destination = shipping.get("shippingDestination")
        if not isinstance(destination, dict):
            return None
        return True if destination.get("addressCountry") == "AU" else None
