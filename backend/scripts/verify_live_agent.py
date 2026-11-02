"""One live synthetic receipt through the full graph, with isolated memory storage."""

import argparse
import io
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import Settings
from app.errors import ApplicationError
from app.evaluate_agent import build_harness
from app.integrations.llm import LlmReceiptExtractor
from app.integrations.masking import SensitiveDataMasker
from app.integrations.policy_local import LocalPolicyRetriever
from app.services.intake import ReceiptUpload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/local/evaluation/live-agent.json"))
    args = parser.parse_args()
    configured = Settings()
    if not configured.llm_api_key or configured.llm_image_privacy_mode != "send":
        parser.error("A configured live key and image privacy mode send are required")
    settings = configured.model_copy(update={"environment": "test", "storage_backend": "memory", "demo_mode": False,
        "provider_mode": "live", "policy_mode": "local", "anomaly_mode": "rules", "provider_fallback": "none",
        "llm_max_retries": 0, "max_processing_retries": 0})
    image = Image.new("RGB", (900, 800), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=32)
    receipt_date = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    lines = ["SYNTHETIC TEST RECEIPT", "WARUNG UJI TERA", receipt_date, "", "Nasi makan siang  50.000",
             "Minuman          10.000", "SUBTOTAL Rp60.000", "PAJAK Rp0", "DISKON Rp0", "TOTAL IDR 60.000", "", "BUKAN TRANSAKSI NYATA"]
    for index, line in enumerate(lines):
        draw.text((40, 30 + index * 55), line, fill="black", font=font)
    content = io.BytesIO()
    image.save(content, format="PNG")
    extractor = LlmReceiptExtractor(settings, SensitiveDataMasker())
    db, resources, processing, intake = build_harness(settings, extractor, LocalPolicyRetriever())
    report = {"synthetic": True, "provider_mode": "live", "mock_fallback": False, "database": "isolated_memory",
              "evaluated_at": datetime.now(UTC).isoformat(), "model": settings.llm_model,
              "expected_total": "60000", "expected_status": "approved", "live_verified": False}
    started = time.perf_counter()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        claim, _, _ = intake.create_claim(employee_id="synthetic-live-test", currency="IDR", declared_amount=Decimal("60000"),
            files=[ReceiptUpload(filename="synthetic-live.png", media_type="image/png", content=content.getvalue())], idempotency_key=None)
        outcome = processing.process_claim(claim.id)
        total = str(outcome.extractions[-1].total.value) if outcome.extractions else None
        passed = outcome.claim.status == "approved" and total is not None and Decimal(total) == Decimal("60000")
        report.update(actual_status=outcome.claim.status, actual_total=total, live_verified=passed,
                      reason_codes=outcome.decision.reason_codes if outcome.decision else [],
                      policy_versions=sorted({e.policy_version for e in outcome.policy_evaluations}),
                      provider_calls=len(outcome.attempts),
                      provider_usage=db.runs.latest_for_claim(claim.id).provider_usage)
    except ApplicationError as exc:
        report.update(error_code=exc.code, http_status=exc.status_code)
    finally:
        resources.close()
    report["duration_ms"] = round((time.perf_counter() - started) * 1000)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["live_verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
