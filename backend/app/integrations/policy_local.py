"""Local versioned expense policy data per the BRD business rules (section 9).

The retrieval stays behind the ``PolicyRetriever`` protocol so a RAG-backed
provider can replace it later without touching the pipeline.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.enums import Severity
from app.errors import ApplicationError, ErrorCode
from app.repositories.protocols import PolicyEvaluator, PolicyRetriever
from app.schemas.core import (
    Claim,
    ExtractionResult,
    Policy,
    PolicyEvaluation,
    PolicyRule,
)

POLICY_ID = "expense-policy"
SUPPORTED_CATEGORIES = ("meals", "fuel", "toll_parking", "hotel", "other")
PROHIBITED_TERMS = ("alkohol", "alcohol", "beer", "wine", "whiskey", "vodka")


def _rule(
    rule_id: str,
    rule_type: str,
    limit: Decimal | None = None,
    *,
    required_terms: list[str] | None = None,
) -> PolicyRule:
    return PolicyRule(
        rule_id=rule_id,
        rule_type=rule_type,
        limit=limit,
        required_terms=required_terms or [],
    )


_CATEGORY_RULES: dict[str, list[PolicyRule]] = {
    "meals": [
        _rule("meal_daily_limit", "max_amount_per_person", Decimal("75000")),
        _rule("receipt_required", "receipt_required"),
    ],
    "fuel": [
        _rule("fuel_daily_limit", "max_amount", Decimal("150000")),
        _rule("receipt_required", "receipt_required"),
        # BRD: fuel claims must be backed by an SPBU receipt.
        _rule("fuel_spbu_required", "vendor_required", required_terms=["spbu"]),
    ],
    "toll_parking": [
        _rule("receipt_required", "receipt_required"),
        # BRD: toll/parking reimburses exactly the receipt amount.
        _rule("toll_amount_matches", "amount_matches_declared"),
    ],
    "hotel": [
        _rule("hotel_nightly_limit", "max_amount", Decimal("600000")),
        _rule("receipt_required", "receipt_required"),
        # BRD: hotel stays require business-trip evidence; missing evidence
        # is clarifiable, not an automatic rejection.
        _rule(
            "hotel_business_trip_required",
            "evidence_required",
            required_terms=["perjalanan dinas"],
        ),
    ],
    "other": [],
}


class LocalPolicyRetriever:
    """Serves versioned policy records from in-repo data."""

    policy_id = POLICY_ID
    version = 1
    effective_from = date(2026, 1, 1)

    def retrieve(self, *, category: str, effective_date: date) -> Policy:
        if effective_date < self.effective_from:
            raise ApplicationError(
                ErrorCode.POLICY_UNAVAILABLE,
                "No policy version is effective for the receipt date.",
                503,
                {"category": category, "effective_from": self.effective_from.isoformat()},
            )
        if category not in SUPPORTED_CATEGORIES:
            raise ApplicationError(
                ErrorCode.POLICY_UNAVAILABLE,
                "No policy covers the extracted category.",
                503,
                {"category": category},
            )
        rules = list(_CATEGORY_RULES[category])
        if category != "other":
            rules.append(
                PolicyRule(
                    rule_id="prohibited_items",
                    rule_type="prohibited_items",
                    prohibited_terms=list(PROHIBITED_TERMS),
                )
            )
        return Policy(
            policy_id=self.policy_id,
            version=self.version,
            category=category,
            effective_from=self.effective_from,
            rules=rules,
        )


class LocalPolicyEvaluator:
    """Evaluates a retrieved policy against one extraction, deterministically."""

    def evaluate(
        self,
        *,
        claim: Claim,
        extraction: ExtractionResult,
        policy: Policy,
        processing_run_id: UUID,
        participants: int = 1,
    ) -> list[PolicyEvaluation]:
        evaluations: list[PolicyEvaluation] = []
        total = self._decimal(extraction.total.value)
        participants = max(participants, 1)
        for rule in policy.rules:
            if rule.rule_type in ("max_amount_per_person", "max_amount"):
                limit = rule.limit
                if rule.rule_type == "max_amount_per_person" and limit is not None:
                    limit = limit * participants
                passed = total is not None and limit is not None and total <= limit
                evaluations.append(
                    self._result(
                        claim=claim,
                        extraction=extraction,
                        policy=policy,
                        processing_run_id=processing_run_id,
                        rule_type=rule.rule_type,
                        rule_id=rule.rule_id,
                        passed=passed,
                        clarifiable=(
                            rule.rule_type == "max_amount_per_person" and not passed
                        ),
                        actual_value=total,
                        limit=limit,
                        reason_code=None if passed else "policy_limit_exceeded",
                        explanation=(
                            f"Receipt total {total} is within the {rule.rule_id} "
                            f"limit for {participants} participant(s)."
                            if passed
                            else (
                                f"Receipt total {total} exceeds the {rule.rule_id} "
                                f"limit of {limit} for {participants} participant(s)."
                            )
                        ),
                    )
                )
            elif rule.rule_type == "receipt_required":
                # Intake guarantees at least one receipt per claim.
                evaluations.append(
                    self._result(
                        claim=claim,
                        extraction=extraction,
                        policy=policy,
                        processing_run_id=processing_run_id,
                        rule_type=rule.rule_type,
                        rule_id=rule.rule_id,
                        passed=True,
                        actual_value=None,
                        limit=None,
                        reason_code=None,
                        explanation="A receipt was attached at intake.",
                    )
                )
            elif rule.rule_type == "vendor_required":
                haystack = self._descriptive_text(extraction)
                matched = any(
                    term in haystack for term in rule.required_terms
                )
                evaluations.append(
                    self._result(
                        claim=claim,
                        extraction=extraction,
                        policy=policy,
                        processing_run_id=processing_run_id,
                        rule_type=rule.rule_type,
                        rule_id=rule.rule_id,
                        passed=matched,
                        actual_value=str(extraction.vendor.value),
                        limit=", ".join(rule.required_terms),
                        reason_code=None if matched else "required_vendor_missing",
                        explanation=(
                            f"Receipt vendor satisfies the {rule.rule_id} "
                            f"requirement."
                            if matched
                            else (
                                f"Receipt is not from the required vendor type; "
                                f"expected it to mention: "
                                f"{', '.join(rule.required_terms)}."
                            )
                        ),
                    )
                )
            elif rule.rule_type == "evidence_required":
                haystack = self._descriptive_text(extraction)
                matched = any(
                    term in haystack for term in rule.required_terms
                )
                evaluations.append(
                    self._result(
                        claim=claim,
                        extraction=extraction,
                        policy=policy,
                        processing_run_id=processing_run_id,
                        rule_type=rule.rule_type,
                        rule_id=rule.rule_id,
                        passed=matched,
                        clarifiable=not matched,
                        actual_value=str(extraction.vendor.value),
                        limit=", ".join(rule.required_terms),
                        reason_code=(
                            None if matched else "business_trip_evidence_required"
                        ),
                        explanation=(
                            f"Business-trip evidence was found on the receipt."
                            if matched
                            else (
                                f"No business-trip evidence found; the receipt "
                                f"must mention: {', '.join(rule.required_terms)}."
                            )
                        ),
                    )
                )
            elif rule.rule_type == "amount_matches_declared":
                declared = self._decimal(claim.declared_amount)
                passed = declared is None or (
                    total is not None and total == declared
                )
                evaluations.append(
                    self._result(
                        claim=claim,
                        extraction=extraction,
                        policy=policy,
                        processing_run_id=processing_run_id,
                        rule_type=rule.rule_type,
                        rule_id=rule.rule_id,
                        passed=passed,
                        actual_value=total,
                        limit=declared,
                        reason_code=None if passed else "amount_mismatch",
                        explanation=(
                            f"Receipt total {total} matches the declared amount."
                            if passed
                            else (
                                f"Receipt total {total} does not match the "
                                f"declared amount {declared}; toll/parking "
                                f"reimburses the receipt amount exactly."
                            )
                        ),
                    )
                )
            elif rule.rule_type == "prohibited_items":
                matched = self._prohibited_matches(extraction, rule)
                evaluations.append(
                    self._result(
                        claim=claim,
                        extraction=extraction,
                        policy=policy,
                        processing_run_id=processing_run_id,
                        rule_type=rule.rule_type,
                        rule_id=rule.rule_id,
                        passed=not matched,
                        actual_value=matched or None,
                        limit=None,
                        reason_code=None if not matched else "prohibited_item",
                        explanation=(
                            "No prohibited items were found on the receipt."
                            if not matched
                            else f"Receipt contains prohibited items: {', '.join(matched)}."
                        ),
                    )
                )
        return evaluations

    def _prohibited_matches(
        self, extraction: ExtractionResult, rule: PolicyRule
    ) -> list[str]:
        haystacks = [item.description.lower() for item in extraction.line_items]
        haystacks.append(str(extraction.vendor.value).lower())
        return [
            term
            for term in rule.prohibited_terms
            if any(term in haystack for haystack in haystacks)
        ]

    @staticmethod
    def _descriptive_text(extraction: ExtractionResult) -> str:
        parts = [str(extraction.vendor.value)]
        parts.extend(item.description for item in extraction.line_items)
        return " ".join(parts).lower()

    def _result(
        self,
        *,
        claim: Claim,
        extraction: ExtractionResult,
        policy: Policy,
        processing_run_id: UUID,
        rule_type: str,
        rule_id: str,
        passed: bool,
        actual_value: object,
        limit: object,
        reason_code: str | None,
        explanation: str,
        clarifiable: bool = False,
    ) -> PolicyEvaluation:
        return PolicyEvaluation(
            claim_id=claim.id,
            processing_run_id=processing_run_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            policy_snapshot=policy.model_dump(mode="json"),
            rule_id=rule_id,
            rule_type=rule_type,
            passed=passed,
            severity=Severity.INFO if passed else Severity.BLOCKING,
            clarifiable=clarifiable,
            actual_value=actual_value,
            limit=limit,
            reason_code=reason_code,
            explanation=explanation,
        )

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        if value is None:
            return None
        return value if isinstance(value, Decimal) else Decimal(str(value))
