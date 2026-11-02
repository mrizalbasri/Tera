"""AnomalyScorer adapter with safe, visible rule fallback."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.enums import Severity, SignalType
from app.integrations.anomaly import RuleBasedAnomalyScorer
from app.integrations.ml_anomaly.features import (
    CategoryContext, FEATURE_NAMES, FEATURE_VERSION, MIN_HISTORY, extract_features, prior_history,
)
from app.schemas.core import Claim, Signal


class SklearnAnomalyScorer:
    def __init__(self, model_path: str, threshold: float = 0.7) -> None:
        self._bundle = None
        self._failure = "model_unavailable"
        self._threshold = Decimal(str(threshold))
        try:
            from app.integrations.ml_anomaly.model import load_model

            self._bundle = load_model(model_path)
        except FileNotFoundError:
            pass
        except Exception:
            # No raw exceptions/paths/model payloads enter logs, evidence or responses.
            self._failure = "model_invalid"

    def score(self, *, claim: Claim, total: Decimal, history: Sequence[Claim],
              processing_run_id: UUID) -> Signal:
        return self.score_with_context(claim=claim, total=total, history=history,
                                       processing_run_id=processing_run_id)

    def score_with_context(
        self, *, claim: Claim, total: Decimal, history: Sequence[Claim],
        processing_run_id: UUID, context: CategoryContext | None = None,
    ) -> Signal:
        prior = prior_history(claim, history)
        if len(prior) < MIN_HISTORY:
            signal = RuleBasedAnomalyScorer().score(
                claim=claim, total=total, history=[], processing_run_id=processing_run_id,
            )
            return signal.model_copy(update={
                "evidence": {"source": "neutral", "reason": "insufficient_history",
                             "usable_history_count": len(prior), "feature_version": FEATURE_VERSION},
                "explanation": "Insufficient comparable prior claims; anomaly score is neutral.",
            })
        reason = self._failure
        if self._bundle is not None:
            try:
                from app.integrations.ml_anomaly.model import predict_scores

                features = extract_features(claim, total, prior, context)
                scores, components = predict_scores(self._bundle, [features])
                score = Decimal(str(scores[0]))
                high = score >= self._threshold
                return Signal(
                    id=uuid4(), claim_id=claim.id, processing_run_id=processing_run_id,
                    signal_type=SignalType.ANOMALY,
                    severity=Severity.WARNING if high else Severity.INFO, score=score,
                    triggered_rules=["ml_anomaly_high"] if high else [],
                    evidence={"source": "ml", "feature_version": FEATURE_VERSION,
                              "features": dict(zip(FEATURE_NAMES, features, strict=True)),
                              "usable_history_count": len(prior),
                              "component_scores": {key: values[0] for key, values in components.items()},
                              "calibration_cutoff": self._bundle["cutoff"]},
                    detector_version=self._bundle["version"],
                    explanation=("Isolation Forest detected an unusual claim pattern; human review is required."
                                 if high else "Isolation Forest score is below the anomaly review threshold."),
                    created_at=datetime.now(UTC),
                )
            except Exception:
                reason = "prediction_failed"
        signal = RuleBasedAnomalyScorer().score(
            claim=claim, total=total, history=prior, processing_run_id=processing_run_id,
        )
        return signal.model_copy(update={
            "evidence": {**signal.evidence, "source": "rules_fallback", "reason": reason,
                         "feature_version": FEATURE_VERSION},
            "explanation": f"ML scoring unavailable ({reason}); rule-based scoring used. " + signal.explanation,
        })
