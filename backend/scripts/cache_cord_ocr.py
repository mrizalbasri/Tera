"""Run PaddleOCR locally on all extracted CORD test images; no LLM calls."""

import argparse
from collections import Counter
from datetime import UTC, datetime
import importlib.metadata
import json
import os
from pathlib import Path
import statistics
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/local/cord-v2-test"))
    args = parser.parse_args()
    base = args.dataset.resolve()
    cache = base.parent / "paddle-model-cache"
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache))
    os.environ.setdefault("HF_HOME", str(cache / "huggingface"))
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    from paddleocr import PaddleOCR

    started = time.monotonic()
    ocr = PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
        ocr_version="PP-OCRv5", device="cpu", cpu_threads=4, enable_mkldnn=False,
        use_doc_orientation_classify=False, use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    startup = time.monotonic() - started
    samples = json.loads((base / "manifest.json").read_text())["samples"]
    output = base / "ocr"
    output.mkdir(exist_ok=True)
    rows = []
    for sample in samples:
        path = output / f"{sample['id']}.json"
        if path.exists():
            rows.append(json.loads(path.read_text(encoding="utf-8")))
            continue
        begin = time.monotonic()
        row = {"id": sample["id"]}
        try:
            result = next(iter(ocr.predict(str(base / sample["image"]))))
            texts = list(result["rec_texts"])
            scores = [float(score) for score in result["rec_scores"]]
            boxes = result["rec_boxes"].tolist()
            row.update(status="success", text="\n".join(texts), lines=texts,
                       scores=scores, boxes=boxes)
        except Exception as exc:
            row.update(status="error", error_type=type(exc).__name__)
        row["duration_seconds"] = round(time.monotonic() - begin, 3)
        path.write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        rows.append(row)
        if len(rows) % 10 == 0:
            print(f"OCR {len(rows)}/{len(samples)}; success={sum(r['status'] == 'success' for r in rows)}", flush=True)
    durations = [r["duration_seconds"] for r in rows if r["status"] == "success"]
    report = {
        "dataset": "naver-clova-ix/cord-v2", "split": "test", "completed": len(rows),
        "paddleocr_version": importlib.metadata.version("paddleocr"),
        "paddlepaddle_version": importlib.metadata.version("paddlepaddle"),
        "models": ["PP-OCRv5_mobile_det", "latin_PP-OCRv5_mobile_rec"],
        "device": "cpu", "cpu_threads": 4, "enable_mkldnn": False,
        "startup_seconds_including_downloads": round(startup, 3),
        "successful_ocr": len(durations),
        "errors": dict(Counter(r.get("error_type") for r in rows if r["status"] != "success")),
        "mean_seconds": statistics.mean(durations) if durations else None,
        "median_seconds": statistics.median(durations) if durations else None,
        "finished_at": datetime.now(UTC).isoformat(),
        "limitations": ["OCR execution success does not establish text or extraction accuracy.",
                        "No vendor, date, item, or total extraction accuracy is claimed here.",
                        "Models are pretrained. CORD test labels are never used as OCR input or training data."],
    }
    (base / "ocr-summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
