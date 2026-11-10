"""Local OCR boundary, bounded transient cache, and selective live-model routing."""

import hashlib
import logging
import math
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from threading import RLock
from uuid import uuid4

from PIL import Image, ImageDraw, ImageOps

from app.config import Settings
from app.domain.enums import ErrorClassification
from app.errors import ErrorCode, classified_error
from app.integrations.image_privacy import strip_image_metadata
from app.integrations.llm import LlmReceiptExtractor
from app.integrations.ocr_parser import OcrLine, parse_receipt
from app.schemas.core import ExtractedLineItem, ExtractionResult, FieldConfidence, Receipt

logger = logging.getLogger(__name__)


def group_ocr_rows(output) -> tuple[OcrLine, ...]:
    """Join same-row OCR boxes left-to-right without hiding low-confidence text."""
    if output.txts is None or output.boxes is None or output.scores is None:
        return ()
    tokens = []
    for box, text, score in zip(output.boxes, output.txts, output.scores, strict=True):
        if not text.strip():
            continue
        score = float(score)
        if not math.isfinite(score) or not 0 <= score <= 1:
            return ()
        xs, ys = [float(p[0]) for p in box], [float(p[1]) for p in box]
        tokens.append((sum(ys) / len(ys), min(xs), max(ys) - min(ys), text.strip(), score))
    if len(tokens) > 500:
        return ()
    rows: list[list[tuple]] = []
    for token in sorted(tokens):
        if rows and abs(token[0] - rows[-1][0][0]) <= min(token[2], rows[-1][0][2]) * 0.45:
            rows[-1].append(token)
        else:
            rows.append([token])
    return tuple(OcrLine(
        " ".join(token[3] for token in sorted(row, key=lambda token: token[1])),
        Decimal(str(min(token[4] for token in row))),
    ) for row in rows)


class RapidOcrReader:
    """One warmed CPU engine per process; no filesystem paths from receipt input."""

    def __init__(self, threads: int = 2) -> None:
        self._threads = threads
        self._engine = None
        self._lock = RLock()
        self._cache: OrderedDict[str, tuple[float, tuple[OcrLine, ...]]] = OrderedDict()

    def ready(self) -> None:
        with self._lock:
            if self._engine is not None:
                return
            import rapidocr
            from rapidocr import RapidOCR

            models = Path(rapidocr.__file__).parent / "models"
            paths = {
                "Det.model_path": models / "PP-OCRv6_det_small.onnx",
                "Cls.model_path": models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
                "Rec.model_path": models / "PP-OCRv6_rec_small.onnx",
            }
            if not all(path.is_file() for path in paths.values()):
                raise RuntimeError("Bundled RapidOCR models are missing; reinstall local OCR requirements.")
            engine = RapidOCR(params={
                **{key: str(path) for key, path in paths.items()},
                "Global.log_level": "error",
                "Global.text_score": 0.0,
                "Global.max_side_len": 2000,
                "EngineConfig.onnxruntime.intra_op_num_threads": self._threads,
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            })
            # Public inference API warms detection, classification AND recognition.
            warmup = Image.new("RGB", (640, 120), "white")
            ImageDraw.Draw(warmup).text((20, 30), "Tera OCR warmup 123", fill="black", font_size=32)
            buffer = BytesIO()
            warmup.save(buffer, format="PNG")
            result = engine(buffer.getvalue())
            if not result.txts:
                raise RuntimeError("RapidOCR warmup did not produce text.")
            self._engine = engine

    def read(self, content: bytes, media_type: str) -> tuple[OcrLine, ...]:
        key = hashlib.sha256(media_type.encode() + b"\0" + content).hexdigest()
        with self._lock:
            now = time.monotonic()
            for expired in [key for key, (stored, _) in self._cache.items() if now - stored >= 120]:
                del self._cache[expired]
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key][1]
            try:
                strip_image_metadata(content, media_type)  # full decode + pixel-count guard
                with Image.open(BytesIO(content)) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((2000, 2000))
                buffer = BytesIO()
                image.save(buffer, format="PNG")  # only pixels enter OCR
            except (ValueError, OSError) as exc:
                raise classified_error(
                    ErrorCode.IMAGE_SANITIZATION_FAILED, ErrorClassification.NON_RETRYABLE,
                    "Receipt image could not be decoded for local OCR.", 422,
                ) from exc
            try:
                self.ready()
                rows = group_ocr_rows(self._engine(buffer.getvalue()))
            except Exception as exc:
                # Library exceptions can contain input/model paths: never log their text.
                logger.warning("local OCR failed error_type=%s", type(exc).__name__)
                raise classified_error(
                    "local_ocr_unavailable", ErrorClassification.NON_RETRYABLE,
                    "Local receipt OCR is unavailable.", 503,
                ) from exc
            self._cache[key] = (time.monotonic(), rows)
            while len(self._cache) > 32:
                self._cache.popitem(last=False)
            return rows


class OcrFirstReceiptExtractor:
    provider_name = "rapidocr"

    def __init__(
        self, settings: Settings, reader: RapidOcrReader,
        fallback: Callable[[], LlmReceiptExtractor],
    ) -> None:
        self._settings, self._reader, self._fallback = settings, reader, fallback

    def extract(
        self, *, receipt: Receipt, content: bytes,
        declared_amount: Decimal | None, attempt: int,
    ) -> ExtractionResult:
        arguments = dict(receipt=receipt, content=content, declared_amount=declared_amount, attempt=attempt)
        if receipt.media_type not in {"image/jpeg", "image/png"}:
            return self._fallback().extract(**arguments)
        rows = self._reader.read(content, receipt.media_type)
        readable = bool(rows) and all(row.confidence >= Decimal(str(self._settings.ocr_min_confidence)) for row in rows)
        output = parse_receipt(rows) if readable else None
        if output is not None:
            def field(value):
                return FieldConfidence(value=value, confidence=output.confidence)

            return ExtractionResult(
                id=uuid4(), receipt_id=receipt.id, vendor=field(output.vendor),
                receipt_date=field(datetime.fromisoformat(output.receipt_date).date()),
                total=field(output.total), currency=field(output.currency), category=field(output.category),
                line_items=[ExtractedLineItem(**item.model_dump()) for item in output.line_items],
                line_items_complete=True, line_items_derived=False,
                subtotal=output.subtotal, tax=output.tax, discount=output.discount,
                provider=f"rapidocr:3.10.0:attempt-{attempt}", created_at=datetime.now(UTC),
            )
        if self._settings.llm_image_privacy_mode == "block":
            raise classified_error(
                ErrorCode.IMAGE_PRIVACY_BLOCKED, ErrorClassification.NON_RETRYABLE,
                "External receipt fallback is disabled by privacy policy.", 422,
            )
        text = "\n".join(row.text for row in rows)
        fallback = self._fallback()
        if readable and len(text) <= 20_000:
            return fallback.extract_text(
                receipt=receipt, text=text, declared_amount=declared_amount, attempt=attempt,
            )
        return fallback.extract(**arguments)
