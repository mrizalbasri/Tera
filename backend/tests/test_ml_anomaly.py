from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import json
from uuid import uuid4

import joblib
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import deps
from app.config import Settings, get_settings
from app.integrations.anomaly import RuleBasedAnomalyScorer
from app.integrations.ml_anomaly.features import CategoryContext, FEATURE_NAMES, extract_features, prior_history
from app.integrations.ml_anomaly.model import load_model, normalized_score, predict_scores, save_model, train_model
from app.integrations.ml_anomaly.scorer import SklearnAnomalyScorer
from app.integrations.ml_anomaly.synthetic import synthetic_cases
from app.main import app
from app.services.decision import DecisionEngine
from app.train_anomaly import train_and_evaluate


@pytest.fixture(scope="module")
def model_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("anomaly") / "model.joblib"
    bundle = train_model([c.features() for c in synthetic_cases(1200, seed=76)],
                         [c.features() for c in synthetic_cases(400, seed=77)])
    save_model(bundle, path)
    return path


def score(scorer, case, **overrides):
    values = dict(claim=case.claim, total=case.claim.declared_amount, history=case.history,
                  context=case.context, processing_run_id=uuid4())
    values.update(overrides)
    return scorer.score_with_context(**values)


def test_features_are_shared_deterministic_and_ignore_unrelated_or_future_history():
    case = synthetic_cases(1, seed=101)[0]
    unrelated = case.history[0].model_copy(update={"id": uuid4(), "employee_id": "someone-else"})
    other_currency = case.history[0].model_copy(update={"id": uuid4(), "currency": "USD"})
    future = case.history[0].model_copy(update={"id": uuid4(), "submitted_at": case.claim.submitted_at + timedelta(days=1)})
    missing = case.history[0].model_copy(update={"id": uuid4(), "declared_amount": None})
    invalid = case.history[0].model_copy(update={"id": uuid4(), "declared_amount": Decimal("NaN")})
    history = [*reversed(case.history), case.claim, unrelated, other_currency, future, missing, invalid]
    assert extract_features(case.claim, case.claim.declared_amount, history, case.context) == case.features()
    assert len(prior_history(case.claim, history)) == len(case.history)
    assert len(case.features()) == len(FEATURE_NAMES)


def test_categories_change_features_without_free_text():
    case = synthetic_cases(2, seed=101)[1]
    unknown = CategoryContext("private vendor text", {p.id: "private text" for p in case.history})
    features = extract_features(case.claim, case.claim.declared_amount, case.history, unknown)
    assert features == extract_features(case.claim, case.claim.declared_amount, case.history)
    assert features[-1] == 0.5
    assert case.features()[-1] != features[-1]


def test_training_is_reproducible_and_data_changes_version():
    train = [c.features() for c in synthetic_cases(64, seed=41)]
    calibration = [c.features() for c in synthetic_cases(64, seed=42)]
    first = train_model(train, calibration)
    second = train_model(train, calibration)
    assert first["version"] == second["version"]
    assert predict_scores(first, calibration) == predict_scores(second, calibration)
    assert train_model(train[:-1], calibration)["version"] != first["version"]


def test_reload_and_concurrent_scoring_preserve_scores(model_path):
    scorer = SklearnAnomalyScorer(str(model_path))
    case = synthetic_cases(1, seed=103, anomalies=True)[0]
    expected = score(scorer, case)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: score(scorer, case), range(8)))
    results.append(score(SklearnAnomalyScorer(str(model_path)), case))
    assert all(s.score == expected.score and s.detector_version == expected.detector_version
               and s.evidence == expected.evidence for s in results)
    assert expected.detector_version.startswith("iforest-v1-")
    assert "synthetic-" not in json.dumps(expected.evidence)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_insufficient_history_is_neutral_even_without_model(tmp_path, count):
    case = synthetic_cases(1, seed=104)[0]
    signal = score(SklearnAnomalyScorer(str(tmp_path / "missing")), case, history=case.history[:count])
    assert signal.score == 0
    assert signal.triggered_rules == []
    assert signal.evidence["reason"] == "insufficient_history"


