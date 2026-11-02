# Local ML anomaly scoring (M7.6)

From `backend/`, using the project's virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.train_anomaly --verify --export-dataset data/local/anomaly/synthetic.jsonl
```

The command generates synthetic claim histories in memory, trains Isolation
Forests and evaluates independent synthetic employees. No application database,
receipt files, LLM, external service or model download is involved.

Outputs (ignored by Git):

- `backend/data/local/anomaly/model.joblib`: trained model bundle.
- `backend/data/local/anomaly/model.report.json`: precision, recall, false positive
  rate, confusion counts, scenario rates, model version and chosen threshold.
- `backend/data/local/anomaly/synthetic.jsonl`: optional feature rows with split
  and scenario labels, without employee identifiers or receipt text.

The default seed is 76. `--seed`, `--output`, `--threshold` and `--export-dataset`
are explicit CLI options. `--verify` checks prototype synthetic recall >=80%,
false positive rate <=10%, deterministic predictions and model reload parity.
Training/calibration use only normal cases; scenario labels never enter fitting.
See [[../superpowers/specs/2026-10-12-ml-anomaly-scoring-design|the implementation design]]
for feature definitions and calibration.

After successful training, set these in local `backend/.env` and restart the API:

```dotenv
ANOMALY_MODE=ml
ANOMALY_MODEL_PATH=./data/local/anomaly/model.joblib
ANOMALY_ESCALATION_THRESHOLD=0.7
```

Paths are relative to the backend working directory. Stop the API before replacing
the artifact. The scorer caches both successful loads and model-unavailable state
until restart. Use only artifacts produced by your trusted local CLI: joblib is
pickle-based and loading untrusted files can execute code. Compatible feature
schema and exact sklearn version are checked. Re-train after changing them.

To return to rule scoring, set `ANOMALY_MODE=rules` and restart. No migration is
required. Existing saved decisions retain their original model version and score.

The existing process endpoint invokes ML after extraction/policy checks. With
fewer than three comparable prior claims with usable declared amounts, the
result is neutral zero. A high score sends the claim to human review through the
existing decision engine. Model errors use visible rule fallback. Detail Signals
show numeric evidence and component scores; timeline entries show score, actual
detector version and source/reason. Category evidence is optional and restricted
to the existing five policy categories.

Scores are anomaly indices, not fraud probabilities. Benchmark metrics describe
only the generator's synthetic patterns. Validate thresholds against representative
reviewed claims before using ML for real operational decisions.

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_ml_anomaly.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

PostgreSQL integration tests still require `TEST_POSTGRES_URL` for disposable
databases. Never point test fixtures at the application database.

## Recorded local evaluation — 2026-10-12

Default seed 76, threshold 0.7, sklearn 1.9.1,
model `iforest-v1-ea480de7573b477c389d`:

| Measure | Synthetic result |
| --- | --- |
| Training / calibration normal cases | 1,200 / 400 |
| Independent test normal / anomalous cases | 400 / 400 |
| True positives / false negatives | 400 / 0 |
| False positives / true negatives | 5 / 395 |
| Precision | 98.77% |
| Recall | 100% |
| False positive rate | 1.25% |

Each anomalous scenario has 100 independent cases. These results are generator
smoke evidence; they do not estimate performance on real claims.

Local verification: `python -m pytest -q` completed with **391 passed, 24
skipped**. PostgreSQL/pgvector cases were skipped without `TEST_POSTGRES_URL`;
ML API persistence/restart was verified with isolated SQLite. `pnpm check`
reported zero errors/warnings and `pnpm build` passed.
