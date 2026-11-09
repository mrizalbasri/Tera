"""Deterministic validation of extracted receipt data (FR-04).

Failures are structured findings, never exceptions, so the decision engine
(FR-08) can weigh them with full context.
"""

from datetime import date, UTC, datetime
from decimal import Decimal, DecimalException
from uuid import UUID

from app.config import Settings
from app.schemas.core import Claim, ExtractionResult, ValidationFinding
from app.domain.enums import Severity

SUPPORTED_CURRENCIES = {"IDR"}
SUPPORTED_CATEGORIES = {"meals", "fuel", "toll_parking", "hotel", "other"}
REQUIRED_FIELDS = ("vendor", "receipt_date", "total", "currency", "category")
LINE_ITEM_TOLERANCE = Decimal("0.01")


class ValidationService:
    def __init__(self, settings: Settings | None = None) -> None:
        if not isinstance(settings, Settings):
            from app.config import get_settings

            settings = get_settings()
        self._settings = settings

    def validate(
        self,
        *,
        claim: Claim,
        extraction: ExtractionResult,
        processing_run_id: UUID,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []

        def add(
            rule_id: str,
            passed: bool,
            explanation: str,
            *,
            severity: Severity = Severity.INFO,
            actual: object = None,
            expected: str | None = None,
            reason_code: str | None = None,
        ) -> None:
            findings.append(
                ValidationFinding(
                    claim_id=claim.id,
                    processing_run_id=processing_run_id,
                    extraction_id=extraction.id,
                    rule_id=rule_id,
                    passed=passed,
                    severity=severity if not passed else Severity.INFO,
                    actual=actual,
                    expected=expected,
                    reason_code=reason_code if not passed else None,
                    explanation=explanation,
                )
            )

        for field in REQUIRED_FIELDS:
            confidence = getattr(extraction, field)
            value = confidence.value
            present = value is not None and str(value).strip() != ""
            add(
                f"required_{field}",
                present,
                f"Required field '{field}' was extracted."
                if present
                else f"Required field '{field}' is missing from the extraction.",
                severity=Severity.BLOCKING,
                reason_code="required_field_missing",
            )

        total = _as_decimal(extraction.total.value)
        complete_items = bool(extraction.line_items) and extraction.line_items_complete and not extraction.line_items_derived
        add("line_items_complete", complete_items,
            "Purchased-item evidence must be complete before automatic approval.",
            severity=Severity.BLOCKING, reason_code="line_items_incomplete")
        if total is None and extraction.total.value is not None:
            add("total_positive_finite", False, "Total must be a finite positive amount.",
                severity=Severity.BLOCKING, reason_code="invalid_total")
        if total is not None:
            add("total_positive_finite", total.is_finite() and total > 0,
                "Total must be a finite positive amount.", severity=Severity.BLOCKING,
                reason_code="invalid_total")
            add("total_unambiguous", not extraction.total_ambiguous,
                "Final payable total must be distinguishable from subtotal and other amounts.",
                severity=Severity.BLOCKING, reason_code="total_ambiguous")
            if extraction.subtotal is not None and total.is_finite():
                expected_total = extraction.subtotal + (extraction.tax or Decimal(0)) - (extraction.discount or Decimal(0))
                add("total_matches_breakdown", abs(total - expected_total) <= LINE_ITEM_TOLERANCE,
                    "Total must match the independently observed subtotal, tax and discount.",
                    severity=Severity.BLOCKING, actual=str(total), expected=str(expected_total),
                    reason_code="total_breakdown_mismatch")
            if extraction.line_items and not extraction.line_items_derived and total.is_finite():
                line_sum = sum(
                    (item.total for item in extraction.line_items), Decimal("0")
                )
                item_total = (extraction.subtotal if extraction.subtotal is not None else
                              total - (extraction.tax or Decimal(0)) + (extraction.discount or Decimal(0)))
                matches = abs(line_sum - item_total) <= LINE_ITEM_TOLERANCE
                add(
                    "total_matches_line_items",
                    matches,
                    f"Item amount {item_total} matches the line item sum {line_sum}."
                    if matches
                    else f"Item amount {item_total} does not match the line item sum {line_sum}.",
                    severity=Severity.BLOCKING,
                    actual=line_sum,
                    expected=str(item_total),
                    reason_code="total_line_item_mismatch",
                )

        receipt_date = extraction.receipt_date.value
        if isinstance(receipt_date, datetime):
            receipt_date = receipt_date.date()
        if isinstance(receipt_date, str):
            try:
                receipt_date = date.fromisoformat(receipt_date)
            except ValueError:
                add("receipt_date_valid", False, "Receipt date must be a valid ISO date.",
                    severity=Severity.BLOCKING, reason_code="invalid_receipt_date")
                receipt_date = None
        if receipt_date is not None and not isinstance(receipt_date, date):
            add("receipt_date_valid", False, "Receipt date must be a valid ISO date.",
                severity=Severity.BLOCKING, reason_code="invalid_receipt_date")
            receipt_date = None
        if isinstance(receipt_date, date):
            today = datetime.now(UTC).date()
            not_future = receipt_date <= today
            add(
                "receipt_date_not_in_future",
                not_future,
                f"Receipt date {receipt_date} is not in the future."
                if not_future
                else f"Receipt date {receipt_date} is in the future.",
                severity=Severity.BLOCKING,
                actual=receipt_date,
                expected=f"<= {today}",
                reason_code="receipt_date_in_future",
            )
            age_days = (datetime.now(UTC).date() - receipt_date).days
            within_window = 0 <= age_days <= self._settings.max_claim_age_days
            add(
                "receipt_within_claim_window",
                within_window,
                f"Receipt is {age_days} days old, within the "
                f"{self._settings.max_claim_age_days}-day claim window."
                if within_window
                else f"Receipt is {age_days} days old, beyond the "
                f"{self._settings.max_claim_age_days}-day claim window.",
                severity=Severity.BLOCKING,
                actual=age_days,
                expected=f"<= {self._settings.max_claim_age_days} days",
                reason_code="receipt_too_old",
            )

        currency = str(extraction.currency.value or "")
        currency_supported = currency in SUPPORTED_CURRENCIES
        add(
            "currency_supported",
            currency_supported,
            f"Currency {currency} is supported."
            if currency_supported
            else f"Currency {currency} is not supported.",
            severity=Severity.BLOCKING,
            actual=currency,
            expected=", ".join(sorted(SUPPORTED_CURRENCIES)),
            reason_code="unsupported_currency",
        )
        if currency != claim.currency:
            add(
                "currency_matches_claim",
                False,
                f"Receipt currency {currency} does not match the claimed "
                f"currency {claim.currency}.",
                severity=Severity.WARNING,
                actual=currency,
                expected=claim.currency,
                reason_code="currency_mismatch",
            )

        category = str(extraction.category.value or "")
        category_supported = category in SUPPORTED_CATEGORIES
        add(
            "category_supported",
            category_supported,
            f"Category {category} is supported."
            if category_supported
            else f"Category {category} is not supported.",
            severity=Severity.BLOCKING,
            actual=category,
            expected=", ".join(sorted(SUPPORTED_CATEGORIES)),
            reason_code="unsupported_category",
        )

        return findings


def _as_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (DecimalException, ValueError):
        return None
