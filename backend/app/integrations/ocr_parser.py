"""Conservative fast path for explicit, independently reconciled IDR receipts.

Unknown rows are a reason to ask the model, not to discard purchased-item evidence.
This deliberately does not attempt to understand arbitrary receipt layouts.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.integrations.llm import LlmExtractionOutput, LlmLineItem
from app.services.money import receipt_money


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: Decimal


_MONEY = r"(?:Rp\.?\s*|IDR\s*)?\d+(?:[.,]\d+)*"
_ITEM = re.compile(
    rf"(?P<description>.+?)\s+(?P<quantity>\d+)\s*[x×]\s*"
    rf"(?P<price>{_MONEY})\s+(?P<total>{_MONEY})", re.I,
)
_AMOUNT = re.compile(
    rf"(?P<label>grand total|total bayar|jumlah bayar|total|sub\s*total|pajak|tax|diskon|discount)"
    rf"\s*:?\s*(?P<amount>{_MONEY})", re.I,
)
_DATE = re.compile(
    r"(?:tanggal|date|tgl)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/-]\d{2}[/-]\d{4})", re.I,
)
_CATEGORIES = {
    "meals": r"\b(nasi|ayam|mie|mi|bakso|soto|teh|kopi|air mineral|jus)\b",
    "fuel": r"\b(pertalite|pertamax|dexlite|solar|bensin|bbm)\b",
    "toll_parking": r"\b(parkir|parking|tol|toll)\b",
    "hotel": r"\b(kamar|room|menginap)\b",
}


def _money(text: str) -> Decimal:
    cleaned = re.sub(r"(?i)^(?:rp\.?|idr)\s*", "", text.strip())
    # Commas with three trailing digits are not Indonesian decimal notation.
    if re.search(r",\d{3}(?:\D|$)", cleaned):
        raise ValueError("ambiguous money separator")
    value = Decimal(receipt_money(cleaned))
    if not value.is_finite() or value < 0:
        raise ValueError("invalid amount")
    return value


def parse_receipt(lines: tuple[OcrLine, ...]) -> LlmExtractionOutput | None:
    """Return evidence only for the narrow supported shape; otherwise abstain."""
    if not 4 <= len(lines) <= 150:
        return None
    vendor = re.sub(r"(?i)^(?:vendor|toko|merchant)\s*:\s*", "", lines[0].text).strip()
    if (
        not 2 <= len(vendor) <= 255
        or not re.search(r"[A-Za-z]", vendor)
        or re.search(r"\d|https?://|@|\b(?:total|tanggal|date|struk|nota|receipt|invoice)\b", vendor, re.I)
    ):
        return None
    receipt_date = None
    amounts: dict[str, Decimal] = {}
    items: list[LlmLineItem] = []
    categories: set[str] = set()
    saw_currency = False
    try:
        for line in lines[1:]:
            text = line.text.strip()
            if re.fullmatch(r"[-=_\s]+|terima kasih|thank you", text, re.I):
                continue
            if match := _DATE.fullmatch(text):
                if receipt_date is not None:
                    return None
                value = match[1]
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    day, month, year = re.split(r"[/-]", value)
                    value = f"{year}-{month}-{day}"
                receipt_date = date.fromisoformat(value).isoformat()
            elif match := _AMOUNT.fullmatch(text):
                label = re.sub(r"\s+", "", match["label"].lower())
                key = (
                    "subtotal" if label == "subtotal" else
                    "tax" if label in ("pajak", "tax") else
                    "discount" if label in ("diskon", "discount") else "total"
                )
                if key in amounts:
                    return None
                amounts[key] = _money(match["amount"])
                saw_currency |= bool(re.search(r"\b(?:rp|idr)\b", match["amount"], re.I))
            elif match := _ITEM.fullmatch(text):
                quantity = Decimal(match["quantity"])
                price, total = _money(match["price"]), _money(match["total"])
                if quantity * price != total:
                    return None
                items.append(LlmLineItem(
                    description=match["description"], quantity=quantity,
                    unit_price=price, total=total,
                ))
                found = {key for key, pattern in _CATEGORIES.items()
                         if re.search(pattern, match["description"], re.I)}
                if len(found) != 1:
                    return None
                categories.update(found)
            else:
                return None
        if not receipt_date or not items or "total" not in amounts or not saw_currency or len(categories) != 1:
            return None
        item_sum = sum((item.total for item in items), Decimal(0))
        if "subtotal" in amounts and amounts["subtotal"] != item_sum:
            return None
        if item_sum + amounts.get("tax", Decimal(0)) - amounts.get("discount", Decimal(0)) != amounts["total"]:
            return None
        return LlmExtractionOutput(
            vendor=vendor, receipt_date=receipt_date, total=amounts["total"],
            currency="IDR", category=categories.pop(),
            confidence=min(line.confidence for line in lines),
            subtotal=amounts.get("subtotal"), tax=amounts.get("tax"),
            discount=amounts.get("discount"), line_items=items, line_items_complete=True,
        )
    except (ValueError, InvalidOperation, ValidationError):
        return None
