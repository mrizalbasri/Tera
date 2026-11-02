"""Parse printed Indonesian amounts without multiplying an already numeric value."""

import re
from decimal import Decimal


def receipt_money(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = re.sub(r"(?i)^\s*rp\.?\s*", "", value).strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", cleaned):
        return Decimal(cleaned.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d+,\d{1,2}", cleaned):
        return Decimal(cleaned.replace(",", "."))
    return value
