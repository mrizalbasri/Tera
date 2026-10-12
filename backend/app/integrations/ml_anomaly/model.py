"""Trusted local model bundle, explicit version checks and atomic publication.

Joblib is pickle-based: only load files produced by the local training CLI.
This module never accepts an upload or a URL as a model source.
"""

from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
from re import fullmatch
import tempfile

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest

from app.integrations.ml_anomaly.features import FEATURE_NAMES, FEATURE_VERSION

MODEL_FORMAT = "isolation-forest-v1"
RANDOM_STATE = 76


def normalized_score(raw: float, cutoff: float) -> float:
    """Monotonic risk index, NOT a fraud probability. p99 normal maps to 0.7."""
    if not isfinite(raw) or not 0 <= raw <= 1 or not isfinite(cutoff) or not 0 < cutoff <= 1:
        raise ValueError("invalid anomaly prediction")
    return round(min(1.0, max(0.0, 0.7 + (raw - cutoff) / 0.15)), 8)


def predict_scores(bundle: dict, rows: list[tuple[float, ...]]) -> tuple[list[float], dict[str, list[float]]]:
    matrix = np.asarray(rows, dtype=np.float64)
    components = {"joint": [normalized_score(float(raw), bundle["cutoff"])
                            for raw in -bundle["model"].score_samples(matrix)]}
    # Per-feature forests avoid diluting a single strong behavioral anomaly
    # by averaging it with unrelated normal features in the joint forest.
    for index, model, cutoff, boundary in bundle["feature_models"]:
        values = []
        for value, raw in zip(matrix[:, index], -model.score_samples(matrix[:, [index]]), strict=True):
            score = normalized_score(float(raw), cutoff)
            tail = value < boundary if index == 4 else value > boundary
            # Discrete counts/repetition can tie the calibration cutoff for many
            # normal rows. Only the learned directional tail may reach 0.7.
            values.append(score if tail else min(score, 0.69999999))
        components[FEATURE_NAMES[index]] = values
    return [max(values) for values in zip(*components.values(), strict=True)], components


def train_model(training: list[tuple[float, ...]], calibration: list[tuple[float, ...]]) -> dict:
    matrix = np.asarray(training, dtype=np.float64)
    validation = np.asarray(calibration, dtype=np.float64)
    for values in (matrix, validation):
        if values.ndim != 2 or values.shape[1] != len(FEATURE_NAMES) or len(values) < 32 or not np.isfinite(values).all():
            raise ValueError("invalid training features")
    model = IsolationForest(n_estimators=128, max_samples=min(256, len(matrix)), contamination="auto",
                            random_state=RANDOM_STATE, n_jobs=1)
    model.fit(matrix)
    cutoff = float(np.quantile(-model.score_samples(validation), 0.99))
    feature_models = []
    for index in range(1, len(FEATURE_NAMES)):
        marginal = IsolationForest(n_estimators=128, max_samples=min(256, len(matrix)), contamination="auto",
                                   random_state=RANDOM_STATE, n_jobs=1)
        marginal.fit(matrix[:, [index]])
        boundary = float(np.quantile(-marginal.score_samples(validation[:, [index]]), 0.99))
        tail_boundary = float(np.quantile(validation[:, index], 0.01 if index == 4 else 0.99))
        feature_models.append((index, marginal, boundary, tail_boundary))
    identity = sha256(matrix.tobytes() + validation.tobytes() + json.dumps({
        "format": MODEL_FORMAT, "features": FEATURE_NAMES, "feature_version": FEATURE_VERSION,
        "sklearn": sklearn.__version__, "params": model.get_params(), "cutoff": cutoff,
        "aggregation": "max-joint-and-directional-marginal-v1",
        "marginal_cutoffs": [(c, b) for _, _, c, b in feature_models],
    }, sort_keys=True).encode()).hexdigest()[:20]
    return {"format": MODEL_FORMAT, "feature_version": FEATURE_VERSION,
            "features": FEATURE_NAMES, "sklearn_version": sklearn.__version__,
            "version": f"iforest-v1-{identity}", "model": model, "cutoff": cutoff,
            "feature_models": feature_models}


def save_model(bundle: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            joblib.dump(bundle, stream)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load_model(path: str | Path) -> dict:
    bundle = joblib.load(path)
    if not isinstance(bundle, dict) or (
        bundle.get("format") != MODEL_FORMAT
        or bundle.get("feature_version") != FEATURE_VERSION
        or tuple(bundle.get("features", ())) != FEATURE_NAMES
        or bundle.get("sklearn_version") != sklearn.__version__
        or not isinstance(bundle.get("model"), IsolationForest)
        or not isinstance(bundle.get("version"), str)
        or fullmatch(r"iforest-v1-[0-9a-f]{20}", bundle["version"]) is None
        or not isfinite(bundle.get("cutoff", float("nan")))
        or not 0 < bundle["cutoff"] <= 1
        or getattr(bundle["model"], "n_features_in_", None) != len(FEATURE_NAMES)
    ):
        raise ValueError("incompatible anomaly model")
    marginal = bundle.get("feature_models", [])
    if len(marginal) != len(FEATURE_NAMES) - 1:
        raise ValueError("missing feature models")
    for expected, (index, model, cutoff, boundary) in enumerate(marginal, start=1):
        if (index != expected or not isinstance(model, IsolationForest)
            or getattr(model, "n_features_in_", None) != 1 or not isfinite(cutoff) or not 0 < cutoff <= 1
            or not isfinite(boundary) or boundary < 0):
            raise ValueError("incompatible feature model")
    return bundle
