"""Offline acceptance evaluation of the real claim graph using synthetic adapters."""

import argparse
import json
import logging
import platform
import subprocess
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median

from app.agent.runtime import GraphResources
from app.config import Settings
from app.errors import ApplicationError
from app.integrations.anomaly import RuleBasedAnomalyScorer
from app.integrations.duplicate import AttributeDuplicateDetector
from app.integrations.mock import MockReceiptExtractor
from app.integrations.policy_local import LocalPolicyEvaluator, LocalPolicyRetriever
from app.integrations.quality import FileQualityChecker
from app.repositories.memory import InMemoryRepositories
from app.schemas.core import FieldConfidence
from app.services.clarification import ClarificationService
from app.services.decision import DecisionEngine
from app.services.extraction import ExtractionService
from app.services.intake import IntakeService, ReceiptUpload
from app.services.processing import ClaimProcessingService
from app.services.validation import ValidationService

SCENARIOS = [
    ("valid_meal", "CATEGORY:MEALS", "60000", "approved"),
    ("over_fuel_limit", "CATEGORY:FUEL SPBU", "200000", "rejected"),
    ("prohibited_item", "CATEGORY:MEALS ALCOHOL", "60000", "rejected"),
    ("high_amount", "ordinary", "700000", "escalated"),
    ("blurry_receipt", "LOW_CONFIDENCE", "60000", "needs_clarification"),
    ("missing_date", "CATEGORY:MEALS", "60000", "needs_clarification"),
    ("ambiguous_total", "ordinary", "60000", "needs_clarification"),
    ("subtotal_selected", "ordinary", "60000", "needs_clarification"),
    ("unsupported_currency", "ordinary", "60000", "needs_clarification"),
    ("future_date", "FUTURE_DATE", "60000", "needs_clarification"),
    ("line_item_mismatch", "TOTAL_MISMATCH", "60000", "needs_clarification"),
    ("policy_unavailable", "CATEGORY:MEALS", "60000", "failed"),
    ("provider_timeout", "ordinary", "60000", "failed"),
    ("clarification_resume", "CATEGORY:MEALS", "240000", "approved"),
    ("clarification_exhausted", "LOW_CONFIDENCE", "60000", "escalated"),
    ("duplicate", "ordinary", "60000", "rejected"),
    ("anomaly", "ordinary", "100000", "escalated"),
    ("idempotent_replay", "CATEGORY:MEALS", "60000", "approved"),
]


class ScenarioExtractor(MockReceiptExtractor):
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        self.calls = 0

    def extract(self, **kwargs):
        self.calls += 1
        if self.scenario == "provider_timeout":
            raise ApplicationError("provider_timeout", "Synthetic provider timeout", 504)
        result = super().extract(**kwargs)
        changes = {
            "missing_date": {"receipt_date": FieldConfidence(value=None, confidence=0)},
            "ambiguous_total": {"total_ambiguous": True},
            "subtotal_selected": {"subtotal": Decimal("60000"), "tax": Decimal("6000")},
            "unsupported_currency": {"currency": FieldConfidence(value="XXX", confidence=1)},
        }
        return result.model_copy(update=changes.get(self.scenario, {}))


class ScenarioPolicy(LocalPolicyRetriever):
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario

    def retrieve(self, **kwargs):
        if self.scenario == "policy_unavailable":
            raise ApplicationError("policy_unavailable", "Synthetic unavailable policy", 503)
        return super().retrieve(**kwargs)


def build_harness(settings: Settings, extractor, policy_retriever):
    db = InMemoryRepositories()
    resources = GraphResources(owner=db)
    resources.settings = settings
    extraction = ExtractionService(
        db.claims, db.receipts, db.file_storage, db.runs, db.extractions, db.attempts,
        db.clarifications, db.findings, db.evaluations, db.signals, db.decisions,
        db.history, db.reviews, db.audit,
        AttributeDuplicateDetector(db.history, db.receipts, db.extractions), RuleBasedAnomalyScorer(),
        extractor, ValidationService(settings), policy_retriever, LocalPolicyEvaluator(), DecisionEngine(settings), settings,
    )
    processing = ClaimProcessingService(db.claims, db.runs, extraction, graph_resources=resources)
    intake = IntakeService(db.claims, db.receipts, db.file_storage, FileQualityChecker(), db.audit, settings, resources)
    return db, resources, processing, intake


