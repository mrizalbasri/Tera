"""Explicit offline training/evaluation: python -m app.train_anomaly --verify."""

import argparse
import json
from pathlib import Path

from app.integrations.ml_anomaly.features import FEATURE_NAMES, FEATURE_VERSION
from app.integrations.ml_anomaly.model import load_model, predict_scores, save_model, train_model
from app.integrations.ml_anomaly.synthetic import DATASET_VERSION, SCENARIOS, synthetic_cases


def train_and_evaluate(output: Path, *, seed: int = 76, threshold: float = 0.7,
                       verify: bool = False, export_dataset: Path | None = None) -> dict:
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be in (0, 1]")
    training = synthetic_cases(1200, seed=seed)
    calibration = synthetic_cases(400, seed=seed + 1)
    testing = synthetic_cases(400, seed=seed + 1002) + synthetic_cases(400, seed=seed + 1003, anomalies=True)
    bundle = train_model([case.features() for case in training], [case.features() for case in calibration])
    scores, _ = predict_scores(bundle, [case.features() for case in testing])
    predicted = [score >= threshold for score in scores]
    true_positive = sum(predicted[400:])
    false_positive = sum(predicted[:400])
    report = {
        "dataset_version": DATASET_VERSION, "model_version": bundle["version"],
        "feature_version": FEATURE_VERSION, "seed": seed, "threshold": threshold,
        "training_normal": len(training), "calibration_normal": len(calibration),
        "test_normal": 400, "test_anomalous": 400,
        "true_positive": true_positive, "false_positive": false_positive,
        "true_negative": 400 - false_positive, "false_negative": 400 - true_positive,
        "precision": true_positive / max(1, true_positive + false_positive),
        "recall": true_positive / 400, "false_positive_rate": false_positive / 400,
        "scenario_detection_rate": {
            scenario: sum(p for case, p in zip(testing, predicted, strict=True) if case.scenario == scenario)
            / sum(case.scenario == scenario for case in testing)
            for scenario in SCENARIOS
        },
        "limitation": "Synthetic benchmark only; not fraud probability or real-world accuracy.",
    }
    # Validate before replacing the current model; old artifact survives failed training.
    if verify:
        again, _ = predict_scores(bundle, [case.features() for case in testing])
        if scores != again or report["recall"] < 0.8 or report["false_positive_rate"] > 0.1:
            raise ValueError("synthetic verification failed; existing model was not replaced")
    save_model(bundle, output)
    if verify:
        restored, _ = predict_scores(load_model(output), [case.features() for case in testing])
        if restored != scores:
            raise ValueError("model reload verification failed")
    output.with_suffix(".report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if export_dataset is not None:
        export_dataset.parent.mkdir(parents=True, exist_ok=True)
        with export_dataset.open("w", encoding="utf-8") as stream:
            for split, cases in (("train", training), ("calibration", calibration), ("test", testing)):
                for case in cases:
                    # Feature rows only: no identities, receipt text or application records.
                    stream.write(json.dumps({"split": split, "scenario": case.scenario,
                                             "features": dict(zip(FEATURE_NAMES, case.features(), strict=True))}) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/local/anomaly/model.joblib"))
    parser.add_argument("--seed", type=int, default=76)
    parser.add_argument("--threshold", type=float, default=0.7)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--export-dataset", type=Path)
    args = parser.parse_args()
    report = train_and_evaluate(args.output, seed=args.seed, threshold=args.threshold,
                                verify=args.verify, export_dataset=args.export_dataset)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