@pytest.mark.parametrize("kind", ["missing", "corrupt", "schema", "library", "nonfinite"])
def test_missing_or_incompatible_model_falls_back_visibly(tmp_path, model_path, kind):
    path = tmp_path / "model.joblib"
    if kind == "corrupt":
        path.write_bytes(b"invalid local model secret-api-key")
    elif kind != "missing":
        bundle = load_model(model_path)
        if kind == "schema":
            bundle["features"] = ("wrong",)
        elif kind == "library":
            bundle["sklearn_version"] = "0.0"
        else:
            bundle["cutoff"] = float("nan")
        joblib.dump(bundle, path)
    case = synthetic_cases(2, seed=105, anomalies=True)[1]
    actual = score(SklearnAnomalyScorer(str(path)), case)
    expected = RuleBasedAnomalyScorer().score(claim=case.claim, total=case.claim.declared_amount,
                                             history=case.history, processing_run_id=uuid4())
    assert actual.score == expected.score
    assert actual.detector_version == "rule-based-v1"
    assert actual.evidence["source"] == "rules_fallback"
    assert actual.evidence["reason"] == ("model_unavailable" if kind == "missing" else "model_invalid")
    assert "secret-api-key" not in actual.model_dump_json()
    assert str(path) not in actual.model_dump_json()


def test_prediction_failure_uses_rule_fallback(model_path, monkeypatch):
    scorer = SklearnAnomalyScorer(str(model_path))
    monkeypatch.setattr(scorer._bundle["model"], "score_samples", lambda _: [float("nan")])
    signal = score(scorer, synthetic_cases(1, seed=106, anomalies=True)[0])
    assert signal.evidence["reason"] == "prediction_failed"
    assert signal.detector_version == "rule-based-v1"


@pytest.mark.parametrize("raw", [float("nan"), float("inf"), -0.1, 1.1])
def test_nonfinite_predictions_are_rejected(raw):
    with pytest.raises(ValueError):
        normalized_score(raw, 0.6)


@pytest.mark.parametrize("value", [0, -0.1, 1.1, float("nan")])
def test_threshold_validation(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, anomaly_escalation_threshold=value)


@pytest.mark.parametrize("boundary,expected", [("0.69999999", "approved"), ("0.7", "escalated")])
def test_ml_and_rules_have_identical_decision_boundary(model_path, boundary, expected):
    case = synthetic_cases(1, seed=107)[0]
    ml = score(SklearnAnomalyScorer(str(model_path)), case).model_copy(update={"score": Decimal(boundary)})
    rules = ml.model_copy(update={"detector_version": "rule-based-v1"})
    engine = DecisionEngine(Settings(_env_file=None))
    for signal in (ml, rules):
        decision = engine.decide(claim=case.claim, total=Decimal("60000"), confidence=Decimal("0.96"),
                                 findings=[], evaluations=[], signals=[signal], policy_version=1,
                                 processing_run_id=uuid4())
        assert decision.outcome == expected


@pytest.mark.parametrize("storage", ["memory", "sqlite"])
def test_api_ml_escalation_persistence_timeline_and_replay(model_path, tmp_path, storage):
    settings = Settings(_env_file=None, anomaly_mode="ml", anomaly_model_path=str(model_path),
                        storage_backend="sql" if storage == "sqlite" else "memory",
                        database_url=f"sqlite:///{(tmp_path / 'claims.db').as_posix()}")
    app.dependency_overrides[get_settings] = lambda: settings
    # Frequency anomaly with amounts below the separate amount-escalation limit.
    case = synthetic_cases(2, seed=108, anomalies=True)[1]
    repositories = deps._backend(settings)
    # Use current API intake time; shift historical timestamps relative to it.
    from datetime import UTC, datetime
    delta = datetime.now(UTC) - case.claim.submitted_at
    for prior in case.history:
        repositories.claims.save(prior.model_copy(update={"submitted_at": prior.submitted_at + delta}))
    with TestClient(app) as client:
        created = client.post("/claims", data={"employee_id": case.claim.employee_id, "declared_amount": "60000"},
                              files={"files": ("synthetic.pdf", b"%PDF-1.7\nml-frequency\n%%EOF", "application/pdf")})
        assert created.status_code == 201, created.text
        claim_id = created.json()["claim"]["id"]
        result = client.post(f"/claims/{claim_id}/process")
        assert result.status_code == 200, result.text
        assert result.json()["decision"]["outcome"] == "escalated"
        assert "anomaly_score_high" in result.json()["decision"]["reason_codes"]
        detail = client.get(f"/claims/{claim_id}").json()
        anomaly = next(s for s in detail["signals"] if s["signal_type"] == "anomaly")
        assert anomaly["evidence"]["source"] == "ml"
        assert anomaly["detector_version"].startswith("iforest-v1-")
        timeline = client.get(f"/claims/{claim_id}/timeline").json()["items"]
        entry = next(e for e in timeline if e["step_name"] == "signal.anomaly")
        assert entry["detail"]["detector_version"] == anomaly["detector_version"]
        assert Decimal(entry["detail"]["score"]) >= Decimal("0.7")
        assert entry["detail"]["component_scores"] == anomaly["evidence"]["component_scores"]
        assert client.post(f"/claims/{claim_id}/process").json() == result.json()
        assert client.get("/reviews").json()["total"] == 1
    if storage == "sqlite":
        with TestClient(app) as restarted:
            assert restarted.get(f"/claims/{claim_id}").json()["signals"] == detail["signals"]
            assert restarted.post(f"/claims/{claim_id}/process").json() == result.json()


