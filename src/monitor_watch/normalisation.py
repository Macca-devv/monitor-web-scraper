"""Conservative text, model, condition, and AUD normalisation."""

import re
from decimal import Decimal, InvalidOperation

from monitor_watch.models import Condition

_MODEL_CHARS = re.compile(r"[^A-Z0-9]")
_PRICE = re.compile(r"(?:AUD\s*|A\$\s*|\$\s*)?([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)


def model_key(value: str) -> str:
    return _MODEL_CHARS.sub("", value.upper())


def matches_model(advertised: str, canonical: str, aliases: list[str]) -> bool:
    advertised_key = model_key(advertised)
    candidates = {model_key(canonical), *(model_key(alias) for alias in aliases)}
    return advertised_key in candidates


def parse_aud(value: str) -> Decimal:
    match = _PRICE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"not an unambiguous AUD price: {value!r}")
    try:
        return Decimal(match.group(1).replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"invalid AUD price: {value!r}") from exc


def classify_condition(value: str) -> Condition:
    text = value.casefold()
    if "factory second" in text or "factory-second" in text:
        return Condition.FACTORY_SECOND
    if "refurb" in text or "renewed" in text:
        return Condition.REFURBISHED
    if re.search(r"\bused\b|pre[- ]owned", text):
        return Condition.USED
    if re.search(r"\bnew\b|brand[- ]new", text):
        return Condition.NEW
    return Condition.UNKNOWN
