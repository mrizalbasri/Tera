"""Real CPU inference on generated synthetic receipts; no provider or database."""

import json
from datetime import UTC, datetime
from io import BytesIO
from statistics import median
from time import perf_counter
from uuid import uuid4

from PIL import Image, ImageDraw

from app.config import Settings
from app.integrations.local_ocr import OcrFirstReceiptExtractor, RapidOcrReader
from app.schemas.core import Receipt


def synthetic_receipt(variant: int) -> bytes:
    image = Image.new("RGB", (1000, 600), "white")
    draw = ImageDraw.Draw(image)
    rows = [
        "WARUNG SINTETIS", f"Tanggal: {datetime.now(UTC).date().isoformat()}",
        "Nasi ayam 2 x 25.000 50.000", "Teh manis 1 x 10.000 10.000",
        "TOTAL Rp 60.000", "Terima kasih",
    ]
    for index, row in enumerate(rows):
        draw.text((30, 30 + index * 80), row, fill="black", font_size=36)
    image.putpixel((999, 599), (variant, variant, variant))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    reader = RapidOcrReader()
    started = perf_counter()
    reader.ready()
    cold = perf_counter() - started

    def no_external_model():
        raise AssertionError("Synthetic clear receipt must not invoke an external model")

    extractor = OcrFirstReceiptExtractor(Settings(_env_file=None), reader, no_external_model)
    receipt = Receipt(
        id=uuid4(), claim_id=uuid4(), original_filename="synthetic.png",
        media_type="image/png", storage_reference="memory:synthetic",
        content_hash="a" * 64, created_at=datetime.now(UTC),
    )
    timings = []
    for variant in range(3):
        content = synthetic_receipt(variant)
        started = perf_counter()
        result = extractor.extract(
            receipt=receipt, content=content, declared_amount=None, attempt=1,
        )
        timings.append(perf_counter() - started)
        assert result.total.value == 60000
        assert len(result.line_items) == 2 and result.line_items_complete
        assert result.provider.startswith("rapidocr:")
    started = perf_counter()
    extractor.extract(receipt=receipt, content=content, declared_amount=None, attempt=2)
    cached = perf_counter() - started
    print(json.dumps({
        "passed": True, "scenario": "synthetic_receipt_only",
        "model_warmup_seconds": round(cold, 3),
        "warm_extraction_seconds": [round(value, 3) for value in timings],
        "warm_median_seconds": round(median(timings), 3),
        "cached_retry_seconds": round(cached, 6), "external_model_calls": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