def run_scenario(name: str, marker: str, amount: str, expected: str) -> dict:
    settings = Settings(_env_file=None, environment="test", demo_mode=False, storage_backend="memory",
                        provider_mode="mock", policy_mode="local", anomaly_mode="rules", max_clarification_rounds=2)
    extractor = ScenarioExtractor(name)
    db, resources, processing, intake = build_harness(settings, extractor, ScenarioPolicy(name))

    def create(suffix: str, value: str = amount):
        claim, _, _ = intake.create_claim(employee_id="synthetic-employee", currency="IDR", declared_amount=Decimal(value),
            files=[ReceiptUpload(filename="synthetic.pdf", media_type="application/pdf",
                                 content=f"%PDF-1.7\n{marker} {suffix}\n%%EOF".encode())], idempotency_key=None)
        return claim

    started = time.perf_counter()
    human_actions = 0
    error = None
    try:
        if name == "anomaly":
            for index in range(3):
                processing.process_claim(create(str(index), str(10000 + index)).id)
        if name == "duplicate":
            processing.process_claim(create("first").id)
        claim = create("target")
        outcome = processing.process_claim(claim.id)
        if name in ("clarification_resume", "clarification_exhausted"):
            service = ClarificationService(db.claims, db.clarifications, db.context, db.audit, processing)
            for _ in range(settings.max_clarification_rounds):
                if outcome.claim.status != "needs_clarification":
                    break
                question = db.clarifications.latest_for_claim(claim.id)
                _, outcome, _ = service.submit_answer(claim.id, question.id, answer="4", answered_by="synthetic-employee")
                human_actions += 1
        if name == "idempotent_replay":
            calls_before = extractor.calls
            decision_before = outcome.decision.id
            repeated = processing.process_claim(claim.id)
            assert repeated.decision.id == decision_before and extractor.calls == calls_before
            assert len(db.decisions.list_for_claim(claim.id)) == 1
        actual = str(outcome.claim.status)
        stage = processing.graph.get_state({"configurable": {"thread_id": str(claim.id)}}).values["stage"]
        reason_codes = outcome.decision.reason_codes if outcome.decision else []
    except ApplicationError as exc:
        actual, error, stage, reason_codes = "failed", exc.code, "failed", []
    finally:
        resources.close()
    return {"scenario": name, "expected": expected, "actual": actual, "passed": actual == expected,
            "false_approval": actual == "approved" and expected != "approved", "error_code": error,
            "duration_ms": round((time.perf_counter() - started) * 1000), "provider_calls": extractor.calls,
            "human_actions": human_actions, "final_stage": stage, "reason_codes": reason_codes}


def evaluate() -> dict:
    rows = [run_scenario(*scenario) for scenario in SCENARIOS]
    durations = sorted(row["duration_ms"] for row in rows)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip() or "unavailable"
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False).stdout.strip())
    return {"schema_version": 1, "evaluated_at": datetime.now(UTC).isoformat(), "git_revision": revision, "working_tree_dirty": dirty,
            "python": platform.python_version(), "dataset": "synthetic_acceptance_v1", "provider_mode": "mock",
            "policy_mode": "local", "anomaly_mode": "rules", "live_verified": False,
            "total": len(rows), "passed": sum(row["passed"] for row in rows),
            "false_approvals": sum(row["false_approval"] for row in rows),
            "expected_failure_cases": sum(row["expected"] == "failed" for row in rows),
            "p50_ms": median(durations), "p95_ms": durations[max(0, (95 * len(durations) + 99) // 100 - 1)],
            "provider_cost": None, "cost_basis": "mock_no_external_calls", "cases": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    logging.disable(logging.INFO)
    report = evaluate()
    encoded = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if report["passed"] != report["total"] or report["false_approvals"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