def test_training_cli_evaluates_separate_data_and_exports_features(tmp_path):
    output = tmp_path / "model.joblib"
    dataset = tmp_path / "synthetic.jsonl"
    report = train_and_evaluate(output, verify=True, export_dataset=dataset)
    assert report["recall"] >= 0.8
    assert report["false_positive_rate"] <= 0.1
    assert report["test_normal"] == report["test_anomalous"] == 400
    assert load_model(output)["version"] == report["model_version"]
    rows = [json.loads(line) for line in dataset.read_text().splitlines()]
    assert len(rows) == 2400
    assert {row["split"] for row in rows} == {"train", "calibration", "test"}
    assert all(set(row) == {"split", "scenario", "features"} for row in rows)
    assert json.loads(output.with_suffix(".report.json").read_text()) == report


def test_failed_training_preserves_existing_artifact(tmp_path):
    path = tmp_path / "model.joblib"
    path.write_bytes(b"existing model")
    with pytest.raises(ValueError, match="verification failed"):
        train_and_evaluate(path, verify=True, threshold=0.01)
    assert path.read_bytes() == b"existing model"


def test_dependency_defaults_to_rules_and_caches_ml(model_path):
    assert isinstance(deps.get_anomaly_scorer(Settings(_env_file=None, anomaly_mode="rules")), RuleBasedAnomalyScorer)
    settings = Settings(_env_file=None, anomaly_mode="ml", anomaly_model_path=str(model_path))
    assert deps.get_anomaly_scorer(settings) is deps.get_anomaly_scorer(settings)


def test_pipeline_uses_only_category_evidence_existing_before_claim(model_path):
    from app.integrations.mock import MockReceiptExtractor
    from app.schemas.core import Receipt

    case = synthetic_cases(1, seed=109)[0]
    repositories = deps._memory_repositories()
    for prior in case.history:
        repositories.claims.save(prior)
    prior = case.history[0]
    receipt = Receipt(id=uuid4(), claim_id=prior.id, original_filename="synthetic.pdf",
                      media_type="application/pdf", storage_reference="synthetic", content_hash="a" * 64,
                      created_at=prior.submitted_at)
    repositories.receipts.save(receipt)
    extraction = MockReceiptExtractor().extract(receipt=receipt, content=b"CATEGORY:MEALS",
                                                declared_amount=prior.declared_amount, attempt=1)
    repositories.extractions.save(extraction.model_copy(update={"created_at": prior.submitted_at}))
    repositories.extractions.save(extraction.model_copy(update={"id": uuid4(),
        "created_at": case.claim.submitted_at + timedelta(days=9999),
        "category": extraction.category.model_copy(update={"value": "hotel"})}))

    class CaptureScorer(SklearnAnomalyScorer):
        context = None

        def score_with_context(self, **kwargs):
            self.context = kwargs["context"]
            return super().score_with_context(**kwargs)

    scorer = CaptureScorer(str(model_path))
    app.dependency_overrides[deps.get_anomaly_scorer] = lambda: scorer
    try:
        with TestClient(app) as client:
            created = client.post("/claims", data={"employee_id": case.claim.employee_id, "declared_amount": "60000"},
                                  files={"files": ("synthetic.pdf", b"%PDF-1.7\nCATEGORY:MEALS\n%%EOF", "application/pdf")})
            claim_id = created.json()["claim"]["id"]
            assert client.post(f"/claims/{claim_id}/process").status_code == 200
            assert scorer.context.category == "meals"
            assert scorer.context.history_categories[prior.id] == "meals"
    finally:
        app.dependency_overrides.pop(deps.get_anomaly_scorer, None)
